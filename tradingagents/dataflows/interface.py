from typing import Annotated, Dict, List, Optional
from .finnhub import FinnhubDataFlow
from .simfin import SimFinDataFlow
from .google_news import GoogleNewsDataFlow
from .reddit import RedditDataFlow
from .yfinance import YFinanceDataFlow
from .stockstats import StockstatsDataFlow
from .config import get_config, set_config

def get_finnhub_news(ticker: str, curr_date: str, look_back_days: int) -> str:
    return FinnhubDataFlow().fetch_news(ticker, curr_date, look_back_days)

def get_finnhub_company_insider_sentiment(ticker: str, curr_date: str, look_back_days: int) -> str:
    return FinnhubDataFlow().fetch_insider_sentiment(ticker, curr_date, look_back_days)

def get_finnhub_company_insider_transactions(ticker: str, curr_date: str, look_back_days: int) -> str:
    return FinnhubDataFlow().fetch_insider_transactions(ticker, curr_date, look_back_days)

def get_simfin_balance_sheet(ticker: str, freq: str, curr_date: str) -> str:
    return SimFinDataFlow().fetch_balance_sheet(ticker, freq, curr_date)

def get_simfin_cashflow(ticker: str, freq: str, curr_date: str) -> str:
    return SimFinDataFlow().fetch_cash_flow(ticker, freq, curr_date)

def get_simfin_income_statements(ticker: str, freq: str, curr_date: str) -> str:
    return SimFinDataFlow().fetch_income_statement(ticker, freq, curr_date)

def get_google_news(query: str, curr_date: str, look_back_days: int) -> str:
    return GoogleNewsDataFlow().fetch_data(query, curr_date, look_back_days)

def get_reddit_global_news(curr_date: str, look_back_days: int, max_limit_per_day: int) -> str:
    return RedditDataFlow().fetch_global_news(curr_date, look_back_days, max_limit_per_day)

def get_reddit_company_news(ticker: str, curr_date: str, look_back_days: int, max_limit_per_day: int) -> str:
    return RedditDataFlow().fetch_company_news(ticker, curr_date, look_back_days, max_limit_per_day)

def get_stock_stats_indicators_window(symbol: str, indicator: str, curr_date: str, look_back_days: int, online: bool) -> str:
    return StockstatsDataFlow().fetch_indicator_window(symbol, indicator, curr_date, look_back_days, online)

def get_stockstats_indicator(symbol: str, indicator: str, curr_date: str, online: bool) -> str:
    return StockstatsDataFlow().fetch_indicator(symbol, indicator, curr_date, online)

def get_YFin_data_online(symbol: str, start_date: str, end_date: str) -> str:
    return YFinanceDataFlow().fetch_data_online(symbol, start_date, end_date)

def get_YFin_data(symbol: str, start_date: str, end_date: str):
    return YFinanceDataFlow().fetch_data_offline(symbol, start_date, end_date)
