"""Breakout-based signal generator for MVP."""

from __future__ import annotations
from typing import Optional
from integration.schema.signal import TradingSignal, RiskPlan, TakeProfit
from integration.data import get_candles, compute_atr

__all__ = ["generate_signal"]

BREAKOUT_LOOKBACK = 20
STOP_LOOKBACK = 10
CONFIDENCE_DEFAULT = 0.6


def generate_signal(symbol: str, limit: int = 200) -> Optional[TradingSignal]:
    """Generate a breakout LONG signal or return None.
    Logic:
      1. Fetch candles (limit used for context).
      2. Identify breakout: last_close > max(high[-BREAKOUT_LOOKBACK-1:-1])
      3. Stop = min(low[-STOP_LOOKBACK:])
      4. Distance = entry - stop (reject if <= 0)
      5. TP1 = entry + distance
         TP2 = entry + 2 * distance
      6. Build TradingSignal with:
         side='long', confidence=CONFIDENCE_DEFAULT,
         entry={'type': 'market'},
         risk.initial_stop=stop, two take_profits @ size_pct=0.5 each
         rationale concise: "Breakout above N-bar high" (N = BREAKOUT_LOOKBACK)
      7. If no breakout → return None
    Deterministic; no randomness.
    """
    # Fetch candles
    candles = get_candles(symbol, limit=limit)
    
    # Check if we have enough candles for analysis
    min_candles_needed = max(BREAKOUT_LOOKBACK + 2, STOP_LOOKBACK + 2)
    if len(candles) < min_candles_needed:
        return None
    
    # Extract price arrays
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    closes = [c['close'] for c in candles]
    
    # Get last close (current entry price)
    last_close = closes[-1]
    
    # Check for breakout: last_close > max of prior 20 highs (excluding current candle)
    prior_window_high = max(highs[-(BREAKOUT_LOOKBACK+1):-1])
    
    if last_close <= prior_window_high:
        return None  # No breakout detected
    
    # Calculate stop loss: minimum of last 10 lows
    stop = min(lows[-STOP_LOOKBACK:])
    
    # Ensure stop is below entry (positive distance)
    if stop >= last_close:
        return None  # Invalid setup - stop above or equal to entry
    
    # Calculate distance and take profit levels
    distance = last_close - stop
    tp1 = last_close + distance  # R = 1
    tp2 = last_close + 2 * distance  # R = 2
    
    # Build risk plan with two take profits
    risk_plan = RiskPlan(
        initial_stop=stop,
        take_profits=[
            TakeProfit(price=tp1, size_pct=0.5),
            TakeProfit(price=tp2, size_pct=0.5),
        ],
        max_capital_pct=0.05
    )
    
    # Create trading signal
    signal = TradingSignal(
        symbol=symbol,
        side="long",
        confidence=CONFIDENCE_DEFAULT,
        entry={"type": "market"},
        risk=risk_plan,
        rationale=f"Breakout above {BREAKOUT_LOOKBACK}-bar high"
    )
    
    return signal 