#!/usr/bin/env python3
"""Latency measurement script for end-to-end trading cycle performance."""

import time
import json
import statistics
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple

# Import pipeline components
from integration.config.config import load_config, Config, RiskSettings, RISK_DEFAULT
from integration.data import get_candles
from integration.signal_gen import generate_signal
from integration.risk import apply_risk
from integration.publish import publish_signal
from integration.logging_utils import append_decision


def measure_once(symbol: str, use_preview_fallback: bool = False) -> Tuple[str, Dict[str, float]]:
    """Execute one complete trading cycle with timing instrumentation.
    
    Args:
        symbol: Trading symbol to process
        use_preview_fallback: Use fallback config if env vars missing
        
    Returns:
        Tuple of (status, timing_stamps) where timing_stamps contains stage timings
    """
    stamps = {}
    
    # Stage 1: Start timing
    t0 = time.perf_counter()
    
    # Stage 2: Load configuration
    try:
        cfg = load_config()
    except RuntimeError as e:
        if use_preview_fallback and "Missing required environment variables" in str(e):
            # Provide sensible defaults for latency testing
            cfg = Config(
                symbol="BTC/USDT",
                timeframe="5m", 
                max_capital_pct=0.05,
                model_name="latency-test",
                risk=RiskSettings(**RISK_DEFAULT)
            )
        else:
            raise
    
    stamps['config_loaded'] = time.perf_counter()
    
    # Stage 3: Fetch market data
    candles = get_candles(symbol, limit=250)
    stamps['candles_fetched'] = time.perf_counter()
    
    # Stage 4: Generate signal
    raw_signal = generate_signal(symbol, limit=250)
    stamps['signal_generated'] = time.perf_counter()
    
    status = 'no_trade'
    
    if raw_signal:
        # Stage 5: Apply risk filters
        risked = apply_risk(raw_signal, candles, {
            "risk": {
                "min_atr_multiple": cfg.risk.min_atr_multiple,
                "max_atr_multiple": cfg.risk.max_atr_multiple,
                "min_rr": cfg.risk.min_rr
            },
            "max_capital_pct": cfg.max_capital_pct
        })
        stamps['risk_applied'] = time.perf_counter()
        
        if risked:
            # Stage 6: Publish and log
            entry_price = candles[-1]["close"]
            
            try:
                publish_signal(risked)
                append_decision(risked, entry_price=entry_price)
                status = 'published'
            except Exception as e:
                # If Redis/logging fails, mark as filtered but continue timing
                print(f"Warning: Publish/log failed: {e}")
                status = 'publish_failed'
            
            stamps['published_logged'] = time.perf_counter()
        else:
            status = 'filtered'
            stamps['published_logged'] = stamps['risk_applied']
    else:
        # No signal generated - mark remaining stages with same timestamp
        stamps['risk_applied'] = stamps['signal_generated']
        stamps['published_logged'] = stamps['signal_generated']
    
    # Stage 7: End timing
    t_end = time.perf_counter()
    stamps['total'] = t_end - t0
    
    # Calculate stage durations
    stage_durations = {
        'config_load_duration': stamps['config_loaded'] - t0,
        'candles_fetch_duration': stamps['candles_fetched'] - stamps['config_loaded'],
        'signal_gen_duration': stamps['signal_generated'] - stamps['candles_fetched'],
        'risk_apply_duration': stamps['risk_applied'] - stamps['signal_generated'],
        'publish_log_duration': stamps['published_logged'] - stamps['risk_applied'],
        'total_duration': stamps['total']
    }
    
    # Merge absolute timestamps and durations
    timing_data = {**stamps, **stage_durations}
    
    return status, timing_data


