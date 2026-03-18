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
    │ 5 Gemini agents│◄─────────────────────┘
    │ + Quick Screen │
    └───────┬────────┘
            │
            ▼
    ┌────────────────┐
    │  Q-Learning    │◄── outcomes ───┐
    │ adjust -20/+15 │                │
    └───────┬────────┘                │
            │                         │
            ▼                         │
    ┌────────────────┐         ┌──────┴────────┐
    │ Trading Engine │         │     Sell      │
    │ proposals +    │────────►│  Automation   │
    │ budget check   │  sells  │ -20% / +50%   │
    └───────┬────────┘         └───────────────┘
            │                         ▲
            ▼                         │
    ┌────────────────┐         ┌──────┴────────┐
    │    Kraken      │         │   Portfolio   │
    │  (via ccxt)    │────────►│   Tracker     │
    │                │  record │ holdings+P&L  │
    └────────────────┘         └───────────────┘
```

## Key Numbers

| Parameter | Value |
|-----------|-------|
| Daily budget | £3 (configurable) |
| Conviction threshold | ≥45% to propose |
| Stop-loss | -20% |
| Profit target | +50% (after 48h) |
| Trailing stop | -20% from peak (after 48h) |
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
| Language | Python 3.12 |
| Web framework | Flask + Gunicorn (1 worker, 2 threads) |
| AI | Google ADK, Gemini Flash |
| Exchange | Kraken via ccxt |
| Frontend | Vanilla JS + Jinja2 (no build step) |
| State | Module-level singletons + JSON files |
| Cache | In-memory + Redis + disk (12h TTL) |
| Package manager | uv |
| Host | Raspberry Pi 4, systemd, nginx |
