from pydantic_settings import BaseSettings
from pydantic import ConfigDict
import os
import logging
from typing import Optional

def setup_logging(level: str = "INFO"):
    """
    Sets up the root logger for the application.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

class Settings(BaseSettings):
    # =============================================================================
    # PROJECT CONFIGURATION
    # =============================================================================
    project_dir: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
    results_dir: str = "./results"
    data_dir: str = "./data"
    data_cache_dir: str = os.path.join(project_dir, "dataflows/data_cache")
    
    # =============================================================================
    # LLM CONFIGURATION
    # =============================================================================
    
    # Primary LLM settings
    llm_provider: str = "openai"
    deep_think_llm: str = "gpt-4o-mini"
    quick_think_llm: str = "gpt-4o-mini"
    backend_url: str = "https://api.openai.com/v1"
    
    # API Keys for different LLM providers
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    
    # =============================================================================
    # SOCIAL MEDIA / DATA SOURCES
    # =============================================================================
    
    # Twitter/X credentials
    twikit_username: Optional[str] = None
    twikit_password: Optional[str] = None
    
    # Financial data APIs
    finnhub_api_key: Optional[str] = None
    whale_alert_api_key: Optional[str] = None
    
    # Twitter API v2
    twitter_bearer_token: Optional[str] = None
    
    # Reddit API
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_user_agent: str = "TradingAgents/1.0"
    
    # =============================================================================
    # DATABASE CONFIGURATION
    # =============================================================================
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "trading"
    postgres_user: str = "trader"
    postgres_password: Optional[str] = None
    
    # =============================================================================
    # DASHBOARD & MONITORING
    # =============================================================================
    
    # Dashboard authentication
    dashboard_api_key: str = "demo-key-123"
    
    # Monitoring
    prom_metrics: bool = True
    
    # Grafana (for Docker setup)
    grafana_admin_user: str = "admin"
    grafana_admin_password: str = "changeme"
    
    # =============================================================================
    # APPLICATION SETTINGS
    # =============================================================================
    
    # Trading behavior
    max_debate_rounds: int = 1
    max_risk_discuss_rounds: int = 1
    live_timeout: int = 30
    max_recur_limit: int = 100
    
    # Feature toggles
    online_tools: bool = True
    
    # Logging
    log_level: str = "INFO"
    
    # =============================================================================
    # DEVELOPMENT & TESTING
    # =============================================================================
    
    # Test configuration
    twikit_e2e: int = 0
    twikit_user: str = "stubuser"
    twikit_email: str = "stub@example.com"
    twikit_pass: str = "stubpass"
    
    # Environment
    node_env: str = "development"
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings() 