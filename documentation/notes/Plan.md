# CryptoApp — Plan Ahead

*Last updated: 8 February 2026*

---

## Where We Are

The core app is functional: live coin data, AI analysis (Gem Detector + 4-agent ADK orchestrator), ML predictions, and a full trading engine with real Coinbase execution. The codebase was recently refactored from a 2761-line monolith into Flask blueprints.

**Working today:**
- Live coin data from CoinMarketCap
- Gem Detector (Random Forest + Gradient Boosting) with integrated RL
- Google ADK multi-agent analysis (research, technical, risk, sentiment)
- Trading engine with £0.05/day budget, email approval, kill switch
- Real Coinbase execution via ccxt
- Trade journal UI with RL learning
- Symbol search & management via data pipeline
- Auto-shutdown idle monitor for the Pi

---

## Priority 1 — Make Trading Actually Automated

Right now the entire pipeline is manual. Someone has to call API endpoints to trigger analysis and trade evaluation. This is the biggest gap.

### 1.1 Build an automated scan loop
- [ ] Add a daily 12pm scan job to the scheduler that:
  1. Refreshes coin data from CoinMarketCap
  2. **Filters to tradeable coins only** (coins listed on the configured exchange — see 1.4)
  3. Runs the orchestrator on top N tradeable coins (favorites + high-scoring gems)
  4. Feeds results into auto-evaluate → auto-execute (see 1.2)
- [ ] Make scan time configurable via env var (`SCAN_TIME` default `12:00`)
- [ ] Start with once daily, increase frequency later once confident
- [ ] Add a manual trigger endpoint (`/api/trades/scan-now`) for on-demand runs
- [ ] Log scan results to `data/scan_logs/` with daily summary

### 1.2 Automate everything except approval
- [ ] The scan loop should handle the full pipeline automatically: refresh → analyse → evaluate → propose → **email for approval**
- [ ] Keep the existing email approve/reject flow — human stays in the loop for real money
- [ ] Auto-execute only after email approval click (this already works)
- [ ] Log every decision (propose, skip, approve, reject, execute) to a persistent audit trail
- [ ] Goal: you receive an email at ~12pm with a trade proposal, click approve/reject, done

### 1.3 Wire RL feedback to live trades
- [ ] When a trade executes, automatically report the outcome back to `simple_rl_learner` after a configurable period (e.g. 24h or 7d)
- [ ] Add a scheduled job (`/api/trades/check-outcomes`) that reviews all open positions and feeds results to RL
- [ ] This closes the learning loop — the system improves from its own trades, not manual reports

### 1.4 Exchange coverage — solving the Coinbase gap
Coinbase only lists ~250 coins. Most sub-£1 low-cap gems won't be there.

**Recommended: hybrid approach (Coinbase + KuCoin)**
- Coinbase for major coins it supports
- KuCoin as secondary for low-cap gems (800+ coins, low fees, UK-available, mature ccxt support)
- The trading engine tries the primary exchange, falls back to secondary
- ccxt already abstracts the API so the code change is minimal

**Steps:**
- [ ] Add `KUCOIN_API_KEY` / `KUCOIN_API_SECRET` / `KUCOIN_PASSPHRASE` env vars
- [ ] On startup, query each exchange for listed trading pairs and cache the list
- [ ] Before scanning, tag each coin with which exchange(s) can trade it
- [ ] Only run the full agent pipeline on coins that are tradeable somewhere
- [ ] Trading engine tries exchanges in priority order: Coinbase → KuCoin
- [ ] Make exchange priority configurable (`EXCHANGE_PRIORITY=coinbase,kucoin`)
- [ ] **You'll need a KuCoin account** — sign up, KYC, generate API keys

**Alternatives considered:**
- *Binance* — restricted for UK users since 2023, not recommended
- *MEXC* — widest listing coverage but less established, could be tertiary option
- *Coinbase-only filtering* — simplest but defeats the purpose of gem detection

