# CryptoApp — Plan

*Updated: 14 Feb 2026*

---

## Summary

Flask crypto trading app. Daily scan (12pm) via Gem Detector ML + 4-agent ADK orchestrator → proposes trades by email → executes on approval via Coinbase. Portfolio tracked with P&L + sell signals. RL learns from outcomes. Frontend: favorites, market bar, trade journal, portfolio. Security: HMAC-signed links, API key auth, CORS, rate limiting, kill switch.

---

## Sprint: Live Trading on Pi — 14 Feb → 28 Feb

**Goal:** App running on Pi, making real trades end-to-end.

### Week 1 (14–21 Feb) — Deploy & Plumb

| # | Task | Status |
|---|------|--------|
| 1 | Clone repo on Pi, install `uv`, run `uv sync` — verify ARM deps | [ ] |
| 2 | Create `.env` (see below) + `mkdir -p data/trades data/scan_logs data/agent_memory data/gem_score_summaries logs` | [ ] |
| 3 | Seed data — `uv run python main.py` once → `data/live_api.json` | [ ] |
| 4 | Fill placeholders in `deploy/cryptoapp.service` + `deploy/nginx-cryptoapp.conf` | [ ] |
| 5 | Install systemd service + nginx, set up SSL via certbot (`apt`, not `setup-ssl-rhel.sh`) | [ ] |
| 6 | Verify Coinbase API keys — test connection via `exchange_manager.py` | [ ] |
| 7 | Trigger manual scan (`/api/scan/trigger`) — confirm proposals generated + email sent | [ ] |
| 8 | Click approve link in email — confirm trade executes on Coinbase | [ ] |

### Week 2 (21–28 Feb) — Validate & Harden

| # | Task | Status |
|---|------|--------|
| 9 | Let daily 12pm scan run automatically for 2+ days — monitor logs | [ ] |
| 10 | Verify portfolio tracker picks up executed trades + shows P&L | [ ] |
| 11 | Test kill switch — confirm it blocks all new proposals | [ ] |
| 12 | Test email reject link — confirm no trade executes | [ ] |
| 13 | Lock Coinbase API key IP to Pi's public IP | [ ] |
| 14 | Retrain ML model on Pi with fresh data (`/api/ml/train`) | [ ] |
| 15 | Review first real trade results — adjust `DAILY_TRADE_BUDGET_GBP` if needed | [ ] |

### Sprint Done When

- [x] Daily scan fires at 12pm, proposes trades, emails arrive
- [x] Approve/reject links work and execute/block correctly
- [x] Portfolio page shows real holdings with live P&L
- [x] App survives Pi reboot (systemd auto-restart)

### `.env`

```env
SECRET_KEY=<random-64-char>
COINMARKETCAP_API_KEY=<key>
GOOGLE_API_KEY=<key>
TRADING_API_KEY=<key>
COINBASE_API_KEY=<key>
COINBASE_API_SECRET=<secret>
TRADE_SERVER_URL=https://<domain>
TRADE_NOTIFICATION_EMAIL=<email>
DAILY_TRADE_BUDGET_GBP=0.05
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<email>
SMTP_PASSWORD=<app-password>
CORS_ORIGINS=https://<domain>
```

---

## Bugs Fixed (14 Feb)

- [x] **Pi dashboard crash** — `dashboard_server.py` referenced `config['cryptoapp_server']` but config uses `local_server`
- [x] **Pi dashboard unreachable** — bound to `127.0.0.1`, changed to `0.0.0.0`
- [x] **Setup script wrong config key** — `setup_pi.sh` embedded config used `cryptoapp_server`
- [x] **Missing `schedule` dependency** — `scan_loop.py` / `scheduler.py` import it but it wasn't in `pyproject.toml`
- [x] **Missing `itsdangerous` dependency** — used by trading engine, only available transitively via Flask
- [x] **Whale risk check dead code** — literal `\n` in comment swallowed the `if` statement in `enhanced_gem_detector.py`
- [x] **ML target variable off-by-one** — `shift(-1).pct_change()` trained on wrong labels; fixed to `pct_change().shift(-1)`
- [x] **SSL proxy timeout too low** — `setup-ssl-rhel.sh` had `proxy_read_timeout 60s`, agent analysis needs up to 120s; bumped to `180s`
- [x] **Scheduler wrong import path** — `from training_pipeline` fails unless cwd is `ml/`; fixed to `from ml.training_pipeline`
- [x] **`siem_config.json` had literal `$ENV_VAR` strings** — JSON doesn't expand shell vars; replaced with empty strings

---

## Before Going Live

- [ ] CSRF tokens (flask-wtf) for web trading forms
- [ ] Persist ADK orchestrator memory (currently `InMemorySessionService`)
- [ ] Persist ML monitoring stats (currently in-memory)

## Backlog

- SIEM dashboard on Pi (`raspberry_pi/` — setup script + files ready, low priority)
- Telegram/Discord notifications
- DCA mode (scheduled fixed-amount buys)
- Kraken as second exchange (keys ready, just configure `exchange_manager.py`)
- Backtest mode against historical data
- Prometheus/Datadog monitoring
- Upgrade CoinMarketCap plan for historical data