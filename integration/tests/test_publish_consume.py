"""Unit tests for Redis publish/consume functionality."""
import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from integration.publish import publish_signal, fetch_latest_signal, get_redis_client, REDIS_LIST
from integration.schema.signal import TradingSignal, RiskPlan, TakeProfit


class MockRedis:
    """Simple in-memory Redis mock for testing."""
    
    def __init__(self):
        self.data = []
    
    def lpush(self, key: str, value: str) -> int:
        """Add to left of list."""
        self.data.insert(0, value)
        return len(self.data)
    
    def llen(self, key: str) -> int:
        """Get list length."""
        return len(self.data)
    
    def lindex(self, key: str, index: int) -> str:
        """Get element at index."""
        if 0 <= index < len(self.data):
            return self.data[index]
        return None
    
    def lrem(self, key: str, count: int, value: str) -> int:
        """Remove count occurrences of value."""
        removed = 0
        while removed < count and value in self.data:
            self.data.remove(value)
            removed += 1
        return removed


class TestPublishConsume:
    """Test cases for Redis publish/consume functionality."""
    
    def create_test_signal(self, symbol="BTC/USDT", timestamp=None):
        """Create a test TradingSignal."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Convert datetime to ISO string as expected by schema
        timestamp_str = timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp
        
        return TradingSignal(
            decision_id="test_123",
            timestamp=timestamp_str,
            symbol=symbol,
            side="long", 
            confidence=0.7,
            entry={"type": "market"},
            risk=RiskPlan(
                initial_stop=49000.0,
                take_profits=[
                    TakeProfit(price=51000.0, size_pct=0.5),
                    TakeProfit(price=52000.0, size_pct=0.5)
                ],
                max_capital_pct=0.03
            ),
            rationale="Breakout above resistance"
        )
    
    def test_publish_and_fetch_signal_success(self):
        """Test successful publish and fetch cycle."""
        mock_redis = MockRedis()
        
        with patch('integration.publish.get_redis_client', return_value=mock_redis):
            signal = self.create_test_signal()
            
            # Publish signal
            publish_signal(signal)
            
            # Verify Redis has data
            assert mock_redis.llen(REDIS_LIST) == 1
            
            # Fetch signal
            fetched = fetch_latest_signal("BTC/USDT")
            
            # Verify correct signal returned
            assert fetched is not None
            assert isinstance(fetched, TradingSignal)
            assert fetched.symbol == "BTC/USDT"
            assert fetched.decision_id == "test_123"
            assert fetched.confidence == 0.7
            
            # Verify signal removed after fetch
            assert mock_redis.llen(REDIS_LIST) == 0
    
    def test_fetch_ignores_other_symbol(self):
        """Test that fetch only returns signals for the requested symbol."""
        mock_redis = MockRedis()
        
        with patch('integration.publish.get_redis_client', return_value=mock_redis):
            # Publish signals for different symbols
            signal_btc = self.create_test_signal("BTC/USDT")
            signal_eth = self.create_test_signal("ETH/USDT")
            
            publish_signal(signal_btc)
            publish_signal(signal_eth)
            
            # Verify both signals in Redis
            assert mock_redis.llen(REDIS_LIST) == 2
            
            # Fetch BTC signal
            fetched = fetch_latest_signal("BTC/USDT")
            
            # Should get BTC signal
            assert fetched is not None
            assert fetched.symbol == "BTC/USDT"
            
            # ETH signal should remain
            assert mock_redis.llen(REDIS_LIST) == 1
            
            # Fetch ETH signal
            fetched_eth = fetch_latest_signal("ETH/USDT")
            assert fetched_eth is not None
            assert fetched_eth.symbol == "ETH/USDT"
            
            # Now list should be empty
            assert mock_redis.llen(REDIS_LIST) == 0
    
    def test_fetch_stale_signal(self):
        """Test that stale signals are ignored."""
        mock_redis = MockRedis()
        
        with patch('integration.publish.get_redis_client', return_value=mock_redis):
            # Create signal with old timestamp (2 hours ago)
            old_timestamp = datetime.now(timezone.utc) - timedelta(hours=2)
            stale_signal = self.create_test_signal(timestamp=old_timestamp)
            
            # Manually insert stale signal
            payload = stale_signal.model_dump()
            mock_redis.lpush(REDIS_LIST, json.dumps(payload))
            
            # Try to fetch with 1 hour max age
            fetched = fetch_latest_signal("BTC/USDT", max_age_sec=3600)
            
            # Should return None (stale)
            assert fetched is None
            
            # Signal should still be in Redis (not removed)
            assert mock_redis.llen(REDIS_LIST) == 1
    
    def test_fetch_no_signal(self):
        """Test fetch from empty list returns None gracefully."""
        mock_redis = MockRedis()
        
        with patch('integration.publish.get_redis_client', return_value=mock_redis):
            # Fetch from empty list
            fetched = fetch_latest_signal("BTC/USDT")
            
            # Should return None gracefully
            assert fetched is None
            assert mock_redis.llen(REDIS_LIST) == 0
    
    def test_idempotent_publish_fetch_cycle(self):
        """Test that second fetch returns None after signal consumed."""
        mock_redis = MockRedis()
        
        with patch('integration.publish.get_redis_client', return_value=mock_redis):
            signal = self.create_test_signal()
            
            # Publish signal
            publish_signal(signal)
            assert mock_redis.llen(REDIS_LIST) == 1
            
            # First fetch should succeed
            first_fetch = fetch_latest_signal("BTC/USDT")
            assert first_fetch is not None
            assert first_fetch.decision_id == "test_123"
            assert mock_redis.llen(REDIS_LIST) == 0
            
            # Second fetch should return None (already consumed)
            second_fetch = fetch_latest_signal("BTC/USDT") 
            assert second_fetch is None
            assert mock_redis.llen(REDIS_LIST) == 0
    
    def test_symbol_case_handling(self):
        """Test that symbol matching is case-insensitive (uppercased)."""
        mock_redis = MockRedis()
        
        with patch('integration.publish.get_redis_client', return_value=mock_redis):
            # Publish with lowercase
            signal = self.create_test_signal("btc/usdt")
            publish_signal(signal)
            
            # Fetch with uppercase
            fetched = fetch_latest_signal("BTC/USDT")
            
            # Should match (signal stored as uppercase due to schema normalization)
            assert fetched is not None
            assert fetched.symbol == "BTC/USDT"  # Schema normalizes to uppercase
    
    def test_malformed_json_handling(self):
        """Test that malformed JSON in Redis is safely ignored."""
        mock_redis = MockRedis()
        
        with patch('integration.publish.get_redis_client', return_value=mock_redis):
            # Manually insert malformed JSON
            mock_redis.lpush(REDIS_LIST, "invalid json")
            
            # Add valid signal
            signal = self.create_test_signal()
            publish_signal(signal)
            
            # Should skip malformed and return valid signal
            fetched = fetch_latest_signal("BTC/USDT")
            assert fetched is not None
            assert fetched.decision_id == "test_123" 