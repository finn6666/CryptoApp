# Skill: AI Agents (Google ADK)

## Overview

Five specialised AI agents running on Google ADK with Gemini 3 Flash Preview. An orchestrator coordinates them to produce structured cryptocurrency analysis and trade decisions.

## Architecture

```
crypto_orchestrator (master agent)
    ├── research_specialist   — fundamentals, partnerships, red flags
    ├── technical_specialist  — chart patterns, indicators, support/resistance
    ├── risk_specialist       — position sizing, stop-loss, exit strategy
    ├── sentiment_specialist  — social sentiment, FUD/FOMO detection
    └── trading_specialist    — final trade decision (no tools, pure LLM)
```

**Weighting (dynamic based on sentiment):**
- High sentiment/hype: Sentiment 40%, Technical 25%, Research 25%, Risk 10%
- Neutral/mixed: Research 30%, Technical 30%, Sentiment 25%, Risk 15%
- Low/bearish: Research 35%, Technical 35%, Sentiment 20%, Risk 10%

Risk agent is **advisory only** at small budgets — flags risks but never blocks trades.

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `ml/agents/official/orchestrator.py` | ~302 | Master agent, `analyze_crypto()` function |
| `ml/agents/official/research_agent.py` | ~112 | Research sub-agent definition |
| `ml/agents/official/technical_agent.py` | ~120 | Technical sub-agent definition |
| `ml/agents/official/risk_agent.py` | ~120 | Risk sub-agent definition |
| `ml/agents/official/sentiment_agent.py` | ~110 | Sentiment sub-agent definition |
| `ml/agents/official/trading_agent.py` | ~145 | Trading decision sub-agent |
| `ml/tools/adk_tools.py` | ~495 | 16 tool functions for agents |

## Agent Details

| Agent | Tools | Output Schema |
|-------|-------|---------------|
| `research_specialist` | `get_project_fundamentals`, `check_github_activity`, `analyze_partnerships` | `ResearchOutput` (findings, strengths, weaknesses, red_flags) |
| `technical_specialist` | `identify_chart_patterns`, `calculate_support_resistance`, `analyze_volume_profile`, `calculate_indicators` | `TechnicalOutput` (patterns, support/resistance, indicators, trend, entry_zones) |
| `risk_specialist` | `calculate_position_size`, `calculate_risk_reward`, `assess_correlation`, `generate_exit_strategy` | `RiskOutput` (risk_score, position_size, stop_loss, take_profit, exit_strategy) |
| `sentiment_specialist` | `analyze_social_sentiment`, `detect_fud_fomo` | `SentimentOutput` (sentiment score -100..100, fud_fomo_level, narratives) |
| `trading_specialist` | (none) | `TradeDecision` (should_trade, side, conviction, reasoning, risk_note, allocation_pct) |

## Key Function: `analyze_crypto()`

```python
analyze_crypto(symbol, coin_data, session_id, use_memory=False) → Dict
```

Returns: `success`, `symbol`, `analysis`, `all_agent_texts`, `trade_decision`, `confidence`, `agents_used`

- Creates `Runner` with `InMemorySessionService`
- Streams events from all sub-agents
- Extracts JSON trade decision from `trading_specialist` output via regex
- Memory disabled by default to reduce API costs

## Trading Agent Rules

- **BUY conviction threshold:** ≥55%
- **Strategy:** Buy and hold — accumulate, hold medium-to-long-term
- **Allocation:** 55-70% conviction → 40-60% budget, 70%+ → up to 100%
- **SELL** only if outlook "fundamentally deteriorated" (not short-term dips)
- Must recognise the coin — no trades on unknown coins

## Orchestrator Personality

- "Sharp crypto analyst" — direct, opinionated, no corporate waffle
- Opportunity-seeking bias: "think like a venture investor"
- Output schema: `CryptoAnalysisOutput` (Pydantic) with 16 fields

## ADK Tools (`ml/tools/adk_tools.py`)

**Important:** Most tools are **placeholder implementations** returning static/approximate data. Real market data comes from the `coin_data` parameter in the agent prompt.

Real calculations:
- `calculate_position_size` — real Kelly Criterion-based sizing
- `calculate_risk_reward` — real R:R ratio
- `generate_exit_strategy` — volatility-adjusted targets
- `check_trade_budget` — calls real `TradingEngine.get_status()`
- `detect_fud_fomo` — keyword-based analysis

Tool registry: `ADK_TOOLS` list, `get_tools_for_agent(agent_type)` helper maps tools to agents.

## Environment Variables

| Var | Purpose |
|-----|---------|
| `GOOGLE_API_KEY` | Gemini API key (required) |

## Data Flow

```
analyze_crypto(symbol, coin_data)
    → Runner.run() streams through sub-agents
    → Each agent calls its tools (mostly placeholders)
    → trading_specialist receives synthesized analysis
    → Produces TradeDecision JSON
    → orchestrator.py extracts via regex JSON parsing
    → Returns to caller (ScanLoop or API endpoint)
```

## Gotchas

- Tool functions are **mostly placeholders** — real data flows via the prompt, not tools
- Memory is **off by default** — pass `use_memory=True` for cross-session context
- The `trading_specialist` has **no tools** — pure LLM decision agent
- JSON extraction from agent output uses **regex** (`\{...\}` matching) — can fail on malformed output
- `OrchestratorWrapper` in `ml/enhanced_gem_detector.py` bridges ADK to the PortfolioManager interface
- Gemini API costs ~£2/month at typical scan rates
