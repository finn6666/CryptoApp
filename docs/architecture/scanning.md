# Scanning & Scheduling

How coins are discovered, filtered, and fed into the analysis pipeline.

## Scan Pipeline (every 12h)

```
1. _refresh_data()
   └─ CoinGecko API (free tier) → all tracked coins with price/volume/rank

2. _get_tradeable_coins()
   └─ ExchangeManager.filter_tradeable_coins() — removes stablecoins, checks exchange pairs

3. _select_candidates(tradeable)
   └─ Priority: user favorites → attractiveness_score fallback
   └─ Capped to SCAN_MAX_COINS (default 10)

4. _quick_screen_candidates(candidates)  [Tier 1 — 1 Gemini call each]
   └─ Regime-aware threshold gates coins through to full analysis
   └─ Gemini budget checked before each call — stops cleanly if exceeded

5. _analyse_and_evaluate(coin_data)  [Tier 2 — 3 Gemini calls each, cap 5/scan]
   └─ Debate orchestrator (bull/bear/referee) → trade_decision dict
   └─ Regime-aware conviction threshold → TradingEngine.propose_and_auto_execute()

6. SellAutomation.check_and_propose_sells(live_prices)
```

## Regime-Aware Thresholds

Market regime is determined by **BTC 7-day performance**: >+10% = bull, <-10% = bear, else neutral.

### Quick-Screen (Tier 1) thresholds

| Regime | Threshold | Env var |
|--------|-----------|---------|
| Bull | 60% | `SCAN_QUICK_SCREEN_BULL` |
| Neutral | 70% | `SCAN_QUICK_SCREEN_NEUTRAL` |
| Bear | 72% | `SCAN_QUICK_SCREEN_BEAR` |

### Conviction thresholds (to propose a trade)

| Regime | Threshold |
|--------|-----------|
| Bull | 40% |
| Neutral | 45% |
| Bear | 60% |

These are independent of the trading agent's own stated ≥55% threshold — the scan loop applies its own gate after receiving the agent's confidence score.

## Market Monitor (between scans)

Runs continuously in a background thread once `start_scheduler()` is called.

| Interval | Job | Purpose |
|----------|-----|---------|
| 5 min | Price check | Trigger stop-loss / profit-target sells |
| 15 min | Momentum check | Alert on held-coin momentum changes |
| 30 min | Quick scan | Score all coins by `attractiveness_score`, auto-buy opportunistically |

**Quick scan scoring:** `gem_probability = min(1.0, attractiveness_score / 10.0)`. Auto-buy fires if above `auto_buy_min_gem` threshold. Coins can be tagged `play_type=swing` for tighter exits.

## Scheduling

**Default (interval mode):** Scans every `SCAN_INTERVAL_HOURS` (12h).

**Legacy daily mode:** Set `SCAN_INTERVAL_HOURS=0` → single scan at `SCAN_TIME` (12:00).

Scheduler runs in a daemon thread checking every 30 seconds for pending jobs.

## ML Scheduler

| Job | Schedule | Purpose |
|-----|----------|---------|
| `weekly_retrain()` | Sunday 2 AM | Retrain ONNX model from trade outcomes |
| `weekly_report_job()` | Monday 9 AM | Email performance report |

## Files

| File | Class | Singleton |
|------|-------|-----------|
| `ml/scan_loop.py` | `ScanLoop` | `get_scan_loop()` |
| `ml/market_monitor.py` | `MarketMonitor` | `get_market_monitor()` |
| `ml/scheduler.py` | `MLScheduler` | `get_ml_scheduler()` |

## Log Files

| File | Format | Contents |
|------|--------|----------|
| `data/scan_logs/scan_YYYY-MM-DD.json` | JSON array | Per-coin results |
| `data/trades/audit_log.jsonl` | JSONL | Every scan/proposal/execution event |
| `data/monitor_logs/monitor_YYYY-MM-DD.jsonl` | JSONL | Market monitor alerts |

## Environment Variables

| Var | Default | Purpose |
|-----|---------|---------|
| `SCAN_ENABLED` | `true` | Enable/disable scan loop |
| `SCAN_INTERVAL_HOURS` | `12` | Hours between scans |
| `SCAN_TIME` | `12:00` | Daily scan time (legacy mode only) |
| `SCAN_MAX_COINS` | `10` | Max coins reaching quick-screen per scan |
| `SCAN_MAX_FULL_ANALYSIS` | `5` | Max coins reaching full debate analysis per scan |
| `SCAN_MAX_PROPOSALS` | `3` | Max trade proposals per scan |
| `SCAN_COOLDOWN_HOURS` | `1` | Min hours between scans |
| `SCAN_QUICK_SCREEN_BULL` | `60` | Quick-screen pass threshold in bull market |
| `SCAN_QUICK_SCREEN_NEUTRAL` | `70` | Quick-screen pass threshold in neutral market |
| `SCAN_QUICK_SCREEN_BEAR` | `72` | Quick-screen pass threshold in bear market |
| `MONITOR_ENABLED` | `true` | Start market monitor between scans |
| `RETRAIN_ENABLED` | `true` | Enable weekly ML retrain |

## Gotchas

- Cooldown gates both scheduled and manual "Scan Now" requests
- Conviction threshold is regime-aware — lower in bull (40%), higher in bear (60%)
- Quick-screen threshold is also regime-aware — higher in bear to save API budget on weak coins
- `propose_and_auto_execute()` means buys execute immediately during scans — no proposal queue
- ADK 429 quota errors trigger `alert_api_quota()` — adds a backoff delay
- Gemini budget is checked before each quick-screen call — scan stops cleanly if £1/day cap hit
