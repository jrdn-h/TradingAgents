import os
import sys
import pandas as pd
import pytest
import asyncio
from tradingagents.backtest.runner import load_candles, run_backtest

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'btc_hourly_small.csv')

@pytest.fixture
def fixture_df():
    return pd.read_csv(FIXTURE, parse_dates=["Datetime"])

@pytest.mark.asyncio
async def test_run_backtest_smoke(monkeypatch, fixture_df):
    # Patch yfinance to never be called
    monkeypatch.setitem(sys.modules, 'yfinance', None)
    # Run backtest
    await run_backtest(fixture_df, 'BTC-USD')
    # Check trades.csv exists
    assert os.path.exists('trades.csv')
    try:
        trades = pd.read_csv('trades.csv')
        # If non-empty, check schema
        if not trades.empty:
            assert set(trades.columns) >= {"datetime", "action", "price", "size"}
    except pd.errors.EmptyDataError:
        # Acceptable: no trades generated on this dataset
        pass

def test_load_candles_csv():
    df = load_candles('BTC-USD', '2024-01-01', '2024-01-02', FIXTURE)
    assert not df.empty
    assert 'Datetime' in df.columns
    assert 'close' in [c.lower() for c in df.columns]

def test_cli_backtest(tmp_path):
    import subprocess
    test_csv = os.path.join(os.path.dirname(__file__), 'fixtures', 'btc_hourly_small.csv')
    result = subprocess.run([
        sys.executable, '-m', 'tradingagents.backtest.runner',
        '--from', '2024-01-01', '--to', '2024-01-02',
        '--symbol', 'BTC-USD', '--csv', test_csv
    ], capture_output=True)
    assert result.returncode == 0
    assert b'Backtest Results' in result.stdout or b'Backtest Results' in result.stderr 