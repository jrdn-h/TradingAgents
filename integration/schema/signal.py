"""TradingSignal v1.0 schema with strict validation for MVP."""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import List, Literal
from uuid import uuid4
from datetime import datetime, timezone

__all__ = [
    "TakeProfit",
    "RiskPlan", 
    "TradingSignal",
]


class TakeProfit(BaseModel):
    """Take profit level with price and position size percentage."""
    price: float
    size_pct: float = Field(gt=0, lt=1)


class RiskPlan(BaseModel):
    """Risk management plan with stop loss and take profits."""
    initial_stop: float
    take_profits: List[TakeProfit]
    max_capital_pct: float = Field(gt=0, lt=1)

    @field_validator("take_profits")
    @classmethod
    def _validate_tp_count(cls, v):
        """Validate exactly 2 take profits that sum to 1.0."""
        if len(v) != 2:
            raise ValueError("Exactly 2 take_profits required for v1.0 schema")
        total = sum(tp.size_pct for tp in v)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Take profit size_pct must sum to 1.0, got {total}")
        return v


class TradingSignal(BaseModel):
    """Complete trading signal with validation for MVP v1.0."""
    version: Literal["1.0"] = "1.0"
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    symbol: str
    side: Literal["long", "short"]
    confidence: float = Field(gt=0, le=1)
    entry: dict
    risk: RiskPlan
    rationale: str = Field(max_length=60)

    @field_validator("rationale")
    @classmethod
    def _trim_rationale(cls, v: str):
        """Trim whitespace from rationale."""
        return v.strip()

    @field_validator("symbol")
    @classmethod
    def _norm_symbol(cls, v: str):
        """Normalize symbol to uppercase."""
        return v.upper()

    @field_validator("entry")
    @classmethod
    def _validate_entry(cls, v):
        """Validate entry dictionary structure."""
        if "type" not in v:
            raise ValueError("entry dict must have 'type'")
        # MVP restrict to market or limit
        if v["type"] not in {"market", "limit"}:
            raise ValueError("entry.type must be 'market' or 'limit'")
        if v["type"] == "limit" and "limit_price" not in v:
            raise ValueError("limit entries require limit_price")
        return v 