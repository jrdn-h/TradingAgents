from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import os
from .config import get_config

class BaseDataFlow(ABC):
    """
    Abstract base class for all dataflow utilities.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or get_config()
        self.data_dir = self.config.get("data_dir", "./data")

    @abstractmethod
    def fetch_data(self, *args, **kwargs) -> Any:
        """
        Fetches data from the data source.
        """
        pass

    def get_date_range(self, curr_date: str, look_back_days: int) -> (str, str):
        """
        Calculates a date range based on the current date and a look-back period.
        """
        end_date = datetime.strptime(curr_date, "%Y-%m-%d")
        start_date = end_date - relativedelta(days=look_back_days)
        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

    def read_csv(self, file_path: str) -> pd.DataFrame:
        """
        Reads a CSV file into a pandas DataFrame.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        return pd.read_csv(file_path) 