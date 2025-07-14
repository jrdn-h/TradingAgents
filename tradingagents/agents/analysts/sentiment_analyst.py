"""
Sentiment analysis agent for social media and news data.
"""

import asyncio
from typing import Dict, Any, List
from ..base_agent import BaseAgent

class SentimentAnalyst(BaseAgent):
    """Agent for analyzing sentiment from social media and news data."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__("sentiment_analyst", model)
        
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze sentiment from input data.
        
        Args:
            input_data: Dictionary containing:
                - tweets: List of tweet data
                - news: List of news articles
                - social_media: Other social media data
                
        Returns:
            Dictionary with sentiment analysis results
        """
        # TODO: Implement actual sentiment analysis logic
        # For now, return hard-coded response matching project overview schema
        
        # Extract data from input
        tweets = input_data.get("tweets", [])
        news = input_data.get("news", [])
        social_media = input_data.get("social_media", [])
        
        # Mock sentiment analysis
        sentiment_score = self._calculate_mock_sentiment(tweets, news, social_media)
        
        # Determine sentiment category
        if sentiment_score >= 70:
            sentiment = "bullish"
        elif sentiment_score >= 40:
            sentiment = "neutral"
        else:
            sentiment = "bearish"
            
        return {
            "sentiment": sentiment,
            "score": sentiment_score,
            "confidence": 0.85,
            "rationale": f"Analyzed {len(tweets)} tweets, {len(news)} news articles, and {len(social_media)} social media posts. Overall sentiment is {sentiment} with score {sentiment_score}.",
            "data_sources": {
                "tweets_analyzed": len(tweets),
                "news_analyzed": len(news),
                "social_media_analyzed": len(social_media)
            },
            "keywords_found": ["bitcoin", "ethereum", "crypto"],
            "timestamp": "2024-06-10T12:34:56Z"
        }
        
    def _calculate_mock_sentiment(self, tweets: List, news: List, social_media: List) -> int:
        """Mock sentiment calculation based on data volume and content."""
        # Simple mock logic: more positive data = higher score
        total_items = len(tweets) + len(news) + len(social_media)
        
        if total_items == 0:
            return 50  # Neutral if no data
            
        # Mock positive bias for demo
        base_score = 60
        
        # Adjust based on data volume (more data = more confidence)
        volume_bonus = min(total_items * 2, 20)
        
        # Mock keyword analysis
        positive_keywords = ["bull", "moon", "pump", "buy", "long"]
        negative_keywords = ["bear", "dump", "sell", "short", "crash"]
        
        # Count keywords in all text data
        all_text = " ".join([
            str(tweet.get("text", "")) for tweet in tweets
        ] + [
            str(article.get("title", "") + " " + article.get("summary", "")) for article in news
        ]).lower()
        
        positive_count = sum(1 for keyword in positive_keywords if keyword in all_text)
        negative_count = sum(1 for keyword in negative_keywords if keyword in all_text)
        
        keyword_score = (positive_count - negative_count) * 5
        
        final_score = base_score + volume_bonus + keyword_score
        
        # Clamp to 0-100 range
        return max(0, min(100, final_score)) 