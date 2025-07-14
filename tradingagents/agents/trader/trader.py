"""
Trader agent for making trading decisions based on all analyst inputs.
"""

import asyncio
from typing import Dict, Any, List, Optional
from ..base_agent import BaseAgent

class TraderAgent(BaseAgent):
    """Agent for making final trading decisions based on all analyst inputs."""
    
    def __init__(self, model: str = "gpt-4o"):
        super().__init__("trader_agent", model)
        self.portfolio_state = {
            "total_value": 10000,
            "cash": 5000,
            "positions": {
                "BTC": {"quantity": 0.1, "avg_price": 45000},
                "ETH": {"quantity": 2.0, "avg_price": 3000}
            },
            "max_position_size": 0.1  # 10% of portfolio
        }
        
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make trading decision based on technical and sentiment signals.
        """
        technical = state.get("technical", {})
        sentiment = state.get("sentiment", {})
        breakout = technical.get("breakout", False)
        score = sentiment.get("score", 0)
        if breakout and score > 60:
            action = "long"
            size_pct = 2
        else:
            action = "flat"
            size_pct = 0
        return {"action": action, "size_pct": size_pct}
