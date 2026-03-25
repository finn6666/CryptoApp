## Notes

### Frontend / UI  (`src/web/**`)
- Want heatmap to be based on holdings P&L rather than gem score — colour-code by price movement, gem score on the tile only
- Don't really like the look of RL insights on the page; want it to be more useful and look better — open to ideas
- Want the dashboard to look as fluid as the Finviz heatmap
- No emojis — remove all existing emojis from frontend templates, JS strings, and Python log messages. Add a section in docs/CLAUDE.md to ensure agents don't add any in future.

### Backend / Trading (`ml/trading_engine.py`, `ml/sell_automation.py`, `ml/agents/**`)
- Check the sell logic — review sell_automation.py and the sell agent to make sure exit triggers are correct
- Check agent instructions so agents trade more expensive coins if the opportunity arises. Focus should remain on small-cap but with freedom to trade upwards when conviction is high.

### Health / Bugs (`routes/health.py`, `src/web/templates/`)
- ~~Gem detector still showing up on the health page — it has been removed, reference should be cleaned up~~ Done
---

## Future Work

### Frontend optimisations
- Switch dashboard polling to SSE (reduces Pi idle CPU vs 30s setInterval)
- Add `/api/dashboard-summary` single-call endpoint to batch page-load requests
- Enable gzip compression in nginx for JSON responses
- Cache-bust CSS/JS via git short SHA

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

