## To Do

### ~~Change the 'how it works bit as that is out of date'~~ ✅
Updated trades.html with step-by-step pipeline breakdown (scanning → multi-agent analysis → proposals → portfolio tracking → hold-first strategy).

### ~~on the manual trade bit and elsewhere, want to focus more on buying and holding rather than quick sells(just buying and selling straight away), we can do a bit of this but want to lean more on buying coins~~ ✅
Raised profit target 20%→50%, widened stop-loss -15%→-20%, trailing stop 10%→20%, added 48h minimum hold period. Updated trading agent prompt to favour accumulation and fundamentals over quick flips.

### ~~Have a look at the conditions for buying, is there anything we can do to help the agent in looking at trends and being more risky/seeing oppertunities~~ ✅
Lowered buy conviction threshold 75%→70%, updated technical agent to spot accumulation zones and dip-buying opportunities, improved orchestrator weighting for buy signals.

### ~~live trading and trade log is basically the same thing, merge them~~ ✅
Merged "Executed Trades" and "Trade Log" into a single unified trade history section on the trades page.

### ~~scan loop on the health section says stopped~~ ✅
Fixed field name mismatch — scan loop now returns both `scheduler_running` and `scheduler_active`. Dashboard scan card also now distinguishes Scanning/Scheduled/Idle states.

### ~~facorites arent't appearing on dashboard~~ ✅
Added null guard for `state.analyzer` in `/api/favorites` endpoint. Favorites container now always shows (with helpful message if empty) instead of silently hiding on error.