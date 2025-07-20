Operating Principles:

Index first, build second. No code changes until codebase inventory logged.

Single symbol, single timeframe, single technical pattern.

Every step: update infrastructure_update.md → run tests (all must pass) → commit → push.

Environment: Always conda activate TradingAgents before any command. Use ; (not &&) on Windows.

If terminal stalls: Ctrl+C, then exit; reopen; retry once. Log any stall.

Freeze schema v1.0 until MVP trades successfully in dry-run.

No new features without passing gates (G1–G4).

1. Project Overview & Goals
Deliver a minimal, reproducible integration between TradingAgents (reasoning layer) and Freqtrade (execution layer) for one symbol (default: BTC/USDT) on one timeframe (default: 5m).

Index & Understand First: Perform a structured inventory of existing tradingagents/ (agents, graph, dataflows) and record in infrastructure_update.md before implementing new modules.

Strict MVP scope: ONE technical breakout signal generator → ONE risk gate → Redis publication → Freqtrade bridge strategy → logging.

Guarantee: every commit corresponds to a logically complete, test‑passing step recorded in infrastructure_update.md.

Version pin Freqtrade via submodule to ensure reproducible environments.

2. Git Integration & Repository Layout 
Status: Freqtrade submodule already added & committed (Add freqtrade as submodule pinned to 2024.2).
Target structure (new directories to scaffold):

repo-root/
  tradingagents/              # existing framework
  vendor/
    freqtrade/                # git submodule (pinned)
  integration/
    adapter/
    strategy/
    schema/
    scripts/
    tests/
    config/
  decision_logs/
  envs/
  infrastructure_update.md
  integration/VERSIONS.toml
2.1 Immediate Actions (Scaffold)
#	Action	PowerShell Command (after conda activate TradingAgents)	Acceptance
1	Verify submodule	git submodule status	Shows pinned commit
2	Create dirs	mkdir integration; mkdir integration\{adapter,strategy,schema,scripts,tests,config}	Dirs exist
3	Env dir	mkdir envs	Exists
4	Logs dir	mkdir decision_logs	Exists & gitignored
5	Infra log	ni infrastructure_update.md -Type File	File created
6	Versions file	ni integration\VERSIONS.toml -Type File	File created
7	.gitignore add	Append entries (see below)	Updated
8	Commit	git add . ; git commit -m "chore: scaffold integration dirs & infra log" ; git push	Remote updated

2.2 .gitignore Additions
bash
Copy
Edit
decision_logs/
trade_results/
*.log
.env
2.3 integration/VERSIONS.toml Baseline
toml
Copy
Edit
[freqtrade]
repo = "https://github.com/freqtrade/freqtrade"
commit = "<SUBMODULE_COMMIT_SHA>"  # output of: git -C vendor/freqtrade rev-parse HEAD
tag = "2024.2"

[bridge]
schema_version = "1.0"
implementation_phase = 0
2.4 infrastructure_update.md Logging Format (MANDATORY)
For every step (including indexing):

ruby
Copy
Edit
## Step <N>: <Short Title>
**Timestamp (UTC):** YYYY-MM-DD HH:MM
**Description:** What was done (1–3 sentences)
**Files Added/Modified:** file1.py, file2.py
**Tests Run:** pytest -k <pattern> (list all)
**Test Result:** PASS / FAIL (brief notes)
**Decision IDs / Commits:** <commit hash(es)>
**Next Action:** <exact next step>
Commit after each addition:

