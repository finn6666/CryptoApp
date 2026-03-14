## Findings & decisions (14 March 2026)

### RL insights — "learnt from 122 trades" (fixed)
The episode counter was incrementing twice per closed trade because `record_outcome` calls `update()` twice (once for buy, once for skip). Added a separate `closed_trades` counter that increments exactly once per closed trade. Dashboard now reads that. Old files estimate it as `episodes // 2` so nothing resets.

### Enhanced Gem Detector — what it actually does
The docstring is aspirational. What it *actually* does is compute ~30 heuristic features from CoinMarketCap price/volume/rank data and feed them into a `GradientBoostingClassifier` trained on CSV data. There is no external sentiment feed, no Twitter, no on-chain data. The "smart money", "fear/greed contrarian", "timing anomaly" etc. signals are all derived from price/rank maths.  

However, **it is not dead code** — it serves three purposes that are worth keeping:
1. **Candidate ranking** — `predict_hidden_gem` scores coins in the scan loop to prioritise which get the full 5-agent analysis first (cheapest pre-filter before burning Gemini calls).
2. **Monitor quick scan** — `market_monitor.py` uses it every ~30 min to spot high-scoring coins and feed them into the trading pipeline opportunistically.
3. **`/api/portfolio/analyze` route** — `PortfolioManager` calls the `OrchestratorWrapper` (which lives in this file) to run batch ADK analysis via the endpoint.

The Gemini fallback in the scan loop (if ADK fails, fall back to gem detector) was the only genuinely unnecessary part — removed (see below).

**Decision: keep the file but don't confuse it for something it isn't.** The GradientBoosting model and heuristic scoring is a perfectly fine fast pre-filter; the agents provide the real intelligence.

### Gemini fallback to local gem detector (removed)
The "Try 2" fallback in `scan_loop._analyse_and_evaluate` — if Gemini ADK fails, fall back to the local GradientBoosting model and make a trade decision from that — has been removed. Gemini has 99.9%+ uptime. The fallback would produce a low-quality signal from heuristics and could result in bad autonomous trades precisely when the system is degraded. If ADK fails, the coin is now skipped cleanly. Transient network errors/quota hits are still caught and alerted.

### Scheduler.py
Single purpose: **weekly ML model retrain every Sunday at 2 AM**. Fetches 30 days of fresh price data, retrains the GradientBoosting model (`training_pipeline.py`), exports to ONNX, hot-reloads the ONNX engine. Background daemon thread started on app startup. Keep it — it ensures the gem detector's scoring model stays current without any manual intervention.

### Quick screen — is it needed?
Yes. It's a 1-call Gemini filter that decides whether each candidate deserves the full 5–6 call analysis. With ~15 candidates per scan it saves ~70 Gemini calls per cycle for coins that obviously aren't worth it. No trade is ever made from it alone — it's purely a cost/efficiency gate, not a decision layer. Keep it.

### Backtesting + Q-learning — do they work together?
**No, they are completely independent.** Backtesting replays historical snapshots through the gem detector and simulates P&L — used manually via the API for strategy validation. Q-learning learns exclusively from live trade outcomes. They could be integrated (pre-train Q-table from backtest outcomes) but are not currently. Both worth keeping as-is.

### Exit triggers — profit target, trailing stop
Changed defaults:
- **Stop loss**: -50% → **-80%** (dead-coin protection only). The 12h agent recheck will flag deteriorating fundamentals long before -80%, so this should rarely fire.
- **Min hold period**: 72h → **0h (disabled)**. Agent decides when to exit. Re-enable with `SELL_MIN_HOLD_HOURS=72` env var if needed.
- **Profit target (75%)** and **trailing stop (45% from peak)** are kept as configurable safety nets, but the primary exit signal is always the agent recheck. A coin hitting 75% gain is a clean exit signal regardless of market type.

### Singleton in sell_automation.py
Standard module-level singleton pattern (`get_sell_automation()`). Correct and intentional — the single instance shares peak price tracking and recheck timestamps across the whole app. Nothing to change.

### Redis cache — keep it
`redis_cache.py` IS used in 3 places (`app_state.py` cache_analysis/get_cached_analysis and `routes/trading.py` stats endpoint), all wrapped in `try/except`. When `REDIS_CONNECTION_STRING` isn't set it silently no-ops at zero cost. If you ever run multiple Gunicorn workers it becomes the shared analysis cache layer. Worth keeping for the ~50 lines.

### `.pytest_cache`
Already in `.gitignore` (line 51). Nothing to do.

### `src/core/crypto_analyzer.py` — actively used
`services/app_state.py` creates the global `analyzer` instance from it at startup. `live_data_fetcher.py` imports its `Coin`, `CoinStatus`, `RiskLevel` dataclasses. It's the backbone data model for every coin in the system.

### Dead code cleaned up this session
- **Sell quantity bug** — `sell_automation` now threads the actual coin quantity through to the exchange, bypassing the amount→quantity reconversion that was causing "have 50, need 92" errors.
- **RL double-count** — `closed_trades` counter added, displayed instead of `episodes`.
- **Gemini gem-detector fallback** — removed from `scan_loop._analyse_and_evaluate`.
- **Unreachable `return entry`** — removed from `app_state.get_cached_analysis`.
- **Sell defaults updated** — stop loss -80%, min hold 0h.

## Still to do

- Would like a new dir for architecture docs — so everything can be explained in isolation and together
- SSH issues while away from Pi?
- Skills and instructions — ensure existing skills/instructions work with the new VS Code agent customisation functionality

### Remove Enhanced Gem Detector — replace with ADK agent
Remove `ml/enhanced_gem_detector.py` (~1400 lines) and replace its three roles with ADK-native alternatives:

1. **Candidate ranking (pre-filter before full scan)** — replace `predict_hidden_gem` scoring with a lightweight ADK quick-screen pass. The existing `quick_screen_coin` agent already does this in one call; wire it into `_select_candidates` as the ranking signal instead of gem score.

2. **Monitor quick scan** — `market_monitor.py` currently scores all tradeable coins with the gem detector every ~30 min to find opportunistic buys. Replace with the `quick_screen_coin` agent called only on coins above a basic attractiveness threshold, keeping the same opportunistic-buy logic downstream.

3. **`/api/portfolio/analyze` route** — `PortfolioManager` uses `OrchestratorWrapper` (which lives in `enhanced_gem_detector.py`) to wrap ADK calls. Move `OrchestratorWrapper` into its own small file (`ml/orchestrator_wrapper.py`) or inline it into `portfolio_manager.py` directly, then delete the dependency on `enhanced_gem_detector.py`.

4. **`app_state.py`** — remove `initialize_gem_detector`, `gem_detector`, `GEM_DETECTOR_AVAILABLE` globals. Update `init_all()` accordingly.

5. **Routes** — `routes/coins.py`, `routes/ml_routes.py` call `gem_detector.predict_hidden_gem` in several places for per-coin scoring in the UI. Replace with cached ADK analysis results from `get_cached_analysis()` where available, or remove the scoring panel if it's dashboard-only.

**Priority:** do the three core replacements (1–4) first so the scan loop and monitor work without the detector, then clean up the routes (5) as a follow-up.

## Future work

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