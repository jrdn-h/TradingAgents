"""Unit tests for latency measurement functionality."""

import time
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Import the measurement function directly
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from measure_latency import measure_once, run_latency_measurement


class TestLatencyMeasurement:
    """Test cases for latency measurement."""
    
    def test_measure_once_basic_structure(self):
        """Test that measure_once returns correct structure and timing."""
        
        def mock_load_config():
            from integration.config.config import Config, RiskSettings, RISK_DEFAULT
            return Config(
                symbol="BTC/USDT",
                timeframe="5m",
                max_capital_pct=0.05,
                model_name="test",
                risk=RiskSettings(**RISK_DEFAULT)
            )
        
        def mock_get_candles(symbol, limit):
            time.sleep(0.001)  # Simulate fetch time
            return [
                {"timestamp": 1700000000, "open": 50000, "high": 50100, "low": 49900, "close": 50050, "volume": 100}
                for _ in range(limit)
            ]
        
        def mock_generate_signal(symbol, limit):
            time.sleep(0.001)  # Simulate processing time
            return None  # Simulate no breakout
        
        def mock_apply_risk(signal, candles, config):
            time.sleep(0.001)  # Simulate risk calculation time
            return signal
        
        def mock_publish_signal(signal):
            time.sleep(0.001)  # Simulate publish time
            pass
        
        def mock_append_decision(signal, entry_price):
            time.sleep(0.001)  # Simulate logging time
            pass
        
        with patch('measure_latency.load_config', mock_load_config), \
             patch('measure_latency.get_candles', mock_get_candles), \
             patch('measure_latency.generate_signal', mock_generate_signal), \
             patch('measure_latency.apply_risk', mock_apply_risk), \
             patch('measure_latency.publish_signal', mock_publish_signal), \
             patch('measure_latency.append_decision', mock_append_decision):
            
            status, timing_data = measure_once("BTC/USDT", use_preview_fallback=True)
            
            # Verify status is valid
            assert status in ['no_trade', 'filtered', 'published', 'publish_failed']
            
            # Verify timing structure
            required_keys = [
                'config_loaded', 'candles_fetched', 'signal_generated', 
                'risk_applied', 'published_logged', 'total',
                'config_load_duration', 'candles_fetch_duration', 
                'signal_gen_duration', 'risk_apply_duration', 
                'publish_log_duration', 'total_duration'
            ]
            
            for key in required_keys:
                assert key in timing_data, f"Missing timing key: {key}"
                assert isinstance(timing_data[key], (int, float)), f"Invalid timing type for {key}"
                assert timing_data[key] >= 0, f"Negative timing for {key}"
            
            # Verify total duration is reasonable (should be > 0 but < 1s for mocked functions)
            assert 0 < timing_data['total_duration'] < 1.0
            
            # Verify stage durations sum approximately to total
            stage_sum = (
                timing_data['config_load_duration'] +
                timing_data['candles_fetch_duration'] +
                timing_data['signal_gen_duration'] +
                timing_data['risk_apply_duration'] +
                timing_data['publish_log_duration']
            )
            
            # Allow small tolerance for timing precision
            assert abs(stage_sum - timing_data['total_duration']) < 0.01
    
    def test_measure_once_with_published_signal(self):
        """Test measure_once when a signal is generated and published."""
        
        # Mock signal object
        mock_signal = MagicMock()
        mock_signal.decision_id = "test-123"
        mock_signal.risk.initial_stop = 49000
        mock_signal.risk.take_profits = [MagicMock(price=51000), MagicMock(price=52000)]
        
        def mock_load_config():
            from integration.config.config import Config, RiskSettings, RISK_DEFAULT
            return Config(
                symbol="BTC/USDT",
                timeframe="5m",
                max_capital_pct=0.05,
                model_name="test",
                risk=RiskSettings(**RISK_DEFAULT)
            )
        
        def mock_get_candles(symbol, limit):
            return [{"timestamp": 1700000000, "open": 50000, "high": 50100, "low": 49900, "close": 50050, "volume": 100}]
        
        def mock_generate_signal(symbol, limit):
            return mock_signal  # Return signal this time
        
        def mock_apply_risk(signal, candles, config):
            return signal  # Pass risk filter
        
        def mock_publish_signal(signal):
            pass
        
        def mock_append_decision(signal, entry_price):
            pass
        
        with patch('measure_latency.load_config', mock_load_config), \
             patch('measure_latency.get_candles', mock_get_candles), \
             patch('measure_latency.generate_signal', mock_generate_signal), \
             patch('measure_latency.apply_risk', mock_apply_risk), \
             patch('measure_latency.publish_signal', mock_publish_signal), \
             patch('measure_latency.append_decision', mock_append_decision):
            
            status, timing_data = measure_once("BTC/USDT", use_preview_fallback=True)
            
            # Should result in published status
            assert status == 'published'
            assert timing_data['total_duration'] > 0
    
    def test_run_latency_measurement_basic(self):
        """Test run_latency_measurement aggregation."""
        
        def mock_measure_once(symbol, use_preview_fallback):
            return 'no_trade', {
                'config_loaded': 0.001,
                'candles_fetched': 0.002,
                'signal_generated': 0.003,
                'risk_applied': 0.003,
                'published_logged': 0.003,
                'total': 0.010,
                'config_load_duration': 0.001,
                'candles_fetch_duration': 0.001,
                'signal_gen_duration': 0.001,
                'risk_apply_duration': 0.000,
                'publish_log_duration': 0.000,
                'total_duration': 0.010
            }
        
        with patch('measure_latency.measure_once', mock_measure_once), \
             patch('builtins.print'):  # Suppress output
            
            result = run_latency_measurement("BTC/USDT", cycles=3, use_preview_fallback=True)
            
            # Verify structure
            assert 'measurement_info' in result
            assert 'status_counts' in result
            assert 'timing_stats' in result
            assert 'gate_criteria' in result
            assert 'raw_results' in result
            
            # Verify measurement info
            assert result['measurement_info']['cycles_requested'] == 3
            assert result['measurement_info']['cycles_completed'] == 3
            assert result['measurement_info']['symbol'] == "BTC/USDT"
            
            # Verify status counts
            assert result['status_counts']['no_trade'] == 3
            
            # Verify timing stats structure
            assert 'total' in result['timing_stats']
            assert 'avg' in result['timing_stats']['total']
            assert 'p95' in result['timing_stats']['total']
            assert 'stages' in result['timing_stats']
            
            # Verify gate criteria
            assert 'avg_total_time_sec' in result['gate_criteria']
            assert 'p95_total_time_sec' in result['gate_criteria']
            assert 'gate_pass' in result['gate_criteria']
            
            # With 0.010s timing, should easily pass gate
            assert result['gate_criteria']['avg_total_time_sec'] == 0.010
            assert result['gate_criteria']['gate_pass'] is True
    
    def test_fallback_config_usage(self):
        """Test that preview fallback config works when env vars missing."""
        
        def mock_load_config():
            raise RuntimeError("Missing required environment variables: ['REDIS_URL']")
        
        def mock_get_candles(symbol, limit):
            return [{"timestamp": 1700000000, "open": 50000, "high": 50100, "low": 49900, "close": 50050, "volume": 100}]
        
        def mock_generate_signal(symbol, limit):
            return None
        
        with patch('measure_latency.load_config', mock_load_config), \
             patch('measure_latency.get_candles', mock_get_candles), \
             patch('measure_latency.generate_signal', mock_generate_signal):
            
            # Should work with fallback enabled
            status, timing_data = measure_once("BTC/USDT", use_preview_fallback=True)
            assert status == 'no_trade'
            assert timing_data['total_duration'] > 0
            
            # Should fail without fallback
            with pytest.raises(RuntimeError):
                measure_once("BTC/USDT", use_preview_fallback=False) 