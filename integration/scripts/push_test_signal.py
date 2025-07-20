#!/usr/bin/env python3
"""Push a test signal for Freqtrade dry-run validation."""

import json
import os
from pathlib import Path
from integration.schema.signal import TradingSignal, RiskPlan, TakeProfit
from datetime import datetime, timezone

def push_test_signal_file_based():
    """Push test signal using file-based approach for dry-run validation."""
    
    # Create a realistic test signal
    signal = TradingSignal(
        symbol="BTC/USDT",
        side="long", 
        confidence=0.6,
        entry={"type": "market"},
        risk=RiskPlan(
            initial_stop=50000.0,
            take_profits=[
                TakeProfit(price=50500.0, size_pct=0.5),
                TakeProfit(price=51000.0, size_pct=0.5),
            ],
            max_capital_pct=0.05
        ),
        rationale="Injected test signal for dry-run validation"
    )
    
    # Create signals directory for file-based testing
    signals_dir = Path("temp_signals")
    signals_dir.mkdir(exist_ok=True)
    
    # Write signal to file with timestamp
    signal_file = signals_dir / f"signal_{signal.symbol.replace('/', '_')}_{int(datetime.now().timestamp())}.json"
    
    with open(signal_file, 'w') as f:
        json.dump(signal.model_dump(), f, indent=2)
    
    print(f"SIGNAL_WRITTEN: {signal_file}")
    print(f"PUBLISHED_DECISION_ID: {signal.decision_id}")
    print(f"SIGNAL_JSON: {signal.model_dump_json()}")
    
    return signal

def push_test_signal_redis():
    """Push test signal using Redis (if available)."""
    try:
        from integration.publish import publish_signal
        
        signal = TradingSignal(
            symbol="BTC/USDT", 
            side="long",
            confidence=0.6,
            entry={"type": "market"},
            risk=RiskPlan(
                initial_stop=50000.0,
                take_profits=[
                    TakeProfit(price=50500.0, size_pct=0.5),
                    TakeProfit(price=51000.0, size_pct=0.5),
                ],
                max_capital_pct=0.05
            ),
            rationale="Injected test signal for dry-run validation"
        )
        
        publish_signal(signal)
        print(f"REDIS_PUBLISHED_DECISION_ID: {signal.decision_id}")
        return signal
        
    except Exception as e:
        print(f"Redis not available: {e}")
        return None

def main():
    """Main function to push test signal."""
    print("=== PUSHING TEST SIGNAL FOR DRY-RUN VALIDATION ===")
    
    # Try Redis first, fall back to file-based
    signal = push_test_signal_redis()
    
    if signal is None:
        print("Falling back to file-based signal injection...")
        signal = push_test_signal_file_based()
    
    print(f"Test signal ready for symbol: {signal.symbol}")
    print(f"Entry: market, Stop: {signal.risk.initial_stop}, TP1: {signal.risk.take_profits[0].price}")

if __name__ == "__main__":
    main() 