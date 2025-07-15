import os
import json
import re
from datetime import datetime
from .base_dataflow import BaseDataFlow
from typing import List, Dict, Any
from tqdm import tqdm
from dateutil.relativedelta import relativedelta

class RedditDataFlow(BaseDataFlow):
    """
    Dataflow for fetching data from Reddit.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.ticker_to_company = {
            "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Google", "AMZN": "Amazon", "TSLA": "Tesla",
            "NVDA": "Nvidia", "TSM": "Taiwan Semiconductor Manufacturing Company OR TSMC", "JPM": "JPMorgan Chase OR JP Morgan",
            "JNJ": "Johnson & Johnson OR JNJ", "V": "Visa", "WMT": "Walmart", "META": "Meta OR Facebook",
            "AMD": "AMD", "INTC": "Intel", "QCOM": "Qualcomm", "BABA": "Alibaba", "ADBE": "Adobe",
            "NFLX": "Netflix", "CRM": "Salesforce", "PYPL": "PayPal", "PLTR": "Palantir", "MU": "Micron",
            "SQ": "Block OR Square", "ZM": "Zoom", "CSCO": "Cisco", "SHOP": "Shopify", "ORCL": "Oracle",
            "X": "Twitter OR X", "SPOT": "Spotify", "AVGO": "Broadcom", "ASML": "ASML", "TWLO": "Twilio",
            "SNAP": "Snap Inc.", "TEAM": "Atlassian", "SQSP": "Squarespace", "UBER": "Uber", "ROKU": "Roku",
            "PINS": "Pinterest",
        }

    def _fetch_top_from_category(self, category: str, date: str, max_limit: int, query: str = None) -> List[Dict[str, Any]]:
        """
        Fetches top posts from a given category.
        """
        base_path = os.path.join(self.data_dir, "reddit_data")
        category_path = os.path.join(base_path, category)
        
        if not os.path.exists(category_path):
            return []

        all_content = []
        files = [f for f in os.listdir(category_path) if f.endswith(".jsonl")]
        if not files:
            return []

        limit_per_subreddit = max_limit // len(files)

        for data_file in files:
            all_content_curr_subreddit = []
            with open(os.path.join(category_path, data_file), "rb") as f:
                for line in f:
                    if not line.strip():
                        continue
                    parsed_line = json.loads(line)
                    post_date = datetime.utcfromtimestamp(parsed_line["created_utc"]).strftime("%Y-%m-%d")
                    if post_date != date:
                        continue
                    if "company" in category and query:
                        search_terms = self.ticker_to_company.get(query, query).split(" OR ")
                        search_terms.append(query)
                        if not any(re.search(term, parsed_line["title"], re.IGNORECASE) or re.search(term, parsed_line["selftext"], re.IGNORECASE) for term in search_terms):
                            continue
                    all_content_curr_subreddit.append({
                        "title": parsed_line["title"], "content": parsed_line["selftext"],
                        "url": parsed_line["url"], "upvotes": parsed_line["ups"], "posted_date": post_date,
                    })
            all_content_curr_subreddit.sort(key=lambda x: x["upvotes"], reverse=True)
            all_content.extend(all_content_curr_subreddit[:limit_per_subreddit])
        return all_content

    def fetch_global_news(self, curr_date: str, look_back_days: int, max_limit_per_day: int) -> str:
        """
        Fetches global news from Reddit.
        """
        start_date, end_date = self.get_date_range(curr_date, look_back_days)
        start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        posts = []
        total_iterations = (end_date_dt - start_date_dt).days + 1
        pbar = tqdm(desc=f"Getting Global News on {end_date}", total=total_iterations)
        
        for i in range(total_iterations):
            curr_day = (start_date_dt + relativedelta(days=i)).strftime("%Y-%m-%d")
            fetch_result = self._fetch_top_from_category("global_news", curr_day, max_limit_per_day)
            posts.extend(fetch_result)
            pbar.update(1)
        pbar.close()

        if not posts:
            return ""
            
        news_str = "".join(f"### {post['title']}\n\n{post['content'] if post['content'] else ''}\n\n" for post in posts)
        return f"## Global News Reddit, from {start_date} to {end_date}:\n{news_str}"

    def fetch_company_news(self, ticker: str, curr_date: str, look_back_days: int, max_limit_per_day: int) -> str:
        """
        Fetches company specific news from Reddit.
        """
        start_date, end_date = self.get_date_range(curr_date, look_back_days)
        start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")

        posts = []
        total_iterations = (end_date_dt - start_date_dt).days + 1
        pbar = tqdm(desc=f"Getting Company News for {ticker} on {end_date}", total=total_iterations)

        for i in range(total_iterations):
            curr_day = (start_date_dt + relativedelta(days=i)).strftime("%Y-%m-%d")
            fetch_result = self._fetch_top_from_category("company_news", curr_day, max_limit_per_day, ticker)
            posts.extend(fetch_result)
            pbar.update(1)
        pbar.close()

        if not posts:
            return ""

        news_str = "".join(f"### {post['title']}\n\n{post['content'] if post['content'] else ''}\n\n" for post in posts)
        return f"## {ticker} News Reddit, from {start_date} to {end_date}:\n\n{news_str}" 