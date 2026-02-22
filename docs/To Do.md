## Recent Findings

### ~~Check activity log is working correctly~~ ✅
Audit log was working but timestamps lacked UTC indicator (causing timezone offset in browser). Fixed by appending `Z` to ISO timestamps. Also improved `get_audit_trail()` to stream-read the file tail instead of loading entire file into memory.

### ~~Success rate is throwing up 500% when there has been no action~~ ✅
Double-multiplication bug: `simple_rl.get_stats()` returned `success_rate * 100` (already a percentage), then the frontend multiplied by 100 again. With 0 trades the default 0.5 became 5000%. Fixed by removing the JS `* 100`.

### ~~Trade log and recent trades need to be merged~~ ✅
The "Recent Trades" section showed RL-reported manual trades separately from the unified Trade Log. Removed the duplicate section — all trades now appear in the single Trade Log which already merges engine + portfolio history.

### ~~Further increase risk taking on trades~~ ✅
Lowered conviction thresholds: trading agent 70% → 55%, scan loop proposal minimum 60% → 45%, gem detector fallback 55% → 45%. Increased allocation ranges so more budget is deployed per trade.

