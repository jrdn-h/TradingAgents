import os
import pytest
from tradingagents.agents.analysts.sentiment_analyst import SentimentAnalyst

@pytest.fixture
def bullish_tweet():
    return [{"text": "🚀 BTC to the moon!"}]

@pytest.mark.asyncio
async def test_heuristic_bullish(monkeypatch, bullish_tweet):
    # Remove OPENAI_API_KEY to force heuristic
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    agent = SentimentAnalyst()
    result = await agent.run({"tweets": bullish_tweet})
    assert "sentiment" in result
    assert "score" in result
    assert result["score"] > 60
    assert result["sentiment"] == "bullish"
    assert "heuristic" in result["rationale"]

@pytest.mark.asyncio
async def test_embedding_bullish(monkeypatch, bullish_tweet):
    # Patch embedding_sentiment_score to simulate embedding path
    monkeypatch.setitem(os.environ, "OPENAI_API_KEY", "sk-test")
    agent = SentimentAnalyst()
    async def fake_embedding_score(texts):
        return {"sentiment": "bullish", "score": 80, "confidence": 0.9, "rationale": "simulated embedding", "keywords_found": [], "timestamp": ""}
    agent.embedding_sentiment_score = fake_embedding_score
    result = await agent.run({"tweets": bullish_tweet})
    assert result["score"] > 60
    assert result["sentiment"] == "bullish"
    assert "embedding" in result["rationale"]

@pytest.mark.asyncio
async def test_schema_validation(bullish_tweet, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    agent = SentimentAnalyst()
    result = await agent.run({"tweets": bullish_tweet})
    allowed = {"bullish", "neutral", "bearish"}
    assert result["sentiment"] in allowed
    for key in ["sentiment", "score", "confidence", "rationale", "data_sources", "keywords_found", "timestamp"]:
        assert key in result 