"""Redis interface for publishing and consuming TradingSignal objects."""

from __future__ import annotations
import json
import os
import time
from typing import Optional
from datetime import datetime, timezone
from redis import Redis
from integration.schema.signal import TradingSignal

__all__ = ["publish_signal", "fetch_latest_signal", "get_redis_client"]

REDIS_LIST = "signals"

_redis_singleton: Optional[Redis] = None

def get_redis_client() -> Redis:
    """Get Redis client singleton."""
    global _redis_singleton
    if _redis_singleton is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_singleton = Redis.from_url(url, decode_responses=True)
    return _redis_singleton

def publish_signal(signal: TradingSignal) -> None:
    """Publish a TradingSignal to Redis list."""
    client = get_redis_client()
    payload = signal.model_dump()
    client.lpush(REDIS_LIST, json.dumps(payload))

def fetch_latest_signal(symbol: str, max_age_sec: int = 600) -> Optional[TradingSignal]:
    """Fetch the latest fresh signal for a symbol.
    
    Args:
        symbol: Symbol to fetch signal for (will be uppercased)
        max_age_sec: Maximum age in seconds for signal freshness
        
    Returns:
        TradingSignal if found and fresh, None otherwise
    """
    client = get_redis_client()
    now = datetime.now(timezone.utc).timestamp()
    # Non-destructive scan (pop only when match)
    length = client.llen(REDIS_LIST)
    for i in range(length):
        raw = client.lindex(REDIS_LIST, i)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if data.get("symbol") != symbol.upper():
            continue
        # Freshness check
        try:
            ts = datetime.fromisoformat(data["timestamp"]).timestamp()
        except Exception:
            continue
        if now - ts > max_age_sec:
            continue
        # If valid -> remove that specific element then return
        # Use LREM to remove only one occurrence
        client.lrem(REDIS_LIST, 1, raw)
        return TradingSignal.model_validate(data)
    return None 