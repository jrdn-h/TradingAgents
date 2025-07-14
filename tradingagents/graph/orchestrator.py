"""
Minimal LangGraph orchestrator for multi-agent trading demo.
"""

import asyncio
import logging
from tradingagents.agents import (
    SentimentAnalyst,
    TechnicalAnalyst,
    TraderAgent,
    RiskManager
)
from tradingagents.dataflows.hyperliquid_utils import mock_hyperliquid_ws_listener

logger = logging.getLogger(__name__)

class Orchestrator:
    async def run_once(self, symbol: str = "BTCUSD", live: bool = False) -> None:
        """Run a single end-to-end pass and print the final approved trade."""
        state = {}
        tech_agent = TechnicalAnalyst()
        sentiment_agent = SentimentAnalyst()
        # Helper to process a price tick
        async def process_tick(price):
            state["tick"] = {"symbol": symbol, "price": price}
            if "sentiment" not in state:
                state["sentiment"] = await sentiment_agent.run(state)
            state["technical"] = await tech_agent.run(state)
        if live:
            # Live mode: subscribe to Hyperliquid and fill deque
            prices = []
            tick_count = 0
            async def on_data(data):
                nonlocal tick_count
                # Extract price from Hyperliquid ticker message
                price = None
                if isinstance(data, dict) and "price" in data:
                    price = float(data["price"])
                elif isinstance(data, dict) and "data" in data and "price" in data["data"]:
                    price = float(data["data"]["price"])
                if price:
                    prices.append(price)
                    tick_count += 1
                    print(f"[Live] Tick {tick_count}: ${price}")
                    await process_tick(price)
                    # Break after first breakout or 50 ticks (whichever comes first)
                    if state.get("technical", {}).get("breakout", False) or tick_count >= 50:
                        print(f"[Live] Breaking after {tick_count} ticks")
                        return  # Signal to stop
            print("[Live] Starting mock WebSocket (real API integration in progress)...")
            try:
                # Use mock WebSocket for now (real API has subscription format issues)
                await mock_hyperliquid_ws_listener([symbol], on_data)
                print("[Live] Mock WebSocket completed")
            except Exception as e:
                print(f"[Live] WebSocket error: {e}")
                print("[Live] Falling back to mock prices for demo")
                # Fall back to mock prices if WebSocket fails
                mock_prices = [42000, 42100, 42250, 42150, 42300, 42400, 42500, 42600, 42700, 42800,
                              42900, 43000, 43100, 43200, 43300, 43400, 43500, 43600, 43700, 43800, 43900, 44000]
                for price in mock_prices:
                    await process_tick(price)
        else:
            # Mock price stream for demo
            prices = [42000, 42100, 42250, 42150, 42300, 42400, 42500, 42600, 42700, 42800,
                      42900, 43000, 43100, 43200, 43300, 43400, 43500, 43600, 43700, 43800, 43900, 44000]
            for price in prices:
                await process_tick(price)
        state["trade"] = await TraderAgent().run(state)
        state["approved_trade"] = await RiskManager().run(state)
        trade = state["trade"]
        approval = state["approved_trade"]
        minimal = {k: trade[k] for k in ("action", "size_pct") if k in trade}
        print(minimal)
        print(approval)
        # Print latest SMA/EMA/breakout for demo visibility
        print({k: state["technical"][k] for k in ("breakout", "sma", "ema")})

    def run(self, **kwargs):
        try:
            asyncio.run(self.run_once(**kwargs))
        except KeyboardInterrupt:
            print("\n[Orchestrator] Interrupted by user.") 