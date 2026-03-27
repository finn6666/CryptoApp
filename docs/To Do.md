## Git Workflow

## Current To Do

### UI layout & visual polish
- Text is showing a bit small on each coin (coin rating, current cost etc)
- Last scan/refresh in corner looks weird
- Scanner/scan now button on the side is a bit pointless
- Want portfolio value and portfolio P&L on the right to be clear and easy to see
- Collapse trade log on the right

### Behaviour & UX changes
- When I click on a tile/coin, just want very short analysis rather than what it's showing currently
- On RL insights, want stuff that I can learn e.g. trade patterns etc

### System & stability
- Daily budget/budget remaining has been removed (bug — restore it)
- Ensure the Pi isn't being overly extended




## Future Work

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
