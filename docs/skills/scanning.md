# Skill: Scanning & Scheduling

## Overview

The scan loop is the automated pipeline that discovers, analyses, and trades coins on a configurable schedule. The ML scheduler handles weekly model retraining and reports.

## Files

| File | Class | Singleton | Lines |
|------|-------|-----------|-------|
| `ml/scan_loop.py` | `ScanLoop` | `get_scan_loop()` | ~692 |
| `ml/enhanced_gem_detector.py` | `EnhancedGemDetector` | — | ~1408 |
| `ml/scheduler.py` | `MLScheduler` | `get_ml_scheduler()` | ~192 |

## Scan Pipeline (5 Steps)

1. **`_refresh_data()`** — Fetches from CoinMarketCap via `live_data_fetcher`, adds pipeline-tracked symbols
2. **`_get_tradeable_coins()`** — Filters via `ExchangeManager.get_exchanges_for_coin()`, skips stablecoins
3. **`_select_candidates(tradeable)`** — Priority order: favorites → high gem scores → high attractiveness. Capped to `max_coins_per_scan`
4. **`_analyse_and_evaluate(coin_data)`** — Runs ADK orchestrator (fallback: gem detector). Extracts trade decision. Calls `TradingEngine.propose_and_auto_execute()` if conviction ≥45% and `should_trade=True`
5. **Sell-side** — Calls `SellAutomation.check_and_propose_sells()` with live prices

## Key Methods

| Method | Purpose |
|--------|---------|
| `run_scan(triggered_by)` | Full pipeline — returns summary dict with metrics |
| `start_scheduler()` | Background thread: interval or daily mode. Also starts MarketMonitor |
| `stop_scheduler()` | Stop background thread |
| `get_status()` | Includes market monitor status, next scan estimate |
| `get_recent_logs(days=7)` | Reads from `data/scan_logs/scan_YYYY-MM-DD.json` |
| `get_audit_trail(limit=100)` | Reads tail of `data/trades/audit_log.jsonl` |
| `_audit(event, data)` | Appends JSONL to audit log |

## Analysis Fallback Chain

```
ADK Orchestrator (Gemini API)
    ↓ fails (quota, timeout, error)
Gem Detector (local GradientBoosting ML)
    ↓ fails
Skip coin
```

## Trade Decision Extraction

- **From ADK:** `trade_decision` dict from orchestrator response
- **Fallback:** Regex JSON extraction from analysis text
- **Gem detector:** `recommendation == "BUY" && confidence >= 45%`
- Scan uses `propose_and_auto_execute()` so trades don't sit waiting overnight

## Scheduling

**Interval mode** (default): Scans every `SCAN_INTERVAL_HOURS` (6h) using `schedule.every(N).minutes.do()`.

**Legacy daily mode**: `SCAN_INTERVAL_HOURS=0` → scans once at `SCAN_TIME` (12:00).

The scheduler runs in a daemon thread, checking every 30 seconds for pending jobs.

## ML Scheduler

| Job | Schedule | Purpose |
|-----|----------|---------|
| `weekly_retrain()` | Sunday 2 AM | Retrain ML model + ONNX export |
| `weekly_report_job()` | Monday 9 AM | Generate and email performance report |

## Gem Detector

- Uses `GradientBoostingClassifier` + `RobustScaler`
- Fast local ML — no API calls needed
- `OrchestratorWrapper` bridges ADK to portfolio manager interface
- Trade history injected into orchestrator prompt for agent learning

## Environment Variables

| Var | Default | Purpose |
|-----|---------|---------|
| `SCAN_ENABLED` | `true` | Enable/disable scan loop |
| `SCAN_TIME` | `12:00` | Daily scan time (legacy mode) |
| `SCAN_INTERVAL_HOURS` | `12` | Hours between scans (0 = daily) |
| `SCAN_MAX_COINS` | `10` | Max coins per scan |
| `SCAN_MIN_GEM_SCORE` | `5.0` | Min gem score for inclusion |
| `SCAN_MAX_PROPOSALS` | `3` | Max trade proposals per scan |
| `SCAN_COOLDOWN_HOURS` | `1` | Min hours between scans |
| `MONITOR_ENABLED` | `true` | Start market monitor between scans |
| `RETRAIN_ENABLED` | `true` | Enable weekly ML retrain |

## Data Flow

```
Scheduler thread (every 6h)
    → ScanLoop.run_scan()
        → _refresh_data() [CoinMarketCap API]
        → _get_tradeable_coins() [ExchangeManager filter]
        → _select_candidates() [favorites → gem score → attractiveness]
        → _analyse_and_evaluate() per coin
            → ADK orchestrator OR GemDetector
            → Extract trade decision
            → TradingEngine.propose_and_auto_execute()
        → SellAutomation.check_and_propose_sells()
        → Audit log + scan log
```

## Log Files

| File | Format | Contents |
|------|--------|----------|
| `data/scan_logs/scan_YYYY-MM-DD.json` | JSON array | Per-coin results for each day |
| `data/trades/audit_log.jsonl` | JSONL | Every action (scans, proposals, executions) |

## Gotchas

- **Cooldown** prevents rapid re-scans (default 1h) — manual "Scan Now" also respects this
- ADK quota/rate limit (429) triggers `alert_api_quota()` notification
- Conviction threshold in scan is **≥45%** (lower than trading agent's stated ≥55%)
- Gem detector fallback: conviction = `gem_probability * 100`, allocation = `min(80, conf - 10)`
- Scan uses `propose_and_auto_execute()` — buys auto-execute during scheduled scans
- `_select_candidates()` prioritises favorites over gem-scored coins
