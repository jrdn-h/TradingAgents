import pytest
from typing import Dict, Any
from tradingagents.agents import RiskManager

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
        
        # The `execute` method is part of BaseAgent, let's call `run` directly
        state = {"trade": sample_trade_proposal}
        result = await agent.run(state)
        
        assert "approved" in result
        assert "new_size_pct" in result
        assert "original_size_pct" in result
        assert "risk_analysis" in result
        assert "rationale" in result
        
        assert isinstance(result["approved"], bool)
        assert 0 <= result["new_size_pct"] <= 10  # Reasonable position size

    @pytest.mark.asyncio
    async def test_risk_manager_blocks_oversize_trade(self):
        agent = RiskManager()
        # Pass a trade with size_pct=5 (over max)
        state = {"trade": {"action": "long", "size_pct": 5}}
        result = await agent.run(state)
        assert "approved" in result
        assert result["approved"] is False
        assert result["new_size_pct"] == 0 