"""
Whale Alert API utilities for on-chain transfer monitoring.
"""

import asyncio
import logging
from typing import Callable, Dict, List, Optional
import httpx
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class WhaleAlertClient:
    """Whale Alert API client for monitoring large transfers."""
    
    def __init__(self, api_key: str, callback: Callable, min_amount: float = 500000):
        self.api_key = api_key
        self.callback = callback
        self.min_amount = min_amount  # Minimum USD amount to track
        self.base_url = "https://api.whale-alert.io/v1"
        self.running = False
        self.check_interval = 60  # 1 minute
        self.last_check = None
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Whale Alert API requests."""
        return {
            "X-WA-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
    async def get_transactions(self, start_time: Optional[datetime] = None) -> List[Dict]:
        """Get recent whale transactions."""
        if start_time is None:
            start_time = datetime.now() - timedelta(minutes=5)
            
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/transactions",
                    headers=self._get_headers(),
                    params={
                        "start": int(start_time.timestamp()),
                        "min_value": self.min_amount,
                        "limit": 100
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("transactions", [])
                else:
                    logger.error(f"Whale Alert API error: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to fetch whale transactions: {e}")
            return []
            
    async def monitor_transactions(self):
        """Monitor for new whale transactions."""
        self.running = True
        while self.running:
            try:
                # Get transactions since last check
                start_time = self.last_check or (datetime.now() - timedelta(minutes=5))
                transactions = await self.get_transactions(start_time)
                
                for transaction in transactions:
                    await self.callback(transaction)
                    
                self.last_check = datetime.now()
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Transaction monitoring error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
                
    async def close(self):
        """Stop monitoring transactions."""
        self.running = False

async def whale_alert_listener(api_key: str, callback: Callable, min_amount: float = 500000):
    """
    Convenience function to start Whale Alert listener.
    
    Args:
        api_key: Whale Alert API key
        callback: Async function to process incoming transactions
        min_amount: Minimum USD amount to track
    """
    client = WhaleAlertClient(api_key, callback, min_amount)
    await client.monitor_transactions()

# Example usage and data processing
async def process_whale_data(transaction: Dict):
    """Example callback function to process whale transactions."""
    logger.info(f"Received whale transaction: {transaction}")
    # TODO: Process and store data for whale activity analysis
    # This could include:
    # - Transfer amount and direction
    # - Source and destination addresses
    # - Token/coin information
    # - Impact assessment

# Alternative: Get historical transactions (for backtesting)
async def get_historical_transactions(api_key: str, hours_back: int = 24, min_amount: float = 500000) -> List[Dict]:
    """Get historical whale transactions (useful for backtesting)."""
    headers = {"X-WA-API-KEY": api_key}
    start_time = datetime.now() - timedelta(hours=hours_back)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.whale-alert.io/v1/transactions",
                headers=headers,
                params={
                    "start": int(start_time.timestamp()),
                    "end": int(datetime.now().timestamp()),
                    "min_value": min_amount,
                    "limit": 1000
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("transactions", [])
            else:
                logger.error(f"Historical data fetch failed: {response.status_code}")
                return []
                
    except Exception as e:
        logger.error(f"Failed to fetch historical transactions: {e}")
        return []

# Transaction analysis utilities
def analyze_transaction_impact(transaction: Dict) -> Dict:
    """Analyze the potential impact of a whale transaction."""
    amount_usd = transaction.get("amount_usd", 0)
    symbol = transaction.get("symbol", "")
    
    # Simple impact scoring based on amount
    if amount_usd > 10000000:  # > $10M
        impact = "high"
    elif amount_usd > 1000000:  # > $1M
        impact = "medium"
    else:
        impact = "low"
        
    return {
        "transaction_id": transaction.get("hash", ""),
        "symbol": symbol,
        "amount_usd": amount_usd,
        "impact_level": impact,
        "timestamp": transaction.get("timestamp", ""),
        "from_address": transaction.get("from", {}).get("address", ""),
        "to_address": transaction.get("to", {}).get("address", ""),
        "transaction_type": transaction.get("transaction_type", "")
    } 