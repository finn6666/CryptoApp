# Architecture

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.13+, uv |
| Web | Flask + Gunicorn (1 worker, 2 threads) |
| AI | Google ADK + Gemini |
| Exchange | ccxt (Kraken only) |
| ML | scikit-learn, ONNX Runtime |
| RL | Q-learning (no PyTorch) |
| Data | CoinMarketCap API |
| Frontend | Vanilla HTML/CSS/JS |
| Deploy | Raspberry Pi, systemd, nginx |

Monthly cost: ~£2.50 (Gemini ~£2, Pi power ~£0.50).

## Project Structure

```
app.py                      # Flask app factory, blueprint registration
main.py                     # CLI entry point
wsgi.py                     # WSGI entrypoint
gunicorn.conf.py            # Gunicorn config (Pi-optimised)
ml/
  agents/official/          # 5 ADK agents + orchestrator
  tools/adk_tools.py        # 16 agent tools
  trading_engine.py         # Trade proposals, approval, execution
  exchange_manager.py       # Kraken routing, FX, balance checks
  scan_loop.py              # Daily scan pipeline
  sell_automation.py        # Exit triggers
  portfolio_tracker.py      # Holdings, cost basis, P&L
  portfolio_manager.py      # Batch analysis, allocation
  enhanced_gem_detector.py  # GradientBoosting gem detection
  training_pipeline.py      # RandomForest training, ONNX export
  simple_rl.py              # Q-learning
  agent_memory.py           # Short/long-term context
  scheduler.py              # Weekly retrain + reports
  monitoring.py             # Prediction logging, alerts
routes/                     # Flask blueprints (coins, health, ml, symbols, trading)
services/app_state.py       # Global state, caching
src/core/                   # CoinMarketCap data fetching
src/web/                    # Templates + static assets
```

## Buy Flow

```
ScanLoop.run_scan()
  → Refresh data (CoinMarketCap)
  → Filter tradeable coins (Kraken pairs)
  → Select candidates (favourites → gem score → attractiveness)
  → Analyse (5-agent orchestrator or gem detector)
  → Conviction ≥ 75?
    → TradingEngine.propose_trade() — budget check, cooldown
    → Email with HMAC-signed APPROVE/REJECT links
    → User clicks APPROVE
    → Re-check budget + expiry
    → ExchangeManager.execute_order() — FX conversion, balance check, market order
    → PortfolioTracker.record_trade() — holdings + fees
```

## Sell Flow

```
ScanLoop step 5 → SellAutomation.check_and_propose_sells()
  → Profit target ≥ 20% → confidence 85
  → Stop loss ≤ -15%   → confidence 90
  → Trailing stop -10%  → confidence 80
  → Same email approval flow
  → Sells don't consume buy budget
```

## Singletons

| Class | Accessor |
|-------|----------|
| TradingEngine | `get_trading_engine()` |
| ExchangeManager | `get_exchange_manager()` |
| ScanLoop | `get_scan_loop()` |
| PortfolioTracker | `get_portfolio_tracker()` |
| ONNXInferenceEngine | `get_onnx_engine()` |
| MLScheduler | `get_ml_scheduler()` |

## Persistence

| File | Purpose |
|------|---------|
| `data/trades/trading_state.json` | Proposals, history, budgets |
| `data/portfolio.json` | Holdings, trade log |
| `data/exchange_pairs_cache.json` | Kraken pair cache (6h TTL) |
| `data/favorites.json` | User favourites |
| `models/crypto_model.onnx` | Trained ONNX model |
| `models/crypto_model.pkl` | sklearn model |
| `models/rl_simple_learner.json` | Q-table + stats |

## Budget

- Daily cap: `DAILY_TRADE_BUDGET_GBP` (software-side, funds must exist on Kraken)
- Buy/sell budgets tracked separately
- Budget resets at midnight (date-keyed)
- Balance verified on Kraken before every order
