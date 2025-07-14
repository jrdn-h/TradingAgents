"""
Trading agents for multi-agent trading system.
"""

from .base_agent import BaseAgent

from .analysts.sentiment_analyst import SentimentAnalyst
from .analysts.technical_analyst import TechnicalAnalyst
from .analysts.fundamentals_analyst import *
from .analysts.market_analyst import *
from .analysts.news_analyst import *
from .analysts.social_media_analyst import *

from .trader.trader import TraderAgent

from .managers.risk_manager import RiskManager
from .managers.research_manager import *

from .researchers.bull_researcher import *
from .researchers.bear_researcher import *

from .risk_mgmt.aggresive_debator import *
from .risk_mgmt.conservative_debator import *
from .risk_mgmt.neutral_debator import *

__all__ = [
    # Base
    "BaseAgent",
    
    # Analysts
    "SentimentAnalyst",
    "TechnicalAnalyst",
    
    # Trader
    "TraderAgent",
    
    # Managers
    "RiskManager",
]
