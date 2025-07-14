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

logger = logging.getLogger(__name__)

class Orchestrator:
    async def run_once(self, symbol: str = "BTCUSD") -> None:
        """Run a single end-to-end pass and print the final approved trade."""
        state = {}
        # Mock price stream for demo
        prices = [42000, 42100, 42250, 42150, 42300, 42400, 42500, 42600, 42700, 42800,
                  42900, 43000, 43100, 43200, 43300, 43400, 43500, 43600, 43700, 43800, 43900, 44000]
        tech_agent = TechnicalAnalyst()
        for price in prices:
            state["tick"] = {"symbol": symbol, "price": price}
            # Sentiment can be run once for simplicity
            if "sentiment" not in state:
                state["sentiment"] = await SentimentAnalyst().run(state)
            state["technical"] = await tech_agent.run(state)
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