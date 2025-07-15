import pytest
from typing import Dict, Any
from tradingagents.agents.analysts.sentiment_analyst import SentimentAnalyst
from tradingagents.agents.analysts.technical_analyst import TechnicalAnalyst

@pytest.fixture
def sample_market_data() -> Dict[str, Any]:
    """Sample market data for testing."""
    return {
        "price_data": {
            "BTC": {"price": 46500, "volume": 1000000, "change_24h": 0.05}
        },
        "indicators": {
            "rsi": 65.5,
            "macd": "bullish",
            "bollinger_bands": "upper_band_touch"
        },
        "order_book": {
            "bids": [[46400, 100], [46300, 200]],
            "asks": [[46600, 150], [46700, 300]]
        },
        "volume": {
            "24h": 1000000,
            "avg_24h": 800000
        }
    }

@pytest.fixture
def sample_social_data() -> Dict[str, Any]:
    """Sample social media data for testing."""
    return {
        "tweets": [
            {"text": "Bitcoin is going to the moon! 🚀", "user": "crypto_bull", "likes": 1000},
            {"text": "BTC looking bullish today", "user": "trader_pro", "likes": 500}
        ],
        "news": [
            {"title": "Bitcoin Adoption Increases", "summary": "Major companies adopt Bitcoin", "source": "CoinDesk"},
            {"title": "Crypto Market Rally", "summary": "Digital assets surge higher", "source": "CoinTelegraph"}
        ],
        "social_media": [
            {"platform": "Reddit", "sentiment": "positive", "engagement": 5000}
        ]
    }

class TestSentimentAnalyst:
    """Test sentiment analyst agent."""
    
    @pytest.mark.asyncio
    async def test_sentiment_analyst_instantiation(self):
        """Test that sentiment analyst can be instantiated."""
        agent = SentimentAnalyst()
        assert agent.name == "sentiment_analyst"
        assert agent.model == "gpt-4o-mini"
        
    @pytest.mark.asyncio
    async def test_sentiment_analyst_output_schema(self, sample_social_data):
        """Test that sentiment analyst returns correct JSON schema."""
        agent = SentimentAnalyst()
        # The `execute` method is part of BaseAgent, let's call `run` directly
        result = await agent.run(sample_social_data)
        
        assert "sentiment" in result
        assert "score" in result
        assert "confidence" in result
        assert "rationale" in result
        
        assert result["sentiment"] in ["bullish", "bearish", "neutral"]
        assert 0 <= result["score"] <= 100
        assert 0 <= result["confidence"] <= 1

class TestTechnicalAnalyst:
    """Test technical analyst agent."""
    
    @pytest.mark.asyncio
    async def test_technical_analyst_instantiation(self):
        """Test that technical analyst can be instantiated."""
        agent = TechnicalAnalyst()
        assert agent.name == "technical_analyst"
        assert agent.model == "gpt-4o-mini"
        
    @pytest.mark.asyncio
    async def test_technical_analyst_output_schema(self, sample_market_data):
        """Test that technical analyst returns correct JSON schema."""
        agent = TechnicalAnalyst()
        # Feed 20 prices to fill the deque
        for price in range(42000, 42020):
            await agent.run({"tick": {"price": price}})
        # Now test with a price that should trigger a breakout
        result = await agent.run({"tick": {"price": 42100}})
        assert "breakout" in result
        assert "sma" in result
        assert "ema" in result
        assert isinstance(result["breakout"], bool) 