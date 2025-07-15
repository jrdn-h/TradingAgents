# TradingAgents 🤖📈
[![CI](https://github.com/<org>/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<org>/<repo>/actions/workflows/ci.yml)

An LLM‑driven, multi‑agent prototype that ingests crypto‑market data, reasons about opportunities, and spits out risk‑checked trades—like a baby hedge fund on your laptop.

## Quick‑start

```bash
git clone https://github.com/<org>/<repo>.git
cd <repo>

# Basic installation (core features only)
poetry install  # Python 3.11+

# Install with financial data support (Yahoo Finance + technical indicators)
poetry install -E finance

# Install with all optional features
poetry install -E all

# Run demo
poetry run python -m tradingagents run-demo --symbol BTCUSD
```

See [DEPENDENCIES.md](DEPENDENCIES.md) for details on optional features.

### Dashboard

Start the live monitoring dashboard:

```bash
poetry run python -m tradingagents dashboard
```

Then open http://localhost:8000 in your browser to see:
- Real-time price updates
- Technical indicators (SMA/EMA/breakout)
- Sentiment analysis
- Trade decisions and risk approvals
- Live equity curve chart
- Auto-refreshing every 2 seconds

### Live mode

Run with `--live` to connect to a real WebSocket feed.

```bash
poetry run python -m tradingagents run-demo --symbol BTCUSD --live
```

*Current status*: falls back to a high‑fidelity mock after 30 s while we finish Hyperliquid integration.

Example output

```json
{"action":"long","size_pct":2}
{"approved":true,"new_size_pct":2}
{"breakout":true,"sma":43050.0,"ema":43123.7}
```

### Historical Replay

Test your strategy against historical data with sentiment correlation analysis:

```bash
# Basic replay with mock data
poetry run python -m tradingagents replay --from 2024-01-01 --to 2024-01-02 --symbol BTCUSD

# Replay with historical tweets
poetry run python -m tradingagents replay \
  --from 2024-01-01 --to 2024-01-02 \
  --symbol BTCUSD --tweets sample_tweets.csv --plot
```

This generates:
- **Performance metrics**: Sharpe ratio, max drawdown, win rate
- **Sentiment correlation**: How well sentiment predicts price movements  
- **Trade analysis**: PnL distribution, entry/exit timing
- **Visualization**: Price vs sentiment overlay, equity curve, trade distribution

Example output:
```
📈 REPLAY RESULTS: BTCUSD
============================================================
Period: 2024-01-01 00:00:00 to 2024-01-02 00:00:00
Initial Equity: $10,000.00
Final Equity:   $10,245.67
Total Return:   2.46%
Sharpe Ratio:   1.23
Max Drawdown:   -1.2%
Total Trades:   8
Sentiment Correlation: 0.156
🎯 SIGNIFICANT sentiment-price correlation detected!
Win Rate:       75.0%
============================================================
```

## How it works
```mermaid
flowchart LR
    subgraph Sequential Pipeline
        START["__start__"] --> M[Market Node<br/>tick]
        M --> S[SentimentAnalyst]
        M --> T[TechnicalAnalyst<br/>SMA/EMA]
        S --> TR[TraderAgent]
        T --> TR
        TR --> R[RiskManager]
        R --> END["__end__"]
    end
```
Market Node – (currently mocked) streams prices into a 20‑tick deque.

TechnicalAnalyst – computes SMA/EMA crossover and sets breakout.

SentimentAnalyst – scores tweets/news using embeddings or keyword heuristics.

TraderAgent – goes long if breakout && sentiment>60.

RiskManager – caps size at 2 % and vetoes oversize trades.

### Sentiment scoring

`SentimentAnalyst` now supports two paths:

| Path | When used | How it works |
|------|-----------|--------------|
| **OpenAI embeddings** | `OPENAI_API_KEY` present in the environment | The tweet text is embedded via `openai.embeddings.create`, compared (cos θ) to bullish/bearish exemplar vectors, and mapped to a 0‑100 score. |
| **Heuristic fallback** | No API key or embedding request fails | Keyword + emoji lookup (`🚀`, `moon`, `rekt`, etc.) with weighted counts produces a quick score. |

> **Tip:** try  
> ```bash
> poetry run python - <<'PY'
> from tradingagents.agents.analysts.sentiment_analyst import SentimentAnalyst
> import asyncio, os
>
> async def main():
>     agent = SentimentAnalyst()
>     state = {"tweets": [{"text": "🚀 $BTC to the moon!"}]}
>     result = await agent.run(state)
>     print(result)
>
> asyncio.run(main())
> PY
> ```  
> and watch the score jump above 60.

## Roadmap
Swap in live Hyperliquid WebSocket feed.

Replace hard‑coded sentiment with an embedding classifier.

Add paper‑trading account and PnL dashboard.

© 2025 Your Name. MIT License.

# (fill in <org>/<repo> once merged)
