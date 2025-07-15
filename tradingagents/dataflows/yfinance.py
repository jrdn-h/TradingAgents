import pandas as pd
from .base_dataflow import BaseDataFlow
from datetime import datetime

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None
    YFINANCE_AVAILABLE = False

class YFinanceDataFlow(BaseDataFlow):
    """
    Dataflow for fetching data from Yahoo Finance.
    """

    def fetch_data_online(self, symbol: str, start_date: str, end_date: str) -> str:
        """
        Fetches historical data from Yahoo Finance.
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance is required to fetch stock data but is not installed. Install with: pip install yfinance")
        
        ticker = yf.Ticker(symbol.upper())
        data = ticker.history(start=start_date, end=end_date)
        
        if data.empty:
            return f"No data found for symbol '{symbol}' between {start_date} and {end_date}"
        
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)
            
        numeric_columns = ["Open", "High", "Low", "Close", "Adj Close"]
        for col in numeric_columns:
            if col in data.columns:
                data[col] = data[col].round(2)
                
        csv_string = data.to_csv()
        header = f"# Stock data for {symbol.upper()} from {start_date} to {end_date}\n"
        header += f"# Total records: {len(data)}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return header + csv_string

    def fetch_data_offline(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetches historical data from a local CSV file.
        """
        file_path = f"{self.data_dir}/market_data/price_data/{symbol}-YFin-data-2015-01-01-2025-03-25.csv"
        data = self.read_csv(file_path)
        
        if end_date > "2025-03-25":
            raise Exception(f"Get_YFin_Data: {end_date} is outside of the data range of 2015-01-01 to 2025-03-25")
            
        data["DateOnly"] = data["Date"].str[:10]
        filtered_data = data[(data["DateOnly"] >= start_date) & (data["DateOnly"] <= end_date)]
        filtered_data = filtered_data.drop("DateOnly", axis=1)
        return filtered_data.reset_index(drop=True) 