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
from fastapi.responses import HTMLResponse, StreamingResponse
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Auth function
async def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key for protected endpoints."""
    expected_key = os.getenv("DASHBOARD_API_KEY", "demo-key-123")
    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

# Pydantic models for type safety
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

app = FastAPI(
    title="TradingAgents Dashboard",
    description="Live monitoring dashboard for the TradingAgents system",
    version="1.0.0",
    lifespan=lifespan
)

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

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Get the HTML dashboard."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TradingAgents Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        .status-bar {
            background: #ecf0f1;
            padding: 15px 20px;
            border-bottom: 1px solid #bdc3c7;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .status-indicator {
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 0.9em;
        }
        .status-idle { background: #95a5a6; color: white; }
        .status-running { background: #f39c12; color: white; }
        .status-completed { background: #27ae60; color: white; }
        .status-error { background: #e74c3c; color: white; }
        .content {
            padding: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #3498db;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .card h3 {
            margin: 0 0 15px 0;
            color: #2c3e50;
            font-size: 1.2em;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid #ecf0f1;
        }
        .metric:last-child {
            border-bottom: none;
        }
        .metric-label {
            font-weight: 500;
            color: #7f8c8d;
        }
        .metric-value {
            font-weight: bold;
            color: #2c3e50;
        }
        .price {
            font-size: 2em;
            font-weight: bold;
            color: #27ae60;
            text-align: center;
            margin: 20px 0;
        }
        .chart-container {
            height: 200px;
            background: white;
            border-radius: 8px;
            padding: 10px;
            border: 1px solid #ecf0f1;
        }
        .error {
            background: #fee;
            color: #c0392b;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            border-left: 4px solid #e74c3c;
        }
        .sentiment-gauge {
            text-align: center;
            margin: 20px 0;
        }
        .sentiment-score {
            font-size: 1.5em;
            font-weight: bold;
            margin-top: 10px;
            color: #2c3e50;
        }
        .tweet-feed {
            max-height: 300px;
            overflow-y: auto;
            background: white;
            border-radius: 8px;
            padding: 10px;
            border: 1px solid #ecf0f1;
        }
        .tweet-item {
            padding: 10px;
            border-bottom: 1px solid #ecf0f1;
            margin-bottom: 10px;
            border-radius: 5px;
            background: #f8f9fa;
            border-left: 4px solid #95a5a6; /* Default neutral */
        }
        .tweet-item.bullish {
            border-left-color: #27ae60;
            background: #f0fff4;
        }
        .tweet-item.bearish {
            border-left-color: #e74c3c;
            background: #fff5f5;
        }
        .tweet-item:last-child {
            border-bottom: none;
            margin-bottom: 0;
        }
        .tweet-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-size: 0.9em;
        }
        .tweet-author {
            font-weight: bold;
            color: #3498db;
        }
        .tweet-time {
            color: #7f8c8d;
        }
        .tweet-text {
            margin-bottom: 8px;
            line-height: 1.4;
        }
        .tweet-sentiment {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .sentiment-badge {
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .sentiment-bullish { background: #d5f4e6; color: #27ae60; }
        .sentiment-bearish { background: #fadbd8; color: #e74c3c; }
        .sentiment-neutral { background: #f8f9fa; color: #7f8c8d; }
        .tweet-keywords {
            font-size: 0.8em;
            color: #7f8c8d;
            margin-top: 5px;
        }
        .tweet-placeholder {
            text-align: center;
            color: #7f8c8d;
            font-style: italic;
            padding: 20px;
        }
        .auto-refresh {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.9);
            padding: 10px;
            border-radius: 8px;
            font-size: 0.9em;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 TradingAgents Dashboard</h1>
        </div>
        
        <div class="status-bar">
            <div>
                <strong>Symbol:</strong> <span id="symbol">-</span> | 
                <strong>Ticks:</strong> <span id="tick-count">0</span> | 
                <strong>Last Update:</strong> <span id="last-update">-</span>
            </div>
            <div class="status-indicator" id="status-indicator">Idle</div>
        </div>
        
        <div class="content">
            <div class="card">
                <h3>💰 Current Price</h3>
                <div class="price" id="current-price">$0.00</div>
            </div>
            
            <div class="card">
                <h3>📊 Technical Indicators</h3>
                <div class="metric">
                    <span class="metric-label">SMA:</span>
                    <span class="metric-value" id="sma">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">EMA:</span>
                    <span class="metric-value" id="ema">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Breakout:</span>
                    <span class="metric-value" id="breakout">-</span>
                </div>
            </div>
            
            <div class="card">
                <h3>😊 Sentiment Index</h3>
                <div class="sentiment-gauge">
                    <svg width="120" height="60" viewBox="0 0 120 60">
                        <defs>
                            <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" style="stop-color:#e74c3c"/>
                                <stop offset="50%" style="stop-color:#95a5a6"/>
                                <stop offset="100%" style="stop-color:#27ae60"/>
                            </linearGradient>
                        </defs>
                        <path d="M 10 50 A 40 40 0 0 1 110 50" stroke="url(#gaugeGradient)" stroke-width="8" fill="none"/>
                        <circle id="gauge-needle" cx="60" cy="50" r="4" fill="#2c3e50"/>
                    </svg>
                    <div id="sentiment-score" class="sentiment-score">0.00</div>
                </div>
            </div>
            
            <div class="card">
                <h3>🐦 Tweet Feed</h3>
                <div id="tweet-feed" class="tweet-feed">
                    <div class="tweet-placeholder">No tweets yet...</div>
                </div>
            </div>
            
            <div class="card">
                <h3>🎯 Trade Decision</h3>
                <div id="trade-decision">-</div>
            </div>
            
            <div class="card">
                <h3>🛡️ Risk Approval</h3>
                <div id="risk-approval">-</div>
            </div>
            
            <div class="card">
                <h3>📈 Equity Curve</h3>
                <div class="chart-container" id="equity-chart">
                    <canvas id="equity-canvas"></canvas>
                </div>
            </div>
        </div>
        
        <div id="errors"></div>
    </div>
    
    <div class="auto-refresh">
        Live SSE stream (500ms updates)
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        let equityChart = null;
        
        function updateDashboard(data) {
            // Update status
            document.getElementById('symbol').textContent = data.symbol || '-';
            document.getElementById('tick-count').textContent = data.tick_count || 0;
            document.getElementById('last-update').textContent = data.last_update ? 
                new Date(data.last_update).toLocaleTimeString() : '-';
            
            // Update status indicator
            const statusIndicator = document.getElementById('status-indicator');
            statusIndicator.className = 'status-indicator status-' + (data.status || 'idle');
            statusIndicator.textContent = data.status || 'idle';
            
            // Update price
            const priceElement = document.getElementById('current-price');
            if (data.current_price) {
                priceElement.textContent = '$' + data.current_price.toLocaleString();
            }
            
            // Update technical indicators
            if (data.technical_indicators) {
                document.getElementById('sma').textContent = data.technical_indicators.sma || '-';
                document.getElementById('ema').textContent = data.technical_indicators.ema || '-';
                document.getElementById('breakout').textContent = data.technical_indicators.breakout || '-';
            }
            
            // Update sentiment gauge
            const sentimentScore = document.getElementById('sentiment-score');
            const gaugeNeedle = document.getElementById('gauge-needle');
            if (data.sentiment_index !== undefined) {
                sentimentScore.textContent = data.sentiment_index.toFixed(3);
                
                // Update gauge needle position (-1 to 1 maps to 10 to 110)
                const angle = (data.sentiment_index + 1) * 50; // -1..1 -> 0..100
                const x = 10 + (angle / 100) * 100; // 10..110
                gaugeNeedle.setAttribute('cx', x);
            }
            
            // Update tweet feed
            const tweetFeed = document.getElementById('tweet-feed');
            if (data.tweet_feed && data.tweet_feed.length > 0) {
                tweetFeed.innerHTML = data.tweet_feed.map(tweet => `
                    <div class="tweet-item ${tweet.sentiment_label}">
                        <div class="tweet-header">
                            <span class="tweet-author">@${tweet.author}</span>
                            <span class="tweet-time">${new Date(tweet.created_at).toLocaleTimeString()}</span>
                        </div>
                        <div class="tweet-text">${tweet.text}</div>
                        <div class="tweet-sentiment">
                            <span class="sentiment-badge sentiment-${tweet.sentiment_label}">${tweet.sentiment_label}</span>
                            <span>Score: ${tweet.sentiment_score.toFixed(3)}</span>
                        </div>
                        ${tweet.keywords.length > 0 ? `<div class="tweet-keywords">Keywords: ${tweet.keywords.join(', ')}</div>` : ''}
                    </div>
                `).join('');
            }
            
            // Update trade decision
            const tradeElement = document.getElementById('trade-decision');
            if (data.trade_decision) {
                tradeElement.textContent = JSON.stringify(data.trade_decision, null, 2);
            }
            
            // Update risk approval
            const riskElement = document.getElementById('risk-approval');
            if (data.risk_approval) {
                riskElement.textContent = JSON.stringify(data.risk_approval, null, 2);
            }
            
            // Update equity chart
            if (data.equity_curve && data.equity_curve.length > 0) {
                updateEquityChart(data.equity_curve);
            }
            
            // Update errors
            const errorsElement = document.getElementById('errors');
            if (data.errors && data.errors.length > 0) {
                errorsElement.innerHTML = data.errors.map(error => 
                    `<div class="error">${error}</div>`
                ).join('');
            } else {
                errorsElement.innerHTML = '';
            }
        }
        
        function updateEquityChart(equityData) {
            const ctx = document.getElementById('equity-canvas').getContext('2d');
            
            if (equityChart) {
                equityChart.destroy();
            }
            
            const labels = equityData.map(point => point.tick);
            const data = equityData.map(point => point.equity);
            
            equityChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Equity',
                        data: data,
                        borderColor: '#27ae60',
                        backgroundColor: 'rgba(39, 174, 96, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false
                        }
                    }
                }
            });
        }
        
        async function fetchStatus() {
            try {
                const response = await fetch('/status');
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Error fetching status:', error);
            }
        }
        
        // Connect to SSE stream
        const eventSource = new EventSource('/stream');
        
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        };
        
        eventSource.onerror = function(event) {
            console.error('SSE connection error:', event);
            // Fallback to polling if SSE fails
            setInterval(fetchStatus, 2000);
        };
        
        // Initial load
        fetchStatus();
    </script>
</body>
</html>
"""

from pydantic import BaseModel

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