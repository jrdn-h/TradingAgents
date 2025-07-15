"""
Backtest metrics calculation and visualization utilities.
"""

from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Optional, Dict, Any
import os

# Optional dependency guard: https://stackoverflow.com/q/77512072
try:
    from stockstats import StockDataFrame as Sdf
except ImportError:
    Sdf = None

# Prometheus metrics for monitoring
try:
    from prometheus_client import Gauge, Counter
    PROMETHEUS_AVAILABLE = True
    
    # Create gauges for backtest metrics
    sharpe_gauge = Gauge("replay_sharpe_last", "Sharpe ratio of last replay run")
    sortino_gauge = Gauge("replay_sortino_last", "Sortino ratio of last replay run")
    max_dd_gauge = Gauge("replay_max_drawdown_last", "Maximum drawdown of last replay run")
    win_rate_gauge = Gauge("replay_win_rate_last", "Win rate of last replay run")
    sentiment_corr_gauge = Gauge("replay_sentiment_correlation_last", "Sentiment-price correlation of last replay run")
    
    # Trading metrics
    sentiment_index_gauge = Gauge("sentiment_index_current", "Current sentiment index value")
    
    # Counters for total events
    tweet_ingested_total_counter = Counter("tweet_ingested_total", "Total number of tweets ingested")
    backoffs_total_counter = Counter("backoffs_total", "Total number of rate limit backoffs")
    
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Dummy gauges for when prometheus_client is not available
    class DummyGauge:
        def set(self, value): pass
    sharpe_gauge = sortino_gauge = max_dd_gauge = win_rate_gauge = sentiment_corr_gauge = DummyGauge()
    sentiment_index_gauge = DummyGauge()

    class DummyCounter:
        def inc(self, value=1): pass
    tweet_ingested_total_counter = backoffs_total_counter = DummyCounter()

@dataclass
class BacktestMetrics:
    sharpe: float
    sortino: float
    max_dd: float
    win_rate: float
    sentiment_price_corr: float

    def to_dict(self):
        return asdict(self)
    
    def update_prometheus(self):
        """Update Prometheus gauges with current metrics."""
        if PROMETHEUS_AVAILABLE:
            sharpe_gauge.set(self.sharpe if not np.isnan(self.sharpe) else 0.0)
            sortino_gauge.set(self.sortino if not np.isnan(self.sortino) else 0.0)
            max_dd_gauge.set(self.max_dd if not np.isnan(self.max_dd) else 0.0)
            win_rate_gauge.set(self.win_rate if not np.isnan(self.win_rate) else 0.0)
            sentiment_corr_gauge.set(self.sentiment_price_corr if not np.isnan(self.sentiment_price_corr) else 0.0)

def calc_sharpe(ret: pd.Series, rf: float = 0.0, periods: int = 252) -> float:
    """Calculate Sharpe ratio using excess returns."""
    if len(ret) < 2:
        return np.nan
    excess = ret - rf
    if excess.std() == 0:
        return np.nan
    return np.sqrt(periods) * excess.mean() / excess.std(ddof=0)

def calc_sortino(ret: pd.Series, rf: float = 0.0, periods: int = 252) -> float:
    """Calculate Sortino ratio using downside deviation."""
    if len(ret) < 2:
        return np.nan
    downside = ret[ret < 0]
    if len(downside) == 0 or downside.std() == 0:
        return np.nan
    return np.sqrt(periods) * (ret.mean() - rf) / downside.std(ddof=0)

def max_drawdown(equity: pd.Series) -> float:
    """Calculate maximum drawdown from equity curve."""
    if len(equity) < 2:
        return 0.0
    cummax = equity.cummax()
    dd = (equity - cummax) / cummax
    return dd.min()

def win_rate(trades: pd.Series) -> float:
    """Calculate win rate from trade PnL series."""
    if len(trades) == 0:
        return 0.0
    return (trades > 0).mean()

def save_correlation_plot(sent: pd.Series, price: pd.Series, path: Path, symbol: str) -> bool:
    """Save sentiment vs price correlation scatter plot."""
    if sent.empty or price.empty or len(sent) < 2 or len(price) < 2:
        return False
    
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(sent, price, alpha=0.6, s=20)
        ax.set_xlabel("Sentiment Index")
        ax.set_ylabel("Price ($)")
        ax.set_title(f"{symbol} Sentiment vs Price Correlation")
        ax.grid(True, alpha=0.3)
        
        # Add correlation coefficient to title
        corr = sent.corr(price, method="pearson")
        if not pd.isna(corr):
            ax.text(0.05, 0.95, f"ρ = {corr:.3f}", transform=ax.transAxes, 
                   bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))
        
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return True
    except Exception as e:
        print(f"⚠️ Failed to save correlation plot: {e}")
        return False

def calculate_metrics(
    equity_curve: pd.Series,
    returns: pd.Series,
    trades_pnl: Optional[pd.Series] = None,
    sentiment_series: Optional[pd.Series] = None,
    price_series: Optional[pd.Series] = None
) -> BacktestMetrics:
    """Calculate comprehensive backtest metrics."""
    
    # Calculate basic metrics
    sharpe = calc_sharpe(returns)
    sortino = calc_sortino(returns)
    max_dd = max_drawdown(equity_curve)
    
    # Calculate win rate
    if trades_pnl is not None and len(trades_pnl) > 0:
        win_rate_val = win_rate(trades_pnl)
    else:
        win_rate_val = 0.0
    
    # Calculate sentiment correlation
    sentiment_corr = np.nan
    if sentiment_series is not None and price_series is not None:
        if not sentiment_series.empty and not price_series.empty:
            # Align series by index
            aligned = pd.concat([sentiment_series, price_series], axis=1).dropna()
            if len(aligned) > 2:
                sentiment_corr = aligned.iloc[:, 0].corr(aligned.iloc[:, 1], method="pearson")
    
    metrics = BacktestMetrics(
        sharpe=sharpe,
        sortino=sortino,
        max_dd=max_dd,
        win_rate=win_rate_val,
        sentiment_price_corr=sentiment_corr
    )
    
    # Update Prometheus gauges
    metrics.update_prometheus()
    
    return metrics 