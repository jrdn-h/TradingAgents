"""Minimal configuration layer for MVP."""
import os
from typing import NoReturn
from pydantic import BaseModel, model_validator
from dotenv import load_dotenv

# Default risk parameters
RISK_DEFAULT = {
    "min_atr_multiple": 0.5,
    "max_atr_multiple": 5.0,
    "min_rr": 1.5
}


class RiskSettings(BaseModel):
    """Risk management settings with validation."""
    min_atr_multiple: float
    max_atr_multiple: float
    min_rr: float

    @model_validator(mode="after")
    def validate_risk_params(self):
        """Validate risk parameter constraints."""
        if not (0 < self.min_atr_multiple < self.max_atr_multiple):
            raise ValueError("min_atr_multiple must be > 0 and < max_atr_multiple")
        if self.min_rr < 1.0:
            raise ValueError("min_rr must be >= 1.0")
        return self


class Config(BaseModel):
    """Main configuration model."""
    symbol: str
    timeframe: str
    max_capital_pct: float
    model_name: str
    risk: RiskSettings


def load_config(env_file: str = '.env') -> Config | NoReturn:
    """
    Load configuration from environment variables.
    
    Args:
        env_file: Path to .env file (optional)
        
    Returns:
        Config: Validated configuration object
        
    Raises:
        RuntimeError: If required environment variables are missing
    """
    # Load .env file if it exists
    if os.path.exists(env_file):
        load_dotenv(env_file)
    
    # Required environment variables
    required_vars = ['REDIS_URL', 'DEFAULT_SYMBOL', 'TIMEFRAME', 'MAX_CAPITAL_PCT', 'MODEL_NAME']
    missing_vars = []
    
    for var in required_vars:
        if os.getenv(var) is None:
            missing_vars.append(var)
    
    if missing_vars:
        raise RuntimeError(f"Missing required environment variables: {missing_vars}")
    
    # Create configuration instance
    config = Config(
        symbol=os.getenv('DEFAULT_SYMBOL'),
        timeframe=os.getenv('TIMEFRAME'),
        max_capital_pct=float(os.getenv('MAX_CAPITAL_PCT')),
        model_name=os.getenv('MODEL_NAME'),
        risk=RiskSettings(**RISK_DEFAULT)
    )
    
    return config


__all__ = ["load_config", "Config", "RiskSettings", "RISK_DEFAULT"] 