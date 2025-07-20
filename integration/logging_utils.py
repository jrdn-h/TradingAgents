"""CSV logging utilities for trading decisions and results."""

from __future__ import annotations
import os
import csv
from pathlib import Path
from typing import Union
from integration.schema.signal import TradingSignal

__all__ = ["append_decision", "append_trade_result", "DECISION_LOG", "TRADE_RESULTS_LOG"]

DECISION_LOG = Path("decision_logs/decision_log.csv")
TRADE_RESULTS_LOG = Path("decision_logs/trade_results.csv")

DECISION_HEADERS = [
    "decision_id", "timestamp", "symbol", "side", "entry_price",
    "stop", "tp1", "tp2", "confidence"
]

TRADE_RESULTS_HEADERS = [
    "decision_id", "exit_price", "pnl_r_multiple", "exit_reason", "timestamp"
]


def _ensure_parent(p: Path):
    """Ensure parent directory exists."""
    p.parent.mkdir(parents=True, exist_ok=True)


def append_decision(signal: TradingSignal, entry_price: float):
    """Append a trading decision to the decision log CSV.
    
    Args:
        signal: TradingSignal containing decision details
        entry_price: Actual entry price for the trade
    """
    _ensure_parent(DECISION_LOG)
    write_header = not DECISION_LOG.exists()
    
    with DECISION_LOG.open("a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(DECISION_HEADERS)
        w.writerow([
            signal.decision_id,
            signal.timestamp,
            signal.symbol,
            signal.side,
            f"{entry_price:.8f}",
            f"{signal.risk.initial_stop:.8f}",
            f"{signal.risk.take_profits[0].price:.8f}",
            f"{signal.risk.take_profits[1].price:.8f}",
            f"{signal.confidence:.4f}"
        ])


def append_trade_result(decision_id: str, exit_price: float, pnl_r_multiple: float, 
                       exit_reason: str, timestamp: str):
    """Append a trade result to the trade results log CSV.
    
    Args:
        decision_id: Decision ID linking to original decision
        exit_price: Price at which trade was closed
        pnl_r_multiple: PnL expressed as R-multiple (risk units)
        exit_reason: Reason for exit (e.g., "tp1_hit", "stop_loss", etc.)
        timestamp: ISO timestamp of trade exit
    """
    _ensure_parent(TRADE_RESULTS_LOG)
    write_header = not TRADE_RESULTS_LOG.exists()
    
    with TRADE_RESULTS_LOG.open("a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(TRADE_RESULTS_HEADERS)
        w.writerow([
            decision_id,
            f"{exit_price:.8f}",
            f"{pnl_r_multiple:.4f}",
            exit_reason,
            timestamp
        ]) 