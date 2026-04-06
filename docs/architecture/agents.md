# ADK Agent Architecture

3-agent sequential debate on Gemini Flash. Replaced the 5-agent parallel chain in April 2026. Costs 3 Gemini calls per coin vs 6 — `SCAN_MAX_FULL_ANALYSIS` raised to 5 within the same budget.

## Debate Flow

```
BullAdvocate   → builds strongest buy case from coin data
    ↓ (bull case passed as context)
BearAdvocate   → reads bull case, dismantles it point by point
    ↓ (both cases passed as context)
RefereeAgent   → weighs both arguments, considers portfolio concentration
               and market regime → produces final trade verdict
```

Returns same dict shape as the old `analyze_crypto()` — drop-in compatible.

## Files

| File | Purpose |
|------|---------|
| `ml/agents/official/debate_orchestrator.py` | All 3 agents + `analyze_crypto_debate()` (active) |
| `ml/agents/official/orchestrator.py` | Legacy 5-agent chain — kept, not used in production |
| `ml/agents/official/quick_screen.py` | Single-call Tier 1 triage (unchanged) |
| `ml/tools/adk_tools.py` | 16 ADK tool functions |
| `ml/orchestrator_wrapper.py` | Thin ADK adapter for portfolio analysis |

## Analysis Entry Point

```python
from ml.agents.official import analyze_crypto_debate
result = await analyze_crypto_debate(symbol, coin_data, session_id, use_memory=False)
```

**Returns:** `success`, `symbol`, `analysis`, `all_agent_texts`, `trade_decision`, `confidence`, `agents_used`

- Sequential: each agent receives previous agent's output as context
- Referee receives `get_portfolio_summary_for_agents()` for concentration awareness
- `use_memory=False` by default — reduces API costs

## Quick Screen

```python
from ml.agents.official.quick_screen import quick_screen_coin
result = await quick_screen_coin(symbol, coin_data)
```

Single ADK call for Tier 1 triage — fast pass before committing full debate budget.

## Referee Rules

- BUY conviction: ≥55% (scan loop fires at ≥45%)
- Allocation: 55–70% → 40–60% of budget; 70%+ → up to 100%
- SELL only on fundamental deterioration — never short-term dips
- Strategy: accumulate and hold medium-to-long-term

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

## Costs & Limits

- ~£2.50/month at normal scan rates (3 calls/coin, up to 5 full analyses/scan)
- 12h analysis cache (in-memory + Redis + disk) minimises repeat calls
- Rate limit (HTTP 429) triggers `alert_api_quota()` notification
