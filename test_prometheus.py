#!/usr/bin/env python3
"""
Test script to verify Prometheus metrics integration.
"""

import asyncio
import requests
from tradingagents.backtest.metrics import (
    tweet_rate_gauge, 
    sentiment_index_gauge, 
    sharpe_gauge,
    calculate_metrics
)
import pandas as pd
import numpy as np

def test_prometheus_metrics():
    """Test that Prometheus metrics are working."""
    print("🧪 Testing Prometheus metrics integration...")
    
    # Test 1: Update some metrics
    print("📊 Updating metrics...")
    tweet_rate_gauge.inc()  # Increment tweet counter
    sentiment_index_gauge.set(0.5)  # Set sentiment to 0.5
    sharpe_gauge.set(1.23)  # Set Sharpe ratio
    
    # Test 2: Calculate metrics with mock data
    print("📈 Calculating backtest metrics...")
    equity_series = pd.Series([10000, 10100, 10200, 10150, 10300])
    returns_series = equity_series.pct_change().fillna(0)
    
    metrics = calculate_metrics(
        equity_curve=equity_series,
        returns=returns_series,
        trades_pnl=pd.Series([100, -50, 200]),
        sentiment_series=pd.Series([0.1, 0.2, 0.3, 0.4, 0.5]),
        price_series=pd.Series([42000, 42100, 42200, 42150, 42300])
    )
    
    print(f"✅ Metrics calculated: {metrics}")
    
    # Test 3: Check if metrics are exposed via HTTP
    print("🌐 Checking HTTP metrics endpoint...")
    try:
        response = requests.get("http://localhost:8001/metrics", timeout=5)
        if response.status_code == 200:
            content = response.text
            print("✅ Metrics endpoint is accessible")
            
            # Check for our custom metrics
            if "tweet_ingested_total" in content:
                print("✅ tweet_ingested_total metric found")
            else:
                print("⚠️ tweet_ingested_total metric not found")
                
            if "sentiment_index_current" in content:
                print("✅ sentiment_index_current metric found")
            else:
                print("⚠️ sentiment_index_current metric not found")
                
            if "replay_sharpe_last" in content:
                print("✅ replay_sharpe_last metric found")
            else:
                print("⚠️ replay_sharpe_last metric not found")
                
        else:
            print(f"❌ Metrics endpoint returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Could not access metrics endpoint: {e}")
    
    print("🎉 Prometheus metrics test completed!")

if __name__ == "__main__":
    test_prometheus_metrics() 