"""End-to-end trading cycle script that orchestrates the complete pipeline."""

from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from integration.config.config import load_config
from integration.signal_gen import generate_signal
from integration.data import get_candles, compute_atr
from integration.risk import apply_risk
from integration.publish import publish_signal
from integration.logging_utils import append_decision
from integration.schema.signal import TradingSignal


def run_cycle(symbol_override: str | None = None, preview: bool = False) -> dict:
    """Execute one complete trading cycle: config→data→signal→risk→publish/log.
    
    Args:
        symbol_override: Override the default symbol from config
        preview: If True, skip publication and logging (dry-run mode)
        
    Returns:
        Dict containing cycle status and results
    """
    # Load configuration
    cfg = load_config()
    symbol = (symbol_override or cfg.symbol).upper()
    
    # Fetch market data
    candles = get_candles(symbol, limit=250)
    
    # Generate raw signal
    raw_signal = generate_signal(candles)
    if not raw_signal:
        return {
            "status": "no_trade",
            "symbol": symbol,
            "reason": "no_breakout",
            "candles": len(candles)
        }
    
    # Apply risk filters
    risked = apply_risk(raw_signal, candles, {
        "risk": {
            "min_atr_multiple": cfg.risk.min_atr_multiple,
            "max_atr_multiple": cfg.risk.max_atr_multiple,
            "min_rr": cfg.risk.min_rr
        },
        "max_capital_pct": cfg.max_capital_pct
    })
    
    if not risked:
        return {
            "status": "filtered",
            "symbol": symbol,
            "reason": "risk_gate_reject",
            "decision_id": raw_signal.decision_id
        }
    
    # Publish signal and log decision
    entry_price = candles[-1]["close"]
    
    if not preview:
        publish_signal(risked)
        append_decision(risked, entry_price=entry_price)
    
    return {
        "status": "published" if not preview else "preview",
        "symbol": symbol,
        "decision_id": risked.decision_id,
        "entry_price": entry_price,
        "stop": risked.risk.initial_stop,
        "tp1": risked.risk.take_profits[0].price,
        "tp2": risked.risk.take_profits[1].price
    }


def main():
    """CLI entry point for run cycle script."""
    parser = argparse.ArgumentParser(description="Run one trading agent cycle.")
    parser.add_argument("--symbol", help="Override default symbol", default=None)
    parser.add_argument("--preview", action="store_true", 
                       help="Do not publish/log, just compute.")
    
    args = parser.parse_args()
    result = run_cycle(symbol_override=args.symbol, preview=args.preview)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main() 