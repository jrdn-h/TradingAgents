import argparse
import logging
import sys
import asyncio
import json
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import os

from tradingagents.graph.orchestrator import Orchestrator
from tradingagents.config import setup_logging

def run_demo(symbol: str, log_level: str = "INFO", live: bool = False):
    setup_logging(log_level)
    orchestrator = Orchestrator()
    orchestrator.run(symbol=symbol, live=live)

def run_replay(start_date: str, end_date: str, symbol: str, tweets_csv: str = None, plot: bool = False):
    """Run historical replay with sentiment correlation analysis."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔄 Starting historical replay: {symbol} from {start_date} to {end_date}")
    
    try:
        # Import here to avoid circular imports
        from tradingagents.backtest.replay_runner import ReplayRunner
        
        runner = ReplayRunner()
        asyncio.run(runner.run_replay(
            start_date=start_date,
            end_date=end_date, 
            symbol=symbol,
            tweets_csv=tweets_csv,
            plot=plot
        ))
        
        logger.info("✅ Replay completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Replay failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def main():
    parser = argparse.ArgumentParser(description="TradingAgents CLI")
    parser.add_argument("--log-level", type=str, default="INFO", help="Set log level (default: INFO)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run-demo command
    demo_parser = subparsers.add_parser("run-demo", help="Run orchestrator demo")
    demo_parser.add_argument("--symbol", type=str, default="BTCUSD", help="Symbol to trade (default: BTCUSD)")
    demo_parser.add_argument("--live", action="store_true", help="Use live Hyperliquid price feed (default: mock prices)")

    # dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Start FastAPI dashboard")
    dashboard_parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    dashboard_parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    dashboard_parser.add_argument("--source", type=str, choices=["demo", "twikit"], default="demo", help="Tweet source (default: demo)")

    # replay command
    replay_parser = subparsers.add_parser("replay", help="Run historical replay with sentiment analysis")
    replay_parser.add_argument("--from", dest="start_date", required=True, help="Start date (YYYY-MM-DD)")
    replay_parser.add_argument("--to", dest="end_date", required=True, help="End date (YYYY-MM-DD)")
    replay_parser.add_argument("--symbol", type=str, default="BTCUSD", help="Symbol to trade (default: BTCUSD)")
    replay_parser.add_argument("--tweets", dest="tweets_csv", help="Path to CSV file with historical tweets")
    replay_parser.add_argument("--plot", action="store_true", help="Generate correlation plots")

    args = parser.parse_args()

    if args.command == "run-demo":
        run_demo(args.symbol, args.log_level, getattr(args, "live", False))
    elif args.command == "dashboard":
        import uvicorn
        from dashboard.main import app
        uvicorn.run(app, host=args.host, port=args.port)
    elif args.command == "replay":
        run_replay(
            start_date=getattr(args, "start_date"),
            end_date=getattr(args, "end_date"),
            symbol=getattr(args, "symbol", "BTCUSD"),
            tweets_csv=getattr(args, "tweets_csv"),
            plot=getattr(args, "plot", False)
        )
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
