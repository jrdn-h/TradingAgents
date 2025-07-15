import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result,
)
from .base_dataflow import BaseDataFlow

class GoogleNewsDataFlow(BaseDataFlow):
    """
    Dataflow for fetching news from Google News.
    """

    def _is_rate_limited(self, response):
        """Check if the response indicates rate limiting (status code 429)"""
        return response.status_code == 429

    @retry(
        retry=(retry_if_result(_is_rate_limited)),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
    )
    def _make_request(self, url, headers):
        """Make a request with retry logic for rate limiting"""
        time.sleep(random.uniform(2, 6))
        return requests.get(url, headers=headers)

    def _get_news_data(self, query, start_date, end_date):
        """
        Scrape Google News search results for a given query and date range.
        """
        if "-" in start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%m/%d/%Y")
        if "-" in end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").strftime("%m/%d/%Y")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36"
        }

        news_results = []
        page = 0
        while True:
            offset = page * 10
            url = f"https://www.google.com/search?q={query}&tbs=cdr:1,cd_min:{start_date},cd_max:{end_date}&tbm=nws&start={offset}"
            try:
                response = self._make_request(url, headers)
                soup = BeautifulSoup(response.content, "html.parser")
                results_on_page = soup.select("div.SoaBEf")
                if not results_on_page:
                    break
                for el in results_on_page:
                    try:
                        news_results.append({
                            "link": el.find("a")["href"],
                            "title": el.select_one("div.MBeuO").get_text(),
                            "snippet": el.select_one(".GI74Re").get_text(),
                            "date": el.select_one(".LfVVr").get_text(),
                            "source": el.select_one(".NUnG9d span").get_text(),
                        })
                    except Exception as e:
                        continue
                if not soup.find("a", id="pnnext"):
                    break
                page += 1
            except Exception as e:
                break
        return news_results

    def fetch_data(self, query: str, curr_date: str, look_back_days: int) -> str:
        """
        Fetches news from Google News.
        """
        query = query.replace(" ", "+")
        start_date, end_date = self.get_date_range(curr_date, look_back_days)
        news_results = self._get_news_data(query, start_date, end_date)
        news_str = ""
        for news in news_results:
            news_str += f"### {news['title']} (source: {news['source']}) \n\n{news['snippet']}\n\n"
        if not news_results:
            return ""
        return f"## {query} Google News, from {start_date} to {end_date}:\n\n{news_str}" 