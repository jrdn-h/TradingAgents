"""
FastAPI dashboard for TradingAgents live monitoring.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from prometheus_fastapi_instrumentator import Instrumentator
from tradingagents.backtest.metrics import tweet_ingested_total_counter, sentiment_index_gauge, backoffs_total_counter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from tradingagents.graph.orchestrator import Orchestrator
from tradingagents.sources.tweet_source import Tweet
from tradingagents.sentiment.model import SentimentResult
from tradingagents.config import setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# --- FastAPI App Setup ---
app = FastAPI(
    title="TradingAgents Dashboard",
    description="Live monitoring dashboard for the TradingAgents system",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")


# --- Auth function ---
async def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key for protected endpoints."""
    expected_key = os.getenv("DASHBOARD_API_KEY", "demo-key-123")
    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

# --- Pydantic models ---
class TechnicalIndicators(BaseModel):
    breakout: Optional[bool] = None
    sma: Optional[float] = None
    ema: Optional[float] = None

class EquityPoint(BaseModel):
    tick: int
    equity: float

class TweetFeedItem(BaseModel):
    id: str
    author: str
    text: str
    created_at: str
    sentiment_score: float
    sentiment_label: str
    keywords: List[str]

class DashboardStatus(BaseModel):
    status: str
    symbol: Optional[str] = None
    current_price: Optional[float] = None
    technical_indicators: TechnicalIndicators = TechnicalIndicators()
    sentiment: Optional[Dict[str, Any]] = None
    sentiment_index: float = 0.0  # Rolling sentiment average
    tweet_feed: List[TweetFeedItem] = []  # Recent tweets with sentiment
    trade_decision: Optional[Dict[str, Any]] = None
    risk_approval: Optional[Dict[str, Any]] = None
    equity_curve: List[EquityPoint] = []
    last_update: Optional[str] = None
    tick_count: int = 0
    errors: List[str] = []

# Global state for the dashboard
dashboard_state = DashboardStatus(status="idle")

# Global tweet source
tweet_source = None

