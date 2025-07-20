"""Minimal data layer for MVP - synthetic candles and ATR computation."""

from __future__ import annotations
from typing import List, Dict
from datetime import datetime, timezone
import math
import os

# Public exports
__all__ = ["get_candles", "compute_atr"]


def get_candles(symbol: str, limit: int = 200) -> List[Dict]:
    """Return ascending list of candle dicts:
    [
      {"timestamp": int (ms), "open": float, "high": float, "low": float, "close": float, "volume": float},
      ...
    ]
    MVP: Provide a *placeholder implementation* generating synthetic candles if no real source integrated yet:
      - Use a deterministic pseudo-random walk (seeded by symbol) OR
      - (Later) replace with real exchange fetch.
    Constraints:
      - len(result) >= min(limit, 50)
      - Timestamps spaced uniformly at 5m intervals ending near 'now'.
    """
    # Ensure minimum candles
    actual_limit = max(limit, 50)
    
    # Deterministic seed from symbol
    seed = hash(symbol) % 10_000
    
    # Base price based on symbol  
    if 'BTC' in symbol.upper():
        base_price = 50_000.0
    else:
        base_price = 1_000.0
    
    # 5-minute interval in milliseconds
    interval_ms = 5 * 60 * 1000
    
    # Current time and calculate start time
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = now_ms - (actual_limit - 1) * interval_ms
    
    candles = []
    
    for i in range(actual_limit):
        # Deterministic price movement using seed and index
        time_factor = (seed + i) / 1000.0
        trend = i * 0.001  # Small upward trend
        noise = math.sin(time_factor) * 0.02 + math.cos(time_factor * 1.7) * 0.01
        
        # Calculate price with variation
        price_multiplier = 1.0 + trend + noise
        current_price = round(base_price * price_multiplier, 2)
        
        # Generate OHLC with realistic intrabar movement
        volatility = current_price * 0.005  # 0.5% volatility
        high = round(current_price + volatility * abs(math.sin(time_factor + 1)), 2)
        low = round(current_price - volatility * abs(math.cos(time_factor + 2)), 2)
        
        # Ensure high >= close >= low
        high = max(high, current_price)
        low = min(low, current_price)
        
        # Open is close of previous candle (or base price for first)
        if i == 0:
            open_price = round(base_price, 2)
        else:
            open_price = candles[-1]["close"]
        
        # Volume with some variation
        base_volume = 20.0 + 30.0 * abs(math.sin(time_factor + 3))
        volume = round(base_volume, 2)
        
        candle = {
            "timestamp": start_ms + i * interval_ms,
            "open": open_price,
            "high": high,
            "low": low,
            "close": current_price,
            "volume": volume
        }
        
        candles.append(candle)
    
    return candles


def compute_atr(candles: List[Dict], period: int = 14) -> float:
    """Compute Average True Range (Wilder's) over last `period` completed candles.
    True Range = max(high-low, abs(high-prev_close), abs(low-prev_close)).
    Return float > 0. Raise ValueError if insufficient candles.
    """
    if len(candles) < period + 1:
        raise ValueError(f"Insufficient candles for ATR calculation: need {period + 1}, got {len(candles)}")
    
    # Calculate True Range for each candle (starting from second candle)
    true_ranges = []
    
    for i in range(1, len(candles)):
        current = candles[i]
        previous = candles[i - 1]
        
        # True Range components
        hl = current["high"] - current["low"]
        hc = abs(current["high"] - previous["close"])
        lc = abs(current["low"] - previous["close"])
        
        # True Range is the maximum of the three
        true_range = max(hl, hc, lc)
        true_ranges.append(true_range)
    
    # Use the last 'period' true ranges for ATR calculation
    if len(true_ranges) < period:
        raise ValueError(f"Insufficient true ranges: need {period}, got {len(true_ranges)}")
    
    # Wilder's smoothing method - simple average for MVP
    # (In production, would use exponential smoothing with alpha = 1/period)
    recent_ranges = true_ranges[-period:]
    atr = sum(recent_ranges) / len(recent_ranges)
    
    return round(atr, 4) 