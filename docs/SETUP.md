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
| `DAILY_TRADE_BUDGET_GBP` | `3.00` | Max daily buy spend (£) |
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
| `SELL_PROFIT_TARGET_PCT` | `20.0` | Take profit % |
| `SELL_STOP_LOSS_PCT` | `-15.0` | Stop loss % |
| `SELL_TRAILING_STOP_PCT` | `10.0` | Trailing stop from peak % |

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


