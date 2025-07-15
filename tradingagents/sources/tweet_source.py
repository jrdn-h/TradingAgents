from typing import AsyncGenerator, List, Dict, Any, Literal, Optional
from abc import ABC, abstractmethod
from datetime import datetime
from pydantic import BaseModel
import logging

from tradingagents.backtest.metrics import backoffs_total_counter
logger = logging.getLogger("TwikitSource")

# --- Tweet and SentimentResult Schemas ---
class Tweet(BaseModel):
    id: str
    created_at: datetime
    author: str
    text: str
    raw_json: dict
    
    @classmethod
    def from_twikit(cls, twikit_tweet):
        """Create Tweet from Twikit tweet object."""
        from datetime import datetime
        
        # Parse the date string to datetime with proper timezone handling
        created = twikit_tweet.created_at
        if isinstance(created, str):
            try:
                # Parse with timezone: "Tue Jul 15 00:07:52 +0000 2025"
                created_at = datetime.strptime(created, "%a %b %d %H:%M:%S %z %Y")
            except Exception as e:
                logger.warning(f"Date parsing failed: {created}, error: {e}")
                created_at = datetime.now()  # Fallback
        else:
            created_at = created
        
        return cls(
            id=str(twikit_tweet.id),
            created_at=created_at,
            author=getattr(twikit_tweet.user, "screen_name", getattr(twikit_tweet.user, "name", "unknown")),
            text=twikit_tweet.text,
            raw_json=twikit_tweet.dict() if hasattr(twikit_tweet, 'dict') else twikit_tweet.__dict__
        )

# SentimentResult is now defined in tradingagents.sentiment.model

# --- Abstract TweetSource ---
class TweetSource(ABC):
    @abstractmethod
    async def stream(self) -> AsyncGenerator[Tweet, None]:
        """Yield tweets as they arrive (live or replay)."""
        pass

# --- TwikitSource: Live Twitter Scraper (no API key) ---
class TwikitSource(TweetSource):
    def __init__(self, filters: list[str] | None = None, query: str = "bitcoin", lang: str = "en-US"):
        import os
        self.username = os.environ.get("TWIKIT_USERNAME")
        self.password = os.environ.get("TWIKIT_PASSWORD")
        self.query = query
        self.lang = lang
        self.filters = filters or ["BTC", "ETH", "SOL", "$", "bitcoin", "ethereum"]
        self._client = None
        
        if not self.username or not self.password:
            raise ValueError("Set TWIKIT_USERNAME and TWIKIT_PASSWORD environment variables")

    async def _ensure_login(self):
        if self._client is not None:
            return self._client
        from twikit import Client
        import asyncio
        self._client = Client(self.lang)
        await self._client.login(
            auth_info_1=self.username,
            auth_info_2=self.username,  # Use username as both fields
            password=self.password,
            cookies_file="twikit_cookies.json"
        )
        return self._client

    async def stream(self) -> AsyncGenerator[Tweet, None]:
        import asyncio
        import random
        
        count = 0
        while True:  # Reconnect loop
            try:
                client = await self._ensure_login()
                logger.info(f"TwikitSource: Starting stream with filters: {self.filters}")
                
                # Use search_tweet for now; can be replaced with streaming logic
                tweets = await client.search_tweet(self.query, "Latest")
                
                for t in tweets:
                    txt = t.text
                    
                    # Apply filters
                    if self.filters and not any(f.lower() in txt.lower() for f in self.filters):
                        continue
                    
                    # Create Tweet using the factory method
                    tweet = Tweet.from_twikit(t)
                    yield tweet
                    count += 1
                    
                    # Rate limiting: ~120 tweets/min max
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"TwikitSource error: {e}")
                
                # Handle rate limiting specifically
                if "429" in str(e) or "Rate limit" in str(e) or "TooManyRequests" in str(e):
                    backoffs_total_counter.inc()
                    wait = random.randint(30, 60)  # Random backoff 30-60s
                    logger.warning(f"429 – backing off for {wait}s")
                    await asyncio.sleep(wait)
                    continue
                elif "404" in str(e):
                    backoffs_total_counter.inc()
                    # Guest token expired - refresh and retry
                    logger.warning("404 - guest token expired, refreshing...")
                    await asyncio.sleep(30)  # Wait for token refresh
                    self._client = None  # Force re-login
                    continue
                else:
                    # Other errors: shorter backoff and force re-login
                    await asyncio.sleep(5)
                    self._client = None  # Force re-login

# --- CSVReplaySource: Offline/Backtest/CI ---
class CSVReplaySource(TweetSource):
    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    async def stream(self) -> AsyncGenerator[Tweet, None]:
        import csv
        import asyncio
        with open(self.csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tweet = Tweet(
                    id=row["id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    author=row["author"],
                    text=row["text"],
                    raw_json=row  # Store the whole row for traceability
                )
                yield tweet
                await asyncio.sleep(0.1)  # Simulate streaming 