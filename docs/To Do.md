## Notes
- Want heatmap to be based on holdings p and l rather than gem score, can have that on the card but dont want to color code based on it
- Don't really like the look of RL insights on the page, want it to be more useful and look better, up for ideas to do that
- No emojis** — remove all existing emojis from logs, frontend templates, JS, and Python strings. Add section in docs to ensure agents don't add any in the future.
- Gem detector still shwoing up in health page
- Can you just check the sell logic/agent is ok
- Can you check the instruction so the agents trade more expensive coins if the oppertunity arises. Would like the focus to be on small cap but also have the freedom to trade upwards if necessary
- Check secruity vulnrabilities with the new web interface/app changes
---

## Future Work

### Dashboard — Finviz-style rework

Agreed design (March 2026):

- Replace coin card grid with a **coin heatmap** — tile size proportional to gem score, colour green→red, text shows symbol/price/24h change/gem score, click → inline analysis
- Replace stacked section cards with a right **sidebar**: Holdings, Live Trading, Scanner, RL Insights
- Replace 5 overview cards with a **compact status strip**: Budget | Portfolio P&L | Scanner status | Monitor status
- Activity Log, Monthly Review, Closed Positions stay on Trades page
- Add sparkline SVG per holding tile once heatmap is in

**Frontend tasks still needed:**
- Switch dashboard polling to SSE (reduces Pi idle CPU vs 30s setInterval)
- Debounce/batch JS API calls on page load
- Add `/api/dashboard-summary` single-call endpoint
- Enable gzip compression in nginx for JSON responses
- Pagination / virtual scroll on trades log
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

