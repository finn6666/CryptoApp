# Architecture Overview

CryptoApp is a Raspberry Pi–hosted automated trading system. Data flows from CoinGecko through AI analysis to trade execution on Kraken.

## System Diagram

```
                    ┌─────────────────┐
                    │   CoinGecko     │
                    │  (free tier)    │
                    └────────┬────────┘
                             │
             ┌───────────────┼───────────────┐
             ▼                               ▼
    ┌────────────────┐              ┌────────────────┐
    │   ScanLoop     │              │ MarketMonitor  │
    │  (every 12h)   │              │ (5/15/30 min)  │
    └───────┬────────┘              └───────┬────────┘
            │                               │
            ▼                               │
    ┌────────────────┐                      │
    │  ADK Agents    │                      │
    │ 3-agent debate │◄─────────────────────┘
    │ + Quick Screen │
    └───────┬────────┘
            │
            ▼
    ┌────────────────┐
    │  Q-Learning    │◄── outcomes ───┐
    │  buy/skip RL   │                │
    └───────┬────────┘                │
            │                         │
            ▼                         │
    ┌────────────────┐         ┌──────┴────────┐
    │ Trading Engine │         │     Sell      │
    │ proposals +    │────────►│  Automation   │
    │ budget check   │  sells  │ tiered exits  │
    └───────┬────────┘         └───────────────┘
            │                         ▲
            ▼                         │
    ┌────────────────┐         ┌──────┴────────┐
    │  Multi-Exchange│         │   Portfolio   │
    │  (via ccxt)    │────────►│   Tracker     │
    │ Kraken/Bitget/ │  record │ holdings+P&L  │
    │ KuCoin/MEXC    │         └───────────────┘
    └────────────────┘
```

## Key Numbers

| Parameter | Value |
|-----------|-------|
| Daily budget | £3 (configurable via `DAILY_TRADE_BUDGET_GBP`) |
| Conviction threshold | ≥45% to propose (regime-aware: 40/45/60%) |
| Stop-loss | -50% (bypasses min hold) |
| Tier 1 profit | +75% (sell 33%, tighten trailing to 20%) |
| Tier 2 profit | +150% (sell 50% of remaining, trailing to 15%) |
| Trailing stop | -45% from peak (tightens after profit tiers) |
| Min hold period | 72h (except stop-loss) |
| Scan interval | 12h |
| Monitor check | 5/15/30 min |
| Monthly API cost | ~£2.50 |

## Component Docs

- [agents.md](agents.md) — ADK agent architecture
- [scanning.md](scanning.md) — scan loop, market monitor, scheduling
- [trading.md](trading.md) — trading engine, exchange, sell automation
- [data-model.md](data-model.md) — Coin dataclass, state globals, file formats
- [infrastructure.md](infrastructure.md) — Flask, Gunicorn, Redis, systemd

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.13 |
| Web framework | Flask + Gunicorn (1 worker, 2 threads) |
| AI | Google ADK, Gemini Flash |
| Exchange | Kraken, Bitget, KuCoin, MEXC via ccxt |
| Frontend | Vanilla JS + Jinja2 (no build step) |
| State | Module-level singletons + JSON files |
| Cache | In-memory + disk (12h TTL), optional Redis |
| Package manager | uv |
| Host | Raspberry Pi 4, systemd, nginx |
