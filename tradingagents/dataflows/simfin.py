import os
import pandas as pd
from .base_dataflow import BaseDataFlow
from datetime import datetime

class SimFinDataFlow(BaseDataFlow):
    """
    Dataflow for fetching data from SimFin.
    """

    def _get_latest_report(self, ticker: str, freq: str, curr_date: str, report_type: str) -> pd.Series:
        """
        Gets the latest financial report for a given ticker and frequency.
        """
        data_path = os.path.join(
            self.data_dir,
            "fundamental_data",
            "simfin_data_all",
            report_type,
            "companies",
            "us",
            f"us-{report_type.replace('_', '')}-{freq}.csv",
        )
        df = self.read_csv(data_path, sep=";")

        # Convert date strings to datetime objects and remove any time components
        df["Report Date"] = pd.to_datetime(df["Report Date"], utc=True).dt.normalize()
        df["Publish Date"] = pd.to_datetime(df["Publish Date"], utc=True).dt.normalize()

        # Convert the current date to datetime and normalize
        curr_date_dt = pd.to_datetime(curr_date, utc=True).normalize()

        # Filter the DataFrame for the given ticker and for reports that were published on or before the current date
        filtered_df = df[(df["Ticker"] == ticker) & (df["Publish Date"] <= curr_date_dt)]

        if filtered_df.empty:
            return None

        # Get the most recent report by selecting the row with the latest Publish Date
        return filtered_df.loc[filtered_df["Publish Date"].idxmax()]

    def fetch_balance_sheet(self, ticker: str, freq: str, curr_date: str) -> str:
        """
        Fetches the latest balance sheet for a given ticker.
        """
        latest_balance_sheet = self._get_latest_report(ticker, freq, curr_date, "balance_sheet")

        if latest_balance_sheet is None:
            return "No balance sheet available before the given current date."

        latest_balance_sheet = latest_balance_sheet.drop("SimFinId")
        return (
            f"## {freq} balance sheet for {ticker} released on {str(latest_balance_sheet['Publish Date'])[0:10]}: \n"
            + str(latest_balance_sheet)
            + "\n\nThis includes metadata like reporting dates and currency, share details, and a breakdown of assets, liabilities, and equity. Assets are grouped as current (liquid items like cash and receivables) and noncurrent (long-term investments and property). Liabilities are split between short-term obligations and long-term debts, while equity reflects shareholder funds such as paid-in capital and retained earnings. Together, these components ensure that total assets equal the sum of liabilities and equity."
        )

    def fetch_cash_flow(self, ticker: str, freq: str, curr_date: str) -> str:
        """
        Fetches the latest cash flow statement for a given ticker.
        """
        latest_cash_flow = self._get_latest_report(ticker, freq, curr_date, "cash_flow")

        if latest_cash_flow is None:
            return "No cash flow statement available before the given current date."
        
        latest_cash_flow = latest_cash_flow.drop("SimFinId")
        return (
            f"## {freq} cash flow statement for {ticker} released on {str(latest_cash_flow['Publish Date'])[0:10]}: \n"
            + str(latest_cash_flow)
            + "\n\nThis includes metadata like reporting dates and currency, share details, and a breakdown of cash movements. Operating activities show cash generated from core business operations, including net income adjustments for non-cash items and working capital changes. Investing activities cover asset acquisitions/disposals and investments. Financing activities include debt transactions, equity issuances/repurchases, and dividend payments. The net change in cash represents the overall increase or decrease in the company's cash position during the reporting period."
        )

    def fetch_income_statement(self, ticker: str, freq: str, curr_date: str) -> str:
        """
        Fetches the latest income statement for a given ticker.
        """
        latest_income = self._get_latest_report(ticker, freq, curr_date, "income_statements")

        if latest_income is None:
            return "No income statement available before the given current date."

        latest_income = latest_income.drop("SimFinId")
        return (
            f"## {freq} income statement for {ticker} released on {str(latest_income['Publish Date'])[0:10]}: \n"
            + str(latest_income)
            + "\n\nThis includes metadata like reporting dates and currency, share details, and a comprehensive breakdown of the company's financial performance. Starting with Revenue, it shows Cost of Revenue and resulting Gross Profit. Operating Expenses are detailed, including SG&A, R&D, and Depreciation. The statement then shows Operating Income, followed by non-operating items and Interest Expense, leading to Pretax Income. After accounting for Income Tax and any Extraordinary items, it concludes with Net Income, representing the company's bottom-line profit or loss for the period."
        ) 