## Completed (14 March 2026)

- **Architecture docs directory** — created `docs/architecture/` with overview, agents, scanning, trading, data-model, and infrastructure pages.
- **SSH / remote access docs** — added Tailscale SSH section to `docs/DEPLOYMENT.md`; also covered in `docs/architecture/infrastructure.md`.
- **VS Code instructions** — created `.github/copilot-instructions.md` (workspace rules) and five `.github/instructions/*.instructions.md` files (agents, scanning, trading, frontend, deployment) replacing the old skills format.
- **Reduce API costs** — increased analysis cache TTL from 4h to 12h (`CACHE_EXPIRY_SECONDS = 43200` in `services/app_state.py`). No functional change.
- **Remove Enhanced Gem Detector** — deleted `ml/enhanced_gem_detector.py` (~1400 lines). Replaced its three roles:
  - Candidate ranking: `_select_candidates()` now uses `attractiveness_score` fallback
  - Monitor quick scan: `_run_quick_scan` in `market_monitor.py` uses `attractiveness_score`
  - Portfolio analysis: extracted `OrchestratorWrapper` into `ml/orchestrator_wrapper.py`
  - Removed `gem_detector` / `GEM_DETECTOR_AVAILABLE` globals from `app_state.py`
  - Removed 5 `/api/gems/detect|scan|train|status|top` endpoints from `ml_routes.py`
  - Updated `scan_loop.py`, `backtesting.py`, `scheduler.py`, `routes/coins.py`, `routes/health.py`, `routes/trading.py`

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
