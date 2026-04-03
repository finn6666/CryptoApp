# Setup

## Prerequisites

- Python 3.11+ (3.13 recommended)
- [uv](https://github.com/astral-sh/uv) package manager

## Install

```bash
git clone <repo-url> && cd CryptoApp
uv sync
cp .env.example .env  # fill in API keys
uv run python app.py   # http://localhost:5001
```

## Required API Keys

| Provider | URL | Cost |
|----------|-----|------|
| CoinGecko | https://www.coingecko.com/en/api | Free (no key required; Demo key optional for higher limits) |
| Google Gemini | https://aistudio.google.com/apikey | Free (1500 req/day) |
| Kraken | https://pro.kraken.com/app/settings/api | Free |

Kraken permissions needed: Query Funds, Query/Create/Cancel Orders, Query Ledger.

## Environment Variables

All set in `.env`. See `.env.example` for full list with descriptions.

### Required

| Variable | Purpose |
|----------|---------|
| `COINGECKO_API_KEY` | Market data (optional — free tier works without it) |
| `GOOGLE_API_KEY` | Gemini agents |
| `SECRET_KEY` | Flask session signing |
| `TRADING_API_KEY` | Bearer auth for trading endpoints |

### Trading

| Variable | Default | Purpose |
|----------|---------|---------|
| `KRAKEN_API_KEY` | — | Kraken credentials |
| `KRAKEN_PRIVATE_KEY` | — | Kraken credentials |
| `DAILY_TRADE_BUDGET_GBP` | `5.00` | Max daily buy spend (£) |
| `MAX_TRADE_PCT` | `50` | Max single trade as % of budget |
| `TRADE_COOLDOWN_MIN` | `60` | Minutes between proposals per side |
| `TRADE_SERVER_URL` | `http://localhost:5001` | Base URL for email links |

### Email (Gmail SMTP)

| Variable | Purpose |
|----------|---------|
| `TRADE_NOTIFICATION_EMAIL` | Recipient for trade proposals |
| `SMTP_USER` | Gmail address |
| `SMTP_PASSWORD` | Gmail app password |

### Sell Automation

| Variable | Default | Purpose |
|----------|---------|---------|
| `SELL_STOP_LOSS_PCT` | `-50.0` | Stop-loss % (full exit, bypasses min hold) |
| `SELL_TRAILING_STOP_PCT` | `45.0` | Drop-from-peak % for trailing stop |
| `SELL_MIN_HOLD_HOURS` | `72.0` | Min hold before profit/trailing triggers |
| `SELL_TIER1_PCT` | `75.0` | Tier 1 partial-sell threshold |
| `SELL_TIER1_FRACTION` | `0.33` | Fraction to sell at Tier 1 |
| `SELL_TIER1_TRAILING_PCT` | `20.0` | Trailing stop after Tier 1 |
| `SELL_TIER2_PCT` | `150.0` | Tier 2 partial-sell threshold |
| `SELL_TIER2_FRACTION` | `0.50` | Fraction of remaining to sell at Tier 2 |
| `SELL_TIER2_TRAILING_PCT` | `15.0` | Trailing stop after Tier 2 |

### Scan Schedule

| Variable | Default | Purpose |
|----------|---------|---------|
| `SCAN_TIME` | `12:00` | Daily scan time |
| `SCAN_MAX_COINS` | `10` | Coins per scan |
| `SCAN_MAX_PROPOSALS` | `3` | Max proposals per scan |
| `SCAN_ENABLED` | `true` | Enable scan scheduler |
| `RETRAIN_ENABLED` | `true` | Enable weekly retrain |

## Verify

```bash
curl http://localhost:5001/health
curl http://localhost:5001/api/exchanges/status
```


