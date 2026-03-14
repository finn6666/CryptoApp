# Scanning & Scheduling

How coins are discovered, filtered, and fed into the analysis pipeline.

## Scan Pipeline (every 12h)

```
1. _refresh_data()
   └─ CoinMarketCap API → all tracked coins with price/volume/rank

2. _get_tradeable_coins()
   └─ ExchangeManager.filter_tradeable_coins() — removes stablecoins, checks Kraken pairs

3. _select_candidates(tradeable)
   └─ Priority: user favorites → attractiveness_score fallback
   └─ Capped to SCAN_MAX_COINS (default 10)

4. _analyse_and_evaluate(coin_data)  [per coin]
   └─ ADK orchestrator → trade_decision dict
   └─ Conviction ≥45% + should_trade=True → TradingEngine.propose_and_auto_execute()

5. SellAutomation.check_and_propose_sells(live_prices)
```

## Market Monitor (between scans)

Runs continuously in a background thread once `start_scheduler()` is called.

| Interval | Job | Purpose |
|----------|-----|---------|
| 5 min | Price check | Trigger stop-loss / profit-target sells |
| 15 min | Momentum check | Alert on held-coin momentum changes |
| 30 min | Quick scan | Score all coins by `attractiveness_score`, auto-buy opportunistically |

**Quick scan scoring:** `gem_score = coin.attractiveness_score`, `gem_probability = min(1.0, score / 10.0)`. Auto-buy fires if `gem_probability * 100 ≥ auto_buy_min_gem`.

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
| `SCAN_MAX_COINS` | `10` | Max coins per scan |
| `SCAN_MAX_PROPOSALS` | `3` | Max trade proposals per scan |
| `SCAN_COOLDOWN_HOURS` | `1` | Min hours between scans |
| `MONITOR_ENABLED` | `true` | Start market monitor between scans |
| `RETRAIN_ENABLED` | `true` | Enable weekly ML retrain |

## Gotchas

- Cooldown gates both scheduled and manual "Scan Now" requests
- Conviction threshold in scan (≥45%) is lower than the trading agent's self-stated ≥55%
- `propose_and_auto_execute()` means buys execute immediately during scans — no proposal queue
- ADK 429 quota errors trigger `alert_api_quota()` — adds a backoff delay
