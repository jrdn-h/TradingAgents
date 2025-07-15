"""
Historical replay runner with sentiment correlation analysis.
"""

import asyncio
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import os
from pathlib import Path
from tradingagents.graph.orchestrator import Orchestrator
from tradingagents.sources.tweet_source import CSVReplaySource, Tweet
from tradingagents.agents.analysts.technical_analyst import TechnicalAnalyst
from tradingagents.agents.trader.trader import TraderAgent
from tradingagents.agents.managers.risk_manager import RiskManager
from tradingagents.backtest.metrics import BacktestMetrics, calculate_metrics, save_correlation_plot

logger = logging.getLogger(__name__)

class ReplayRunner:
    """Historical replay with sentiment correlation analysis."""
    
    def __init__(self):
        self.orchestrator = Orchestrator()
        self.technical_analyst = TechnicalAnalyst()
        self.trader = TraderAgent()
        self.risk_manager = RiskManager()
        
        # Results storage
        self.price_data = []
        self.sentiment_data = []
        self.trade_log = []
        self.equity_curve = []
        
        # Trading state
        self.cash = 10000.0
        self.position = 0.0
        self.entry_price = 0.0
        
    async def run_replay(
        self, 
        start_date: str, 
        end_date: str, 
        symbol: str, 
        tweets_csv: Optional[str] = None,
        plot: bool = False
    ):
        """Run historical replay with sentiment correlation."""
        
        logger.info(f"📊 Loading price data for {symbol} from {start_date} to {end_date}")
        
        # Load price data
        price_df = await self._load_price_data(symbol, start_date, end_date)
        if price_df.empty:
            logger.error("❌ No price data found for the specified period")
            return
            
        logger.info(f"✅ Loaded {len(price_df)} price points")
        
        # Load tweet data if provided
        tweet_df = None
        if tweets_csv and os.path.exists(tweets_csv):
            logger.info(f"🐦 Loading tweets from {tweets_csv}")
            tweet_df = pd.read_csv(tweets_csv, parse_dates=["created_at"], dtype={"id": str})
            logger.info(f"✅ Loaded {len(tweet_df)} tweets")
        else:
            logger.warning("⚠️ No tweet CSV provided - running without sentiment")
            
        # Run the replay
        await self._run_replay_simulation(price_df, tweet_df, symbol)
        
        # Analyze results
        await self._analyze_results(symbol, plot)
        
    async def _load_price_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Load historical price data."""
        try:
            # Try to load from local CSV first
            csv_path = f"data/{symbol}_price_data.csv"
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path, parse_dates=["datetime"])
                df = df[(df["datetime"] >= start_date) & (df["datetime"] <= end_date)]
                return df
                
            # Fallback to yfinance
            import yfinance as yf
            df = yf.download(symbol, start=start_date, end=end_date, interval="1h")
            df = df.reset_index()
            df.columns = [col.lower() for col in df.columns]
            df["datetime"] = pd.to_datetime(df.index)
            return df
            
        except Exception as e:
            logger.error(f"Failed to load price data: {e}")
            # Return mock data for demo
            return self._generate_mock_price_data(start_date, end_date)
    
    def _generate_mock_price_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Generate mock price data for demo purposes."""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Generate hourly timestamps
        timestamps = pd.date_range(start, end, freq="1H")
        
        # Generate realistic BTC price movement
        np.random.seed(42)  # For reproducible results
        base_price = 42000
        returns = np.random.normal(0, 0.02, len(timestamps))  # 2% hourly volatility
        prices = [base_price]
        
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(new_price)
            
        df = pd.DataFrame({
            "datetime": timestamps,
            "open": prices,
            "high": [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            "low": [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            "close": prices,
            "volume": np.random.randint(1000, 10000, len(timestamps))
        })
        
        return df
    
    async def _run_replay_simulation(self, price_df: pd.DataFrame, tweet_df: Optional[pd.DataFrame], symbol: str):
        """Run the actual replay simulation."""
        logger.info("🔄 Starting replay simulation...")
        
        # Initialize tracking
        self.price_data = []
        self.sentiment_data = []
        self.trade_log = []
        self.equity_curve = []
        
        # Process each price point
        for idx, row in price_df.iterrows():
            price = row["close"]
            timestamp = row["datetime"]
            
            # Store price data
            self.price_data.append({
                "timestamp": timestamp,
                "price": price,
                "tick": idx
            })
            
            # Get relevant tweets for this time window
            relevant_tweets = []
            if tweet_df is not None:
                # Get tweets from the last hour
                window_start = timestamp - timedelta(hours=1)
                window_tweets = tweet_df[
                    (tweet_df["created_at"] >= window_start) & 
                    (tweet_df["created_at"] <= timestamp)
                ]
                
                # Process tweets and update sentiment
                for _, tweet_row in window_tweets.iterrows():
                    tweet = Tweet(
                        id=tweet_row["id"],
                        created_at=tweet_row["created_at"],
                        author=tweet_row["author"],
                        text=tweet_row["text"],
                        raw_json=tweet_row.to_dict()
                    )
                    sentiment = await self.orchestrator.ingest_tweet(tweet)
                    relevant_tweets.append({
                        "tweet": tweet,
                        "sentiment": sentiment
                    })
            
            # Store sentiment data
            self.sentiment_data.append({
                "timestamp": timestamp,
                "sentiment_index": self.orchestrator.sentiment_index,
                "tweet_count": len(relevant_tweets),
                "tick": idx
            })
            
            # Run trading logic
            await self._process_trading_decision(price, timestamp, idx)
            
            # Update equity curve
            equity = self.cash + (self.position * price)
            self.equity_curve.append({
                "timestamp": timestamp,
                "equity": equity,
                "tick": idx
            })
            
            # Progress indicator
            if idx % 100 == 0:
                logger.info(f"📈 Processed {idx}/{len(price_df)} ticks (${price:.2f})")
        
        # Close any remaining position
        if self.position > 0:
            final_price = price_df.iloc[-1]["close"]
            self.cash += self.position * final_price
            self.trade_log.append({
                "timestamp": price_df.iloc[-1]["datetime"],
                "action": "close",
                "price": final_price,
                "size": self.position * final_price,
                "reason": "end_of_period"
            })
            self.position = 0
            
        logger.info("✅ Replay simulation completed")
    
    async def _process_trading_decision(self, price: float, timestamp: datetime, tick: int):
        """Process trading decision for current price point."""
        
        # Technical analysis
        tech_state = {"tick": {"price": price}}
        tech_result = await self.technical_analyst.run(tech_state)
        
        # Sentiment analysis (use current sentiment index)
        sentiment_result = {
            "score": self.orchestrator.sentiment_index,
            "label": "bullish" if self.orchestrator.sentiment_index > 0.1 else "bearish" if self.orchestrator.sentiment_index < -0.1 else "neutral"
        }
        
        # Trader decision
        trade_state = {
            "technical": tech_result,
            "sentiment": sentiment_result
        }
        trade_decision = await self.trader.run(trade_state)
        
        # Risk management
        risk_state = {"trade": trade_decision}
        risk_approval = await self.risk_manager.run(risk_state)
        
        # Execute trade if approved
        if risk_approval.get("approved", False):
            action = trade_decision.get("action", "flat")
            size_pct = risk_approval.get("new_size_pct", 0)
            
            if action == "long" and self.position == 0 and size_pct > 0:
                # Open long position
                trade_size = self.cash * size_pct / 100
                self.position = trade_size / price
                self.cash -= trade_size
                self.entry_price = price
                
                self.trade_log.append({
                    "timestamp": timestamp,
                    "action": "buy",
                    "price": price,
                    "size": trade_size,
                    "sentiment": self.orchestrator.sentiment_index,
                    "technical_breakout": tech_result.get("breakout", False)
                })
                
            elif action == "flat" and self.position > 0:
                # Close position
                close_value = self.position * price
                self.cash += close_value
                
                self.trade_log.append({
                    "timestamp": timestamp,
                    "action": "sell",
                    "price": price,
                    "size": close_value,
                    "sentiment": self.orchestrator.sentiment_index,
                    "pnl": close_value - (self.position * self.entry_price)
                })
                
                self.position = 0
                self.entry_price = 0
    
    async def _analyze_results(self, symbol: str, plot: bool):
        """Analyze replay results and generate reports."""
        logger.info("📊 Analyzing results...")
        
        # Convert to DataFrames
        price_df = pd.DataFrame(self.price_data)
        sentiment_df = pd.DataFrame(self.sentiment_data)
        equity_df = pd.DataFrame(self.equity_curve)
        trades_df = pd.DataFrame(self.trade_log) if self.trade_log else pd.DataFrame()
        
        # Calculate performance metrics
        if len(equity_df) > 1:
            # Prepare series for metrics calculation
            equity_series = equity_df.set_index("timestamp")["equity"]
            returns_series = equity_series.pct_change().fillna(0)
            
            # Prepare trades PnL series
            trades_pnl = None
            if len(trades_df) > 0 and "pnl" in trades_df.columns:
                trades_pnl = trades_df["pnl"].dropna()
            
            # Prepare sentiment and price series for correlation
            sentiment_series = None
            price_series = None
            if len(sentiment_df) > 0 and len(price_df) > 0:
                # Align sentiment and price data
                sentiment_series = sentiment_df.set_index("timestamp")["sentiment_index"]
                price_series = price_df.set_index("timestamp")["price"]
                
                # Forward fill sentiment to align with price timestamps
                sentiment_series = sentiment_series.reindex(price_series.index, method="ffill")
            
            # Calculate comprehensive metrics
            metrics = calculate_metrics(
                equity_curve=equity_series,
                returns=returns_series,
                trades_pnl=trades_pnl,
                sentiment_series=sentiment_series,
                price_series=price_series
            )
            
            # Print metrics to console
            print(f"\n📈 BACKTEST RESULTS: {symbol}")
            print("=" * 60)
            print(f"Sharpe Ratio:        {metrics.sharpe:.3f}")
            print(f"Sortino Ratio:       {metrics.sortino:.3f}")
            print(f"Max Drawdown:        {metrics.max_dd:.3f}")
            print(f"Win Rate:            {metrics.win_rate:.3f}")
            print(f"Sentiment Correlation: {metrics.sentiment_price_corr:.3f}")
            print("=" * 60)
            
            # Save metrics CSV
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            metrics_path = reports_dir / f"backtest_metrics_{symbol}.csv"
            pd.DataFrame([metrics.to_dict()]).to_csv(metrics_path, index=False)
            logger.info(f"📊 Metrics saved to {metrics_path}")
            
            # Save correlation plot
            if plot and sentiment_series is not None and price_series is not None:
                corr_path = reports_dir / f"sentiment_price_corr_{symbol}.png"
                plot_success = save_correlation_plot(sentiment_series, price_series, corr_path, symbol)
                if plot_success:
                    logger.info(f"📊 Correlation plot saved to {corr_path}")
                else:
                    logger.warning("⚠️ Not enough sentiment/price data for correlation plot.")
            elif plot:
                logger.warning("⚠️ No sentiment data available - correlation plot skipped.")
        
        # Save results
        self._save_results(symbol, price_df, sentiment_df, equity_df, trades_df)
        
        # Generate plots
        if plot:
            await self._generate_plots(symbol, price_df, sentiment_df, equity_df, trades_df)
    
    def _save_results(self, symbol: str, price_df: pd.DataFrame, sentiment_df: pd.DataFrame, 
                     equity_df: pd.DataFrame, trades_df: pd.DataFrame):
        """Save replay results to files."""
        os.makedirs("reports", exist_ok=True)
        
        # Save equity curve
        equity_df.to_csv(f"reports/equity_{symbol}.csv", index=False)
        
        # Save trades
        if len(trades_df) > 0:
            trades_df.to_csv(f"reports/trades_{symbol}.csv", index=False)
        
        # Save sentiment data
        if len(sentiment_df) > 0:
            sentiment_df.to_csv(f"reports/sentiment_{symbol}.csv", index=False)
        
        logger.info(f"💾 Results saved to reports/ directory")
    
    async def _generate_plots(self, symbol: str, price_df: pd.DataFrame, sentiment_df: pd.DataFrame,
                            equity_df: pd.DataFrame, trades_df: pd.DataFrame):
        """Generate correlation and performance plots."""
        logger.info("📊 Generating plots...")
        
        # Set up the plotting style
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'Replay Analysis: {symbol}', fontsize=16, fontweight='bold')
        
        # 1. Price and Sentiment Overlay
        ax1 = axes[0, 0]
        ax1_twin = ax1.twinx()
        
        ax1.plot(price_df['timestamp'], price_df['price'], 'b-', alpha=0.7, label='Price')
        if len(sentiment_df) > 0:
            ax1_twin.plot(sentiment_df['timestamp'], sentiment_df['sentiment_index'], 'r-', alpha=0.7, label='Sentiment')
        
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Price ($)', color='b')
        ax1_twin.set_ylabel('Sentiment Index', color='r')
        ax1.set_title('Price vs Sentiment Correlation')
        
        # 2. Equity Curve
        ax2 = axes[0, 1]
        ax2.plot(equity_df['timestamp'], equity_df['equity'], 'g-', linewidth=2)
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Equity ($)')
        ax2.set_title('Portfolio Equity Curve')
        ax2.grid(True, alpha=0.3)
        
        # 3. Sentiment Distribution
        ax3 = axes[1, 0]
        if len(sentiment_df) > 0:
            ax3.hist(sentiment_df['sentiment_index'], bins=30, alpha=0.7, color='orange')
            ax3.axvline(sentiment_df['sentiment_index'].mean(), color='red', linestyle='--', 
                       label=f'Mean: {sentiment_df["sentiment_index"].mean():.3f}')
            ax3.set_xlabel('Sentiment Index')
            ax3.set_ylabel('Frequency')
            ax3.set_title('Sentiment Distribution')
            ax3.legend()
        
        # 4. Trade Analysis
        ax4 = axes[1, 1]
        if len(trades_df) > 0 and 'pnl' in trades_df.columns:
            pnl_data = trades_df['pnl'].dropna()
            if len(pnl_data) > 0:
                ax4.hist(pnl_data, bins=20, alpha=0.7, color='purple')
                ax4.axvline(pnl_data.mean(), color='red', linestyle='--', 
                           label=f'Mean PnL: ${pnl_data.mean():.2f}')
                ax4.set_xlabel('Trade PnL ($)')
                ax4.set_ylabel('Frequency')
                ax4.set_title('Trade PnL Distribution')
                ax4.legend()
        
        plt.tight_layout()
        
        # Save plot
        plot_path = f"reports/replay_analysis_{symbol}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"📊 Plot saved to {plot_path}") 