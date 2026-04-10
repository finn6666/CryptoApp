## To Do

### Null current prices for some holdings
Fallback now uses `avg_entry_price` when `last_buy_price` is also unavailable, and holdings are tagged `price_stale: true` in the API response. The root cause for XPR/SOSO is that these tokens are likely delisted or not listed on any configured exchange — the exchange price fetch fails and CoinGecko doesn't track them. The `price_stale` flag lets the UI indicate the position value is estimated rather than live.

**Remaining:** Surface `price_stale` visually in the holdings table (greyed-out price or "(est.)" label).


### Agent memory
`agent_memory.py` and Q-learning are completely separate systems:

- **Q-learning** (`q_learning.py`) = the active learning mechanism. Tracks trade outcomes (P&L, hold time) and adjusts future buy confidence scores. Connected to scan loop and sell automation. This IS the experiential feedback loop.
- **Agent memory** (`agent_memory.py`) = a simple key-value context cache (6h in-memory TTL, 30d on disk). Previously only used by the legacy 5-agent orchestrator. Now also available to the 5-agent validator (Option B). It does not "learn" — it stores context, not outcomes.

**They don't need merging.** Q-learning is the right learning system. Agent memory is useful for providing the validator with historical analysis context to avoid re-analysing a coin the same way twice.

**Backtesting** (`ml/backtesting.py`) is a separate historical simulation tool — not connected to Q-learning or agent memory. Currently, Q-learning only learns from live trades. Potential improvement: use backtest outcomes to pre-seed the Q-table (not implemented).


## In Progress



---

## Recently Completed

### Rework agent functionality — Option B validator
Debate runs first (3 calls). If conviction ≥75% (`DEBATE_VALIDATOR_THRESHOLD`), the 5-agent chain runs as a second opinion before executing. If the validator also agrees (conviction ≥45%), uses max conviction. If it disagrees, conviction is averaged — may fall below the regime threshold. Controlled by `DEBATE_VALIDATOR_ENABLED` (default: true) and `DEBATE_VALIDATOR_THRESHOLD` (default: 75).

### Null prices fix
Improved price fallback in `routes/trading.py`: step 4 now falls back to `avg_entry_price` if `last_buy_price` is also missing. Holdings using stale fallback prices are tagged `price_stale: true` in the API response.

### Doc updater deleted
`ml/doc_updater.py` removed. `deploy/security-check.sh` updated to remove the changelog step.

### Redis cache removed
`services/redis_cache.py` deleted. Redis calls removed from `services/app_state.py` (cache_analysis, get_cached_analysis) and `routes/trading.py` (/api/cache/status route removed). App uses in-memory + JSON file cache only — appropriate for single-worker Pi deployment.

### .gitignore consolidation
`.pytest_cache/.gitignore` removed. Root `.gitignore` already covers `.pytest_cache/` and `.venv/`.

### Gem score tracker
`GemScoreTracker` records every Gemini analysis conviction score to `data/gem_score_history.jsonl`. It's called in `scan_loop.py` and `market_monitor.py` after each analysis. Daily summaries are now generated automatically at the end of each scan (previously `generate_daily_summary()` was never auto-called) and saved to `data/gem_score_summaries/YYYY-MM-DD.json`. API endpoints in `ml_routes.py` expose history, accuracy report, and per-symbol trends.

### Short-term trade removed
Swing trade code removed from `sell_automation.py` and `scan_loop.py`. All new positions use `trade_mode="accumulate"` with the standard 72h hold + wide trailing stops. The strategy is medium-to-long-term accumulation only. Swing trade env vars removed from `.env.example` and `trading.instructions.md`.

### .env.example updated
Added missing env vars: `DEBATE_AGENT_MODEL`, `DEBATE_VALIDATOR_ENABLED/THRESHOLD`, all `QL_*` Q-learning params, `MAX_SLIPPAGE_PCT`, `SELL_DRAWDOWN_RECHECK_MIN_HOURS`, `SCAN_CONCENTRATION_LIMIT/MIN_CONVICTION`.
