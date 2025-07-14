# TradingAgents 🤖📈
[![CI](https://github.com/<org>/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<org>/<repo>/actions/workflows/ci.yml)

An LLM‑driven, multi‑agent prototype that ingests crypto‑market data, reasons about opportunities, and spits out risk‑checked trades—like a baby hedge fund on your laptop.

## Quick‑start

```bash
git clone https://github.com/<org>/<repo>.git
cd <repo>
poetry install  # Python 3.11+
poetry run python -m tradingagents run-demo --symbol BTCUSD
```

Example output

```json
{"action":"long","size_pct":2}
{"approved":true,"new_size_pct":2}
{"breakout":true,"sma":43050.0,"ema":43123.7}
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

SentimentAnalyst – stub that scores tweets/news (hard‑coded 78).

TraderAgent – goes long if breakout && sentiment>60.

RiskManager – caps size at 2 % and vetoes oversize trades.

## Roadmap
Swap in live Hyperliquid WebSocket feed.

Replace hard‑coded sentiment with an embedding classifier.

Add paper‑trading account and PnL dashboard.

© 2025 Your Name. MIT License.

# (fill in <org>/<repo> once merged)
