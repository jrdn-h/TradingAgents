# TradingAgents Codebase Index Report
**Generated:** 2025-01-27 19:35 UTC  
**Purpose:** Comprehensive inventory of existing tradingagents/ framework for MVP planning

## Agents Inventory

### Analysts (tradingagents/agents/analysts/)
| Module | Class/Function | Role Category | Primary Inputs | Primary Outputs | Side Effects | MVP Relevance |
|--------|----------------|---------------|----------------|-----------------|--------------|---------------|
| market_analyst.py | create_market_analyst | analyst | state(ticker, date), toolkit | Technical analysis report with indicators | YFin API calls, stockstats computation | DEFERRED |
| news_analyst.py | create_news_analyst | analyst | state(ticker, date), toolkit | News sentiment analysis | News API calls | DEFERRED |
| fundamentals_analyst.py | create_fundamentals_analyst | analyst | state(ticker, date), toolkit | Fundamentals report | Financial data API calls | DEFERRED |
| social_media_analyst.py | create_social_media_analyst | analyst | state(ticker, date), toolkit | Social sentiment report | Reddit/social API calls | DEFERRED |

### Researchers (tradingagents/agents/researchers/)  
| Module | Class/Function | Role Category | Primary Inputs | Primary Outputs | Side Effects | MVP Relevance |
|--------|----------------|---------------|----------------|-----------------|--------------|---------------|
| bull_researcher.py | create_bull_researcher | researcher | state(reports), llm | Bullish research analysis | LLM API calls | DEFERRED |
| bear_researcher.py | create_bear_researcher | researcher | state(reports), llm | Bearish research analysis | LLM API calls | DEFERRED |

### Managers (tradingagents/agents/managers/)
| Module | Class/Function | Role Category | Primary Inputs | Primary Outputs | Side Effects | MVP Relevance |
|--------|----------------|---------------|----------------|-----------------|--------------|---------------|
| research_manager.py | create_research_manager | manager | state(debate_state), llm | Research coordination | LLM API calls, state mutation | DEFERRED |
| risk_manager.py | create_risk_manager | manager | state(risk_debate_state), llm, memory | Risk management decision | LLM API calls, memory access | DEFERRED |

### Trader (tradingagents/agents/trader/)
| Module | Class/Function | Role Category | Primary Inputs | Primary Outputs | Side Effects | MVP Relevance |
|--------|----------------|---------------|----------------|-----------------|--------------|---------------|
| trader.py | create_trader | trader | state(reports), llm, memory | Trading decision (BUY/SELL/HOLD) | LLM API calls, memory access | DEFERRED |

### Risk Management Debators (tradingagents/agents/risk_mgmt/)
| Module | Class/Function | Role Category | Primary Inputs | Primary Outputs | Side Effects | MVP Relevance |
|--------|----------------|---------------|----------------|-----------------|--------------|---------------|
| conservative_debator.py | create_safe_debator | risk_mgmt | state(risk_debate), llm | Conservative risk argument | LLM API calls | DEFERRED |
| neutral_debator.py | create_neutral_debator | risk_mgmt | state(risk_debate), llm | Neutral risk argument | LLM API calls | DEFERRED |
| aggressive_debator.py | create_aggressive_debator | risk_mgmt | state(risk_debate), llm | Aggressive risk argument | LLM API calls | DEFERRED |

### Utilities (tradingagents/agents/utils/)
| Module | Class/Function | Role Category | Primary Inputs | Primary Outputs | Side Effects | MVP Relevance |
|--------|----------------|---------------|----------------|-----------------|--------------|---------------|
| agent_utils.py | Various utility functions | util | Various | Helper functions | Logging, state management | DEFERRED |
| memory.py | FinancialSituationMemory | util | config, situations | Memory storage/retrieval | ChromaDB operations, OpenAI embedding calls | DEFERRED |
| agent_states.py | State classes | util | N/A | State definitions | N/A | DEFERRED |

## Graph/Orchestration Analysis (tradingagents/graph/)

### Main Entry Points
- **trading_graph.py**: TradingAgentsGraph class - main orchestrator
- **setup.py**: GraphSetup - graph initialization (206 lines)
- **propagation.py**: Propagator - message propagation (50 lines)

### Pipeline Flow  
1. TradingAgentsGraph initializes selected analysts
2. ConditionalLogic determines execution paths
3. Propagator handles message flow between agents
4. Reflector processes final decisions
5. SignalProcessor extracts BUY/SELL/HOLD decisions

### Dependencies Between Agents
- **Sequential**: Analysts → Researchers → Risk Debate → Risk Manager → Trader
- **Conditional**: Based on market conditions and debate outcomes
- **Reflection**: Post-decision analysis and memory updates