nginx
Copy
Edit
git add infrastructure_update.md ;
git commit -m "docs(infra): step <N> <short title>" ;
git push
2.5 Codebase Indexing Procedure (Step 1)
Catalog agents (tradingagents/agents/*): role, inputs, outputs.

Graph pipeline (tradingagents/graph/): entry points, propagation order.

Data sources (tradingagents/dataflows/): which external APIs invoked.

Identify DEFERRED components for MVP (fundamentals, news, social, debate).

Run baseline tests (if present): pytest -q. Record results.

Update infrastructure_update.md (Step 1).

Increment implementation_phase in integration/VERSIONS.toml → 1; commit & push.

2.6 Pre-Commit Guard (Optional)
.git/hooks/pre-commit (bash):

bash
Copy
Edit
#!/usr/bin/env bash
CHANGED=$(git diff --cached --name-only | grep -E '\.py$')
if [ ! -z "$CHANGED" ] && ! git diff --cached --name-only | grep -q 'infrastructure_update.md'; then
  echo "[HOOK] Update infrastructure_update.md for this change." >&2
  exit 1
fi
2.7 Test Gate Policy
Rule: No forward progress if any test fails.

Add tests incrementally; always run full set: pytest -q.

2.8 Terminal Usage (Windows)
Activate env: conda activate TradingAgents

Chain commands: cmd1 ; cmd2

If hang > 60s: Ctrl+C; if still unresponsive: exit; reopen; document stall.

2.9 Promotion Criteria to Implementation Phase 2
All below satisfied & logged:

Indexing complete.

Scaffolding & version file committed.

Baseline tests pass.

implementation_phase=1 recorded.

Then proceed to Section 3.

3. Configuration & .env (Phase 2)
3.1 Environment Variables (add to .env.example)
ini
Copy
Edit
REDIS_URL=redis://localhost:6379/0
DEFAULT_SYMBOL=BTC/USDT
TIMEFRAME=5m
MAX_CAPITAL_PCT=0.05
MODEL_NAME=gpt-4o-mini
3.2 Minimal Config Loader (integration/config/config.py)
Function: load_config() -> dict

Required keys: "symbol", "timeframe", "max_capital_pct", "risk" (subdict).

Provide default risk:

python
Copy
Edit
RISK_DEFAULT = {
  "min_atr_multiple": 0.5,
  "max_atr_multiple": 5.0,
  "min_rr": 1.5
}
Acceptance: Unit test ensures missing env raises explicit error.

4. Data Layer (Phase 2)
File: integration/data.py

Functions:

get_candles(symbol: str, limit: int = 200) -> list[dict]

Returns sorted ascending dicts with keys: timestamp, open, high, low, close, volume.

compute_atr(candles: list[dict], period: int = 14) -> float

Tests:

test_data_candles_shape

test_atr_positive

5. Schema (Signal Contract) – v1.0
File: integration/schema/signal.py

Classes (Pydantic v2):

TakeProfit

RiskPlan

TradingSignal

Frozen fields:

python
Copy
Edit
version = "1.0"
symbol: str
side: Literal["long","short"]
confidence: float
entry: dict  # e.g., {"type": "market"}
risk: RiskPlan
rationale: constr(max_length=60)
Validation:

Exactly 2 take_profits entries.

Sum of size_pct equals 1.0 (tolerance 1e-6).

0 < confidence <= 1.

Test: test_signal_roundtrip.py.

6. Signal Generation
File: integration/signal_gen.py

Function: generate_signal(candles: list[dict]) -> Optional[TradingSignal]

Pattern (Breakout Long Only MVP):

Entry condition: last_close > max(high[-20:-1])

Stop: min(low[-10:])

TP1: entry + (entry - stop) (R = 1)

TP2: entry + 2*(entry - stop) (R = 2)

Confidence: constant 0.6 (placeholder)

If no breakout → return None

Tests:

test_generate_signal_breakout

test_generate_signal_no_trade

7. Risk Gate
File: integration/risk.py

Function: apply_risk(signal: TradingSignal, candles: list[dict], cfg: dict) -> Optional[TradingSignal]

Checks:

ATR distance: (entry - stop) between [min_atr_multiple*ATR, max_atr_multiple*ATR]

RR ≥ min_rr (based on TP1)

Cap risk.max_capital_pct to cfg["max_capital_pct"]

Return None if any fail.

Test: test_risk_filter_bounds.

8. Redis Publish/Consume
File: integration/publish.py

Functions:

publish_signal(signal: TradingSignal) -> None

fetch_latest_signal(symbol: str, max_age_sec: int = 600) -> Optional[TradingSignal]

Redis List Name: signals
Timestamp freshness check.

Test: test_publish_consume_signal.

9. Freqtrade Bridge Strategy
File: integration/strategy/AgentBridgeStrategy.py

Core Attributes:

python
Copy
Edit
timeframe = "5m"
startup_candle_count = 50
can_short = False  # initially
Key Methods:

_fetch_signal(pair) → use fetch_latest_signal()

populate_entry_trend(df, metadata) → set last row enter_long = 1 if valid signal

Store initial_stop, tp1, tp2 in custom_info

custom_stoploss → compute ratio from stored stop

(Optional MVP) custom_exit → exit fully at TP1

Test: test_strategy_sets_flag (mock Redis + DataFrame).

10. Logging
File: integration/logging_utils.py

Functions:

append_decision(signal: TradingSignal, path="decision_logs/decision_log.csv")

Ensure header if missing.

append_trade_result(decision_id: str, exit_price: float, pnl_r: float, path="decision_logs/trade_results.csv")

Test: test_logging_append.

11. Run Cycle Script
File: integration/scripts/run_cycle.py

Flow:

Load config

Fetch candles

Generate signal

If signal → compute ATR → risk gate → publish → log

Print summary to stdout

Acceptance: Running prints either NO_TRADE or JSON of signal.

12. Tests Summary
Minimal Test List:

Copy
Edit
test_signal_roundtrip.py
test_data_candles_shape.py
test_atr_positive.py
test_generate_signal_breakout.py
test_generate_signal_no_trade.py
test_risk_filter_bounds.py
test_publish_consume_signal.py
test_strategy_sets_flag.py
test_logging_append.py
All placed in integration/tests/.

13. CI (GitHub Actions)
Workflow: .github/workflows/mvp-integration.yml

Checkout with submodules

Install core deps (envs/core.txt)

Start Redis service (GitHub Action service container or redis-server &)

Run tests

(Later) Add Freqtrade strategy import smoke test

14. Execution Environments
Core env (envs/core.txt):

shell
Copy
Edit
pydantic>=2
redis
fastapi
uvicorn
ccxt
python-dotenv
pytest
Freqtrade env (separate): use vendor/freqtrade/requirements.txt, plus:

nginx
Copy
Edit
pandas
15. Acceptance Gates
Gate	Condition
G1 – Core Valid	All unit tests pass locally
G2 – Dry-Run Trade	At least 1 recorded trade in Freqtrade dry-run using strategy
G3 – Log Integrity	decision_log.csv & trade_results.csv entries share matching decision_id
G4 – Latency	Fetch→publish cycle < 3s average (log latency for 5 cycles)

Progress beyond MVP only after G4.

16. Version Update Process
When updating Freqtrade:

git -C vendor/freqtrade fetch --all

Checkout new tag: git -C vendor/freqtrade checkout <tag>

Update integration/VERSIONS.toml commit & tag.

Increment implementation_phase if entering new feature phase.

Run full tests; commit & push.

17. Deferred Feature Backlog (Do Not Implement Yet)
Sentiment / news / fundamentals agents

Multi-timeframe logic

Short trading

Partial scaling out beyond single TP

Trailing stops

Funding rate / OI ingestion

Portfolio correlation / exposure nets

Debate / multi-agent consensus

Confidence calibration loop

Advanced sizing (ATR-adjusted stake)

Record these under a “Deferred” section in infrastructure_update.md Step 1.

18. Reference Glossary (Use EXACT Names)
Environment / Config Keys

REDIS_URL

DEFAULT_SYMBOL

TIMEFRAME

MAX_CAPITAL_PCT

MODEL_NAME

RISK_DEFAULT

min_atr_multiple, max_atr_multiple, min_rr

Files

integration/config/config.py

integration/data.py

integration/schema/signal.py

integration/signal_gen.py

integration/risk.py

integration/publish.py

integration/strategy/AgentBridgeStrategy.py

integration/logging_utils.py

integration/scripts/run_cycle.py

integration/VERSIONS.toml

infrastructure_update.md

Classes

TakeProfit

RiskPlan

TradingSignal

AgentBridgeStrategy

Functions (Public)

load_config

get_candles

compute_atr

generate_signal

apply_risk

publish_signal

fetch_latest_signal

append_decision

append_trade_result

Redis List

signals

Pydantic Field Names

version

decision_id

timestamp

symbol

side

confidence

entry

risk

initial_stop

take_profits

size_pct

max_capital_pct

rationale

Strategy Stored Keys (in custom_info)

initial_stop

tp1

tp2

decision_id

Log CSV Columns

Decision log: decision_id,timestamp,symbol,side,entry_price,stop,tp1,tp2,confidence

Trade results: decision_id,exit_price,pnl_r_multiple

Test Filenames

EXACT as Section 12 list.

19. Step Numbering Suggestion for infrastructure_update.md
Step	Description
0	(Optional) Initial repository sanity check
1	Codebase indexing (agents, graph, dataflows)
2	Directory scaffolding + versions file
3	Config loader & env setup
4	Data layer (candles + ATR)
5	Schema implementation
6	Signal generator
7	Risk gate
8	Publish/consume (Redis)
9	Strategy bridge
10	Logging utilities
11	Run cycle script
12	Full test suite green (G1)
13	Dry-run live test (G2)
14	Log integrity verification (G3)
15	Latency measurement (G4)

Add new steps if needed after 15 for post-MVP enhancements.

20. Post-MVP Roadmap (Record Later)
Add TP2 partial exit logic

Enable shorts

Introduce a Sentiment micro-agent

Multi-timeframe filter (HTF trend alignment)

Funding rate ingestion
(Keep this in backlog; do not start before Gates met.)

