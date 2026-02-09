# CryptoApp — Plan

*Last updated: 9 February 2026*

---

## Done

Full-stack crypto trading app running on Flask blueprints. Automated daily scan loop (12pm, configurable) analyses coins via Gem Detector ML + 4-agent Google ADK orchestrator, proposes trades by email, executes on approval via Coinbase. Multi-exchange support built (`exchange_manager.py`) with priority routing + fallback — needs a secondary exchange configured. Portfolio auto-tracked with P&L + sell signals. RL learns from live outcomes. Trading secured with API key auth, HMAC-signed email links (1h expiry), CORS, rate limiting, input validation. Safety caps on trade size/cooldowns, error alerts, retry logic, kill switch. Frontend has scan button, portfolio holdings, audit trail. Analysis cache, 7d price data, gem score history all persist to disk.

---

## What's Left

### Before Going Live

- [x] **Kraken account** — API key generated (`KRAKEN_API_KEY` + `KRAKEN_PRIVATE_KEY` in `.env`). Permissions: Query Funds, Query/Create/Cancel Orders, Query Ledger. IP restriction to add once Pi is deployed.
- [ ] **Deploy to Pi** — test full pipeline on ARM, verify ccxt works on Pi network
  - [ ] Gunicorn (bind `127.0.0.1`, never Flask dev server)
  - [ ] nginx reverse proxy with SSL (approve/reject links must not be plaintext)
  - [ ] systemd service for auto-start (`deploy/cryptoapp.service` — update placeholders)
  - [ ] Consider IP whitelist if Pi is externally accessible
- [ ] **CSRF tokens** — add flask-wtf when web UI trading forms exist

### Should Do

- [ ] **Persist orchestrator session memory** — ADK uses `InMemorySessionService`, lost on restart
- [ ] **Persist ML monitoring stats** — `ml/monitoring.py` is in-memory only

### Future Ideas

- [ ] Telegram/Discord notifications as alternative to email
- [ ] DCA mode — auto-buy fixed amount at regular intervals for selected coins
- [ ] Multi-exchange expansion (Binance, Kraken) via ccxt
- [ ] Upgrade CoinMarketCap plan for historical data → better ML retraining
- [ ] Production monitoring (Prometheus/Datadog)
- [ ] Backtest mode — run agent pipeline against historical data to validate