## Dataflows Analysis (tradingagents/dataflows/)

### Data Modules Inventory
| Module | Purpose | External API | Auth Requirements | Rate Limits | Output Structure | MVP Relevance |
|--------|---------|--------------|-------------------|-------------|------------------|---------------|
| finnhub_utils.py | Finnhub data access | Finnhub API | API key | Yes | JSON | DEFERRED |
| yfin_utils.py | Yahoo Finance data | Yahoo Finance | None | Yes | DataFrame/JSON | DEFERRED |
| googlenews_utils.py | Google News data | Google News | None | Yes | Text/JSON | DEFERRED |
| reddit_utils.py | Reddit sentiment | Reddit API | API key | Yes | JSON | DEFERRED |
| stockstats_utils.py | Technical indicators | StockStats library | None | No | DataFrame | DEFERRED |
| interface.py | Unified data interface | Multiple | Various | Various | Standardized | DEFERRED |

### Network Assumptions
- All modules assume internet connectivity
- Most require API keys/authentication
- Rate limiting implemented for external APIs
- Caching mechanisms present in interface.py

## Config & Defaults Analysis

### Current Configuration (tradingagents/default_config.py)
```python
DEFAULT_CONFIG = {
    "project_dir": "<project_path>",
    "results_dir": "./results", 
    "data_dir": "/Users/yluo/Documents/Code/ScAI/FR1-data",
    "data_cache_dir": "<project>/dataflows/data_cache",
    "llm_provider": "openai",
    "deep_think_llm": "o4-mini", 
    "quick_think_llm": "gpt-4o-mini",
    "backend_url": "https://api.openai.com/v1",
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    "online_tools": True
}
```

### Identified Issues for MVP
- **Equities-focused paths**: Hard-coded data directories
- **LLM dependencies**: Heavy reliance on OpenAI
- **Complex debate logic**: Multi-round discussion mechanisms

## Current Test Coverage
- **Status**: No tests found (pytest returned 0 tests)
- **Coverage**: 0% - no existing test infrastructure
- **Test Framework**: pytest available in dependencies

## MVP Component Mapping Table

| MVP Component | Source | Reuse? | Reason |
|---------------|--------|--------|---------|
| Candle Fetch | New (integration/data.py) | New | Keep decoupled & minimal |
| Technical Signal Generator | New (integration/signal_gen.py) | New | Existing analysts too complex |
| Risk Filter (ATR bounds + RR) | New (integration/risk.py) | New | Existing risk manager overkill |
| Redis Publish/Consume | New (integration/publish.py) | New | No simple module currently |
| Strategy Bridge | New (integration/strategy/AgentBridgeStrategy.py) | New | Not present |
| Logging (CSV) | New (integration/logging_utils.py) | New | Simple & isolated |
| Schema (Pydantic v1.0) | New (integration/schema/signal.py) | New | Ensure frozen contract |

## Potential Naming Conflicts

### Existing Names That May Clash
- **SignalProcessor** (tradingagents/graph/signal_processing.py) 
  - **Conflict with**: MVP signal generation
  - **Resolution**: Use `generate_signal()` function instead of class

### Proposed MVP Naming (Disambiguation)
- `TradingSignal` (vs existing SignalProcessor)
- `generate_signal()` (function, not class)
- `apply_risk()` (vs existing risk_manager)
- `publish_signal()` / `fetch_latest_signal()` (new functionality)

## Baseline Test Results
- **Command**: `pytest -q`
- **Total Tests**: 0
- **Failures**: 0  
- **Execution Time**: 0.02s
- **Status**: PASS (no tests to fail)

## Deferred Components Summary
Total: **13 major components** deferred from MVP:

### Agent-Level Deferrals
1. Complex analyst agents (4): market, news, fundamentals, social
2. Research debate system (2): bull/bear researchers  
3. Risk debate system (3): conservative/neutral/aggressive debators
4. Advanced risk manager with LLM integration
5. Trader agent with memory integration

### Infrastructure Deferrals  
6. Memory/embeddings system (ChromaDB + OpenAI)
7. Multi-source dataflow integration (5 external APIs)
8. Graph orchestration with reflection/debate
9. LLM-based analysis and reasoning
10. Complex configuration and caching systems

### External Dependencies Deferrals
11. Heavy LLM frameworks (langchain-*)
12. Social/news API integrations  
13. Advanced technical analysis libraries

---

**Next Steps**: Proceed to Step 2 - Git Integration & Repository Layout scaffolding per instructions.md guidelines. 