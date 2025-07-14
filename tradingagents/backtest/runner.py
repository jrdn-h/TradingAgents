import argparse
import pandas as pd
import numpy as np
import os
import asyncio
from datetime import datetime
from tradingagents.agents.analysts.sentiment_analyst import SentimentAnalyst
from tradingagents.agents.analysts.technical_analyst import TechnicalAnalyst
from tradingagents.agents.trader.trader import TraderAgent
from tradingagents.agents.managers.risk_manager import RiskManager

def load_candles(symbol, start, end, csv_path=None):
    if csv_path:
        df = pd.read_csv(csv_path, parse_dates=["Datetime"])
    else:
        try:
            import yfinance as yf
            df = yf.download(symbol, start=start, end=end, interval="1h")
            df = df.reset_index()
        except Exception as e:
            raise RuntimeError("No CSV provided and failed to fetch from yfinance: %s" % e)
    # Standardize columns
    col_map = {c.lower(): c for c in df.columns}
    for want in ["open", "high", "low", "close", "volume"]:
        if want not in col_map:
            raise ValueError(f"Missing column: {want}")
    if "datetime" not in col_map and "date" in col_map:
        df["Datetime"] = pd.to_datetime(df[col_map["date"]])
    elif "datetime" in col_map:
        df["Datetime"] = pd.to_datetime(df[col_map["datetime"]])
    else:
        df["Datetime"] = pd.to_datetime(df.index)
    return df

async def run_backtest(df, symbol):
    sentiment = SentimentAnalyst()
    technical = TechnicalAnalyst()
    trader = TraderAgent()
    risk = RiskManager()
    cash = 10000.0
    position = 0.0
    entry_price = 0.0
    trade_log = []
    equity_curve = []
    for i, row in df.iterrows():
        price = row['close'] if 'close' in row else row['Close']
        # Technical
        tech_out = await technical.run({'tick': {'price': price}})
        # Sentiment (stub: no tweets)
        sent_out = await sentiment.run({'tweets': []})
        # Trader
        trade = await trader.run({'technical': tech_out, 'sentiment': sent_out})
        # Risk
        approval = await risk.run({'trade': trade})
        # Simulate trade
        action = trade.get('action', 'flat')
        size_pct = approval.get('new_size_pct', 0)
        trade_size = cash * size_pct / 100
        if approval.get('approved') and action == 'long' and position == 0 and trade_size > 0:
            position = trade_size / price
            cash -= trade_size
            entry_price = price
            trade_log.append({'datetime': row['Datetime'], 'action': 'buy', 'price': price, 'size': trade_size})
        elif approval.get('approved') and action == 'flat' and position > 0:
            cash += position * price
            trade_log.append({'datetime': row['Datetime'], 'action': 'sell', 'price': price, 'size': position * price})
            position = 0
            entry_price = 0
        equity = cash + position * price
        equity_curve.append({'datetime': row['Datetime'], 'equity': equity})
    # Final closeout
    if position > 0:
        cash += position * price
        trade_log.append({'datetime': row['Datetime'], 'action': 'sell', 'price': price, 'size': position * price})
        position = 0
    pnl = pd.Series([e['equity'] for e in equity_curve], index=[e['datetime'] for e in equity_curve])
    returns = pnl.pct_change().fillna(0)
    sharpe = np.sqrt(24*365) * returns.mean() / (returns.std() + 1e-9)
    mdd = (pnl / pnl.cummax() - 1).min()
    # Write trades
    trades_df = pd.DataFrame(trade_log)
    trades_df.to_csv('trades.csv', index=False)
    # Print metrics
    print("\nBacktest Results:")
    print(f"  Start equity: $10000.00")
    print(f"  End equity:   ${pnl.iloc[-1]:.2f}")
    print(f"  Sharpe:       {sharpe:.2f}")
    print(f"  Max DD:       {mdd:.2%}")
    print(f"  Trades:       {len(trades_df)//2}")
    print("  Trades log written to trades.csv")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--from', dest='start', required=True)
    parser.add_argument('--to', dest='end', required=True)
    parser.add_argument('--symbol', required=True)
    parser.add_argument('--csv', dest='csv_path', default=None)
    parser.add_argument('--plot', action='store_true')
    args = parser.parse_args()
    df = load_candles(args.symbol, args.start, args.end, args.csv_path)
    asyncio.run(run_backtest(df, args.symbol)) 