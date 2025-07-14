"""
Risk management agent for validating and adjusting trading decisions.
"""

import asyncio
from typing import Dict, Any, List, Optional
from ..base_agent import BaseAgent

MAX_SIZE_PCT = 2  # percent
STOP_LOSS_BPS = 150  # basis points (1.5%)

class RiskManager(BaseAgent):
    """Agent for risk management and trade validation."""
    
    def __init__(self, model: str = "gpt-4o"):
        super().__init__("risk_manager", model)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and adjust trading decision based on risk parameters.
        """
        trade = state.get("trade", {})
        action = trade.get("action", "flat")
        size_pct = trade.get("size_pct", 0)
        # 1. Block trade if size_pct > MAX_SIZE_PCT
        if size_pct > MAX_SIZE_PCT:
            return {"approved": False, "new_size_pct": 0, "original_size_pct": size_pct, "risk_analysis": "Trade size exceeds max allowed", "rationale": "Trade size exceeds max allowed"}
        # 2. If action == 'flat', auto-approve
        if action == "flat":
            return {"approved": True, "new_size_pct": 0, "original_size_pct": size_pct, "risk_analysis": "Trade auto-approved (flat)", "rationale": "Trade auto-approved (flat)"}
        # 3. Approve, possibly resize
        return {"approved": True, "new_size_pct": min(size_pct, MAX_SIZE_PCT), "original_size_pct": size_pct, "risk_analysis": "Trade approved", "rationale": "Trade approved"}
