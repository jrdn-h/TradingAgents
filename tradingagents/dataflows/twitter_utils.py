"""
Twitter v2 API utilities for sentiment data ingestion.
"""

import asyncio
import json
import logging
from typing import Callable, Dict, List, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

class TwitterStreamClient:
    """Twitter v2 API client for streaming tweets."""
    
    def __init__(self, bearer_token: str, keywords: List[str], callback: Callable):
        self.bearer_token = bearer_token
        self.keywords = keywords
        self.callback = callback
        self.base_url = "https://api.twitter.com/2"
        self.running = False
        self.reconnect_delay = 1
        self.max_reconnect_delay = 60
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Twitter API requests."""
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
        
    async def _get_rules(self) -> List[Dict]:
        """Get current stream rules."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/tweets/search/stream/rules",
                headers=self._get_headers()
            )
            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                logger.error(f"Failed to get rules: {response.status_code}")
                return []
                
    async def _delete_rules(self, rule_ids: List[str]):
        """Delete existing stream rules."""
        if not rule_ids:
            return
            
        async with httpx.AsyncClient() as client:
            payload = {"delete": {"ids": rule_ids}}
            response = await client.post(
                f"{self.base_url}/tweets/search/stream/rules",
                headers=self._get_headers(),
                json=payload
            )
            if response.status_code != 200:
                logger.error(f"Failed to delete rules: {response.status_code}")
                
    async def _add_rules(self, keywords: List[str]):
        """Add new stream rules for keywords."""
        rules = []
        for keyword in keywords:
            rules.append({"value": keyword, "tag": f"crypto_{keyword}"})
            
        async with httpx.AsyncClient() as client:
            payload = {"add": rules}
            response = await client.post(
                f"{self.base_url}/tweets/search/stream/rules",
                headers=self._get_headers(),
                json=payload
            )
            if response.status_code == 201:
                logger.info(f"Added rules for keywords: {keywords}")
            else:
                logger.error(f"Failed to add rules: {response.status_code}")
                
    async def setup_stream(self):
        """Setup Twitter stream with rules."""
        # Get existing rules
        existing_rules = await self._get_rules()
        existing_ids = [rule["id"] for rule in existing_rules]
        
        # Delete existing rules
        await self._delete_rules(existing_ids)
        
        # Add new rules
        await self._add_rules(self.keywords)
        
    async def stream_tweets(self):
        """Stream tweets matching the rules."""
        self.running = True
        while self.running:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    async with client.stream(
                        "GET",
                        f"{self.base_url}/tweets/search/stream",
                        headers=self._get_headers(),
                        params={
                            "tweet.fields": "created_at,author_id,public_metrics,entities",
                            "user.fields": "username,verified",
                            "expansions": "author_id"
                        }
                    ) as response:
                        if response.status_code != 200:
                            logger.error(f"Stream request failed: {response.status_code}")
                            await asyncio.sleep(self.reconnect_delay)
                            continue
                            
                        async for line in response.aiter_lines():
                            if line.strip():
                                try:
                                    data = json.loads(line)
                                    await self.callback(data)
                                except json.JSONDecodeError:
                                    logger.warning(f"Invalid JSON: {line}")
                                    
            except Exception as e:
                logger.error(f"Stream error: {e}")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                
    async def close(self):
        """Stop the stream."""
        self.running = False

async def twitter_stream_listener(bearer_token: str, keywords: List[str], callback: Callable):
    """
    Convenience function to start Twitter stream listener.
    
    Args:
        bearer_token: Twitter API bearer token
        keywords: List of crypto keywords to track
        callback: Async function to process incoming tweets
    """
    client = TwitterStreamClient(bearer_token, keywords, callback)
    await client.setup_stream()
    await client.stream_tweets()

# Example usage and data processing
async def process_twitter_data(data: Dict):
    """Example callback function to process Twitter data."""
    logger.info(f"Received Twitter data: {data}")
    # TODO: Process and store data for sentiment analysis
    # This could include:
    # - Tweet text and metadata
    # - User information
    # - Engagement metrics
    # - Sentiment scoring

# Alternative: Search recent tweets (for backtesting)
async def search_recent_tweets(bearer_token: str, query: str, max_results: int = 100) -> List[Dict]:
    """Search for recent tweets (useful for backtesting)."""
    headers = {"Authorization": f"Bearer {bearer_token}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.twitter.com/2/tweets/search/recent",
            headers=headers,
            params={
                "query": query,
                "max_results": max_results,
                "tweet.fields": "created_at,author_id,public_metrics"
            }
        )
        
        if response.status_code == 200:
            return response.json().get("data", [])
        else:
            logger.error(f"Search failed: {response.status_code}")
            return [] 