---
description: Google ADK agent architecture, orchestrator, sub-agents, tools, and analysis entry points.
applyTo: "ml/agents/**,ml/tools/**,ml/orchestrator_wrapper.py"
---

# AI Agents (Google ADK)

Five specialised agents on `gemini-2.0-flash` coordinated by `crypto_orchestrator`. Model is configurable via `ORCHESTRATOR_MODEL` env var. Entry point: `analyze_crypto()` in `ml/agents/official/orchestrator.py`.

## Architecture

```
crypto_orchestrator (master agent)
    ├── research_specialist   — fundamentals, partnerships, red flags
    ├── technical_specialist  — chart patterns, indicators, support/resistance
    ├── risk_specialist       — position sizing, stop-loss, exit strategy (advisory only)
    ├── sentiment_specialist  — social sentiment, FUD/FOMO detection
    └── trading_specialist    — final trade decision (no tools, pure LLM)
```

**Dynamic weighting:**
- High hype: Sentiment 40%, Technical 25%, Research 25%, Risk 10%
- Neutral: Research 30%, Technical 30%, Sentiment 25%, Risk 15%
- Bearish: Research 35%, Technical 35%, Sentiment 20%, Risk 10%

## Key Files

| File | Purpose |
|------|---------|
| `ml/agents/official/orchestrator.py` | Master agent, `analyze_crypto()` |
| `ml/agents/official/research_agent.py` | Research sub-agent |
| `ml/agents/official/technical_agent.py` | Technical sub-agent |
| `ml/agents/official/risk_agent.py` | Risk sub-agent |
| `ml/agents/official/sentiment_agent.py` | Sentiment sub-agent |
| `ml/agents/official/trading_agent.py` | Trading decision sub-agent |
| `ml/tools/adk_tools.py` | 16 ADK tool functions |
| `ml/orchestrator_wrapper.py` | Thin adapter: `analyze_coin()` coroutine for portfolio analysis |

## analyze_crypto()

```python
analyze_crypto(symbol, coin_data, session_id, use_memory=False) → Dict
```

Returns: `success`, `symbol`, `analysis`, `all_agent_texts`, `trade_decision`, `confidence`, `agents_used`

- `use_memory=False` by default — reduces API costs
- Creates `Runner` with `InMemorySessionService`
- Extracts JSON trade decision from `trading_specialist` via regex

## Quick Screen

```python
quick_screen_coin(symbol, coin_data) → Dict  # ml/agents/official/quick_screen.py
```

Single ADK call for Tier 1 triage. Used by scan loop before full analysis.

## Trading Agent Rules

- BUY conviction threshold: ≥55% (scan loop uses ≥45%)
- Allocation: 55-70% conviction → 40-60% of budget; 70%+ → up to 100%
- SELL only on fundamental deterioration — not short-term dips
- Strategy: accumulate and hold medium-to-long-term

## ADK Tools (`ml/tools/adk_tools.py`)

Most tools are placeholder implementations — real market data comes from `coin_data` in the agent prompt. Real calculations: `calculate_position_size` (Kelly Criterion), `calculate_risk_reward`, `generate_exit_strategy`, `check_trade_budget`, `detect_fud_fomo`.

Tool registry: `ADK_TOOLS` list. `get_tools_for_agent(agent_type)` maps tools to agents.

## OrchestratorWrapper

`ml/orchestrator_wrapper.py` — thin adapter used by `PortfolioManager` for batch analysis.

```python
wrapper = get_orchestrator_wrapper()          # module-level singleton
result = await wrapper.analyze_coin(symbol, coin_data)
metrics = wrapper.get_metrics()
```

## Environment Variables

| Var | Purpose |
|-----|---------|
| `GOOGLE_API_KEY` | Gemini API key (required) |