class DashboardOrchestrator(Orchestrator):
    """Extended orchestrator that updates dashboard state."""
    
    async def ingest_tweet(self, tweet: Tweet) -> SentimentResult:
        """Process a tweet and update dashboard state."""
        global dashboard_state
        
        # Call parent method
        sentiment = await super().ingest_tweet(tweet)
        
        # Update dashboard state
        dashboard_state.sentiment_index = self.sentiment_index
        
        # Update Prometheus metrics
        tweet_ingested_total_counter.inc()
        sentiment_index_gauge.set(self.sentiment_index)
        
        # Add to tweet feed
        feed_item = TweetFeedItem(
            id=tweet.id,
            author=tweet.author,
            text=tweet.text,
            created_at=tweet.created_at.isoformat(),
            sentiment_score=sentiment.score,
            sentiment_label=sentiment.label,
            keywords=sentiment.keywords
        )
        
        dashboard_state.tweet_feed.insert(0, feed_item)  # Prepend newest
        if len(dashboard_state.tweet_feed) > 20:  # Keep last 20 tweets
            dashboard_state.tweet_feed = dashboard_state.tweet_feed[:20]
        
        dashboard_state.last_update = datetime.now().isoformat()
        
        return sentiment
    
    async def run_once(self, symbol: str = "BTCUSD", live: bool = False) -> None:
        """Run a single end-to-end pass and update dashboard state."""
        global dashboard_state
        
        try:
            dashboard_state.status = "running"
            dashboard_state.symbol = symbol
            dashboard_state.last_update = datetime.now().isoformat()
            dashboard_state.errors = []
            
            state = {}
            tech_agent = self._create_technical_analyst()
            sentiment_agent = self._create_sentiment_analyst()
            
            # Helper to process a price tick
            async def process_tick(price):
                dashboard_state.current_price = price
                dashboard_state.tick_count += 1
                dashboard_state.last_update = datetime.now().isoformat()
                
                state["tick"] = {"symbol": symbol, "price": price}
                if "sentiment" not in state:
                    state["sentiment"] = await sentiment_agent.run(state)
                    dashboard_state.sentiment = state["sentiment"]
                
                state["technical"] = await tech_agent.run(state)
                dashboard_state.technical_indicators = TechnicalIndicators(
                    breakout=state["technical"].get("breakout"),
                    sma=state["technical"].get("sma"),
                    ema=state["technical"].get("ema")
                )
                
                # Update equity curve (mock for now)
                if len(dashboard_state.equity_curve) == 0:
                    dashboard_state.equity_curve = [EquityPoint(tick=0, equity=10000)]
                
                # Simple mock equity calculation
                base_equity = 10000
                price_change = (price - 42000) / 42000  # Mock baseline
                current_equity = base_equity * (1 + price_change * 0.1)  # 10% leverage
                dashboard_state.equity_curve.append(EquityPoint(
                    tick=dashboard_state.tick_count,
                    equity=round(current_equity, 2)
                ))
                
                # Keep only last 100 points
                if len(dashboard_state.equity_curve) > 100:
                    dashboard_state.equity_curve = dashboard_state.equity_curve[-100:]
            
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
                        logger.info(f"[Live] Tick {tick_count}: ${price}")
                        await process_tick(price)
                        # Break after first breakout or 50 ticks (whichever comes first)
                        if state.get("technical", {}).get("breakout", False) or tick_count >= 50:
                            logger.info(f"[Live] Breaking after {tick_count} ticks")
                            return  # Signal to stop
                
                logger.info("[Live] Starting mock WebSocket (real API integration in progress)...")
                try:
                    # Use mock WebSocket for now (real API has subscription format issues)
                    await self._mock_hyperliquid_ws_listener([symbol], on_data)
                    logger.info("[Live] Mock WebSocket completed")
                except Exception as e:
                    logger.error(f"[Live] WebSocket error: {e}")
                    dashboard_state.errors.append(f"WebSocket error: {e}")
                    logger.info("[Live] Falling back to mock prices for demo")
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
            
            state["trade"] = await self._create_trader().run(state)
            state["approved_trade"] = await self._create_risk_manager().run(state)
            
            dashboard_state.trade_decision = state["trade"]
            dashboard_state.risk_approval = state["approved_trade"]
            dashboard_state.status = "completed"
            dashboard_state.last_update = datetime.now().isoformat()
            
            logger.info(f"Trade decision: {state['trade']}")
            logger.info(f"Risk approval: {state['approved_trade']}")
            logger.info(f"Technical indicators: {dashboard_state.technical_indicators}")
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {e}")
            dashboard_state.status = "error"
            dashboard_state.errors.append(str(e))
            dashboard_state.last_update = datetime.now().isoformat()
    
    def _create_technical_analyst(self):
        """Create technical analyst agent."""
        from tradingagents.agents.analysts.technical_analyst import TechnicalAnalyst
        return TechnicalAnalyst()
    
    def _create_sentiment_analyst(self):
        """Create sentiment analyst agent."""
        from tradingagents.agents.analysts.sentiment_analyst import SentimentAnalyst
        return SentimentAnalyst()
    
    def _create_trader(self):
        """Create trader agent."""
        from tradingagents.agents.trader.trader import TraderAgent
        return TraderAgent()
    
    def _create_risk_manager(self):
        """Create risk manager agent."""
        from tradingagents.agents.managers.risk_manager import RiskManager
        return RiskManager()
    
    async def _mock_hyperliquid_ws_listener(self, symbols, on_data):
        """Mock WebSocket listener for demo purposes."""
        from tradingagents.dataflows.hyperliquid_utils import mock_hyperliquid_ws_listener
        await mock_hyperliquid_ws_listener(symbols, on_data)

