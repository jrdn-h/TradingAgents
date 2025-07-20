"""Unit tests for log integrity validation."""

import pytest
import tempfile
import csv
from pathlib import Path
from unittest.mock import patch

# We'll import the validation function directly
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from validate_log_integrity import validate_integrity


class TestLogIntegrity:
    """Test cases for log integrity validation."""
    
    def test_log_integrity_with_matching_data(self, monkeypatch):
        """Test integrity validation with properly matched decision-result pairs."""
        
        # Create temporary CSV data
        decisions_data = [
            ["decision_id", "timestamp", "symbol", "side", "entry_price", "stop", "tp1", "tp2", "confidence"],
            ["dec-001", "2025-01-01T10:00:00Z", "BTC/USDT", "long", "50000", "49000", "51000", "52000", "0.7"],
            ["dec-002", "2025-01-01T11:00:00Z", "ETH/USDT", "short", "3000", "3100", "2900", "2800", "0.6"],
        ]
        
        results_data = [
            ["decision_id", "exit_price", "pnl_r_multiple", "exit_reason", "timestamp"],
            ["dec-001", "51000", "1.0", "tp1_hit", "2025-01-01T12:00:00Z"],
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create temporary CSV files
            decisions_path = Path(temp_dir) / "decisions.csv"
            results_path = Path(temp_dir) / "results.csv"
            
            with open(decisions_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(decisions_data)
                
            with open(results_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(results_data)
            
            # Mock the load functions to use our temp files
            def mock_load_decisions(path=None):
                with open(decisions_path, 'r') as f:
                    reader = csv.DictReader(f)
                    return list(reader)
                    
            def mock_load_trade_results(path=None):
                with open(results_path, 'r') as f:
                    reader = csv.DictReader(f)
                    return list(reader)
            
            # Patch the functions and run validation
            with patch('validate_log_integrity.load_decisions', mock_load_decisions), \
                 patch('validate_log_integrity.load_trade_results', mock_load_trade_results), \
                 patch('builtins.print'):  # Suppress output during test
                
                exit_code = validate_integrity()
                
                # Should return 0 (success) since no orphan results
                assert exit_code == 0
    
    def test_log_integrity_with_orphan_results(self, monkeypatch):
        """Test integrity validation with orphan results (should fail)."""
        
        decisions_data = [
            ["decision_id", "timestamp", "symbol", "side", "entry_price", "stop", "tp1", "tp2", "confidence"],
            ["dec-001", "2025-01-01T10:00:00Z", "BTC/USDT", "long", "50000", "49000", "51000", "52000", "0.7"],
        ]
        
        results_data = [
            ["decision_id", "exit_price", "pnl_r_multiple", "exit_reason", "timestamp"],
            ["dec-001", "51000", "1.0", "tp1_hit", "2025-01-01T12:00:00Z"],
            ["dec-999", "52000", "2.0", "tp1_hit", "2025-01-01T13:00:00Z"],  # Orphan!
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path = Path(temp_dir) / "decisions.csv"
            results_path = Path(temp_dir) / "results.csv"
            
            with open(decisions_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(decisions_data)
                
            with open(results_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(results_data)
            
            def mock_load_decisions(path=None):
                with open(decisions_path, 'r') as f:
                    reader = csv.DictReader(f)
                    return list(reader)
                    
            def mock_load_trade_results(path=None):
                with open(results_path, 'r') as f:
                    reader = csv.DictReader(f)
                    return list(reader)
            
            with patch('validate_log_integrity.load_decisions', mock_load_decisions), \
                 patch('validate_log_integrity.load_trade_results', mock_load_trade_results), \
                 patch('builtins.print'):
                
                exit_code = validate_integrity()
                
                # Should return 1 (failure) due to orphan result
                assert exit_code == 1
    
    def test_log_integrity_with_unmatched_decisions(self, monkeypatch):
        """Test integrity validation with unmatched decisions (should pass since not orphan results)."""
        
        decisions_data = [
            ["decision_id", "timestamp", "symbol", "side", "entry_price", "stop", "tp1", "tp2", "confidence"],
            ["dec-001", "2025-01-01T10:00:00Z", "BTC/USDT", "long", "50000", "49000", "51000", "52000", "0.7"],
            ["dec-002", "2025-01-01T11:00:00Z", "ETH/USDT", "short", "3000", "3100", "2900", "2800", "0.6"],
        ]
        
        results_data = [
            ["decision_id", "exit_price", "pnl_r_multiple", "exit_reason", "timestamp"],
            ["dec-001", "51000", "1.0", "tp1_hit", "2025-01-01T12:00:00Z"],
            # dec-002 has no result (unmatched decision) - this is OK
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path = Path(temp_dir) / "decisions.csv"
            results_path = Path(temp_dir) / "results.csv"
            
            with open(decisions_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(decisions_data)
                
            with open(results_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(results_data)
            
            def mock_load_decisions(path=None):
                with open(decisions_path, 'r') as f:
                    reader = csv.DictReader(f)
                    return list(reader)
                    
            def mock_load_trade_results(path=None):
                with open(results_path, 'r') as f:
                    reader = csv.DictReader(f)
                    return list(reader)
            
            with patch('validate_log_integrity.load_decisions', mock_load_decisions), \
                 patch('validate_log_integrity.load_trade_results', mock_load_trade_results), \
                 patch('builtins.print'):
                
                exit_code = validate_integrity()
                
                # Should return 0 since no orphan results (unmatched decisions are acceptable)
                assert exit_code == 0
    
    def test_empty_logs(self, monkeypatch):
        """Test integrity validation with empty logs."""
        
        def mock_load_decisions(path=None):
            return []
                    
        def mock_load_trade_results(path=None):
            return []
        
        with patch('validate_log_integrity.load_decisions', mock_load_decisions), \
             patch('validate_log_integrity.load_trade_results', mock_load_trade_results), \
             patch('builtins.print'):
            
            exit_code = validate_integrity()
            
            # Should return 0 since no orphan results in empty logs
            assert exit_code == 0 