def run_latency_measurement(symbol: str, cycles: int, use_preview_fallback: bool = False) -> Dict:
    """Run multiple measurement cycles and aggregate results.
    
    Args:
        symbol: Trading symbol to test
        cycles: Number of cycles to run
        use_preview_fallback: Use fallback config if env vars missing
        
    Returns:
        Dict containing aggregated latency metrics
    """
    print(f"=== LATENCY MEASUREMENT: {cycles} cycles for {symbol} ===")
    
    results = []
    status_counts = {'no_trade': 0, 'filtered': 0, 'published': 0, 'publish_failed': 0}
    
    for cycle in range(cycles):
        print(f"Cycle {cycle + 1}/{cycles}...", end=' ')
        
        try:
            status, timing_data = measure_once(symbol, use_preview_fallback)
            status_counts[status] += 1
            results.append({
                'cycle': cycle + 1,
                'status': status,
                'timing': timing_data
            })
            print(f"{status} ({timing_data['total_duration']:.3f}s)")
            
        except Exception as e:
            print(f"ERROR: {e}")
            status_counts['publish_failed'] += 1
            # Continue with other cycles
    
    if not results:
        raise RuntimeError("No successful cycles completed")
    
    # Aggregate timing metrics
    total_times = [r['timing']['total_duration'] for r in results]
    config_times = [r['timing']['config_load_duration'] for r in results]
    candles_times = [r['timing']['candles_fetch_duration'] for r in results]
    signal_times = [r['timing']['signal_gen_duration'] for r in results]
    risk_times = [r['timing']['risk_apply_duration'] for r in results]
    publish_times = [r['timing']['publish_log_duration'] for r in results]
    
    # Calculate statistics
    metrics = {
        'measurement_info': {
            'symbol': symbol,
            'cycles_requested': cycles,
            'cycles_completed': len(results),
            'timestamp': datetime.now(timezone.utc).isoformat()
        },
        'status_counts': status_counts,
        'timing_stats': {
            'total': {
                'avg': statistics.mean(total_times),
                'median': statistics.median(total_times),
                'min': min(total_times),
                'max': max(total_times),
                'p95': sorted(total_times)[int(0.95 * len(total_times))] if len(total_times) > 1 else total_times[0]
            },
            'stages': {
                'config_load': {
                    'avg': statistics.mean(config_times),
                    'max': max(config_times)
                },
                'candles_fetch': {
                    'avg': statistics.mean(candles_times),
                    'max': max(candles_times)
                },
                'signal_generation': {
                    'avg': statistics.mean(signal_times),
                    'max': max(signal_times)
                },
                'risk_application': {
                    'avg': statistics.mean(risk_times),
                    'max': max(risk_times)
                },
                'publish_logging': {
                    'avg': statistics.mean(publish_times),
                    'max': max(publish_times)
                }
            }
        },
        'gate_criteria': {
            'avg_total_time_sec': statistics.mean(total_times),
            'p95_total_time_sec': sorted(total_times)[int(0.95 * len(total_times))] if len(total_times) > 1 else total_times[0],
            'avg_under_3sec': statistics.mean(total_times) < 3.0,
            'p95_under_3_5sec': (sorted(total_times)[int(0.95 * len(total_times))] if len(total_times) > 1 else total_times[0]) < 3.5,
            'gate_pass': (
                statistics.mean(total_times) < 3.0 and 
                (sorted(total_times)[int(0.95 * len(total_times))] if len(total_times) > 1 else total_times[0]) < 3.5
            )
        },
        'raw_results': results
    }
    
    return metrics


def main():
    """CLI entry point for latency measurement."""
    parser = argparse.ArgumentParser(description="Measure end-to-end trading cycle latency.")
    parser.add_argument("--symbol", default=None, help="Trading symbol (default from config)")
    parser.add_argument("--cycles", type=int, default=10, help="Number of cycles to run")
    parser.add_argument("--json-out", default="decision_logs/latency_metrics.json", 
                       help="Output file for metrics JSON")
    parser.add_argument("--preview-fallback", action="store_true",
                       help="Use fallback config if env vars missing")
    
    args = parser.parse_args()
    
    # Determine symbol
    if args.symbol:
        symbol = args.symbol.upper()
    else:
        try:
            cfg = load_config()
            symbol = cfg.symbol
        except RuntimeError:
            if args.preview_fallback:
                symbol = "BTC/USDT"
            else:
                print("Error: Could not load config. Use --symbol or --preview-fallback")
                return 1
    
    # Run measurement
    try:
        metrics = run_latency_measurement(symbol, args.cycles, args.preview_fallback)
        
        # Save to file
        output_path = Path(args.json_out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"\n=== LATENCY MEASUREMENT RESULTS ===")
        print(f"Average total time: {metrics['gate_criteria']['avg_total_time_sec']:.3f}s")
        print(f"P95 total time: {metrics['gate_criteria']['p95_total_time_sec']:.3f}s")
        print(f"Published cycles: {metrics['status_counts']['published']}")
        print(f"Gate pass: {metrics['gate_criteria']['gate_pass']}")
        print(f"Metrics saved to: {output_path}")
        
        # Print summary JSON
        print(f"\n=== SUMMARY JSON ===")
        summary = {
            "avg_total_time_sec": metrics['gate_criteria']['avg_total_time_sec'],
            "p95_total_time_sec": metrics['gate_criteria']['p95_total_time_sec'],
            "published_count": metrics['status_counts']['published'],
            "gate_pass": metrics['gate_criteria']['gate_pass']
        }
        print(json.dumps(summary, indent=2))
        
        return 0 if metrics['gate_criteria']['gate_pass'] else 1
        
    except Exception as e:
        print(f"Error during measurement: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 