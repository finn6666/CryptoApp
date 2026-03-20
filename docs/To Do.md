## Questions
- Does the Q-learning only learn from buying or selling or can it learn from unrealised results as well?

- Is there a cheaper way to do the API gemeni costs, will be around £20 a month which is quite a bit, want to see if frequency of scans could be increased though?



## Future Work

### Trade sizing / allocation tuning

Track per-coin allocation performance. Tune the trading agent's budget allocation rules (currently 55-70% conviction = 40-60% budget). The Q-learning agent adjusts conviction but allocation % could be smarter.

### Self-custody / single wallet consolidation

Currently coins bought on KuCoin/MEXC sit on those exchanges. Consider auto-withdrawing to a single hardware wallet (e.g. Ledger) after buy. App already tracks holdings via `data/portfolio.json` so P&L and sell decisions don't depend on which exchange holds the coin — withdrawal would just reduce exchange counterparty risk. Needs: per-exchange withdrawal API calls, minimum withdrawal threshold to avoid fee bleed.

### Learning Insights section (revisit in future)

Current section on the Trades page surfaces Q-learning stats (epsilon, win/loss pattern, best/worst states). It works but feels thin — the displayed text is generic and not very actionable. Options to consider: richer per-coin pattern breakdowns, trend over time charts, confidence intervals, or surfacing the actual state strings more readably. Section currently renamed from "RL Insights" to "Learning Insights" since Q-learning is technically RL but the label was confusing.

### Weekly Report (revisit in future)

### Multi-agent teams (revisit in future)

Run multiple agent teams with different strategies (e.g., conservative vs aggressive) analyzing the same coins. Teams vote or compete — highest-conviction consensus triggers trades. Needs: team-scoped orchestrator configs, per-team Q-learning state, ensemble voting logic in trading engine.
