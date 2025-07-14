"""
Unit tests for trading agents.
"""

import pytest
import asyncio
from typing import Dict, Any

from tradingagents.agents import (
    SentimentAnalyst,
    TechnicalAnalyst,
    TraderAgent,
    RiskManager
)

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

@pytest.fixture
def sample_trade_proposal() -> Dict[str, Any]:
    """Sample trade proposal for testing."""
    return {
        "action": "long",
        "size_pct": 4.0,
        "symbol": "BTC",
        "price_target": 48000,
        "stop_loss": 44000,
        "take_profit": 52000,
        "rationale": "Strong bullish signals from sentiment and technical analysis",
        "confidence": 0.75
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
        result = await agent.execute(sample_social_data)
        
        # Check metadata
        assert "agent" in result
        assert "timestamp" in result
        assert "execution_time_ms" in result
        assert "input" in result
        assert "output" in result
        
        # Check output schema matches project overview
        output = result["output"]
        assert "sentiment" in output
        assert "score" in output
        assert "confidence" in output
        assert "rationale" in output
        
        # Validate sentiment values
        assert output["sentiment"] in ["bullish", "bearish", "neutral"]
        assert 0 <= output["score"] <= 100
        assert 0 <= output["confidence"] <= 1

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
        # Output is direct dict, not wrapped in 'output'
        assert "breakout" in result
        assert "sma" in result
        assert "ema" in result
        assert isinstance(result["breakout"], bool)

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

class TestRiskManager:
    """Test risk manager agent."""
    
    @pytest.mark.asyncio
    async def test_risk_manager_instantiation(self):
        """Test that risk manager can be instantiated."""
        agent = RiskManager()
        assert agent.name == "risk_manager"
        assert agent.model == "gpt-4o"
        
    @pytest.mark.asyncio
    async def test_risk_manager_output_schema(self, sample_trade_proposal):
        """Test that risk manager returns correct JSON schema."""
        agent = RiskManager()
        
        input_data = {
            "trade_proposal": sample_trade_proposal,
            "portfolio_state": {
                "total_value": 10000,
                "cash": 5000,
                "positions": {"BTC": {"quantity": 0.1, "avg_price": 45000}}
            },
            "market_data": {"volatility": 0.3},
            "risk_metrics": {"var_95": 0.02}
        }
        
        result = await agent.execute(input_data)
        
        # Check metadata
        assert "agent" in result
        assert "timestamp" in result
        assert "execution_time_ms" in result
        assert "input" in result
        assert "output" in result
        
        # Check output schema matches project overview
        output = result["output"]
        assert "approved" in output
        assert "new_size_pct" in output
        assert "original_size_pct" in output
        assert "risk_analysis" in output
        assert "rationale" in output
        
        # Validate approval is boolean
        assert isinstance(output["approved"], bool)
        assert 0 <= output["new_size_pct"] <= 10  # Reasonable position size

    @pytest.mark.asyncio
    async def test_risk_manager_blocks_oversize_trade(self):
        agent = RiskManager()
        # Pass a trade with size_pct=5 (over max)
        state = {"trade": {"action": "long", "size_pct": 5}}
        result = await agent.run(state)
        assert "approved" in result
        assert result["approved"] is False
        assert result["new_size_pct"] == 0

@pytest.mark.asyncio
async def test_agent_error_handling():
    """Test that agents handle errors gracefully."""
    agent = SentimentAnalyst()
    
    # Test with invalid input
    result = await agent.execute({"invalid": "data"})
    
    assert "agent" in result
    assert "timestamp" in result
    assert "input" in result
    # Should not have error for this case, but should handle gracefully
    assert "output" in result or "error" in result 