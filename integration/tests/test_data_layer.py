"""Unit tests for data layer (candles and ATR)."""
import pytest
from datetime import datetime, timezone
from integration.data import get_candles, compute_atr


class TestDataLayer:
    """Test cases for data layer functionality."""

    def test_get_candles_structure(self):
        """Test candle structure and basic constraints."""
        candles = get_candles("BTC/USDT", limit=120)
        
        # Length constraints
        assert len(candles) >= 50
        assert len(candles) <= 120
        
        # Required keys per candle
        required_keys = {"timestamp", "open", "high", "low", "close", "volume"}
        for candle in candles:
            assert isinstance(candle, dict)
            assert set(candle.keys()) == required_keys
            
            # Type validation
            assert isinstance(candle["timestamp"], int)
            assert isinstance(candle["open"], (int, float))
            assert isinstance(candle["high"], (int, float))
            assert isinstance(candle["low"], (int, float))
            assert isinstance(candle["close"], (int, float))
            assert isinstance(candle["volume"], (int, float))
            
            # OHLC constraints
            assert candle["high"] >= candle["close"]
            assert candle["low"] <= candle["close"]
            assert candle["high"] >= candle["low"]
            assert candle["volume"] > 0
        
        # Ascending timestamps
        timestamps = [candle["timestamp"] for candle in candles]
        assert timestamps == sorted(timestamps), "Timestamps must be in ascending order"
        
        # Last timestamp within 15 minutes of current UTC time
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        last_timestamp = candles[-1]["timestamp"]
        time_diff_minutes = (now_ms - last_timestamp) / (1000 * 60)
        assert time_diff_minutes <= 15, f"Last timestamp too old: {time_diff_minutes} minutes"

    def test_compute_atr_positive(self):
        """Test ATR computation returns positive value."""
        candles = get_candles("BTC/USDT", limit=50)
        atr = compute_atr(candles, period=14)
        
        assert isinstance(atr, float)
        assert atr > 0
        assert atr < 10000  # Reasonable upper bound for ATR

    def test_compute_atr_insufficient(self):
        """Test ATR computation with insufficient candles."""
        # Create a small list of candles manually (fewer than period+1)
        small_candles = []
        base_time = 1700000000000  # Fixed timestamp
        for i in range(10):  # Only 10 candles
            candle = {
                "timestamp": base_time + i * 300000,  # 5-minute intervals
                "open": 50000.0 + i,
                "high": 50010.0 + i,
                "low": 49990.0 + i,
                "close": 50005.0 + i,
                "volume": 100.0
            }
            small_candles.append(candle)
        
        with pytest.raises(ValueError) as exc_info:
            compute_atr(small_candles, period=14)  # Needs 15 candles (14+1)
        
        error_message = str(exc_info.value)
        assert "Insufficient candles" in error_message
        assert "need 15" in error_message
        assert "got 10" in error_message

    def test_determinism_same_symbol(self):
        """Test that same symbol produces identical results."""
        # Call get_candles twice for same symbol
        candles1 = get_candles("BTC/USDT", limit=60)
        candles2 = get_candles("BTC/USDT", limit=60)
        
        # Compare first 10 close values for determinism
        close_values1 = [candle["close"] for candle in candles1[:10]]
        close_values2 = [candle["close"] for candle in candles2[:10]]
        
        assert close_values1 == close_values2, "Same symbol should produce identical results"
        
        # Also check other OHLC values for first candle
        assert candles1[0]["open"] == candles2[0]["open"]
        assert candles1[0]["high"] == candles2[0]["high"]  
        assert candles1[0]["low"] == candles2[0]["low"]
        assert candles1[0]["volume"] == candles2[0]["volume"]

    def test_symbol_variation_differs(self):
        """Test that different symbols produce different results."""
        candles_btc = get_candles("BTC/USDT", limit=60)
        candles_eth = get_candles("ETH/USDT", limit=60)
        
        # First candle close should be different for different symbols
        btc_first_close = candles_btc[0]["close"]
        eth_first_close = candles_eth[0]["close"]
        
        assert btc_first_close != eth_first_close, "Different symbols should produce different results"
        
        # BTC should have higher base price than ETH
        assert btc_first_close > eth_first_close, "BTC should have higher price than ETH"
        
        # Check price ranges are reasonable
        assert 45000 <= btc_first_close <= 55000, f"BTC price out of expected range: {btc_first_close}"
        assert 900 <= eth_first_close <= 1100, f"ETH price out of expected range: {eth_first_close}" 