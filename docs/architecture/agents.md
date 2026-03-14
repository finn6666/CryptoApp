# ADK Agent Architecture

Five specialised agents on Gemini Flash coordinated by `crypto_orchestrator`. Full pipeline takes 30–120 seconds depending on Gemini API response times.

## Agent Tree

```
crypto_orchestrator (master agent)
    ├── research_specialist   — on-chain fundamentals, partnerships, red flags
    ├── technical_specialist  — chart patterns, indicators, support/resistance
    ├── risk_specialist       — position sizing, stop-loss, exit strategy (advisory)
    ├── sentiment_specialist  — social sentiment, FUD/FOMO detection
    └── trading_specialist    — final trade decision (no tools, pure LLM)
```

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `ml/agents/official/orchestrator.py` | ~302 | Master agent, `analyze_crypto()` |
| `ml/agents/official/research_agent.py` | ~112 | Research sub-agent |
| `ml/agents/official/technical_agent.py` | ~120 | Technical sub-agent |
| `ml/agents/official/risk_agent.py` | ~120 | Risk sub-agent |
| `ml/agents/official/sentiment_agent.py` | ~110 | Sentiment sub-agent |
| `ml/agents/official/trading_agent.py` | ~145 | Trading decision sub-agent |
| `ml/agents/official/quick_screen.py` | — | Single-call Tier 1 triage |
| `ml/tools/adk_tools.py` | ~495 | 16 ADK tool functions |
| `ml/orchestrator_wrapper.py` | — | Thin ADK adapter for portfolio analysis |

## Analysis Entry Point

```python
from ml.agents.official import analyze_crypto
result = await analyze_crypto(symbol, coin_data, session_id, use_memory=False)
```

**Returns:** `success`, `symbol`, `analysis`, `all_agent_texts`, `trade_decision`, `confidence`, `agents_used`

- `use_memory=False` by default — reduces API costs
- Uses `InMemorySessionService` (no cross-session state unless enabled)
- Trade decision extracted via regex JSON from `trading_specialist` output

## Dynamic Weighting

Sentiment state drives agent weighting:

| Condition | Research | Technical | Sentiment | Risk |
|-----------|----------|-----------|-----------|------|
| High hype | 25% | 25% | 40% | 10% |
| Neutral | 30% | 30% | 25% | 15% |
| Bearish | 35% | 35% | 20% | 10% |

## Quick Screen

```python
from ml.agents.official.quick_screen import quick_screen_coin
result = await quick_screen_coin(symbol, coin_data)
```

Single ADK call for Tier 1 triage — fast pass before committing full 5-agent analysis budget.

## Trading Agent Rules

- BUY conviction: ≥55% (scan loop fires at ≥45%)
- Allocation: 55–70% → 40–60% of budget; 70%+ → up to 100%
- SELL only on fundamental deterioration — never short-term dips
- Strategy: accumulate and hold medium-to-long-term
- Must recognise the coin — no trades on unknown assets

## ADK Tools

Most tool functions in `ml/tools/adk_tools.py` are **placeholder implementations** — real market data flows through the prompt, not the tools. Exceptions:

- `calculate_position_size` — Kelly Criterion sizing
- `calculate_risk_reward` — real R:R calculation
- `generate_exit_strategy` — volatility-adjusted targets
- `check_trade_budget` — calls `TradingEngine.get_status()`
- `detect_fud_fomo` — keyword-based scoring

## OrchestratorWrapper

`ml/orchestrator_wrapper.py` — module-level singleton used by `PortfolioManager` for batch analysis.

```python
from ml.orchestrator_wrapper import get_orchestrator_wrapper
wrapper = get_orchestrator_wrapper()
result = await wrapper.analyze_coin(symbol, coin_data)
```

## Orchestrator Personality

- "Sharp crypto analyst" — direct, opinionated, no corporate hedging
- Opportunity-seeking bias: "think like a venture investor"
- Output: `CryptoAnalysisOutput` (Pydantic, 16 fields)

## Costs & Limits

- ~£2.50/month at normal scan rates
- 12h analysis cache (in-memory + Redis + disk) minimises repeat calls
- Rate limit (HTTP 429) triggers `alert_api_quota()` notification
