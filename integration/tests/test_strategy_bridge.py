"""Unit tests for AgentBridgeStrategy."""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import sys

# Mock freqtrade modules before importing strategy
mock_freqtrade = MagicMock()
mock_freqtrade.strategy = MagicMock()
mock_freqtrade.strategy.interface = MagicMock()

# Create a mock IStrategy class
class MockIStrategy:
    pass

mock_freqtrade.strategy.interface.IStrategy = MockIStrategy
sys.modules['freqtrade'] = mock_freqtrade
sys.modules['freqtrade.strategy'] = mock_freqtrade.strategy
sys.modules['freqtrade.strategy.interface'] = mock_freqtrade.strategy.interface

from integration.strategy.AgentBridgeStrategy import AgentBridgeStrategy
from integration.schema.signal import TradingSignal, RiskPlan, TakeProfit


class TestAgentBridgeStrategy:
    """Test cases for AgentBridgeStrategy."""
    
    def create_test_signal(self, symbol="BTC/USDT"):
        """Create a test TradingSignal for mocking."""
        return TradingSignal(
            decision_id="test_bridge_123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            side="long",
            confidence=0.8,
            entry={"type": "market"},
            risk=RiskPlan(
                initial_stop=48000.0,
                take_profits=[
                    TakeProfit(price=52000.0, size_pct=0.5),
                    TakeProfit(price=54000.0, size_pct=0.5)
                ],
                max_capital_pct=0.03
            ),
            rationale="Test breakout signal"
        )
    
    def create_test_dataframe(self, num_candles=60):
        """Create a dummy DataFrame with required OHLCV columns."""
        base_price = 50000.0
        data = []
        
        for i in range(num_candles):
            price = base_price + i * 10  # slight uptrend
            candle = {
                "open": price,
                "high": price + 100,
                "low": price - 100,
                "close": price + 50,
                "volume": 1000 + i
            }
            data.append(candle)
            
        return pd.DataFrame(data)
    
    def test_populate_entry_trend_with_signal(self):
        """Test that entry flag is set when signal is available."""
        strategy = AgentBridgeStrategy()
        test_signal = self.create_test_signal()
        df = self.create_test_dataframe()
        metadata = {"pair": "BTC/USDT"}
        
        with patch('integration.strategy.AgentBridgeStrategy.fetch_latest_signal', return_value=test_signal):
            result_df = strategy.populate_entry_trend(df, metadata)
            
            # Check that enter_long flag is set on last row
            assert result_df["enter_long"].iloc[-1] == 1
            assert result_df["enter_long"].iloc[-2] == 0  # previous rows should be 0
            
            # Check that metadata is stored
            assert hasattr(strategy, "_bridge_meta")
            assert "BTC/USDT" in strategy._bridge_meta
            meta = strategy._bridge_meta["BTC/USDT"]
            assert meta["decision_id"] == "test_bridge_123"
            assert meta["initial_stop"] == 48000.0
            assert meta["tp1"] == 52000.0
            assert meta["tp2"] == 54000.0
    
    def test_populate_entry_trend_no_signal(self):
        """Test that no entry flag is set when no signal available."""
        strategy = AgentBridgeStrategy()
        df = self.create_test_dataframe()
        metadata = {"pair": "BTC/USDT"}
        
        with patch('integration.strategy.AgentBridgeStrategy.fetch_latest_signal', return_value=None):
            result_df = strategy.populate_entry_trend(df, metadata)
            
            # Check that no enter_long flags are set
            assert (result_df["enter_long"] == 0).all()
            
            # Check that no metadata is stored
            assert not hasattr(strategy, "_bridge_meta") or "BTC/USDT" not in getattr(strategy, "_bridge_meta", {})
    
    def test_populate_entry_trend_empty_dataframe(self):
        """Test handling of empty dataframe."""
        strategy = AgentBridgeStrategy()
        df = pd.DataFrame()
        metadata = {"pair": "BTC/USDT"}
        
        result_df = strategy.populate_entry_trend(df, metadata)
        
        # Should return empty dataframe without errors
        assert len(result_df) == 0
    
    def test_custom_stoploss_calculation(self):
        """Test dynamic stoploss calculation based on stored signal."""
        strategy = AgentBridgeStrategy()
        
        # Setup mock metadata
        strategy._bridge_meta = {
            "BTC/USDT": {
                "initial_stop": 48000.0,
                "tp1": 52000.0,
                "tp2": 54000.0
            }
        }
        
        # Mock trade object
        mock_trade = MagicMock()
        mock_trade.open_rate = 50000.0  # entry price
        
        stoploss = strategy.custom_stoploss(
            pair="BTC/USDT",
            trade=mock_trade,
            current_time=datetime.now(),
            current_rate=49000.0,
            current_profit=-0.02
        )
        
        # Expected: (48000 / 50000) - 1 = -0.04 (4% stop)
        expected_stoploss = (48000.0 / 50000.0) - 1
        assert abs(stoploss - expected_stoploss) < 1e-6
        assert stoploss < 0  # Should be negative for Freqtrade
    
    def test_custom_stoploss_no_metadata(self):
        """Test stoploss fallback when no metadata available."""
        strategy = AgentBridgeStrategy()
        mock_trade = MagicMock()
        mock_trade.open_rate = 50000.0
        
        stoploss = strategy.custom_stoploss(
            pair="BTC/USDT",
            trade=mock_trade,
            current_time=datetime.now(),
            current_rate=49000.0,
            current_profit=-0.02
        )
        
        # Should return 1 as fallback (no-op)
        assert stoploss == 1
    
    def test_custom_stoploss_invalid_entry_price(self):
        """Test stoploss handling with invalid entry price."""
        strategy = AgentBridgeStrategy()
        strategy._bridge_meta = {
            "BTC/USDT": {"initial_stop": 48000.0}
        }
        
        mock_trade = MagicMock()
        mock_trade.open_rate = 0  # invalid entry price
        
        stoploss = strategy.custom_stoploss(
            pair="BTC/USDT",
            trade=mock_trade,
            current_time=datetime.now(),
            current_rate=49000.0,
            current_profit=0
        )
        
        # Should return 1 as fallback
        assert stoploss == 1
    
    def test_custom_exit_tp1_not_hit(self):
        """Test custom exit when TP1 not reached."""
        strategy = AgentBridgeStrategy()
        strategy._bridge_meta = {
            "BTC/USDT": {
                "tp1": 52000.0,
                "tp2": 54000.0
            }
        }
        
        mock_trade = MagicMock()
        
        exit_signal = strategy.custom_exit(
            pair="BTC/USDT",
            trade=mock_trade,
            current_time=datetime.now(),
            current_rate=51000.0,  # below TP1
            current_profit=0.02
        )
        
        # Should return None (no exit)
        assert exit_signal is None
    
    def test_custom_exit_tp1_hit(self):
        """Test custom exit when TP1 is reached."""
        strategy = AgentBridgeStrategy()
        strategy._bridge_meta = {
            "BTC/USDT": {
                "tp1": 52000.0,
                "tp2": 54000.0
            }
        }
        
        mock_trade = MagicMock()
        
        exit_signal = strategy.custom_exit(
            pair="BTC/USDT",
            trade=mock_trade,
            current_time=datetime.now(),
            current_rate=52500.0,  # above TP1
            current_profit=0.05
        )
        
        # Should return "tp1_hit"
        assert exit_signal == "tp1_hit"
    
    def test_custom_exit_no_metadata(self):
        """Test custom exit when no metadata available."""
        strategy = AgentBridgeStrategy()
        mock_trade = MagicMock()
        
        exit_signal = strategy.custom_exit(
            pair="BTC/USDT",
            trade=mock_trade,
            current_time=datetime.now(),
            current_rate=52000.0,
            current_profit=0.04
        )
        
        # Should return None (no exit)
        assert exit_signal is None
    
    def test_strategy_configuration(self):
        """Test basic strategy configuration."""
        strategy = AgentBridgeStrategy()
        
        assert strategy.timeframe == "5m"
        assert strategy.startup_candle_count == 50
        assert strategy.can_short is False
        assert strategy.stoploss == -0.99
        assert strategy.minimal_roi == {"0": 10}
        assert strategy.informative_pairs() == []
    
    def test_populate_indicators_passthrough(self):
        """Test that populate_indicators passes dataframe through unchanged."""
        strategy = AgentBridgeStrategy()
        df = self.create_test_dataframe()
        metadata = {"pair": "BTC/USDT"}
        
        result_df = strategy.populate_indicators(df, metadata)
        
        # Should return the same dataframe
        pd.testing.assert_frame_equal(result_df, df) 