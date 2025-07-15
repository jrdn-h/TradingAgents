import pytest
from tradingagents.agents import BaseAgent, SentimentAnalyst

@pytest.mark.asyncio
async def test_agent_error_handling():
    """Test that agents handle errors gracefully."""
    agent = SentimentAnalyst()
    
    # Test with invalid input
    result = await agent.execute({"invalid": "data"})
    
    assert "agent" in result
    assert "timestamp" in result
    assert "input" in result
    # The `run` method of SentimentAnalyst will not raise an error,
    # but this tests that the `execute` method of BaseAgent works correctly.
    assert "output" in result 