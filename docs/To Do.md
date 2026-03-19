## Future Work

### Multi-agent teams

Run multiple agent teams with different strategies (e.g., conservative vs aggressive) analyzing the same coins. Teams vote or compete — highest-conviction consensus triggers trades. Needs: team-scoped orchestrator configs, per-team Q-learning state, ensemble voting logic in trading engine.

### Trade sizing / allocation tuning

Track per-coin allocation performance. Tune the trading agent's budget allocation rules (currently 55-70% conviction = 40-60% budget). The Q-learning agent adjusts conviction but allocation % could be smarter.

### Phase 2 — Add Gate.io

Gate.io requires a UTR (UK tax ID) to complete KYC — revisit once available. Code change needed: none (generic fallback handles it). Just add `GATEIO_API_KEY`, `GATEIO_API_SECRET` to `.env` and append `gateio` to `EXCHANGE_PRIORITY`.

### Weekly Report (revisit in future)
