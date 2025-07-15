import pandas as pd
from .base_dataflow import BaseDataFlow
from datetime import datetime

try:
    from stockstats import StockDataFrame as Sdf
    STOCKSTATS_AVAILABLE = True
except ImportError:
    Sdf = None
    STOCKSTATS_AVAILABLE = False

class StockstatsDataFlow(BaseDataFlow):
    """
    Dataflow for calculating technical indicators using stockstats.
    """
    def __init__(self, config=None):
        super().__init__(config)
        self.best_ind_params = {
            "close_50_sma": "50 SMA: A medium-term trend indicator...",
            "close_200_sma": "200 SMA: A long-term trend benchmark...",
            "close_10_ema": "10 EMA: A responsive short-term average...",
            "macd": "MACD: Computes momentum via differences of EMAs...",
            "macds": "MACD Signal: An EMA smoothing of the MACD line...",
            "macdh": "MACD Histogram: Shows the gap between the MACD line and its signal...",
            "rsi": "RSI: Measures momentum to flag overbought/oversold conditions...",
            "boll": "Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands...",
            "boll_ub": "Bollinger Upper Band: Typically 2 standard deviations above the middle line...",
            "boll_lb": "Bollinger Lower Band: Typically 2 standard deviations below the middle line...",
            "atr": "ATR: Averages true range to measure volatility...",
            "vwma": "VWMA: A moving average weighted by volume...",
            "mfi": "MFI: The Money Flow Index is a momentum indicator...",
        }

    def _get_stock_stats(self, symbol: str, indicator: str, curr_date: str, online: bool) -> str:
        """
        Calculates a technical indicator for a given symbol and date.
        """
        curr_date = datetime.strptime(curr_date, "%Y-%m-%d").strftime("%Y-%m-%d")
        
        try:
            # This logic needs to be updated to use the new YFinanceDataFlow
            # For now, we'll keep the existing logic.
            if not online:
                data = pd.read_csv(f"{self.data_dir}/market_data/price_data/{symbol}-YFin-data-2015-01-01-2025-03-25.csv")
            else:
                # Online fetching logic will be updated later
                return "Online fetching not yet implemented in refactored dataflow."

            if not STOCKSTATS_AVAILABLE:
                raise ImportError("stockstats is required for technical indicators but is not installed.")
                
            df = Sdf.retype(data)
            df[indicator]
            matching_rows = df[df["date"].str.startswith(curr_date)]
            
            if not matching_rows.empty:
                return str(matching_rows[indicator].values[0])
            else:
                return "N/A: Not a trading day (weekend or holiday)"
        except Exception as e:
            return f"Error: {e}"

    def fetch_indicator_window(self, symbol: str, indicator: str, curr_date: str, look_back_days: int, online: bool) -> str:
        """
        Fetches a window of technical indicator data.
        """
        if indicator not in self.best_ind_params:
            raise ValueError(f"Indicator {indicator} is not supported.")
            
        start_date, end_date = self.get_date_range(curr_date, look_back_days)
        
        ind_string = ""
        current_day = datetime.strptime(start_date, "%Y-%m-%d")
        end_day = datetime.strptime(end_date, "%Y-%m-%d")
        
        while current_day <= end_day:
            indicator_value = self._get_stock_stats(symbol, indicator, current_day.strftime("%Y-%m-%d"), online)
            ind_string += f"{current_day.strftime('%Y-%m-%d')}: {indicator_value}\n"
            current_day += pd.Timedelta(days=1)
            
        result_str = (
            f"## {indicator} values from {start_date} to {end_date}:\n\n"
            + ind_string
            + "\n\n"
            + self.best_ind_params.get(indicator, "No description available.")
        )
        return result_str

    def fetch_indicator(self, symbol: str, indicator: str, curr_date: str, online: bool) -> str:
        """
        Fetches a single technical indicator value.
        """
        return self._get_stock_stats(symbol, indicator, curr_date, online) 