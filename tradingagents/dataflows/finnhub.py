import json
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from .base_dataflow import BaseDataFlow

class FinnhubDataFlow(BaseDataFlow):
    """
    Dataflow for fetching data from Finnhub.
    """

    def _get_data_in_range(self, ticker, start_date, end_date, data_type, period=None):
        """
        Gets finnhub data saved and processed on disk.
        """
        if period:
            data_path = os.path.join(
                self.data_dir,
                "finnhub_data",
                data_type,
                f"{ticker}_{period}_data_formatted.json",
            )
        else:
            data_path = os.path.join(
                self.data_dir, "finnhub_data", data_type, f"{ticker}_data_formatted.json"
            )

        with open(data_path, "r") as f:
            data = json.load(f)

        # filter keys (date, str in format YYYY-MM-DD) by the date range (str, str in format YYYY-MM-DD)
        filtered_data = {}
        for key, value in data.items():
            if start_date <= key <= end_date and len(value) > 0:
                filtered_data[key] = value
        return filtered_data

    def fetch_news(self, ticker: str, curr_date: str, look_back_days: int) -> str:
        """
        Fetches news for a given ticker.
        """
        start_date, end_date = self.get_date_range(curr_date, look_back_days)
        result = self._get_data_in_range(ticker, start_date, end_date, "news_data")

        if not result:
            return ""

        combined_result = ""
        for day, data in result.items():
            if not data:
                continue
            for entry in data:
                current_news = f"### {entry['headline']} ({day})\n{entry['summary']}"
                combined_result += current_news + "\n\n"

        return f"## {ticker} News, from {start_date} to {end_date}:\n{combined_result}"

    def fetch_insider_sentiment(self, ticker: str, curr_date: str, look_back_days: int) -> str:
        """
        Fetches insider sentiment for a given ticker.
        """
        start_date, end_date = self.get_date_range(curr_date, look_back_days)
        data = self._get_data_in_range(ticker, start_date, end_date, "insider_senti")

        if not data:
            return ""

        result_str = ""
        seen_dicts = []
        for date, senti_list in data.items():
            for entry in senti_list:
                if entry not in seen_dicts:
                    result_str += f"### {entry['year']}-{entry['month']}:\nChange: {entry['change']}\nMonthly Share Purchase Ratio: {entry['mspr']}\n\n"
                    seen_dicts.append(entry)

        return (
            f"## {ticker} Insider Sentiment Data for {start_date} to {end_date}:\n"
            + result_str
            + "The change field refers to the net buying/selling from all insiders' transactions. The mspr field refers to monthly share purchase ratio."
        )

    def fetch_insider_transactions(self, ticker: str, curr_date: str, look_back_days: int) -> str:
        """
        Fetches insider transactions for a given ticker.
        """
        start_date, end_date = self.get_date_range(curr_date, look_back_days)
        data = self._get_data_in_range(ticker, start_date, end_date, "insider_trans")

        if not data:
            return ""

        result_str = ""
        seen_dicts = []
        for date, senti_list in data.items():
            for entry in senti_list:
                if entry not in seen_dicts:
                    result_str += f"### Filing Date: {entry['filingDate']}, {entry['name']}:\nChange:{entry['change']}\nShares: {entry['share']}\nTransaction Price: {entry['transactionPrice']}\nTransaction Code: {entry['transactionCode']}\n\n"
                    seen_dicts.append(entry)

        return (
            f"## {ticker} insider transactions from {start_date} to {end_date}:\n"
            + result_str
            + "The change field reflects the variation in share count—here a negative number indicates a reduction in holdings—while share specifies the total number of shares involved. The transactionPrice denotes the per-share price at which the trade was executed, and transactionDate marks when the transaction occurred. The name field identifies the insider making the trade, and transactionCode (e.g., S for sale) clarifies the nature of the transaction. FilingDate records when the transaction was officially reported, and the unique id links to the specific SEC filing, as indicated by the source. Additionally, the symbol ties the transaction to a particular company, isDerivative flags whether the trade involves derivative securities, and currency notes the currency context of the transaction."
        ) 