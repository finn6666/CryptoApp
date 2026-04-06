---
description: Scan loop, market monitor, and ML scheduler — how coins are discovered and analysed on schedule.
applyTo: "ml/scan_loop.py,ml/market_monitor.py,ml/scheduler.py"
---

# Scanning & Scheduling

## Scan Pipeline (runs every 12h)

```
_refresh_data()              → CoinGecko prices + tracked symbols
_get_tradeable_coins()       → filter via ExchangeManager (remove stablecoins)
_select_candidates()         → priority: favorites → attractiveness_score fallback
_quick_screen_candidates()   → Tier 1: 1 Gemini call each, regime-aware threshold
_analyse_and_evaluate()      → Tier 2: debate orchestrator (3 calls: bull/bear/referee)
                               → propose_and_auto_execute()
SellAutomation.check_and_propose_sells()
```

Candidate selection capped to `SCAN_MAX_COINS` (default 10). Full debate analysis capped to `SCAN_MAX_FULL_ANALYSIS` (default 5).

## Analysis Fallback Chain

```
Debate Orchestrator (Gemini API — 3 sequential calls)
    ↓ fails (quota / timeout / error)
Skip coin
```

No local ML fallback — if ADK fails, the coin is skipped.

## Trade Decision

- **From ADK:** `trade_decision` dict from orchestrator response
- **Fallback regex:** JSON extraction from analysis text
- Scan uses `propose_and_auto_execute()` — buys auto-execute, no overnight waits
- Conviction threshold: **≥45%** (lower than agent's stated ≥55%)

## Market Monitor (between scans)

| Interval | Action |
|----------|--------|
| 5 min | Price check — stop-loss / profit-target triggers |
| 15 min | Momentum alerts for held coins |
| 30 min | Quick opportunity scan using `attractiveness_score` |

Quick scan ranks coins by `attractiveness_score`, maps to `gem_probability = min(1.0, score / 10.0)`. Auto-buy fires if above `auto_buy_min_gem` threshold.

## Key Files

| File | Class | Singleton |
|------|-------|-----------|
| `ml/scan_loop.py` | `ScanLoop` | `get_scan_loop()` |
| `ml/market_monitor.py` | `MarketMonitor` | `get_market_monitor()` |
| `ml/scheduler.py` | `MLScheduler` | `get_ml_scheduler()` |

## ML Scheduler Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `weekly_retrain()` | Sunday 2 AM | Retrain ML model + ONNX export |
| `weekly_report_job()` | Monday 9 AM | Performance report email |

## Environment Variables

| Var | Default | Purpose |
|-----|---------|---------|
| `SCAN_ENABLED` | `true` | Enable/disable scan loop |
| `SCAN_INTERVAL_HOURS` | `12` | Hours between scans (0 = legacy daily mode) |
| `SCAN_TIME` | `12:00` | Daily scan time (legacy mode only) |
| `SCAN_MAX_COINS` | `10` | Max coins reaching quick-screen per scan |
| `SCAN_MAX_FULL_ANALYSIS` | `5` | Max coins reaching full debate analysis per scan |
| `SCAN_MAX_PROPOSALS` | `3` | Max trade proposals per scan |
| `SCAN_COOLDOWN_HOURS` | `1` | Min hours between scans |
| `MONITOR_ENABLED` | `true` | Start market monitor between scans |
| `RETRAIN_ENABLED` | `true` | Enable weekly ML retrain |

## Gotchas

- Cooldown prevents rapid re-scans — manual "Scan Now" also checks cooldown
- ADK quota/rate limit (429) triggers `alert_api_quota()` notification
- `_select_candidates()` always prefers favorites over all other coins
- Scan uses `propose_and_auto_execute()` — buys auto-execute during scheduled scans