# Create FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting TradingAgents Dashboard...")
    
    # Initialize tweet source if specified
    global tweet_source
    import sys
    if "--source" in sys.argv:
        source_idx = sys.argv.index("--source")
        if source_idx + 1 < len(sys.argv) and sys.argv[source_idx + 1] == "twikit":
            try:
                from tradingagents.sources.tweet_source import TwikitSource
                tweet_source = TwikitSource()
                logger.info("TwikitSource initialized - live tweets enabled!")
                
                # Start tweet streaming if TwikitSource is enabled
                if tweet_source:
                    asyncio.create_task(stream_tweets())
            except Exception as e:
                logger.error(f"Failed to initialize TwikitSource: {e}")
                tweet_source = None
    
    yield
    # Shutdown
    logger.info("Shutting down TradingAgents Dashboard...")

async def stream_tweets():
    """Background task to stream tweets from TwikitSource."""
    global tweet_source, dashboard_state
    
    if not tweet_source:
        return
    
    # Create a single orchestrator instance
    orchestrator = DashboardOrchestrator()
        
    try:
        async for tweet in tweet_source.stream():
            await orchestrator.ingest_tweet(tweet)
            await asyncio.sleep(0.1)  # Small delay between tweets
    except Exception as e:
        logger.error(f"Tweet streaming error: {e}")
        dashboard_state.errors.append(f"Tweet streaming error: {e}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus instrumentation
Instrumentator().instrument(app).expose(app)

# Register custom metrics with Prometheus
from prometheus_client import REGISTRY
from tradingagents.backtest.metrics import (
    tweet_ingested_total_counter, 
    sentiment_index_gauge, 
    sharpe_gauge,
    sortino_gauge,
    max_dd_gauge,
    win_rate_gauge,
    sentiment_corr_gauge,
    backoffs_total_counter
)

@app.get("/status", response_model=DashboardStatus)
async def get_status():
    """Get current dashboard status as JSON."""
    return dashboard_state

@app.get("/stream")
async def stream_status(request: Request):
    """Stream dashboard status updates via Server-Sent Events."""
    async def event_generator():
        last_state = None
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
            
            # Only send if state changed
            current_state = dashboard_state.model_dump()
            if last_state != current_state:
                yield f"data: {json.dumps(current_state)}\n\n"
                last_state = current_state
            
            await asyncio.sleep(0.5)  # 500ms updates
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.get("/", include_in_schema=False)
async def get_dashboard():
    """Get the HTML dashboard."""
    return FileResponse('dashboard/static/index.html')


class TweetIngestRequest(BaseModel):
    tweet_text: str
    author: str = "demo_user"

@app.post("/ingest-tweet")
async def ingest_tweet(request: TweetIngestRequest, api_key: str = Depends(verify_api_key)):
    """Ingest a single tweet for demo purposes."""
    from tradingagents.sources.tweet_source import Tweet
    from datetime import datetime
    
    # Create a mock tweet
    tweet = Tweet(
        id=f"demo_{datetime.now().timestamp()}",
        created_at=datetime.now(),
        author=request.author,
        text=request.tweet_text,
        raw_json={"demo": True}
    )
    
    # Process it
    orchestrator = DashboardOrchestrator()
    sentiment = await orchestrator.ingest_tweet(tweet)
    
    return {
        "message": "Tweet ingested",
        "tweet": tweet.model_dump(),
        "sentiment": sentiment.model_dump()
    }

@app.post("/run-demo")
async def run_demo(symbol: str = "BTCUSD", live: bool = False, api_key: str = Depends(verify_api_key)):
    """Run a demo trading session."""
    global dashboard_state
    
    # Reset state
    dashboard_state = DashboardStatus(
        status="idle",
        symbol=symbol,
        current_price=None,
        technical_indicators=TechnicalIndicators(),
        sentiment=None,
        trade_decision=None,
        risk_approval=None,
        equity_curve=[],
        last_update=None,
        tick_count=0,
        errors=[]
    )
    
    # Run orchestrator in background
    orchestrator = DashboardOrchestrator()
    asyncio.create_task(orchestrator.run_once(symbol, live))
    
    return {"message": f"Demo started for {symbol}", "status": "running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 