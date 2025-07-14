"""
Unit tests for market functionality and live feed integration.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock
from tradingagents.graph.orchestrator import Orchestrator
from tradingagents.dataflows import hyperliquid_utils

@pytest.mark.asyncio
async def test_market_live_patch(monkeypatch):
    """Test that live mode works with mocked WebSocket feed."""
    
    # Create a mock async generator that yields ascending prices
    async def fake_feed(symbols, callback):
        for i, price in enumerate(range(40000, 40025)):
            mock_data = {
                "channel": "ticker",
                "symbol": symbols[0],
                "price": price,
                "timestamp": 1234567890000 + i
            }
            await callback(mock_data)
            await asyncio.sleep(0.1)  # Simulate tick frequency
    
    # Patch the mock WebSocket function
    monkeypatch.setattr(hyperliquid_utils, "mock_hyperliquid_ws_listener", fake_feed)
    
    # Run the orchestrator in live mode
    orchestrator = Orchestrator()
    await orchestrator.run_once(symbol="BTCUSD", live=True)
    
    # The test passes if no exceptions are raised and the function completes
    # The orchestrator will print the results, but we're testing the integration works

@pytest.mark.asyncio
async def test_technical_analyst_deque_fill():
    """Test that TechnicalAnalyst deque fills correctly with live data."""
    from tradingagents.agents.analysts.technical_analyst import TechnicalAnalyst
    
    agent = TechnicalAnalyst()
    
    # Feed 19 prices (should not trigger SMA/EMA calculation yet)
    for price in range(42000, 42019):
        result = await agent.run({"tick": {"price": price}})
        assert result["breakout"] is False
        assert result["sma"] is None
        assert result["ema"] is None
    
    # Feed the 20th price (should trigger SMA/EMA calculation)
    result = await agent.run({"tick": {"price": 42019}})
    assert result["sma"] is not None
    assert result["ema"] is not None
    assert isinstance(result["breakout"], bool)

@pytest.mark.asyncio
async def test_breakout_logic():
    """Test that breakout logic works correctly with ascending prices."""
    from tradingagents.agents.analysts.technical_analyst import TechnicalAnalyst
    
    agent = TechnicalAnalyst()
    
    # Fill the deque with ascending prices to trigger breakout
    base_price = 42000
    for i in range(20):
        price = base_price + (i * 10)  # Ascending prices
        result = await agent.run({"tick": {"price": price}})
    
    # Add one more price that should be above both SMA and EMA
    final_price = base_price + 200  # Well above the averages
    result = await agent.run({"tick": {"price": final_price}})
    
    # Should detect breakout
    assert result["breakout"] is True
    assert result["sma"] is not None
    assert result["ema"] is not None
    assert final_price > result["sma"]
    assert final_price > result["ema"] 