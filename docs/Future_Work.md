## Future Work

### Self-custody / wallet consolidation

Auto-withdraw bought coins to a hardware wallet (e.g. Ledger) after purchase to reduce exchange counterparty risk. Portfolio tracking via `data/portfolio.json` already works exchange-agnostic. Needs per-exchange withdrawal API calls + minimum threshold to avoid fee bleed.

---

### Weekly report email

Automated weekly performance summary sent via email. MLScheduler already has a `weekly_report_job()` stub scheduled for Monday 9 AM — needs the email content and send logic implemented.

---

### Debate orchestrator — tuning and iteration

The 3-agent debate architecture (BullAdvocate → BearAdvocate → RefereeAgent) replaced the 5-agent parallel chain in April 2026. It costs 3 Gemini calls vs 6, allowing `SCAN_MAX_FULL_ANALYSIS` to be raised to 5 within the same budget.

Next steps:
- Monitor referee verdict quality vs the old chain on real trades
- Tune bear/bull prompt aggression — referee currently has no minimum conviction floor separate from the scan threshold
- Consider passing recent closed-trade outcomes into the referee prompt for regime-aware calibration

---

### Multi-exchange routing — further improvements

Best-price routing across Kraken, Bitget, KuCoin, MEXC is live. Current gaps:
- Live price fetch failures fall back to priority order silently — add alerting when best-price routing is degraded
- Pair cache (6h TTL) means a new listing on a cheaper exchange won't be used until cache expires — consider shorter TTL or event-driven invalidation
- No spread comparison — currently picks best mid-price, not accounting for bid/ask spread width

---

### Multi-agent strategy teams (longer term)

Multiple agent teams with different risk profiles (conservative vs aggressive) vote on the same coins. Highest-conviction consensus triggers trades. Needs: team-scoped orchestrator configs, per-team Q-learning state, ensemble voting logic.

**Consider CrewAI** for implementation — natural `Crew` + `Agent` + `Task` model maps directly to the debate orchestrator pattern. Supports role delegation, sequential or parallel task execution, shared memory, and works with Gemini via the LiteLLM backend.

---

### OpenViking for agent memory (longer term)

Open-source tiered context database for agents (L0 abstract / L1 overview / L2 full content). Better than flat prompt stuffing for long-running agents with large memory.

Not worth it now: `use_memory=False`, Pi RAM limit, needs Go + C++ build, extra embedding API. Revisit if agent memory is re-enabled and past trade context starts overflowing prompts.
