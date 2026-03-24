# CryptoApp — Copilot Instructions

CryptoApp is a Raspberry Pi–hosted automated cryptocurrency trading system. Flask + Gunicorn backend, vanilla JS frontend, Google ADK agents for analysis, Kraken for execution.

## Stack

- **Backend:** Python 3.13, Flask, Gunicorn (1 worker, 2 threads)
- **AI:** Google ADK, Gemini Flash — `ml/agents/official/`
- **Exchange:** Kraken via ccxt — `ml/exchange_manager.py`
- **Frontend:** Vanilla JS + Jinja2 templates, no build step
- **State:** Module-level singletons in `services/app_state.py`
- **Package manager:** `uv`

## Key Conventions

- All ML/AI classes have a module-level singleton getter: `get_trading_engine()`, `get_scan_loop()`, etc.
- App state globals live in `services/app_state.py` — never import them at module level in a class; use `import services.app_state as state` inside functions.
- Routes use Flask blueprints, registered in `app.py`.
- Analysis results are cached in-memory + Redis + disk (12h TTL).
- Never add `gem_detector` or `HiddenGemDetector` — that class has been removed.

## Project Layout

```
ml/agents/official/     # ADK agents (orchestrator + 5 sub-agents)
ml/tools/adk_tools.py   # 16 ADK tool functions
ml/scan_loop.py         # 12h scan pipeline
ml/market_monitor.py    # 5/15/30min between-scan checks
ml/trading_engine.py    # Proposals, budget, execution
ml/exchange_manager.py  # Kraken routing, FX, pair cache
ml/sell_automation.py   # Stop-loss, profit target, trailing stop
ml/orchestrator_wrapper.py  # Thin ADK adapter for portfolio analysis
services/app_state.py   # All globals, init_all()
routes/                 # Flask blueprints
src/web/                # Frontend templates + static JS/CSS
```

## Constraints

- Pi 4 RAM cap: 1G systemd limit — avoid large in-memory data structures.
- Single Gunicorn worker — no shared state via worker memory; use singletons + files.
- Agent analysis can take up to 2 minutes — always use async or background threads, never block a Flask request.
- Buys auto-approve; sells always need HMAC email confirmation.

## Skills

For domain-specific context, see `.github/instructions/`:
- `agents.instructions.md` — ADK agent architecture
- `scanning.instructions.md` — scan loop and market monitor
- `trading.instructions.md` — trading engine and execution
- `frontend.instructions.md` — templates and JS
- `deployment.instructions.md` — systemd, nginx, Pi setup
