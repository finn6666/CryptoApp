# Claude Code Context — CryptoApp

## Developer Preferences

- **Package manager:** `uv` — always use `uv run`, `uv add`, `uv sync` (never pip)
- **Code style:** Keep the project tidy — no redundant files, dead code, or orphaned imports
- **Git workflow:** Single `dev` branch for work, merge to `main` for releases. Descriptive commit messages with bullet-point body
- **Commit convention:** Commit + push after every completed change. Verify syntax first with `uv run python -c "import py_compile; ..."`
- **Deployment:** Raspberry Pi 4 — restart with `ssh pi "sudo systemctl restart cryptoapp"`

## Project Overview

AI-powered low-cap cryptocurrency analysis and automated trading system. Uses a 5-agent Google ADK (Gemini) architecture to discover undervalued coins, analyse them, and execute live trades on Kraken. Runs headlessly on a Raspberry Pi 4 for ~£2.50/month.

**Key flow:** CoinMarketCap data → gem detection → 5 AI agents analyse → trading engine proposes → auto-approve or email → Kraken execution → portfolio tracking → sell automation monitors exits.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ (targets 3.13) |
| Web | Flask + Gunicorn (1 worker, 2 gthread) |
| AI Agents | Google ADK + Gemini 3 Flash Preview |
| Exchange | Kraken via ccxt |
| ML | scikit-learn (training), ONNX Runtime (inference), Q-learning RL |
| Frontend | Vanilla JS + Jinja2 templates + CSS |
| Data | JSON file persistence, optional Redis cache |
| Deploy | systemd + nginx + Let's Encrypt SSL |
| Scheduling | `schedule` library in background threads |

## Directory Structure

```
app.py              — Flask app factory, extension init, scheduler starts
main.py             — CLI dev server entry point
wsgi.py             — Gunicorn WSGI entry (wsgi:app)
gunicorn.conf.py    — Pi-optimised config (1 worker, 120s timeout)
extensions.py       — Flask-Limiter, Flask-CORS (avoids circular imports)

ml/                 — All ML, trading, and agent logic
  scan_loop.py      — Automated scan pipeline (every N hours)
  trading_engine.py — Proposals, budget, approval, execution, kill switch
  exchange_manager.py — Kraken via ccxt, pair cache, FX, orders
  sell_automation.py  — Exit triggers (profit/stop-loss/trailing/agent)
  portfolio_tracker.py — Holdings, cost basis, unrealised P&L
  enhanced_gem_detector.py — GradientBoosting gem scoring (local ML)
  training_pipeline.py — RandomForest → ONNX export
  onnx_inference.py    — ONNX Runtime inference
  agent_memory.py      — Short/long-term agent context
  scheduler.py         — Weekly retrain + performance reports
  agents/official/     — 5 ADK agents + orchestrator

routes/             — Flask Blueprints (coins, health, ml, symbols, trading)
services/           — Shared app state + optional Redis cache
src/core/           — Config, CryptoAnalyzer model, CoinMarketCap fetcher
src/web/            — Jinja2 templates + static JS/CSS
data/               — Runtime JSON state (gitignored)
deploy/             — systemd unit, nginx config, SSL script
docs/               — Markdown documentation
```

## Key Patterns

- **Singletons:** `get_trading_engine()`, `get_scan_loop()`, `get_exchange_manager()` — module-level globals with lazy init
- **State init:** `services/app_state.py` → `init_all()` called once at startup
- **Error handling:** try/except with `logger.warning()` fallback; graceful degradation if dependencies missing
- **Logging:** Per-module `logger = logging.getLogger(__name__)`, emoji prefixes in messages
- **Data models:** `@dataclass` for core models, Pydantic `BaseModel` for agent I/O
- **Section separators:** `# ─── Section Name ───────────────────`
- **Auth:** Bearer token (`TRADING_API_KEY`) on all trading POST endpoints
- **Frontend:** Vanilla JS modules in `src/web/static/js/`, no build step

## Safety Mechanisms

| Mechanism | Default |
|-----------|---------|
| Kill switch | Halts all trading instantly |
| Daily budget | `DAILY_TRADE_BUDGET_GBP` (£3 default) |
| Per-trade max | 50% of daily budget |
| Proposal expiry | 1 hour |
| Trade cooldown | 60 min between proposals |
| Scan cooldown | 1 hour between scans |
| Max proposals/scan | 3 |
| Conviction threshold | ≥55% (agent) / ≥75% (scan loop) |
| Min hold period | 48h before profit/trailing triggers |
| Balance check | Kraken balance verified before every order |
| Email approval | HMAC-signed links; sells always require manual approval |
| Memory guard | systemd MemoryMax=1G, Gunicorn max_requests=500 |
| Rate limiting | 200 req/hour (Flask-Limiter) |
| Audit trail | `data/trades/audit_log.jsonl` + daily scan logs |

## Environment Variables

See `.env.example` for the full list. Key groups:
- **Required:** `COINMARKETCAP_API_KEY`, `GOOGLE_API_KEY`
- **Trading:** `KRAKEN_API_KEY`, `KRAKEN_PRIVATE_KEY`, `TRADING_API_KEY`, `DAILY_TRADE_BUDGET_GBP`
- **Approval:** `BUY_AUTO_APPROVE`, `SELL_REQUIRE_APPROVAL`, `TRADE_NOTIFICATION_EMAIL`, SMTP settings
- **Scan:** `SCAN_ENABLED`, `SCAN_INTERVAL_HOURS`, `SCAN_MAX_COINS`, `SCAN_MIN_GEM_SCORE`
- **Sell:** `SELL_PROFIT_TARGET_PCT`, `SELL_STOP_LOSS_PCT`, `SELL_TRAILING_STOP_PCT`, `SELL_MIN_HOLD_HOURS`

## Skills Reference

See `docs/skills/` for detailed guides on specific subsystems:
- `trading.md` — Trading engine, proposals, approval flow, execution
- `agents.md` — ADK agent architecture, orchestrator, sub-agents
- `scanning.md` — Scan loop, gem detection, scheduling
- `deployment.md` — Pi setup, systemd, nginx, SSL, monitoring
- `frontend.md` — Templates, JS modules, API endpoints, dashboard