### 1.5 Automatic portfolio tracking
Every trade the agent makes should be tracked automatically — no manual reporting.
- [ ] Trading engine auto-records every execution into a portfolio ledger (`data/portfolio.json`)
- [ ] Track: symbol, quantity, entry price, timestamp, agent reasoning, exchange used
- [ ] Add `/api/portfolio/holdings` endpoint — current positions + unrealised P&L
- [ ] Add `/api/portfolio/history` endpoint — full trade log with outcomes
- [ ] Show holdings on the trades page with live P&L
- [ ] Use portfolio state to inform sell decisions — propose SELL when RL/agent confidence drops or profit target hit

---

## Priority 2 — Security (MUST DO before trading live)

Real money is involved. These must be fixed before any automated trading goes live.

### 2.1 Authentication on trading endpoints ~~(CRITICAL)~~ ✅ Done (9 Feb)
- [x] Added `@require_trading_auth` decorator to all trading POST endpoints
- [x] Checks `TRADING_API_KEY` env var via `Authorization: Bearer <key>` header
- [x] Protects: `/api/trades/propose`, `/api/trades/kill-switch`, `/api/trades/auto-evaluate`
- [x] Read-only routes (status, pending, history) remain open
- [x] `/api/trades/confirm/<token>` protected by HMAC signature instead
- [x] `TRADING_API_KEY` added to `.env.example` and `.env`

### 2.2 Fix approve/reject email links ~~(CRITICAL)~~ ✅ Done (9 Feb)
- [x] Changed to 2-step flow: GET shows confirmation page, POST executes with signed token
- [x] Signed with `itsdangerous.URLSafeTimedSerializer` (HMAC + 1-hour expiry)
- [x] Old GET-executes-trade routes (`/approve/<id>`, `/reject/<id>`) removed entirely
- [x] New route: `/api/trades/confirm/<token>` — verifies signature + expiry before action
- [x] Error pages sanitised — no stack traces leaked to users

### 2.3 CORS & CSRF protection ~~(CRITICAL)~~ ✅ Done (9 Feb)
- [x] Installed `flask-cors` — restricts to `CORS_ORIGINS` env var (default: `http://127.0.0.1:5001`)
- [x] Installed `flask-limiter` — rate limits on all trading endpoints
- [x] Limits: 10 proposals/hour, 5 kill-switch/minute, 10 confirms/minute
- [x] Extensions module (`extensions.py`) avoids circular imports
- [ ] CSRF tokens (flask-wtf) — deferred until web UI forms exist for trading

### 2.4 Rate limiting ✅ Done (9 Feb)
- [x] Installed `flask-limiter` with in-memory store
- [x] 200 req/hour global default
- [x] Tight limits on trading endpoints (see 2.3)

### 2.5 Input validation on trades ✅ Done (9 Feb)
- [x] Validates `side` is only `"buy"` or `"sell"`
- [x] Validates `amount_gbp > 0` and within remaining daily budget
- [x] Validates `symbol` is non-empty and max 20 chars
- [x] Validates `confidence` is 0–100
- [x] Validates `current_price > 0`
- [x] Reason capped at 500 chars
- [x] All error messages sanitised — no stack traces leak to users
- [x] Kill-switch action validated (`activate` / `deactivate` only)

