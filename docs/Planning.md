## Current Work

- Some of the tiles (coins) have a white line border while otheres don't
- Check if the frontend can be optimized at all
- Refresh takes a while to load
## Future Work

---

### Continuous trading: Claude agent layer

Keep ADK intact but add a scheduled Claude Code agent that runs every 1-2h as a lighter portfolio manager between deep scans.

**Architecture:**
- ADK scan loop (every 12h) — coin discovery, 5-agent analysis, new buys. Unchanged.
- Claude agent (every 1-2h via `/schedule`) — portfolio review, held coin monitoring, approve/reject pending proposals, trigger targeted re-analysis on specific coins

Both layers share the same trading engine, budget, kill switch, and approval flow.

**What the Claude agent does each run:**
1. `GET /api/portfolio/holdings` — check held coin P&L and hold duration
2. `GET /api/market/conditions` — overall sentiment
3. `GET /api/trades/pending` — proposals needing a decision
4. Reason and act: sell anything? Approve/reject proposals? Anything moving unusually?
5. Optionally propose a buy directly via a new `POST /api/claude/propose` endpoint

**Backend changes (DONE):**
- `POST /api/claude/propose` — accepts `{symbol, side, reasoning, confidence}`, fetches live price, routes through `propose_and_auto_execute()`. Confidence drives allocation (55-69% -> 40% budget, 70%+ -> up to 100%). Min conviction 55%.
- `GET /api/claude/context` — compact single-call snapshot: holdings + P&L, budget, kill switch, pending proposals, market conditions, recent audit trail.

**Frontend:** no changes needed.

**TODO:** use the `/schedule` skill to create the recurring agent with a crafted prompt giving it the Pi URL, API key from env, and conservative instructions (flag rather than auto-buy unless very high conviction).

---

### Self-custody / wallet consolidation

Auto-withdraw bought coins to a hardware wallet (e.g. Ledger) after purchase to reduce exchange counterparty risk. Portfolio tracking via `data/portfolio.json` already works exchange-agnostic. Needs per-exchange withdrawal API calls + minimum threshold to avoid fee bleed.

---

### Future: Weekly report email

---

### Future: Multi-agent teams

Multiple teams with different strategies (conservative vs aggressive) vote on the same coins. Highest-conviction consensus triggers trades. Needs: team-scoped orchestrator configs, per-team Q-learning state, ensemble voting logic.

**Consider CrewAI** for implementation — natural `Crew` + `Agent` + `Task` model maps directly to the existing orchestrator/specialist pattern. Supports role delegation, sequential or parallel task execution, shared memory between agents, and works with Gemini via the LiteLLM backend. Much cleaner than wiring ADK multi-team logic manually.

---

### Future: OpenViking for agent memory

[OpenViking](https://github.com/volcengine/OpenViking) — open-source tiered context database for agents (L0 abstract / L1 overview / L2 full content). Better than flat prompt stuffing for long-running agents with large memory.

Not worth it now: `use_memory=False`, Pi RAM limit, needs Go + C++ build, extra embedding API. Revisit if agent memory is re-enabled and past trade context starts overflowing prompts.
