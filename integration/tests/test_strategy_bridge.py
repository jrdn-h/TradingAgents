# integration/tests/test_strategy_bridge.py
from __future__ import annotations
import math
import types
import pandas as pd
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import sys

# Mock freqtrade modules before importing strategy
mock_freqtrade = MagicMock()
mock_freqtrade.strategy = MagicMock()
mock_freqtrade.strategy.interface = MagicMock()

# Create a mock IStrategy class
class MockIStrategy:
    pass

mock_freqtrade.strategy.interface.IStrategy = MockIStrategy
mock_freqtrade.strategy.IStrategy = MockIStrategy
sys.modules['freqtrade'] = mock_freqtrade
sys.modules['freqtrade.strategy'] = mock_freqtrade.strategy
sys.modules['freqtrade.strategy.interface'] = mock_freqtrade.strategy.interface

from integration.schema.signal import TradingSignal, RiskPlan, TakeProfit
from integration.strategy.AgentBridgeStrategy import AgentBridgeStrategy

# ---- Fixtures ---- #

@pytest.fixture
def candles_df():
    """
    Create a minimal OHLCV DataFrame >= startup_candle_count (50) to satisfy strategy.
    """
    periods = 60
    base = datetime.now(timezone.utc) - timedelta(minutes=5 * periods)
    idx = pd.date_range(base, periods=periods, freq="5min", tz=timezone.utc)
    # Simple upward drift
    close = [50000 + i * 5 for i in range(periods)]
    high  = [c + 2 for c in close]
    low   = [c - 2 for c in close]
    open_ = [c - 1 for c in close]
    volume = [100 + i for i in range(periods)]
    df = pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    }, index=idx)
    return df

@pytest.fixture
def valid_signal():
    return TradingSignal(
        symbol="BTC/USDT",
        side="long",
        confidence=0.6,
        entry={"type": "market"},
        risk=RiskPlan(
            initial_stop=49950.0,
            take_profits=[
                TakeProfit(price=50050.0, size_pct=0.5),
                TakeProfit(price=50100.0, size_pct=0.5),
            ],
            max_capital_pct=0.05
        ),
        rationale="Breakout test"
    )

@pytest.fixture
def strategy():
    # Fresh instance per test prevents shared _bridge_meta side-effects
    return AgentBridgeStrategy()

def _inject_fetch(strategy: AgentBridgeStrategy, signal: TradingSignal | None):
    """
    Monkeypatch the strategy's fetch method in-place, avoiding global patches.
    Always returns the provided signal (idempotent).
    """
    def _fetch(pair: str):
        return signal
    strategy.fetch_bridge_signal = _fetch  # type: ignore

# ---- Tests ---- #

def test_entry_flag_set_on_signal(strategy, candles_df, valid_signal):
    _inject_fetch(strategy, valid_signal)
    pair_meta = {"pair": "BTC/USDT"}
    out = strategy.populate_entry_trend(candles_df.copy(), pair_meta)
    assert out.iloc[-1]["enter_long"] == 1, "Entry flag not set"
    # Metadata stored
    assert hasattr(strategy, "_bridge_meta")
    meta = strategy._bridge_meta["BTC/USDT"]
    assert meta["initial_stop"] == pytest.approx(valid_signal.risk.initial_stop)

def test_no_signal_no_entry(strategy, candles_df):
    _inject_fetch(strategy, None)
    out = strategy.populate_entry_trend(candles_df.copy(), {"pair": "BTC/USDT"})
    assert out.iloc[-1]["enter_long"] == 0
    assert not hasattr(strategy, "_bridge_meta")

def test_custom_stoploss_returns_fraction(strategy, candles_df, valid_signal):
    _inject_fetch(strategy, valid_signal)
    pair = "BTC/USDT"
    df = strategy.populate_entry_trend(candles_df.copy(), {"pair": pair})
    # Mock trade
    class Trade:
        open_rate = candles_df.iloc[-1]["close"]
    trade = Trade()
    rate = candles_df.iloc[-1]["close"]
    sl = strategy.custom_stoploss(pair, trade, candles_df.index[-1], rate, 0.0)
    # Expect negative fraction (stop below entry)
    assert sl < 0
    # Validate approximate ratio
    expected = (valid_signal.risk.initial_stop / trade.open_rate) - 1
    assert sl == pytest.approx(expected, rel=1e-6)

def test_custom_exit_triggers_at_tp1(strategy, candles_df, valid_signal):
    _inject_fetch(strategy, valid_signal)
    pair = "BTC/USDT"
    strategy.populate_entry_trend(candles_df.copy(), {"pair": pair})
    meta = strategy._bridge_meta[pair]
    tp1 = meta["tp1"]
    # Rate below TP1 => no exit
    exit_none = strategy.custom_exit(pair, None, candles_df.index[-1], tp1 - 1, 0.0)
    assert exit_none is None
    # Rate at/above TP1 => exit
    exit_hit = strategy.custom_exit(pair, None, candles_df.index[-1], tp1, 0.0)
    assert exit_hit == "tp1_hit"

def test_multiple_calls_idempotent(strategy, candles_df, valid_signal):
    _inject_fetch(strategy, valid_signal)
    pair = "BTC/USDT"
    for _ in range(3):
        candles_df = strategy.populate_entry_trend(candles_df.copy(), {"pair": pair})
    assert candles_df.iloc[-1]["enter_long"] == 1
    # Ensure no duplication or KeyError in metadata
    assert len(strategy._bridge_meta) == 1

def test_fetch_returns_none_does_not_create_meta(strategy, candles_df):
    _inject_fetch(strategy, None)
    strategy.populate_entry_trend(candles_df.copy(), {"pair": "BTC/USDT"})
    assert not hasattr(strategy, "_bridge_meta")

def test_signal_symbol_case_insensitive(strategy, candles_df, valid_signal):
    # Simulate lowercase pair usage
    valid_signal.symbol = "btc/usdt"
    _inject_fetch(strategy, valid_signal)
    out = strategy.populate_entry_trend(candles_df.copy(), {"pair": "BTC/USDT"})
    assert out.iloc[-1]["enter_long"] == 1

def test_stoploss_no_meta_returns_noop(strategy, candles_df):
    class Trade: open_rate = candles_df.iloc[-1]["close"]
    val = strategy.custom_stoploss("BTC/USDT", Trade(), candles_df.index[-1], Trade.open_rate, 0.0)
    assert val == 1  # fallback return

def test_exit_no_meta(strategy, candles_df):
    val = strategy.custom_exit("BTC/USDT", None, candles_df.index[-1], 50000, 0.0)
    assert val is None

def test_tp2_meta_presence(strategy, candles_df, valid_signal):
    _inject_fetch(strategy, valid_signal)
    strategy.populate_entry_trend(candles_df.copy(), {"pair": "BTC/USDT"})
    meta = strategy._bridge_meta["BTC/USDT"]
    assert "tp2" in meta
    assert meta["tp2"] > meta["tp1"] 