### 2.6 Clean up secrets in source
- [ ] Remove hardcoded email fallback from `trading_engine.py` — require it from env
- [ ] Move SIEM placeholder creds out of `siem_config.json` (it's tracked in git)
- [ ] Default Flask dev server to `127.0.0.1` instead of `0.0.0.0`

---

## Priority 3 — Environment & Deployment

### 3.1 Create a proper .env setup
- [ ] Create `.env.example` with all required vars:
  - `COINMARKETCAP_API_KEY`
  - `GOOGLE_API_KEY` (Gemini)
  - `DEEPSEEK_API_KEY`
  - `COINBASE_API_KEY` / `COINBASE_API_SECRET`
  - `KUCOIN_API_KEY` / `KUCOIN_API_SECRET` / `KUCOIN_PASSPHRASE`
  - `SMTP_USER` / `SMTP_PASSWORD`
  - `TRADE_NOTIFICATION_EMAIL`
  - `DAILY_TRADE_BUDGET_GBP`
  - `TRADE_SERVER_URL`
  - `TRADING_API_KEY` (for endpoint auth)
  - `SECRET_KEY` (Flask session signing)
  - `AUTO_SHUTDOWN`
  - `SCAN_TIME`
- [ ] Document which are required vs optional
- [ ] Ensure `.env` is in `.gitignore` (already done)

### 3.2 Raspberry Pi deployment
- [ ] Test full pipeline on the Pi (ARM compatibility for all deps)
- [ ] Verify ccxt + Coinbase/KuCoin works on the Pi's network
- [ ] **Always use Gunicorn in production** (binds 127.0.0.1, never Flask dev server)
- [ ] **HTTPS via nginx is mandatory** — approve/reject links must not travel over plaintext
- [ ] Set up systemd service for auto-start
- [ ] Configure SSL via the existing nginx setup + `setup-ssl-rhel.sh`
- [ ] Consider IP whitelist in nginx if the Pi is accessible externally

---

## Priority 4 — Robustness & Safety

### 4.1 Trading safety
- [ ] Add a max single trade size cap (e.g. never more than 50% of daily budget on one coin)
- [ ] Add a cooldown between trades (e.g. min 1 hour between proposals)
- [ ] Log all trade decisions (including rejections) to a persistent audit file
- [ ] Add Gemini API fallback or graceful degradation if the API is down

### 4.2 Error handling & monitoring
- [ ] Add email alerts for errors (failed trades, API quota exhaustion, unexpected shutdowns)
- [ ] Persist orchestrator session memory across restarts (currently in-memory only)
- [ ] Add retry logic for exchange API calls (network blips on the Pi)
- [ ] Health check endpoint should report trading engine status too

---

## Priority 5 — UI & Quality of Life

### 4.1 Frontend fixes
- [ ] Fix `trades.html` JS referencing `winningTrades`/`losingTrades` elements that don't exist in the DOM
- [ ] Add a "Scan Now" button to the trading dashboard
- [ ] Show current holdings and unrealised P&L
- [ ] Add a trading activity log/timeline view

### 4.2 Data improvements
- [ ] Cache agent analysis results to disk (currently in-memory dict, lost on restart)
- [ ] Add 7-day price change data (currently only 24h)
- [ ] Historical gem score tracking to see if the detector improves over time

---

## Priority 6 — Future Ideas

- [ ] Telegram/Discord notifications as alternative to email approval
- [ ] Multi-exchange support (Binance, Kraken) via ccxt
- [ ] DCA (dollar cost averaging) mode — auto-buy a fixed amount at regular intervals for selected coins
- [ ] Backtest mode — run the agent pipeline against historical data to validate before going live
- [ ] SIEM dashboard on the Pi (partially built in `raspberry_pi/`)
- [ ] Weekly performance report email (scheduler has the hook, `weekly_report.py` exists)

---

## Suggested Order of Work

1. ~~**`.env.example` + `SECRET_KEY`** — quick win, needed for everything~~ ✅ Done (8 Feb)
2. ~~**Fix approve/reject links** — signed tokens + POST confirmation (CRITICAL before any trading)~~ ✅ Done (9 Feb)
3. ~~**Add auth to trading endpoints** — API key decorator on all `/api/trades/*`~~ ✅ Done (9 Feb)
4. ~~**CORS + CSRF + rate limiting** — install `flask-cors`, `flask-wtf`, `flask-limiter`~~ ✅ Done (9 Feb)
5. ~~**Input validation + sanitise errors** — lock down trade parameters~~ ✅ Done (9 Feb)
6. **Exchange setup** — sign up for KuCoin, add multi-exchange support
7. **Tradeable coin filtering** — cache exchange pairs, only scan what you can buy
8. **12pm daily scan loop** — the core automation: scan → analyse → propose → email
9. **Portfolio tracker** — auto-log every agent trade, show holdings + P&L
10. **RL feedback wiring** — close the learning loop with real trade outcomes
11. **Pi deployment with HTTPS** — Gunicorn + nginx + SSL, never Flask dev server
12. **Safety hardening** — trade caps, cooldowns, audit log
13. **Frontend polish** — scan button, holdings view, activity log