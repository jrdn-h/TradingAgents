# TradingAgents Optional Dependencies

This document outlines which optional packages are required for specific features.

## Installation

### Base Installation (Core Features Only)
```bash
poetry install
```

### Install with Specific Features
```bash
# Financial data and analysis
poetry install -E finance

# Memory/vector storage features  
poetry install -E memory

# Anthropic LLM support
poetry install -E anthropic

# Google LLM support
poetry install -E google

# Everything
poetry install -E all
```

## Dependency Matrix

| Feature | Required Package(s) | Poetry Extra | Commands/Functions Affected |
|---------|-------------------|--------------|---------------------------|
| **Yahoo Finance Data** | `yfinance` | `finance` | • `get_stock_data()`<br>• Historical price fetching<br>• Real-time quotes |
| **Technical Indicators** | `stockstats` | `finance` | • `calculate_indicators()`<br>• RSI, MACD, Bollinger Bands<br>• Technical analysis in backtests |
| **Memory Agents** | `chromadb` | `memory` | • `FinancialSituationMemory`<br>• Agent context persistence<br>• Semantic search over past decisions |
| **Anthropic LLMs** | `langchain-anthropic` | `anthropic` | • Claude model support<br>• Set `llm_provider: "anthropic"` in config |
| **Google LLMs** | `langchain-google-genai` | `google` | • Gemini model support<br>• Set `llm_provider: "google"` in config |

## Feature Availability by Installation Type

### Minimal Installation (no extras)
✅ Core trading logic  
✅ OpenAI LLM support  
✅ Twitter sentiment analysis (Twikit)  
✅ Redis/PostgreSQL integration  
✅ FastAPI endpoints  
✅ Prometheus metrics  
❌ Yahoo Finance data  
❌ Technical indicators  
❌ Memory persistence  
❌ Alternative LLMs (Anthropic/Google)  

### With `finance` Extra
✅ All minimal features  
✅ Historical price data from Yahoo Finance  
✅ Technical indicators (RSI, MACD, etc.)  
✅ Full backtesting capabilities  
❌ Memory persistence  
❌ Alternative LLMs  

### With `all` Extra
✅ Every feature available  
✅ All LLM providers  
✅ Full backtesting with technical analysis  
✅ Agent memory and context persistence  

## Docker Considerations

The current Dockerfile installs only base dependencies. To include extras in Docker:

```dockerfile
# Install with specific extras
RUN poetry install --no-interaction --no-ansi --no-root -E finance -E memory

# Or install everything
RUN poetry install --no-interaction --no-ansi --no-root -E all
```

## Error Messages

When a feature requiring an optional dependency is used without the package installed, you'll see clear error messages:

- **yfinance**: `"yfinance is required to fetch stock data but is not installed. Install with: pip install yfinance"`
- **stockstats**: `"stockstats is required for technical indicators but is not installed. Install with: pip install stockstats"`
- **chromadb**: `"chromadb is required for FinancialSituationMemory but is not installed. Install with: pip install chromadb"`
- **langchain-anthropic**: `"langchain_anthropic is required for Anthropic LLMs. Install with: pip install langchain-anthropic"`
- **langchain-google-genai**: `"langchain_google_genai is required for Google LLMs. Install with: pip install langchain-google-genai"` 