## To Do

### Surface stale prices in the UI
Holdings that fall back to `avg_entry_price` (delisted/unlisted tokens like XPR, SOSO) are now
tagged `price_stale: true` in the API response. The UI should surface this — e.g. grey out the
price column or append "(est.)" — so it's clear the value is estimated, not live.

### Scan frequency — review after validator is live
With the 5-agent validator added, high-conviction scan outcomes are better validated before
execution. This may justify scanning more frequently (e.g. every 6–8h instead of 12h) to
catch more opportunities.

**Budget impact before changing:** the validator adds up to 6 extra Gemini calls per
high-conviction coin. At 6h intervals:
- Quick screen: ~10 calls × 4 scans/day = 40
- Debate: ~4 coins × 3 calls × 4 scans = 48
- Validator (1 coin/scan estimate): ~6 calls × 4 scans = 24
- Total: ~112 calls/day vs ~37 at 12h

That likely hits the £1/day Gemini budget. Options:
- Reduce `SCAN_MAX_FULL_ANALYSIS` from 4→2 when moving to 6h intervals
- Or disable validator on automatic scans, keep it only for manual "Scan Now"
  (`DEBATE_VALIDATOR_ENABLED=false` in .env, override via API param)
- Or raise `GEMINI_DAILY_BUDGET_GBP` to £2.00 — still cheap at Pi cost levels


## In Progress


---

## Recently Completed

### Rework agent functionality — Option B validator
Debate runs first (3 calls). If conviction ≥75%, the 5-agent chain runs as a second opinion.
Validator agrees (≥45%) → use max conviction. Disagrees → average both, may kill the trade.
Env: `DEBATE_VALIDATOR_ENABLED` (default: true), `DEBATE_VALIDATOR_THRESHOLD` (default: 75).

### Null prices fix
Fallback chain in `routes/trading.py` now uses `avg_entry_price` if `last_buy_price` is also
missing. Stale holdings tagged `price_stale: true` in API response.

### Gem score daily summaries
`generate_daily_summary()` now auto-called at end of each scan. Saves to
`data/gem_score_summaries/YYYY-MM-DD.json`. Was never auto-invoked before.

### Swing trade removed
All positions use `trade_mode="accumulate"` (72h hold, wide trailing stops). Strategy is
medium-to-long-term only.

### Redis removed
`services/redis_cache.py` deleted — single-worker Pi has no use for shared cache.

### doc_updater deleted
`ml/doc_updater.py` removed; `deploy/security-check.sh` updated.

### .gitignore consolidation
`.pytest_cache/.gitignore` removed — root `.gitignore` already covers it.

### .env.example
Added `DEBATE_AGENT_MODEL`, `DEBATE_VALIDATOR_*`, all `QL_*`, `MAX_SLIPPAGE_PCT`,
`SELL_DRAWDOWN_RECHECK_MIN_HOURS`, `SCAN_CONCENTRATION_*`.
