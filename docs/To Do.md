## Cur work


## Future Work

### Multi-agent teams

Run multiple agent teams with different strategies (e.g., conservative vs aggressive) analyzing the same coins. Teams vote or compete — highest-conviction consensus triggers trades. Needs: team-scoped orchestrator configs, per-team Q-learning state, ensemble voting logic in trading engine.

### Multi-user support

Allow others to access the dashboard (read-only viewers, shared portfolio managers, or independent traders with their own portfolios). Needs: user auth system (Flask-Login or similar), user database (SQLite/Postgres), per-user portfolio files, role-based route access. Current blockers: all state is global singletons, single JSON portfolio file, single exchange account, single API key.
Like the idea of sharing a portfolio manager, users can choose different customized agents that i have created/tested

### Crypto Twitter sentiment

Add direct Twitter/X API integration for real-time crypto trader sentiment. Needs API key + rate-limited endpoint.

### Trade sizing / allocation tuning

Track per-coin allocation performance. Tune the trading agent's budget allocation rules (currently 55-70% conviction = 40-60% budget). The Q-learning agent adjusts conviction but allocation % could be smarter.

### Phase 1 — More CEXes via ccxt

Add KuCoin + Gate.io to `EXCHANGE_PRIORITY`. The `ExchangeManager` already supports multi-exchange routing — just need API keys and a small tweak for KuCoin's passphrase field. Goes from ~700 Kraken pairs to ~5,000+ tradeable coins with zero architecture changes.

### Weekly Report (revisit in future)
