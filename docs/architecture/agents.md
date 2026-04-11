# ADK Agent Architecture

3-agent sequential debate on Gemini Flash. Each coin that passes the quick-screen gets a full bull/bear/referee analysis costing 3 Gemini calls.

For current model names, thresholds, and env vars, see [agents.instructions.md](../../.github/instructions/agents.instructions.md).

## Why a Debate?

Independent agents (the previous 5-agent parallel chain) produced analysis in isolation -- each agent's opinion was unaware of the others. The debate format forces the bear to directly respond to the bull's arguments, and the referee to weigh both sides with portfolio context. This catches blind spots that independent analysis misses.

The tradeoff: sequential means higher latency per coin (~10-15s vs ~5s parallel), but the scan pipeline caps how many coins reach full analysis anyway.

## Debate Flow

```
BullAdvocate   -- builds strongest buy case from coin data
    |
    v (bull case passed as context)
BearAdvocate   -- reads bull case, dismantles it point by point
    |
    v (both cases passed as context)
RefereeAgent   -- weighs both arguments with portfolio concentration
                  and market regime context, produces final verdict
```

Returns: `trade_decision` dict with `should_trade`, `trade_side`, `trade_conviction`, `trade_reasoning`.

## Two-Tier Filtering

```
All tracked coins (CoinGecko)
    |
    v  Quick Screen (1 Gemini call each, regime-aware threshold)
Tier 1 survivors (capped)
    |
    v  Full Debate (3 Gemini calls each)
Tier 2 decisions --> Trading Engine
```

Quick screen exists to save API budget. A single cheap call filters out obvious skips before committing the full 3-call debate budget.

## Key Files

| File | Role |
|------|------|
| `ml/agents/official/debate_orchestrator.py` | 3-agent debate -- primary analysis path |
| `ml/agents/official/orchestrator.py` | 5-agent chain -- used by sell automation rechecks and scan fallback |
| `ml/agents/official/quick_screen.py` | Single-call Tier 1 triage |
| `ml/tools/adk_tools.py` | ADK tool functions (mostly placeholders; real data flows via prompt) |
| `ml/orchestrator_wrapper.py` | Thin adapter for portfolio batch analysis |

## ADK Tools

Most tool functions are placeholder implementations -- real market data is injected into the agent prompt via `coin_data`, not fetched by tools at runtime. The exceptions that do real work: `calculate_position_size` (Kelly Criterion), `calculate_risk_reward`, `generate_exit_strategy`, `check_trade_budget`, `detect_fud_fomo`.

## Cost Control

The main cost driver is Gemini API calls. The system controls spend through:
- Quick-screen filtering (reduces coins reaching full debate)
- Regime-aware thresholds (bear market = stricter filter = fewer calls)
- Daily Gemini budget cap with 80% warning
- 12h analysis cache (avoids re-analysing the same coin)
- Scan cooldown preventing rapid re-scans
