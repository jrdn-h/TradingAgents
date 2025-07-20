"""Risk gate for validating TradingSignals against ATR and RR criteria."""

from __future__ import annotations
from typing import Optional
from integration.schema.signal import TradingSignal
from integration.data import compute_atr
from math import isfinite

__all__ = ["apply_risk"]


def apply_risk(signal: TradingSignal, candles: list[dict], cfg: dict) -> Optional[TradingSignal]:
    """Return signal if it passes risk filters else None.

    Filters:
      - Ensure enough candles for ATR (>= period+1).
      - Compute ATR over last `period` (default 14).
      - Distance = entry_price - initial_stop (long) or initial_stop - entry (short).
      - Reject if distance < min_atr_multiple * ATR or distance > max_atr_multiple * ATR.
      - Compute RR1 using first TP vs stop; require >= min_rr.
      - Cap signal.risk.max_capital_pct to cfg['max_capital_pct'] if higher.
    """
    # Extract risk configuration with defaults
    risk_cfg = cfg.get("risk", {})
    min_mult = risk_cfg.get("min_atr_multiple", 0.5)
    max_mult = risk_cfg.get("max_atr_multiple", 5.0)
    min_rr = risk_cfg.get("min_rr", 1.5)
    period = risk_cfg.get("atr_period", 14)

    # Check if we have enough candles for ATR calculation
    if len(candles) < period + 1:
        return None

    # Compute ATR and validate
    atr = compute_atr(candles, period=period)
    if not isfinite(atr) or atr <= 0:
        return None

    # Get entry price from last candle close
    entry_price = candles[-1]["close"]
    stop = signal.risk.initial_stop

    # Calculate distance and RR based on signal side
    if signal.side == "long":
        distance = entry_price - stop
        tp1 = signal.risk.take_profits[0].price
        rr = (tp1 - entry_price) / (entry_price - stop) if (entry_price - stop) > 0 else -1
    else:  # short
        distance = stop - entry_price
        tp1 = signal.risk.take_profits[0].price
        rr = (entry_price - tp1) / (stop - entry_price) if (stop - entry_price) > 0 else -1

    # Basic validity check - distance must be positive
    if distance <= 0:
        return None

    # ATR distance bounds check
    if distance < min_mult * atr or distance > max_mult * atr:
        return None

    # Minimum risk-reward ratio check
    if rr < min_rr:
        return None

    # Cap capital percentage if needed
    max_cap = cfg.get("max_capital_pct", 0.05)
    if signal.risk.max_capital_pct > max_cap:
        signal.risk.max_capital_pct = max_cap

    return signal 