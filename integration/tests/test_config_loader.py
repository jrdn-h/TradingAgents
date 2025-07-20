"""Unit tests for config loader."""
import os
import tempfile
from pathlib import Path
import pytest
from pydantic import ValidationError

from integration.config.config import load_config, Config, RiskSettings, RISK_DEFAULT


class TestConfigLoader:
    """Test cases for configuration loading and validation."""

    def test_load_config_success(self, tmp_path, monkeypatch):
        """Test successful configuration loading with all required variables."""
        # Clear any existing environment variables to avoid pollution
        for var in ['REDIS_URL', 'DEFAULT_SYMBOL', 'TIMEFRAME', 'MAX_CAPITAL_PCT', 'MODEL_NAME']:
            monkeypatch.delenv(var, raising=False)
        
        # Create temporary .env file
        env_file = tmp_path / ".env.test"
        env_content = """REDIS_URL=redis://localhost:6379/0
DEFAULT_SYMBOL=BTC/USDT
TIMEFRAME=5m
MAX_CAPITAL_PCT=0.05
MODEL_NAME=gpt-4o-mini"""
        env_file.write_text(env_content)
        
        # Load configuration
        config = load_config(env_file=str(env_file))
        
        # Assertions
        assert isinstance(config, Config)
        assert config.symbol == "BTC/USDT"
        assert config.timeframe == "5m"
        assert config.max_capital_pct == 0.05
        assert config.model_name == "gpt-4o-mini"
        assert isinstance(config.risk, RiskSettings)
        assert config.risk.min_rr == 1.5
        assert config.risk.min_atr_multiple == 0.5
        assert config.risk.max_atr_multiple == 5.0

    def test_load_config_missing_vars(self, tmp_path, monkeypatch):
        """Test configuration loading with missing required variables."""
        # Clear all environment variables that might be set
        for var in ['REDIS_URL', 'DEFAULT_SYMBOL', 'TIMEFRAME', 'MAX_CAPITAL_PCT', 'MODEL_NAME']:
            monkeypatch.delenv(var, raising=False)
        
        # Create temporary .env file missing MODEL_NAME and MAX_CAPITAL_PCT
        env_file = tmp_path / ".env.test"
        env_content = """REDIS_URL=redis://localhost:6379/0
DEFAULT_SYMBOL=BTC/USDT
TIMEFRAME=5m"""
        env_file.write_text(env_content)
        
        # Expect RuntimeError with both missing keys in message
        with pytest.raises(RuntimeError) as exc_info:
            load_config(env_file=str(env_file))
        
        error_message = str(exc_info.value)
        assert "MODEL_NAME" in error_message
        assert "MAX_CAPITAL_PCT" in error_message
        assert "Missing required environment variables" in error_message

    def test_risk_settings_validation(self):
        """Test RiskSettings validation constraints."""
        # Test invalid: min_atr_multiple >= max_atr_multiple
        with pytest.raises(ValidationError):
            RiskSettings(min_atr_multiple=2, max_atr_multiple=1, min_rr=1.5)
        
        # Test invalid: min_rr < 1.0
        with pytest.raises(ValidationError):
            RiskSettings(min_atr_multiple=0.4, max_atr_multiple=5, min_rr=0.8)
        
        # Test valid settings
        valid_settings = RiskSettings(min_atr_multiple=0.5, max_atr_multiple=5.0, min_rr=1.5)
        assert valid_settings.min_atr_multiple == 0.5
        assert valid_settings.max_atr_multiple == 5.0
        assert valid_settings.min_rr == 1.5 