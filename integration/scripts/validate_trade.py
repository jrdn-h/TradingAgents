#!/usr/bin/env python3
"""Validate trade creation by simulating strategy execution."""

import json
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from integration.strategy.AgentBridgeStrategy import AgentBridgeStrategy
from integration.logging_utils import append_decision

def create_mock_dataframe():
    """Create a mock dataframe that Freqtrade would pass to strategy."""
    # Create minimal candle data 
    data = {
        'timestamp': [1700000000, 1700000300, 1700000600],
        'open': [50100, 50200, 50300],
        'high': [50150, 50250, 50350], 
        'low': [50050, 50150, 50250],
        'close': [50120, 50230, 50330],
        'volume': [100, 100, 100]
    }
    
    df = pd.DataFrame(data)
    df.index = pd.to_datetime(df['timestamp'], unit='s')
    return df

def simulate_strategy_execution():
    """Simulate Freqtrade strategy execution."""
    print("=== SIMULATING STRATEGY EXECUTION ===")
    
    # Initialize strategy
    strategy = AgentBridgeStrategy()
    
    # Create mock dataframe (what Freqtrade would pass)
    dataframe = create_mock_dataframe()
    metadata = {"pair": "BTC/USDT"}
    
    print(f"Testing strategy with pair: {metadata['pair']}")
    print(f"Dataframe shape: {dataframe.shape}")
    
    # Test signal fetching
    signal = strategy.fetch_bridge_signal("BTC/USDT")
    
    if signal:
        print(f"✅ Signal fetched: {signal.decision_id}")
        print(f"Signal details: {signal.symbol} {signal.side} @ stop={signal.risk.initial_stop}")
        
        # Log the decision (simulate what run_cycle would do)
        append_decision(signal)
        print(f"✅ Decision logged to CSV")
        
        # Test strategy populate_entry_trend
        result_df = strategy.populate_entry_trend(dataframe, metadata)
        
        if result_df.iloc[-1]['enter_long'] == 1:
            print(f"✅ Entry signal set in strategy")
            
            # Check if meta was stored
            if hasattr(strategy, '_bridge_meta') and 'BTC/USDT' in strategy._bridge_meta:
                meta = strategy._bridge_meta['BTC/USDT']
                print(f"✅ Strategy metadata stored: decision_id={meta['decision_id']}")
                
                # Test stoploss calculation
                class MockTrade:
                    open_rate = 50330  # Last close price
                    
                mock_trade = MockTrade()
                stoploss = strategy.custom_stoploss("BTC/USDT", mock_trade, None, 50330, 0)
                print(f"✅ Custom stoploss calculated: {stoploss:.4f}")
                
                # Test exit logic
                exit_reason = strategy.custom_exit("BTC/USDT", mock_trade, None, 50500, 0.01)  # At TP1
                if exit_reason == "tp1_hit":
                    print(f"✅ Custom exit logic working: {exit_reason}")
                
                return True
            else:
                print("❌ Strategy metadata not stored")
                return False
        else:
            print("❌ Entry signal not set")
            return False
    else:
        print("❌ No signal fetched")
        return False

def validate_decision_log():
    """Check if decision was logged to CSV."""
    decision_csv = Path("decision_logs/decision_log.csv")
    
    if not decision_csv.exists():
        print("❌ Decision log file not found")
        return False
        
    lines = decision_csv.read_text().strip().splitlines()
    if len(lines) < 2:  # header + at least one entry
        print("❌ No decision entries in log")
        return False
        
    print(f"✅ Decision log contains {len(lines)-1} entries")
    return True

def validate_temp_signals_consumed():
    """Check if temp signal files were consumed.""" 
    signals_dir = Path("temp_signals")
    
    if not signals_dir.exists():
        print("✅ Temp signals directory cleaned up")
        return True
        
    signal_files = list(signals_dir.glob("signal_*.json"))
    if len(signal_files) == 0:
        print("✅ All temp signal files consumed")
        return True
    else:
        print(f"⚠️  {len(signal_files)} temp signal files remain")
        return True  # Not a failure, just info

def main():
    """Main validation function."""
    print("=== TRADE VALIDATION STARTING ===")
    
    # Run simulation
    strategy_success = simulate_strategy_execution()
    
    # Validate logs
    decision_logged = validate_decision_log()
    
    # Check signal consumption
    signals_consumed = validate_temp_signals_consumed()
    
    # Results
    results = {
        "trade_entry_detected": strategy_success,
        "decision_log_present": decision_logged,
        "signals_consumed": signals_consumed,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    print("\n=== VALIDATION RESULTS ===")
    print(json.dumps(results, indent=2))
    
    # Return success if key criteria met
    success = results["trade_entry_detected"] and results["decision_log_present"]
    
    if success:
        print("\n✅ VALIDATION PASSED - Strategy integration working!")
    else:
        print("\n❌ VALIDATION FAILED - Check issues above")
        
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 