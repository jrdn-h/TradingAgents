"""Unit tests for breakout signal generator."""
import pytest
from integration.signal_gen import generate_signal
from integration.schema.signal import TradingSignal


class TestSignalGen:
    """Test cases for signal generation functionality."""

    def create_test_candles(self, num_candles=50, breakout_last=False, stop_invalid=False):
        """Helper to create test candle data."""
        candles = []
        base_time = 1700000000000  # Fixed timestamp
        base_price = 50000.0
        
        for i in range(num_candles):
            # Create normal price action for most candles
            if i < num_candles - 1:  # All except last candle
                price = base_price + i * 10  # Slight upward trend
                candle = {
                    "timestamp": base_time + i * 300000,  # 5-minute intervals
                    "open": price,
                    "high": price + 5,
                    "low": price - 5,
                    "close": price,
                    "volume": 100.0
                }
            else:  # Last candle
                if breakout_last:
                    # Make last close break above all prior highs
                    max_prior_high = max(c["high"] for c in candles[-20:] if candles)
                    breakout_price = max_prior_high + 100  # Clear breakout
                    
                    if stop_invalid:
                        # Make stop above entry (invalid setup)
                        candle = {
                            "timestamp": base_time + i * 300000,
                            "open": breakout_price - 10,
                            "high": breakout_price + 5,
                            "low": breakout_price + 50,  # Low above close (invalid)
                            "close": breakout_price,
                            "volume": 100.0
                        }
                    else:
                        # Valid breakout setup
                        candle = {
                            "timestamp": base_time + i * 300000,
                            "open": breakout_price - 10,
                            "high": breakout_price + 5,
                            "low": breakout_price - 50,  # Valid low below close
                            "close": breakout_price,
                            "volume": 100.0
                        }
                else:
                    # No breakout - last close below prior highs
                    price = base_price + i * 10 - 200  # Below trend
                    candle = {
                        "timestamp": base_time + i * 300000,
                        "open": price,
                        "high": price + 5,
                        "low": price - 5,
                        "close": price,
                        "volume": 100.0
                    }
            
            candles.append(candle)
        
        return candles

    def test_generate_signal_breakout_creates_signal(self, monkeypatch):
        """Test that a valid breakout creates a TradingSignal."""
        # Create test candles with breakout
        test_candles = self.create_test_candles(num_candles=50, breakout_last=True)
        
        # Mock get_candles to return our test data
        def mock_get_candles(symbol, limit=200):
            return test_candles
        
        monkeypatch.setattr("integration.signal_gen.get_candles", mock_get_candles)
        
        # Generate signal
        signal = generate_signal("BTC/USDT")
        
        # Assertions
        assert signal is not None
        assert isinstance(signal, TradingSignal)
        assert signal.side == "long"
        assert signal.symbol == "BTC/USDT"
        assert signal.confidence == 0.6
        assert signal.entry == {"type": "market"}
        assert signal.rationale == "Breakout above 20-bar high"
        
        # Check take profits
        assert len(signal.risk.take_profits) == 2
        tp1 = signal.risk.take_profits[0]
        tp2 = signal.risk.take_profits[1]
        
        # Entry price is last close
        entry_price = test_candles[-1]["close"]
        
        # TP2 should be higher than TP1, both higher than entry
        assert tp2.price > tp1.price > entry_price
        assert signal.risk.initial_stop < entry_price

    def test_generate_signal_no_breakout_returns_none(self, monkeypatch):
        """Test that no breakout returns None."""
        # Create test candles WITHOUT breakout
        test_candles = self.create_test_candles(num_candles=50, breakout_last=False)
        
        # Mock get_candles
        def mock_get_candles(symbol, limit=200):
            return test_candles
        
        monkeypatch.setattr("integration.signal_gen.get_candles", mock_get_candles)
        
        # Generate signal
        signal = generate_signal("BTC/USDT")
        
        # Should return None (no breakout)
        assert signal is None

    def test_generate_signal_stop_below_entry(self, monkeypatch):
        """Test that generated stop is below entry and distance is positive."""
        # Create valid breakout candles
        test_candles = self.create_test_candles(num_candles=50, breakout_last=True)
        
        def mock_get_candles(symbol, limit=200):
            return test_candles
        
        monkeypatch.setattr("integration.signal_gen.get_candles", mock_get_candles)
        
        signal = generate_signal("BTC/USDT")
        
        assert signal is not None
        entry_price = test_candles[-1]["close"]
        stop_price = signal.risk.initial_stop
        
        # Stop must be below entry
        assert stop_price < entry_price
        
        # Distance must be positive
        distance = entry_price - stop_price
        assert distance > 0
        
        # Check TP calculations
        tp1_price = signal.risk.take_profits[0].price
        tp2_price = signal.risk.take_profits[1].price
        
        assert abs(tp1_price - (entry_price + distance)) < 1e-6  # TP1 = entry + 1R
        assert abs(tp2_price - (entry_price + 2 * distance)) < 1e-6  # TP2 = entry + 2R

    def test_generate_signal_sizes_sum(self, monkeypatch):
        """Test that take profit size percentages sum to 1.0."""
        test_candles = self.create_test_candles(num_candles=50, breakout_last=True)
        
        def mock_get_candles(symbol, limit=200):
            return test_candles
        
        monkeypatch.setattr("integration.signal_gen.get_candles", mock_get_candles)
        
        signal = generate_signal("BTC/USDT")
        
        assert signal is not None
        
        # Sum of take profit sizes should equal 1.0
        total_size = sum(tp.size_pct for tp in signal.risk.take_profits)
        assert abs(total_size - 1.0) < 1e-6
        
        # Each TP should be 0.5 (50%)
        assert signal.risk.take_profits[0].size_pct == 0.5
        assert signal.risk.take_profits[1].size_pct == 0.5

    def test_generate_signal_minimum_candles(self, monkeypatch):
        """Test that insufficient candles returns None."""
        # Create too few candles (less than max(BREAKOUT_LOOKBACK+2, STOP_LOOKBACK+2) = 22)
        test_candles = self.create_test_candles(num_candles=15)  # Only 15 candles
        
        def mock_get_candles(symbol, limit=200):
            return test_candles
        
        monkeypatch.setattr("integration.signal_gen.get_candles", mock_get_candles)
        
        signal = generate_signal("BTC/USDT")
        
        # Should return None due to insufficient candles
        assert signal is None

    def test_generate_signal_invalid_stop_position(self, monkeypatch):
        """Test that stop above entry returns None."""
        # Create special candles where the last 10 lows are all above the breakout price
        test_candles = []
        base_time = 1700000000000
        base_price = 50000.0
        
        # Create 40 normal candles first
        for i in range(40):
            price = base_price + i * 10
            candle = {
                "timestamp": base_time + i * 300000,
                "open": price,
                "high": price + 5,
                "low": price - 5,
                "close": price,
                "volume": 100.0
            }
            test_candles.append(candle)
        
        # Create last 10 candles with lows above breakout price
        breakout_price = 52000.0  # Higher than all previous highs
        for i in range(40, 50):
            if i == 49:  # Last candle - the breakout
                candle = {
                    "timestamp": base_time + i * 300000,
                    "open": breakout_price - 10,
                    "high": breakout_price + 5,
                    "low": breakout_price + 100,  # Low way above close
                    "close": breakout_price,
                    "volume": 100.0
                }
            else:  # Previous 9 candles in stop lookback also have high lows
                candle = {
                    "timestamp": base_time + i * 300000,
                    "open": breakout_price - 50,
                    "high": breakout_price - 30,
                    "low": breakout_price + 50,  # Low above breakout close
                    "close": breakout_price - 40,
                    "volume": 100.0
                }
            test_candles.append(candle)
        
        def mock_get_candles(symbol, limit=200):
            return test_candles
        
        monkeypatch.setattr("integration.signal_gen.get_candles", mock_get_candles)
        
        signal = generate_signal("BTC/USDT")
        
        # Should return None due to invalid stop position (stop >= entry)
        assert signal is None 