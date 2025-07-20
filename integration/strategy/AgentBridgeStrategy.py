"""Freqtrade strategy bridge consuming Redis signals for trading decisions."""

import logging
from pathlib import Path
import json
from typing import Dict, Any, Optional
from pandas import DataFrame

# Freqtrade imports
from freqtrade.strategy import IStrategy

# Integration imports
from integration.publish import fetch_latest_signal
from integration.schema.signal import TradingSignal

logger = logging.getLogger(__name__)


class AgentBridgeStrategy(IStrategy):
    """Freqtrade strategy that consumes TradingSignals from Redis."""
    
    INTERFACE_VERSION = 3
    timeframe = "5m"
    startup_candle_count = 50
    can_short = False

    # Simple stoploss placeholder (will override dynamically)
    stoploss = -0.99  # large so custom_stoploss handles actual

    minimal_roi = {
        "0": 10  # effectively ignore built-in ROI (use our custom exit)
    }

    def informative_pairs(self):
        """Return list of informative pairs."""
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: Dict[str, Any]) -> DataFrame:
        """Populate indicators - no indicators for MVP."""
        return dataframe

    def fetch_bridge_signal_file_based(self, pair: str) -> Optional[TradingSignal]:
        """Fetch signal from file-based approach (fallback for testing)."""
        try:
            signals_dir = Path("temp_signals")
            if not signals_dir.exists():
                return None
                
            # Look for recent signal files for this pair
            pair_pattern = pair.replace('/', '_')
            signal_files = list(signals_dir.glob(f"signal_{pair_pattern}_*.json"))
            
            if not signal_files:
                return None
                
            # Get the most recent signal file
            latest_file = max(signal_files, key=lambda f: f.stat().st_mtime)
            
            # Read and parse signal
            with open(latest_file, 'r') as f:
                signal_data = json.load(f)
                
            signal = TradingSignal(**signal_data)
            logger.info(f"Loaded file-based signal: {signal.decision_id} for {pair}")
            
            # Remove file after reading to prevent re-use
            latest_file.unlink()
            
            return signal
            
        except Exception as e:
            logger.warning(f"File-based signal fetch failed: {e}")
            return None

    def fetch_bridge_signal(self, pair: str):
        """Fetch latest signal from Redis for given pair, with file-based fallback."""
        try:
            # Try Redis first
            signal = fetch_latest_signal(pair)
            if signal:
                logger.info(f"Redis signal fetched: {signal.decision_id}")
                return signal
        except Exception as e:
            logger.warning(f"Redis signal fetch failed: {e}")
        
        # Fallback to file-based approach
        logger.info("Trying file-based signal fetch...")
        return self.fetch_bridge_signal_file_based(pair)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: Dict[str, Any]) -> DataFrame:
        """Populate entry signals based on Redis queue."""
        pair = metadata.get("pair")
        dataframe["enter_long"] = 0
        
        # Only act on the last row
        if len(dataframe) == 0:
            return dataframe
            
        signal = self.fetch_bridge_signal(pair)
        if signal:
            # Store risk params in last row custom columns for reference
            dataframe.loc[dataframe.index[-1], "enter_long"] = 1
            
            # Stash meta on the strategy (per run) keyed by pair
            if not hasattr(self, "_bridge_meta"):  # lazy init
                self._bridge_meta = {}
                
            self._bridge_meta[pair] = {
                "decision_id": signal.decision_id,
                "initial_stop": signal.risk.initial_stop,
                "tp1": signal.risk.take_profits[0].price,
                "tp2": signal.risk.take_profits[1].price,
                "timestamp": signal.timestamp
            }
            
            logger.info(f"Entry signal set for {pair}, decision_id: {signal.decision_id}")
            
        return dataframe

    def custom_stoploss(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs):
        """Dynamic stoploss based on stored signal parameters."""
        # Retrieve stored initial stop
        meta = getattr(self, "_bridge_meta", {}).get(pair)
        if not meta:
            return 1  # fallback no-op
            
        stop = meta["initial_stop"]
        entry_price = trade.open_rate
        if entry_price <= 0:
            return 1
            
        # Return stoploss as relative negative fraction
        distance = (stop / entry_price) - 1
        return distance  # negative value (Freqtrade expects)

    def custom_exit(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs):
        """Custom exit logic - full exit at TP1 for MVP."""
        meta = getattr(self, "_bridge_meta", {}).get(pair)
        if not meta:
            return None
            
        # Full exit at TP1 for MVP
        tp1 = meta["tp1"]
        if current_rate >= tp1:
            return "tp1_hit"
            
        return None 