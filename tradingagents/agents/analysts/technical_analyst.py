"""
Technical analysis agent for price and market data.
"""

import asyncio
from typing import Dict, Any, List, Optional
from ..base_agent import BaseAgent
from collections import deque

class TechnicalAnalyst(BaseAgent):
    """Agent for technical analysis of price and market data."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__("technical_analyst", model)
        self.prices = deque(maxlen=20)
        self.last_ema = None

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform technical analysis on market data.
        """
        # Get the latest price from the state
        price = None
        tick = input_data.get("tick")
        if tick and "price" in tick:
            price = tick["price"]
            self.prices.append(price)
        
        if len(self.prices) < 20:
            return {"breakout": False, "sma": None, "ema": None}
        
        # Compute SMA20
        sma20 = sum(self.prices) / 20
        # Compute EMA20
        alpha = 2 / (20 + 1)
        if self.last_ema is None:
            # Seed EMA with SMA for first calculation
            ema20 = sma20
        else:
            ema20 = alpha * price + (1 - alpha) * self.last_ema
        self.last_ema = ema20
        breakout = price > sma20 and price > ema20
        return {"breakout": breakout, "sma": sma20, "ema": ema20} 