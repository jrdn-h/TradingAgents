"""Unit tests for logging utilities."""
import pytest
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import tempfile
import os

from integration.logging_utils import (
    append_decision, append_trade_result, 
    DECISION_HEADERS, TRADE_RESULTS_HEADERS
)
from integration.schema.signal import TradingSignal, RiskPlan, TakeProfit


class TestLoggingUtils:
    """Test cases for CSV logging utilities."""
    
    def create_test_signal(self, decision_id="test_log_123"):
        """Create a test TradingSignal for logging tests."""
        return TradingSignal(
            decision_id=decision_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol="BTC/USDT",
            side="long",
            confidence=0.75,
            entry={"type": "market"},
            risk=RiskPlan(
                initial_stop=48500.0,
                take_profits=[
                    TakeProfit(price=52000.0, size_pct=0.5),
                    TakeProfit(price=54000.0, size_pct=0.5)
                ],
                max_capital_pct=0.03
            ),
            rationale="Test logging signal"
        )
    
    def test_append_decision_creates_and_appends(self, tmp_path):
        """Test that append_decision creates file with header and appends data."""
        decision_log = tmp_path / "test_decision_log.csv"
        
        with patch('integration.logging_utils.DECISION_LOG', decision_log):
            signal = self.create_test_signal()
            entry_price = 50000.0
            
            # Append decision
            append_decision(signal, entry_price)
            
            # Verify file exists
            assert decision_log.exists()
            
            # Read and verify contents
            with decision_log.open('r') as f:
                reader = csv.reader(f)
                rows = list(reader)
                
            # Should have header + 1 data row = 2 total rows
            assert len(rows) == 2
            
            # Verify header
            assert rows[0] == DECISION_HEADERS
            assert len(rows[0]) == 9  # 9 columns as specified
            
            # Verify data row
            data_row = rows[1]
            assert data_row[0] == "test_log_123"  # decision_id
            assert data_row[2] == "BTC/USDT"      # symbol
            assert data_row[3] == "long"          # side
            assert data_row[4] == "50000.00000000"  # entry_price formatted
            assert data_row[5] == "48500.00000000"  # stop formatted
            assert data_row[6] == "52000.00000000"  # tp1 formatted
            assert data_row[7] == "54000.00000000"  # tp2 formatted
            assert data_row[8] == "0.7500"          # confidence formatted
    
    def test_append_trade_result_creates_and_appends(self, tmp_path):
        """Test that append_trade_result creates file with header and appends data."""
        results_log = tmp_path / "test_trade_results.csv"
        
        with patch('integration.logging_utils.TRADE_RESULTS_LOG', results_log):
            # Append trade result
            append_trade_result(
                decision_id="abc123",
                exit_price=60000.0,
                pnl_r_multiple=2.5,
                exit_reason="tp1_hit",
                timestamp="2025-07-20T00:00:00Z"
            )
            
            # Verify file exists
            assert results_log.exists()
            
            # Read and verify contents
            with results_log.open('r') as f:
                reader = csv.reader(f)
                rows = list(reader)
                
            # Should have header + 1 data row = 2 total rows
            assert len(rows) == 2
            
            # Verify header
            assert rows[0] == TRADE_RESULTS_HEADERS
            assert len(rows[0]) == 5  # 5 columns as specified
            
            # Verify data row
            data_row = rows[1]
            assert data_row[0] == "abc123"           # decision_id
            assert data_row[1] == "60000.00000000"   # exit_price formatted
            assert data_row[2] == "2.5000"           # pnl_r_multiple formatted
            assert data_row[3] == "tp1_hit"          # exit_reason
            assert data_row[4] == "2025-07-20T00:00:00Z"  # timestamp
    
    def test_append_decision_idempotent_header(self, tmp_path):
        """Test that multiple append_decision calls only create header once."""
        decision_log = tmp_path / "test_decision_log.csv"
        
        with patch('integration.logging_utils.DECISION_LOG', decision_log):
            signal1 = self.create_test_signal("decision_001")
            signal2 = self.create_test_signal("decision_002")
            
            # Append two decisions
            append_decision(signal1, 50000.0)
            append_decision(signal2, 51000.0)
            
            # Read file contents
            with decision_log.open('r') as f:
                reader = csv.reader(f)
                rows = list(reader)
                
            # Should have header + 2 data rows = 3 total rows
            assert len(rows) == 3
            
            # Verify only one header (first row)
            assert rows[0] == DECISION_HEADERS
            
            # Verify second and third rows are data (not headers)
            assert rows[1][0] == "decision_001"
            assert rows[2][0] == "decision_002"
            
            # Ensure header appears exactly once
            header_count = sum(1 for row in rows if row[0] == "decision_id")
            assert header_count == 1
    
    def test_append_trade_result_idempotent_header(self, tmp_path):
        """Test that multiple append_trade_result calls only create header once."""
        results_log = tmp_path / "test_trade_results.csv"
        
        with patch('integration.logging_utils.TRADE_RESULTS_LOG', results_log):
            # Append two trade results
            append_trade_result("abc123", 60000.0, 2.5, "tp1_hit", "2025-07-20T00:00:00Z")
            append_trade_result("def456", 45000.0, -1.2, "stop_loss", "2025-07-20T01:00:00Z")
            
            # Read file contents
            with results_log.open('r') as f:
                reader = csv.reader(f)
                rows = list(reader)
                
            # Should have header + 2 data rows = 3 total rows
            assert len(rows) == 3
            
            # Verify only one header (first row)
            assert rows[0] == TRADE_RESULTS_HEADERS
            
            # Verify second and third rows are data (not headers)
            assert rows[1][0] == "abc123"
            assert rows[2][0] == "def456"
            
            # Ensure header appears exactly once
            header_count = sum(1 for row in rows if row[0] == "decision_id")
            assert header_count == 1
    
    def test_append_decision_formats_numbers(self, tmp_path):
        """Test that numeric fields are properly formatted with decimals."""
        decision_log = tmp_path / "test_decision_log.csv"
        
        with patch('integration.logging_utils.DECISION_LOG', decision_log):
            signal = self.create_test_signal()
            entry_price = 49999.12345678
            
            append_decision(signal, entry_price)
            
            # Read file contents
            with decision_log.open('r') as f:
                reader = csv.reader(f)
                rows = list(reader)
                
            data_row = rows[1]  # Skip header
            
            # Check that numeric fields contain decimal points and proper formatting
            assert "." in data_row[4]  # entry_price
            assert "." in data_row[5]  # stop
            assert "." in data_row[6]  # tp1 
            assert "." in data_row[7]  # tp2
            assert "." in data_row[8]  # confidence
            
            # Verify specific formatting (8 decimals for prices, 4 for confidence)
            assert data_row[4] == "49999.12345678"  # entry_price (8 decimals)
            assert len(data_row[5].split('.')[1]) == 8  # stop (8 decimals)
            assert len(data_row[6].split('.')[1]) == 8  # tp1 (8 decimals)
            assert len(data_row[7].split('.')[1]) == 8  # tp2 (8 decimals)
            assert len(data_row[8].split('.')[1]) == 4  # confidence (4 decimals)
    
    def test_append_trade_result_formats_numbers(self, tmp_path):
        """Test that trade result numeric fields are properly formatted."""
        results_log = tmp_path / "test_trade_results.csv"
        
        with patch('integration.logging_utils.TRADE_RESULTS_LOG', results_log):
            append_trade_result(
                decision_id="test123",
                exit_price=59999.87654321,
                pnl_r_multiple=1.2345,
                exit_reason="tp1_hit",
                timestamp="2025-07-20T00:00:00Z"
            )
            
            # Read file contents
            with results_log.open('r') as f:
                reader = csv.reader(f)
                rows = list(reader)
                
            data_row = rows[1]  # Skip header
            
            # Check that numeric fields contain decimal points
            assert "." in data_row[1]  # exit_price
            assert "." in data_row[2]  # pnl_r_multiple
            
            # Verify specific formatting
            assert data_row[1] == "59999.87654321"  # exit_price (8 decimals)
            assert data_row[2] == "1.2345"          # pnl_r_multiple (4 decimals)
    
    def test_directory_creation(self, tmp_path):
        """Test that parent directories are created automatically."""
        # Create a deep path that doesn't exist
        nested_log = tmp_path / "deep" / "nested" / "path" / "decision_log.csv"
        
        with patch('integration.logging_utils.DECISION_LOG', nested_log):
            signal = self.create_test_signal()
            
            # This should create the nested directory structure
            append_decision(signal, 50000.0)
            
            # Verify directory and file were created
            assert nested_log.exists()
            assert nested_log.parent.exists()
    
    def test_empty_decision_logs_directory_handling(self, tmp_path):
        """Test behavior when decision_logs directory doesn't exist initially."""
        non_existent_dir = tmp_path / "non_existent" / "decision_log.csv"
        
        with patch('integration.logging_utils.DECISION_LOG', non_existent_dir):
            signal = self.create_test_signal()
            
            # Should create directory and file without errors
            append_decision(signal, 50000.0)
            
            assert non_existent_dir.exists()
            assert non_existent_dir.parent.exists() 