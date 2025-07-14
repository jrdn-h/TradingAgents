"""
Hyperliquid WebSocket utilities for real-time crypto data ingestion.
"""

import asyncio
import json
import logging
from typing import Callable, Dict, List, Optional
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)

class HyperliquidWebSocket:
    """WebSocket client for Hyperliquid real-time data."""
    
    def __init__(self, symbols: List[str], callback: Callable):
        self.symbols = symbols
        self.callback = callback
        self.ws_url = "wss://api.hyperliquid.xyz/ws"  # Keep this URL
        self.running = False
        self.reconnect_delay = 1
        self.max_reconnect_delay = 60
        
    async def connect(self):
        """Establish WebSocket connection and subscribe to symbols."""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            logger.info(f"Connected to Hyperliquid WebSocket")
            
            # Subscribe to symbols - Hyperliquid uses a different format
            for symbol in self.symbols:
                # Try different subscription formats for Hyperliquid
                # Format 1: Simple subscribe
                subscribe_msg = {
                    "subscribe": f"{symbol.upper()}/ticker"
                }
                await self.websocket.send(json.dumps(subscribe_msg))
                logger.info(f"Subscribed to {symbol} with format 1")
                
                # Wait a moment and try format 2 if needed
                await asyncio.sleep(1)
                subscribe_msg2 = {
                    "method": "SUBSCRIBE",
                    "params": [f"{symbol.lower()}@ticker"],
                    "id": 1
                }
                await self.websocket.send(json.dumps(subscribe_msg2))
                logger.info(f"Subscribed to {symbol} with format 2")
                
        except Exception as e:
            logger.error(f"Failed to connect to Hyperliquid: {e}")
            raise
            
    async def listen(self):
        """Listen for incoming messages and process them."""
        self.running = True
        while self.running:
            try:
                message = await self.websocket.recv()
                logger.debug(f"Raw message: {message}")
                data = json.loads(message)
                logger.info(f"Processed data: {data}")
                await self.callback(data)
                
            except ConnectionClosed:
                logger.warning("WebSocket connection closed, attempting to reconnect...")
                await self._reconnect()
            except WebSocketException as e:
                logger.error(f"WebSocket error: {e}")
                await self._reconnect()
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                await asyncio.sleep(1)
                
    async def _reconnect(self):
        """Handle reconnection with exponential backoff."""
        self.running = False
        await asyncio.sleep(self.reconnect_delay)
        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
        
        try:
            await self.connect()
            self.reconnect_delay = 1  # Reset delay on successful connection
            self.running = True
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            
    async def close(self):
        """Close the WebSocket connection."""
        self.running = False
        if hasattr(self, 'websocket'):
            await self.websocket.close()

async def hyperliquid_ws_listener(symbols: List[str], callback: Callable):
    """
    Convenience function to start Hyperliquid WebSocket listener.
    
    Args:
        symbols: List of trading symbols to subscribe to
        callback: Async function to process incoming data
    """
    client = HyperliquidWebSocket(symbols, callback)
    await client.connect()
    await client.listen()

async def mock_hyperliquid_ws_listener(symbols: List[str], callback: Callable):
    """
    Mock Hyperliquid WebSocket listener for testing.
    Simulates live price data without requiring actual API connection.
    """
    import random
    import time
    
    logger.info(f"Mock WebSocket: Starting for symbols {symbols}")
    print(f"[Mock] Starting WebSocket for {symbols}")
    
    # Generate realistic price movements
    base_price = 42000
    for i in range(25):  # Generate 25 ticks
        # Simulate price movement with some randomness
        price_change = random.uniform(-100, 100)
        base_price += price_change
        price = round(base_price, 2)
        
        # Create mock ticker data
        mock_data = {
            "channel": "ticker",
            "symbol": symbols[0],
            "price": price,
            "timestamp": int(time.time() * 1000)
        }
        
        print(f"[Mock] Tick {i+1}: ${price}")
        await callback(mock_data)
        await asyncio.sleep(0.5)  # Simulate tick frequency
    
    print("[Mock] WebSocket completed")
    logger.info("Mock WebSocket: Completed")

# Example usage and data processing
async def process_hyperliquid_data(data: Dict):
    """Example callback function to process Hyperliquid data."""
    logger.info(f"Received Hyperliquid data: {data}")
    # TODO: Process and store data for agents to consume
    # This could include:
    # - Price updates
    # - Funding rates
    # - Order book changes
    # - Trade executions 