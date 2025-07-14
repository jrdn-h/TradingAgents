import argparse
import logging
import sys
import asyncio
import json

from tradingagents.graph.orchestrator import Orchestrator

def run_demo(symbol: str, log_level: str = "INFO", live: bool = False):
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(message)s")
    orchestrator = Orchestrator()
    orchestrator.run(symbol=symbol, live=live)

def main():
    parser = argparse.ArgumentParser(description="TradingAgents CLI")
    parser.add_argument("--log-level", type=str, default="INFO", help="Set log level (default: INFO)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run-demo command
    demo_parser = subparsers.add_parser("run-demo", help="Run orchestrator demo")
    demo_parser.add_argument("--symbol", type=str, default="BTCUSD", help="Symbol to trade (default: BTCUSD)")
    demo_parser.add_argument("--live", action="store_true", help="Use live Hyperliquid price feed (default: mock prices)")

    args = parser.parse_args()

    if args.command == "run-demo":
        run_demo(args.symbol, args.log_level, getattr(args, "live", False))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
