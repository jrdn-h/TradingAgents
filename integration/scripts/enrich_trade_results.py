#!/usr/bin/env python3
"""Enrich trade results by inferring closed trades from decision log."""

from integration.logging_utils import load_decisions, load_trade_results, append_trade_result
from integration.data import get_candles
from datetime import datetime, timezone


def compute_r(entry, stop, exit_price, side):
    """Compute R-multiple for a trade."""
    if side == "long":
        return (exit_price - entry) / (entry - stop) if (entry - stop) > 0 else 0
    else:
        return (entry - exit_price) / (stop - entry) if (stop - entry) > 0 else 0


def main(symbol="BTC/USDT"):
    """Main enrichment function."""
    print("=== TRADE RESULTS ENRICHMENT ===")
    
    # Load existing data
    decisions = load_decisions()
    if not decisions:
        print("NO_DECISIONS")
        return
    
    print(f"Found {len(decisions)} decisions")
    
    # Index existing results by decision_id
    existing_results = load_trade_results()
    existing_ids = {r['decision_id'] for r in existing_results}
    
    print(f"Found {len(existing_results)} existing trade results")
    
    # Get current market data
    try:
        candles = get_candles(symbol, limit=50)
        last_close = candles[-1]['close']
        print(f"Current {symbol} price: {last_close}")
    except Exception as e:
        print(f"Error getting candles: {e}")
        return
    
    # Process each decision
    closed_inferred = 0
    open_trades = 0
    
    for decision in decisions:
        decision_id = decision['decision_id']
        
        # Skip if we already have a result for this decision
        if decision_id in existing_ids:
            continue
            
        # Parse decision data
        try:
            entry = float(decision['entry_price'])
            stop = float(decision['stop'])
            tp1 = float(decision['tp1'])
            tp2 = float(decision['tp2'])
            side = decision['side']
            symbol_from_decision = decision['symbol']
        except (KeyError, ValueError) as e:
            print(f"Error parsing decision {decision_id}: {e}")
            continue
        
        # Only process if symbol matches
        if symbol_from_decision != symbol:
            continue
            
        # Determine if trade closed based on current price
        exit_reason = None
        exit_price = None
        
        if side == "long":
            if last_close >= tp1:
                exit_reason = "tp1_inferred"
                exit_price = tp1
            elif last_close <= stop:
                exit_reason = "stop_inferred" 
                exit_price = stop
        elif side == "short":
            # Add short logic for future
            if last_close <= tp1:
                exit_reason = "tp1_inferred"
                exit_price = tp1
            elif last_close >= stop:
                exit_reason = "stop_inferred"
                exit_price = stop
                
        # If we inferred a closure, record it
        if exit_reason and exit_price:
            r_mult = compute_r(entry, stop, exit_price, side)
            
            try:
                append_trade_result(
                    decision_id, 
                    exit_price, 
                    r_mult, 
                    exit_reason,
                    datetime.now(timezone.utc).isoformat()
                )
                print(f"✅ Inferred closure: {decision_id} -> {exit_reason} @ {exit_price} (R={r_mult:.2f})")
                closed_inferred += 1
                
            except Exception as e:
                print(f"Error logging result for {decision_id}: {e}")
        else:
            print(f"⏳ Open trade: {decision_id} (entry={entry}, current={last_close})")
            open_trades += 1
    
    print(f"\n=== ENRICHMENT SUMMARY ===")
    print(f"INFERRED_CLOSED={closed_inferred}")
    print(f"OPEN_TRADES={open_trades}")
    print(f"EXISTING_RESULTS={len(existing_results)}")


if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTC/USDT"
    main(symbol) 