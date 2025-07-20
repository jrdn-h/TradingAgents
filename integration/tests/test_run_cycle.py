"""Unit tests for run cycle script."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from integration.scripts.run_cycle import run_cycle
from integration.schema.signal import TradingSignal, RiskPlan, TakeProfit


class TestRunCycle:
    """Test cases for run cycle script."""
    
    def create_test_signal(self, decision_id="cycle_test_123"):
        """Create a test TradingSignal for run cycle tests."""
        return TradingSignal(
            decision_id=decision_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol="BTC/USDT",
            side="long",
            confidence=0.8,
            entry={"type": "market"},
            risk=RiskPlan(
                initial_stop=48000.0,
                take_profits=[
                    TakeProfit(price=52000.0, size_pct=0.5),
                    TakeProfit(price=54000.0, size_pct=0.5)
                ],
                max_capital_pct=0.03
            ),
            rationale="Test cycle signal"
        )
    
    def create_mock_config(self):
        """Create a mock configuration object."""
        config = MagicMock()
        config.symbol = "BTC/USDT"
        config.max_capital_pct = 0.05
        config.risk = MagicMock()
        config.risk.min_atr_multiple = 0.5
        config.risk.max_atr_multiple = 5.0
        config.risk.min_rr = 1.5
        return config
    
    def create_mock_candles(self, num_candles=250):
        """Create mock candle data."""
        candles = []
        base_price = 50000.0
        
        for i in range(num_candles):
            price = base_price + i * 10
            candles.append({
                "timestamp": 1700000000000 + i * 300000,
                "open": price,
                "high": price + 100,
                "low": price - 100,
                "close": price + 50,
                "volume": 1000
            })
        
        return candles
    
    @patch('integration.scripts.run_cycle.load_config')
    @patch('integration.scripts.run_cycle.get_candles')
    @patch('integration.scripts.run_cycle.generate_signal')
    def test_run_cycle_no_breakout(self, mock_generate, mock_candles, mock_config):
        """Test run cycle when no breakout signal is generated."""
        # Setup mocks
        mock_config.return_value = self.create_mock_config()
        mock_candles.return_value = self.create_mock_candles()
        mock_generate.return_value = None  # No signal generated
        
        # Run cycle
        result = run_cycle()
        
        # Verify result
        assert result["status"] == "no_trade"
        assert result["symbol"] == "BTC/USDT"
        assert result["reason"] == "no_breakout"
        assert result["candles"] == 250
        
        # Verify calls
        mock_config.assert_called_once()
        mock_candles.assert_called_once_with("BTC/USDT", limit=250)
        mock_generate.assert_called_once()
    
    @patch('integration.scripts.run_cycle.load_config')
    @patch('integration.scripts.run_cycle.get_candles')
    @patch('integration.scripts.run_cycle.generate_signal')
    @patch('integration.scripts.run_cycle.apply_risk')
    def test_run_cycle_risk_filtered(self, mock_risk, mock_generate, mock_candles, mock_config):
        """Test run cycle when signal is rejected by risk gate."""
        # Setup mocks
        mock_config.return_value = self.create_mock_config()
        mock_candles.return_value = self.create_mock_candles()
        test_signal = self.create_test_signal()
        mock_generate.return_value = test_signal
        mock_risk.return_value = None  # Risk gate rejects signal
        
        # Run cycle
        result = run_cycle()
        
        # Verify result
        assert result["status"] == "filtered"
        assert result["symbol"] == "BTC/USDT"
        assert result["reason"] == "risk_gate_reject"
        assert result["decision_id"] == "cycle_test_123"
        
        # Verify calls
        mock_config.assert_called_once()
        mock_candles.assert_called_once_with("BTC/USDT", limit=250)
        mock_generate.assert_called_once()
        mock_risk.assert_called_once()
    
    @patch('integration.scripts.run_cycle.load_config')
    @patch('integration.scripts.run_cycle.get_candles')
    @patch('integration.scripts.run_cycle.generate_signal')
    @patch('integration.scripts.run_cycle.apply_risk')
    @patch('integration.scripts.run_cycle.publish_signal')
    @patch('integration.scripts.run_cycle.append_decision')
    def test_run_cycle_published(self, mock_log, mock_publish, mock_risk, 
                                mock_generate, mock_candles, mock_config):
        """Test run cycle when signal is successfully published."""
        # Setup mocks
        mock_config.return_value = self.create_mock_config()
        mock_candles.return_value = self.create_mock_candles()
        test_signal = self.create_test_signal()
        mock_generate.return_value = test_signal
        mock_risk.return_value = test_signal  # Risk gate accepts signal
        
        # Track calls
        publish_calls = []
        log_calls = []
        
        def track_publish(signal):
            publish_calls.append(signal)
            
        def track_log(signal, entry_price):
            log_calls.append((signal, entry_price))
            
        mock_publish.side_effect = track_publish
        mock_log.side_effect = track_log
        
        # Run cycle
        result = run_cycle()
        
        # Verify result
        assert result["status"] == "published"
        assert result["symbol"] == "BTC/USDT"
        assert result["decision_id"] == "cycle_test_123"
        assert "entry_price" in result
        assert result["stop"] == 48000.0
        assert result["tp1"] == 52000.0
        assert result["tp2"] == 54000.0
        
        # Verify all functions called exactly once
        mock_config.assert_called_once()
        mock_candles.assert_called_once_with("BTC/USDT", limit=250)
        mock_generate.assert_called_once()
        mock_risk.assert_called_once()
        mock_publish.assert_called_once()
        mock_log.assert_called_once()
        
        # Verify publish and log were called with correct data
        assert len(publish_calls) == 1
        assert len(log_calls) == 1
        assert publish_calls[0] == test_signal
        assert log_calls[0][0] == test_signal
    
    @patch('integration.scripts.run_cycle.load_config')
    @patch('integration.scripts.run_cycle.get_candles')
    @patch('integration.scripts.run_cycle.generate_signal')
    @patch('integration.scripts.run_cycle.apply_risk')
    @patch('integration.scripts.run_cycle.publish_signal')
    @patch('integration.scripts.run_cycle.append_decision')
    def test_run_cycle_preview(self, mock_log, mock_publish, mock_risk, 
                              mock_generate, mock_candles, mock_config):
        """Test run cycle in preview mode (no publish/log calls)."""
        # Setup mocks
        mock_config.return_value = self.create_mock_config()
        mock_candles.return_value = self.create_mock_candles()
        test_signal = self.create_test_signal()
        mock_generate.return_value = test_signal
        mock_risk.return_value = test_signal  # Risk gate accepts signal
        
        # Run cycle in preview mode
        result = run_cycle(preview=True)
        
        # Verify result
        assert result["status"] == "preview"
        assert result["symbol"] == "BTC/USDT"
        assert result["decision_id"] == "cycle_test_123"
        assert "entry_price" in result
        assert result["stop"] == 48000.0
        assert result["tp1"] == 52000.0
        assert result["tp2"] == 54000.0
        
        # Verify core pipeline functions called
        mock_config.assert_called_once()
        mock_candles.assert_called_once_with("BTC/USDT", limit=250)
        mock_generate.assert_called_once()
        mock_risk.assert_called_once()
        
        # Verify publish and log NOT called in preview mode
        mock_publish.assert_not_called()
        mock_log.assert_not_called()
    
    @patch('integration.scripts.run_cycle.load_config')
    @patch('integration.scripts.run_cycle.get_candles')
    @patch('integration.scripts.run_cycle.generate_signal')
    @patch('integration.scripts.run_cycle.apply_risk')
    @patch('integration.scripts.run_cycle.publish_signal')
    @patch('integration.scripts.run_cycle.append_decision')
    def test_run_cycle_symbol_override(self, mock_log, mock_publish, mock_risk, 
                                      mock_generate, mock_candles, mock_config):
        """Test run cycle with symbol override."""
        # Setup mocks
        config = self.create_mock_config()
        config.symbol = "BTC/USDT"  # Default symbol
        mock_config.return_value = config
        mock_candles.return_value = self.create_mock_candles()
        test_signal = self.create_test_signal()
        test_signal.symbol = "ETH/USDT"  # Signal will have the overridden symbol
        mock_generate.return_value = test_signal
        mock_risk.return_value = test_signal
        
        # Run cycle with symbol override
        result = run_cycle(symbol_override="ETH/USDT")
        
        # Verify symbol override is used
        assert result["symbol"] == "ETH/USDT"
        
        # Verify get_candles called with overridden symbol
        mock_candles.assert_called_once_with("ETH/USDT", limit=250)
    
    @patch('integration.scripts.run_cycle.load_config')
    @patch('integration.scripts.run_cycle.get_candles')
    @patch('integration.scripts.run_cycle.generate_signal')
    @patch('integration.scripts.run_cycle.apply_risk')
    @patch('integration.scripts.run_cycle.publish_signal')
    @patch('integration.scripts.run_cycle.append_decision')
    def test_run_cycle_risk_config_mapping(self, mock_log, mock_publish, mock_risk, mock_generate, mock_candles, mock_config):
        """Test that risk configuration is properly mapped from config to apply_risk."""
        # Setup mocks with specific config values
        config = self.create_mock_config()
        config.risk.min_atr_multiple = 0.3
        config.risk.max_atr_multiple = 3.0
        config.risk.min_rr = 2.0
        config.max_capital_pct = 0.04
        mock_config.return_value = config
        
        mock_candles.return_value = self.create_mock_candles()
        test_signal = self.create_test_signal()
        mock_generate.return_value = test_signal
        mock_risk.return_value = test_signal
        
        # Run cycle
        result = run_cycle()
        
        # Verify apply_risk called with correct config mapping
        mock_risk.assert_called_once()
        call_args = mock_risk.call_args
        risk_config = call_args[0][2]  # Third argument is the config dict
        
        assert risk_config["risk"]["min_atr_multiple"] == 0.3
        assert risk_config["risk"]["max_atr_multiple"] == 3.0
        assert risk_config["risk"]["min_rr"] == 2.0
        assert risk_config["max_capital_pct"] == 0.04 