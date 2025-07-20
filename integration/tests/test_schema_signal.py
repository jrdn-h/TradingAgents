"""Unit tests for TradingSignal schema validation."""
import pytest
from pydantic import ValidationError

from integration.schema.signal import TradingSignal, RiskPlan, TakeProfit


class TestSchemaSignal:
    """Test cases for TradingSignal schema validation."""

    def test_valid_signal_roundtrip(self):
        """Test valid signal creation, serialization, and deserialization."""
        # Create take profits that sum to 1.0
        tp1 = TakeProfit(price=51000.0, size_pct=0.5)
        tp2 = TakeProfit(price=52000.0, size_pct=0.5)
        
        # Create risk plan
        risk = RiskPlan(
            initial_stop=50000.0,
            take_profits=[tp1, tp2],
            max_capital_pct=0.05
        )
        
        # Create trading signal
        signal = TradingSignal(
            symbol="BTC/USDT",
            side="long",
            confidence=0.6,
            entry={"type": "market"},
            risk=risk,
            rationale="Breakout above resistance"
        )
        
        # Test basic properties
        assert signal.version == "1.0"
        assert signal.symbol == "BTC/USDT"
        assert signal.side == "long"
        assert signal.confidence == 0.6
        assert signal.rationale == "Breakout above resistance"
        
        # Test take profit sum
        tp_sum = sum(tp.size_pct for tp in signal.risk.take_profits)
        assert abs(tp_sum - 1.0) < 1e-6
        
        # Test serialization roundtrip
        json_str = signal.model_dump_json()
        restored = TradingSignal.model_validate_json(json_str)
        
        assert restored.version == "1.0"
        assert restored.symbol == "BTC/USDT"
        assert restored.confidence == 0.6
        assert len(restored.risk.take_profits) == 2
        
        # Test rationale trimming (create signal with whitespace)
        signal_with_spaces = TradingSignal(
            symbol="BTC/USDT",
            side="long", 
            confidence=0.6,
            entry={"type": "market"},
            risk=risk,
            rationale="  Trimmed rationale  "
        )
        assert signal_with_spaces.rationale == "Trimmed rationale"

    def test_invalid_tp_count(self):
        """Test validation fails with wrong number of take profits."""
        # Only one take profit (should fail)
        tp1 = TakeProfit(price=51000.0, size_pct=0.99)
        
        with pytest.raises(ValidationError) as exc_info:
            RiskPlan(
                initial_stop=50000.0,
                take_profits=[tp1],  # Only 1 TP
                max_capital_pct=0.05
            )
        
        error_message = str(exc_info.value)
        assert "Exactly 2 take_profits required" in error_message

    def test_invalid_tp_sum(self):
        """Test validation fails when take profits don't sum to 1.0."""
        # Take profits sum to 1.1 (should fail)
        tp1 = TakeProfit(price=51000.0, size_pct=0.6)
        tp2 = TakeProfit(price=52000.0, size_pct=0.5)
        
        with pytest.raises(ValidationError) as exc_info:
            RiskPlan(
                initial_stop=50000.0,
                take_profits=[tp1, tp2],  # Sum = 1.1
                max_capital_pct=0.05
            )
        
        error_message = str(exc_info.value)
        assert "Take profit size_pct must sum to 1.0" in error_message
        assert "1.1" in error_message

    def test_confidence_bounds(self):
        """Test confidence validation bounds."""
        tp1 = TakeProfit(price=51000.0, size_pct=0.5)
        tp2 = TakeProfit(price=52000.0, size_pct=0.5)
        risk = RiskPlan(
            initial_stop=50000.0,
            take_profits=[tp1, tp2],
            max_capital_pct=0.05
        )
        
        # confidence = 0 should fail
        with pytest.raises(ValidationError):
            TradingSignal(
                symbol="BTC/USDT",
                side="long",
                confidence=0,  # Invalid: must be > 0
                entry={"type": "market"},
                risk=risk,
                rationale="Test"
            )
        
        # confidence = 1.1 should fail  
        with pytest.raises(ValidationError):
            TradingSignal(
                symbol="BTC/USDT",
                side="long",
                confidence=1.1,  # Invalid: must be <= 1
                entry={"type": "market"},
                risk=risk,
                rationale="Test"
            )

    def test_entry_requirements(self):
        """Test entry dictionary validation."""
        tp1 = TakeProfit(price=51000.0, size_pct=0.5)
        tp2 = TakeProfit(price=52000.0, size_pct=0.5)
        risk = RiskPlan(
            initial_stop=50000.0,
            take_profits=[tp1, tp2],
            max_capital_pct=0.05
        )
        
        # Missing 'type' should fail
        with pytest.raises(ValidationError) as exc_info:
            TradingSignal(
                symbol="BTC/USDT",
                side="long",
                confidence=0.6,
                entry={},  # Missing 'type'
                risk=risk,
                rationale="Test"
            )
        assert "entry dict must have 'type'" in str(exc_info.value)
        
        # type='limit' without 'limit_price' should fail
        with pytest.raises(ValidationError) as exc_info:
            TradingSignal(
                symbol="BTC/USDT",
                side="long",
                confidence=0.6,
                entry={"type": "limit"},  # Missing limit_price
                risk=risk,
                rationale="Test"
            )
        assert "limit entries require limit_price" in str(exc_info.value)

    def test_symbol_uppercased(self):
        """Test symbol normalization to uppercase."""
        tp1 = TakeProfit(price=51000.0, size_pct=0.5)
        tp2 = TakeProfit(price=52000.0, size_pct=0.5)
        risk = RiskPlan(
            initial_stop=50000.0,
            take_profits=[tp1, tp2],
            max_capital_pct=0.05
        )
        
        signal = TradingSignal(
            symbol="btc/usdt",  # lowercase input
            side="long",
            confidence=0.6,
            entry={"type": "market"},
            risk=risk,
            rationale="Test"
        )
        
        assert signal.symbol == "BTC/USDT"  # Should be uppercased

    def test_rationale_max_length(self):
        """Test rationale length validation."""
        tp1 = TakeProfit(price=51000.0, size_pct=0.5)
        tp2 = TakeProfit(price=52000.0, size_pct=0.5)
        risk = RiskPlan(
            initial_stop=50000.0,
            take_profits=[tp1, tp2],
            max_capital_pct=0.05
        )
        
        # 80-character rationale should fail (max 60)
        long_rationale = "This is a very long rationale that exceeds the maximum allowed length limit xxxx"
        assert len(long_rationale) == 80
        
        with pytest.raises(ValidationError) as exc_info:
            TradingSignal(
                symbol="BTC/USDT",
                side="long",
                confidence=0.6,
                entry={"type": "market"},
                risk=risk,
                rationale=long_rationale
            )
        
        error_message = str(exc_info.value)
        assert "at most 60 characters" in error_message

    def test_max_capital_pct_bounds(self):
        """Test max_capital_pct validation bounds."""
        tp1 = TakeProfit(price=51000.0, size_pct=0.5)
        tp2 = TakeProfit(price=52000.0, size_pct=0.5)
        
        # max_capital_pct = 1.2 should fail
        with pytest.raises(ValidationError):
            RiskPlan(
                initial_stop=50000.0,
                take_profits=[tp1, tp2],
                max_capital_pct=1.2  # Invalid: must be < 1
            )
        
        # max_capital_pct = 0 should fail
        with pytest.raises(ValidationError):
            RiskPlan(
                initial_stop=50000.0,
                take_profits=[tp1, tp2],
                max_capital_pct=0  # Invalid: must be > 0
            ) 