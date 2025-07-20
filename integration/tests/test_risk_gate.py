"""Unit tests for risk gate functionality."""
import pytest
from integration.risk import apply_risk
from integration.schema.signal import TradingSignal, RiskPlan, TakeProfit


class TestRiskGate:
    """Test cases for risk gate validation."""

    def create_synthetic_candles(self, num_candles=50, volatility=100.0):
        """Create synthetic candles with controlled ATR."""
        candles = []
        base_time = 1700000000000
        base_price = 50000.0
        
        for i in range(num_candles):
            # Create consistent volatility for predictable ATR
            price = base_price + i * 10  # Slight trend
            high = price + volatility
            low = price - volatility
            
            candle = {
                "timestamp": base_time + i * 300000,
                "open": price,
                "high": high,
                "low": low,
                "close": price,
                "volume": 100.0
            }
            candles.append(candle)
        
        return candles

    def create_test_signal(self, symbol="BTC/USDT", stop=49000.0, tp1=51000.0, tp2=52000.0, max_capital_pct=0.05):
        """Create a test trading signal."""
        risk_plan = RiskPlan(
            initial_stop=stop,
            take_profits=[
                TakeProfit(price=tp1, size_pct=0.5),
                TakeProfit(price=tp2, size_pct=0.5),
            ],
            max_capital_pct=max_capital_pct
        )
        
        signal = TradingSignal(
            symbol=symbol,
            side="long",
            confidence=0.6,
            entry={"type": "market"},
            risk=risk_plan,
            rationale="Test signal"
        )
        
        return signal

    def create_test_config(self, min_atr_mult=0.5, max_atr_mult=5.0, min_rr=1.5, max_capital_pct=0.05):
        """Create test configuration."""
        return {
            "risk": {
                "min_atr_multiple": min_atr_mult,
                "max_atr_multiple": max_atr_mult,
                "min_rr": min_rr,
                "atr_period": 14
            },
            "max_capital_pct": max_capital_pct
        }

    def test_apply_risk_accepts_valid_signal(self):
        """Test that a valid signal passes all risk filters."""
        # Create candles with known volatility (ATR ≈ 200)
        candles = self.create_synthetic_candles(num_candles=50, volatility=100.0)
        
        # Current price is 50490 (last candle), ATR ≈ 200
        # Create signal with stop=49500, TP1=51500, TP2=52500
        # Distance = 50490 - 49500 = 990
        # RR = (51500 - 50490) / (50490 - 49500) = 1010/990 ≈ 1.02
        signal = self.create_test_signal(
            stop=49500.0,
            tp1=51500.0,  
            tp2=52500.0
        )
        
        # Config with min_rr=1.0 to accept this signal
        config = self.create_test_config(min_rr=1.0)
        
        result = apply_risk(signal, candles, config)
        
        # Should return the signal (passes all filters)
        assert result is not None
        assert result.symbol == "BTC/USDT"
        assert result.side == "long"
        assert result.risk.initial_stop == 49500.0

    def test_apply_risk_rejects_small_distance(self):
        """Test rejection when distance is too small relative to ATR."""
        candles = self.create_synthetic_candles(num_candles=50, volatility=100.0)
        
        # ATR ≈ 200, min_mult = 0.5, so min distance = 100
        # Create signal with very tight stop: distance = 50490 - 50450 = 40 < 100
        signal = self.create_test_signal(
            stop=50450.0,  # Very close to entry
            tp1=51000.0,
            tp2=52000.0
        )
        
        config = self.create_test_config(min_atr_mult=0.5)
        
        result = apply_risk(signal, candles, config)
        
        # Should return None (distance too small)
        assert result is None

    def test_apply_risk_rejects_large_distance(self):
        """Test rejection when distance is too large relative to ATR."""
        candles = self.create_synthetic_candles(num_candles=50, volatility=100.0)
        
        # ATR ≈ 200, max_mult = 5.0, so max distance = 1000
        # Create signal with very wide stop: distance = 50490 - 48000 = 2490 > 1000
        signal = self.create_test_signal(
            stop=48000.0,  # Very far from entry
            tp1=52000.0,
            tp2=54000.0
        )
        
        config = self.create_test_config(max_atr_mult=5.0)
        
        result = apply_risk(signal, candles, config)
        
        # Should return None (distance too large)
        assert result is None

    def test_apply_risk_rejects_low_rr(self):
        """Test rejection when risk-reward ratio is too low."""
        candles = self.create_synthetic_candles(num_candles=50, volatility=100.0)
        
        # Current price ≈ 50490
        # Create signal with poor RR: stop=49000, TP1=50700
        # Distance = 50490 - 49000 = 1490
        # RR = (50700 - 50490) / (50490 - 49000) = 210/1490 ≈ 0.14 < 1.5
        signal = self.create_test_signal(
            stop=49000.0,
            tp1=50700.0,  # Small TP relative to stop distance
            tp2=51000.0
        )
        
        config = self.create_test_config(min_rr=1.5)
        
        result = apply_risk(signal, candles, config)
        
        # Should return None (RR too low)
        assert result is None

    def test_apply_risk_caps_max_capital_pct(self):
        """Test that max_capital_pct is capped to config value."""
        candles = self.create_synthetic_candles(num_candles=50, volatility=100.0)
        
        # Create signal with high capital percentage
        signal = self.create_test_signal(
            stop=49500.0,
            tp1=51500.0,
            tp2=52500.0,
            max_capital_pct=0.9  # High initial value
        )
        
        # Config with lower max capital
        config = self.create_test_config(
            min_rr=1.0,  # Allow the signal to pass RR check
            max_capital_pct=0.05  # Should cap to this value
        )
        
        result = apply_risk(signal, candles, config)
        
        # Should return signal with capped capital percentage
        assert result is not None
        assert result.risk.max_capital_pct == 0.05  # Capped to config value

    def test_apply_risk_insufficient_candles(self):
        """Test rejection when insufficient candles for ATR calculation."""
        # Create too few candles (only 10, need 15 for ATR period 14)
        candles = self.create_synthetic_candles(num_candles=10)
        
        signal = self.create_test_signal()
        config = self.create_test_config()
        
        result = apply_risk(signal, candles, config)
        
        # Should return None (insufficient candles)
        assert result is None

    def test_apply_risk_handles_short_signals(self):
        """Test risk gate with short signals."""
        candles = self.create_synthetic_candles(num_candles=50, volatility=100.0)
        
        # Create short signal (reverse logic)
        risk_plan = RiskPlan(
            initial_stop=51000.0,  # Stop above entry for short
            take_profits=[
                TakeProfit(price=49500.0, size_pct=0.5),  # TP below entry for short
                TakeProfit(price=48500.0, size_pct=0.5),
            ],
            max_capital_pct=0.05
        )
        
        signal = TradingSignal(
            symbol="BTC/USDT",
            side="short",
            confidence=0.6,
            entry={"type": "market"},
            risk=risk_plan,
            rationale="Test short signal"
        )
        
        config = self.create_test_config(min_rr=1.0)
        
        result = apply_risk(signal, candles, config)
        
        # Should handle short signals correctly
        assert result is not None
        assert result.side == "short" 