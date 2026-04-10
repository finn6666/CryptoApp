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
