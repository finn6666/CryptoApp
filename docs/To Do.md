## Future Work

### Multi-agent teams

Run multiple agent teams with different strategies (e.g., conservative vs aggressive) analyzing the same coins. Teams vote or compete — highest-conviction consensus triggers trades. Needs: team-scoped orchestrator configs, per-team Q-learning state, ensemble voting logic in trading engine.

### Trade sizing / allocation tuning

Track per-coin allocation performance. Tune the trading agent's budget allocation rules (currently 55-70% conviction = 40-60% budget). The Q-learning agent adjusts conviction but allocation % could be smarter.

### Self-custody / single wallet consolidation

Currently coins bought on KuCoin/MEXC sit on those exchanges. Consider auto-withdrawing to a single hardware wallet (e.g. Ledger) after buy. App already tracks holdings via `data/portfolio.json` so P&L and sell decisions don't depend on which exchange holds the coin — withdrawal would just reduce exchange counterparty risk. Needs: per-exchange withdrawal API calls, minimum withdrawal threshold to avoid fee bleed.

### Weekly Report (revisit in future)
