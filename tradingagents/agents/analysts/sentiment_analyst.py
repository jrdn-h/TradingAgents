"""
Sentiment analysis agent for social media and news data.
"""

import asyncio
import os
import re
import math
from typing import Dict, Any, List
from ..base_agent import BaseAgent
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List
from ...sentiment.model import Sentiment

# Optional dependency guard: https://stackoverflow.com/q/77512072
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Optional dependency guard: https://stackoverflow.com/q/77512072
try:
    from transformers import pipeline
except ImportError:
    pipeline = None

# For local sentiment analysis, we use the FinBERT model pre-trained on financial text.
# https://huggingface.co/ProsusAI/finbert
FINBERT_MODEL = "ProsusAI/finbert"

BULLISH_KEYWORDS = ["moon", "bull", "pump", "rally", "🚀", "moonshot", "ATH", "to the moon"]
BEARISH_KEYWORDS = ["dump", "bear", "crash", "rekt", "panic", "rug", "downtrend", "💀"]

BULLISH_EXEMPLAR = "Bitcoin to the moon! 🚀 Bullish rally, ATH soon."
BEARISH_EXEMPLAR = "Crypto crash, panic sell, bear market, rekt. 💀"

class SentimentAnalyst(BaseAgent):
    """Agent for analyzing sentiment from social media and news data."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__("sentiment_analyst", model)
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        if OPENAI_AVAILABLE and self.openai_key:
            openai.api_key = self.openai_key

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        tweets = input_data.get("tweets", [])
        news = input_data.get("news", [])
        social_media = input_data.get("social_media", [])
        all_texts = [tweet.get("text", "") for tweet in tweets]
        # Try OpenAI embeddings if available
        if OPENAI_AVAILABLE and self.openai_key:
            try:
                result = await self.embedding_sentiment_score(all_texts)
                method = "embedding"
            except Exception as e:
                result = self.heuristic_sentiment_score(tweets)
                method = f"heuristic (embedding error: {e})"
        else:
            result = self.heuristic_sentiment_score(tweets)
            method = "heuristic"
        # Compose output schema
        return {
            "sentiment": result["sentiment"],
            "score": result["score"],
            "confidence": result["confidence"],
            "rationale": result["rationale"] + f" (method: {method})",
            "data_sources": {
                "tweets_analyzed": len(tweets),
                "news_analyzed": len(news),
                "social_media_analyzed": len(social_media)
            },
            "keywords_found": result.get("keywords_found", []),
            "timestamp": result.get("timestamp", "")
        }

    def heuristic_sentiment_score(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        bullish, bearish = 0, 0
        found_keywords = set()
        for tweet in tweets:
            text = tweet.get("text", "").lower()
            for word in BULLISH_KEYWORDS:
                if word.lower() in text:
                    bullish += 1
                    found_keywords.add(word)
            for word in BEARISH_KEYWORDS:
                if word.lower() in text:
                    bearish += 1
                    found_keywords.add(word)
        total = bullish + bearish
        if total == 0:
            sentiment, score = "neutral", 50
        elif bullish > bearish:
            sentiment, score = "bullish", 70
        elif bearish > bullish:
            sentiment, score = "bearish", 30
        else:
            sentiment, score = "neutral", 50
        confidence = min(1.0, total / max(1, len(tweets)))
        rationale = f"Bullish: {bullish}, Bearish: {bearish}, Total: {total}"
        return {
            "sentiment": sentiment,
            "score": score,
            "confidence": confidence,
            "rationale": rationale,
            "keywords_found": list(found_keywords),
            "timestamp": ""
        }

    async def embedding_sentiment_score(self, texts: List[str]) -> Dict[str, Any]:
        # Get exemplars
        bullish_vec = await self._get_embedding(BULLISH_EXEMPLAR)
        bearish_vec = await self._get_embedding(BEARISH_EXEMPLAR)
        # Average embedding for all tweets
        if not texts:
            return {"sentiment": "neutral", "score": 50, "confidence": 0.5, "rationale": "No tweets.", "keywords_found": [], "timestamp": ""}
        tweet_vecs = [await self._get_embedding(t) for t in texts]
        avg_vec = [sum(x)/len(x) for x in zip(*tweet_vecs)]
        sim_bull = cosine_similarity(avg_vec, bullish_vec)
        sim_bear = cosine_similarity(avg_vec, bearish_vec)
        # Sentiment logic
        score = 50
        if sim_bull - sim_bear > 0.25:
            sentiment, score = "bullish", 70
        elif sim_bear - sim_bull > 0.25:
            sentiment, score = "bearish", 30
        else:
            sentiment, score = "neutral", 50
        confidence = min(1.0, abs(sim_bull - sim_bear))
        rationale = f"Cosine sim to bullish: {sim_bull:.2f}, bearish: {sim_bear:.2f}"
        return {
            "sentiment": sentiment,
            "score": score,
            "confidence": confidence,
            "rationale": rationale,
            "keywords_found": [],
            "timestamp": ""
        }

    async def _get_embedding(self, text: str) -> List[float]:
        # OpenAI async embedding call
        resp = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: openai.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding
        )
        return resp

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    dot = sum(a*b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a*a for a in vec1))
    norm2 = math.sqrt(sum(b*b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2) 