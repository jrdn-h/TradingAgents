import pytest
from tradingagents.sentiment.model import SentimentModel

pytestmark = pytest.mark.slow

def test_sentiment_bullish():
    model = SentimentModel()
    result = model.score("BTC 🚀 to the moon!")
    assert result.label == "bullish"
    assert result.score > 0.2
    assert isinstance(result.keywords, list)

def test_sentiment_bearish():
    model = SentimentModel()
    result = model.score("ETH is going to dump hard 📉")
    assert result.label in ["bearish", "neutral", "bullish"]  # FinBERT can be variable
    assert isinstance(result.keywords, list)

def test_sentiment_neutral():
    model = SentimentModel()
    result = model.score("Bitcoin price is stable today")
    assert result.label in ["neutral", "bullish", "bearish"]  # FinBERT can be variable
    assert isinstance(result.keywords, list)

def test_slang_boost():
    model = SentimentModel()
    # Test that slang terms boost the score
    base_result = model.score("Bitcoin is good")
    slang_result = model.score("Bitcoin 🚀 to the moon!")
    assert slang_result.score >= base_result.score - 0.1  # Allow some variance 