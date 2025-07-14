"""
News RSS utilities for crypto news data ingestion.
"""

import asyncio
import logging
from typing import Callable, Dict, List, Optional
import httpx
import feedparser
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class NewsRSSClient:
    """RSS client for crypto news feeds."""
    
    def __init__(self, feeds: List[Dict], callback: Callable):
        self.feeds = feeds  # List of {"name": str, "url": str, "keywords": List[str]}
        self.callback = callback
        self.running = False
        self.last_check = {}
        self.check_interval = 300  # 5 minutes
        
    async def fetch_feed(self, feed: Dict) -> List[Dict]:
        """Fetch and parse a single RSS feed."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(feed["url"])
                response.raise_for_status()
                
                # Parse RSS feed
                feed_data = feedparser.parse(response.text)
                articles = []
                
                for entry in feed_data.entries:
                    # Check if article is recent (within last hour)
                    pub_date = getattr(entry, 'published_parsed', None)
                    if pub_date:
                        pub_datetime = datetime(*pub_date[:6])
                        if datetime.now() - pub_datetime > timedelta(hours=1):
                            continue
                    
                    # Check if article contains relevant keywords
                    title = getattr(entry, 'title', '').lower()
                    summary = getattr(entry, 'summary', '').lower()
                    content = f"{title} {summary}"
                    
                    if any(keyword.lower() in content for keyword in feed.get("keywords", [])):
                        article = {
                            "title": getattr(entry, 'title', ''),
                            "summary": getattr(entry, 'summary', ''),
                            "link": getattr(entry, 'link', ''),
                            "published": getattr(entry, 'published', ''),
                            "source": feed["name"],
                            "keywords_found": [k for k in feed.get("keywords", []) if k.lower() in content]
                        }
                        articles.append(article)
                        
                return articles
                
        except Exception as e:
            logger.error(f"Failed to fetch feed {feed['name']}: {e}")
            return []
            
    async def monitor_feeds(self):
        """Monitor all feeds for new articles."""
        self.running = True
        while self.running:
            try:
                for feed in self.feeds:
                    articles = await self.fetch_feed(feed)
                    for article in articles:
                        await self.callback(article)
                        
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Feed monitoring error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
                
    async def close(self):
        """Stop monitoring feeds."""
        self.running = False

async def news_rss_listener(feeds: List[Dict], callback: Callable):
    """
    Convenience function to start news RSS listener.
    
    Args:
        feeds: List of feed configurations
        callback: Async function to process incoming articles
    """
    client = NewsRSSClient(feeds, callback)
    await client.monitor_feeds()

# Predefined crypto news feeds
CRYPTO_NEWS_FEEDS = [
    {
        "name": "CoinDesk",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "keywords": ["bitcoin", "ethereum", "crypto", "defi", "nft", "blockchain"]
    },
    {
        "name": "CoinTelegraph",
        "url": "https://cointelegraph.com/rss",
        "keywords": ["bitcoin", "ethereum", "crypto", "defi", "nft", "blockchain"]
    },
    {
        "name": "Decrypt",
        "url": "https://decrypt.co/feed",
        "keywords": ["bitcoin", "ethereum", "crypto", "defi", "nft", "blockchain"]
    }
]

# Example usage and data processing
async def process_news_data(article: Dict):
    """Example callback function to process news articles."""
    logger.info(f"Received news article: {article['title']}")
    # TODO: Process and store data for news sentiment analysis
    # This could include:
    # - Article title and content
    # - Source credibility
    # - Sentiment scoring
    # - Impact assessment

# Alternative: Fetch recent articles (for backtesting)
async def fetch_recent_news(feeds: List[Dict], hours_back: int = 24) -> List[Dict]:
    """Fetch recent news articles from all feeds (useful for backtesting)."""
    all_articles = []
    
    for feed in feeds:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(feed["url"])
                response.raise_for_status()
                
                feed_data = feedparser.parse(response.text)
                
                for entry in feed_data.entries:
                    pub_date = getattr(entry, 'published_parsed', None)
                    if pub_date:
                        pub_datetime = datetime(*pub_date[:6])
                        if datetime.now() - pub_datetime <= timedelta(hours=hours_back):
                            title = getattr(entry, 'title', '').lower()
                            summary = getattr(entry, 'summary', '').lower()
                            content = f"{title} {summary}"
                            
                            if any(keyword.lower() in content for keyword in feed.get("keywords", [])):
                                article = {
                                    "title": getattr(entry, 'title', ''),
                                    "summary": getattr(entry, 'summary', ''),
                                    "link": getattr(entry, 'link', ''),
                                    "published": getattr(entry, 'published', ''),
                                    "source": feed["name"],
                                    "keywords_found": [k for k in feed.get("keywords", []) if k.lower() in content]
                                }
                                all_articles.append(article)
                                
        except Exception as e:
            logger.error(f"Failed to fetch feed {feed['name']}: {e}")
            
    return all_articles 