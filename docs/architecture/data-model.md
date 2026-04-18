# Data Model

Key data structures and persistence approach.

## Core Principle

All state is stored as JSON files in `data/` with atomic writes (write to `.tmp`, then `os.replace`). No database. This keeps the Pi deployment simple and the data human-readable for debugging.

## Runtime State

Each major subsystem is a module-level singleton accessed via `get_*()` functions. State is initialised once by `services/app_state.py:init_all()` on startup and persisted to disk on each change.

| Singleton | State it owns |
|-----------|--------------|
| `TradingEngine` | Proposals, daily budgets, kill switch, trade history |
| `PortfolioTracker` | Holdings, cost basis, closed positions, P&L |
| `SellAutomation` | Peak prices, recheck timestamps, tier state |
| `ExchangeManager` | Exchange connections, pair cache |
| `ScanLoop` | Scan schedule, cooldown state |
| `MarketMonitor` | Price observations, alert history |

## Coin Data

Coins flowing through the pipeline carry data from CoinGecko (price, volume, market cap, percent changes, rank) plus a computed `attractiveness_score` (0-10 scale) used for candidate ranking.

## State Files

| File | What it stores |
|------|---------------|
| `data/portfolio.json` | Holdings, trade history, closed positions |
| `data/trades/trading_state.json` | Active proposals, daily budgets, cooldown timers |
| `data/trades/sell_automation_state.json` | Peak prices, recheck timestamps, profit tiers taken |
| `data/trades/audit_log.jsonl` | Full event audit trail (JSONL, append-only) |
| `data/agent_analysis_cache.json` | Disk backup of analysis results (survives restarts) |
| `data/exchange_pairs_cache.json` | Exchange pair lists (TTL-based refresh) |
| `data/scan_logs/scan_YYYY-MM-DD.json` | Per-coin results from each scan |
| `data/gem_score_history.jsonl` | Historical attractiveness scores per coin |

## Pruning

State files are pruned on save to prevent unbounded growth:
- Proposals: expired/rejected older than 7 days are removed
- Daily budgets: older than 30 days are removed
- Trade history: capped at 500 entries in memory
