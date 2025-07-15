import pytest
from typing import Dict, Any
from tradingagents.agents import TraderAgent

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
    
class TestTraderAgent:
    """Test trader agent."""
    
    @pytest.mark.asyncio
    async def test_trader_agent_instantiation(self):
        """Test that trader agent can be instantiated."""
        agent = TraderAgent()
        assert agent.name == "trader_agent"
        assert agent.model == "gpt-4o"
        
    @pytest.mark.asyncio
    async def test_trader_agent_output_schema(self, sample_social_data, sample_market_data):
        """Test that trader agent returns correct JSON schema."""
        agent = TraderAgent()
        # Simulate technical breakout and strong sentiment
        state = {
            "technical": {"breakout": True},
            "sentiment": {"score": 70}
        }
        result = await agent.run(state)
        assert "action" in result
        assert "size_pct" in result
        assert result["action"] == "long"
        assert result["size_pct"] <= 2 