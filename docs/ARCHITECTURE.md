# Architecture

```
                        ┌─────────────────┐
                        │  CoinMarketCap  │
                        │    (prices)     │
                        └────────┬────────┘
                                 │
                 ┌───────────────┼───────────────┐
                 ▼                               ▼
        ┌────────────────┐              ┌────────────────┐
        │   ScanLoop     │◄─────────────│ MarketMonitor  │
        │  (every 12h)   │  high gems / │ (5/15/30 min)  │
        │                │  momentum    │                │
        └───────┬────────┘              └───────┬────────┘
                │                               │
                ▼                               │
        ┌────────────────┐                      │
        │   Analysis     │                      │
        │ Gemini Agents  │                      │
        │ + Gem Detector │                      │
        └───────┬────────┘                      │
                │                               │
                ▼                               │
        ┌────────────────┐                      │
        │  Q-Learning    │◄─── outcomes ───┐    │
        │ adjust -20/+15 │                 │    │
        └───────┬────────┘                 │    │
                │                          │    │
                ▼                          │    │
        ┌────────────────┐          ┌──────┴────────┐
        │ Trading Engine │          │     Sell      │
        │  proposals +   │────────► │  Automation   │◄──┘
        │  budget check  │  sells   │ -35% / +75%   │
        └───────┬────────┘          └───────────────┘
                │                          ▲
                ▼                          │
        ┌────────────────┐          ┌──────┴────────┐
        │    Kraken      │          │   Portfolio   │
        │  (via ccxt)    │────────► │   Tracker     │
        │                │  record  │ holdings+P&L  │
        └────────────────┘          └───────────────┘
```

## How it works

**Scanning:** ScanLoop runs every 12h — pulls CoinMarketCap data, filters to Kraken-tradeable coins, picks top 10 candidates. MarketMonitor runs between scans — checks prices every 5min, momentum every 15min, quick ML scan every 30min. High-scoring finds get fed into the full pipeline.

**Analysis:** Candidates go through 5 Gemini agents (Sentiment, Research, Technical, Risk, Trading) which produce a conviction score 0–100. Falls back to the local GradientBoosting gem detector if Gemini's down. Q-learning then adjusts conviction -20 to +15 based on past experience with similar patterns.

**Trading:** Conviction 45+ creates a proposal. Buys auto-approve, large sells need email confirmation (HMAC-signed, 1h expiry). Exchange Manager handles pair routing, FX, balance checks, executes on Kraken via ccxt.

**Portfolio:** Tracks holdings, cost basis, P&L. Sell automation checks stop-loss (-35%), profit target (+75%), trailing stop (35% from peak), plus 12h agent re-checks. All outcomes feed back into Q-learning.

**Learning:** Q-learning maps market patterns (gem score / volume / trend / cap size) to buy/skip actions. Losses hurt 1.5x more than equivalent wins. Repeat losers get progressive penalties. Exploration decays from 30% to 5% as it gains experience.

**Weekly:** Model retrains Sunday 2am, report emails Monday 9am.

## Key numbers

| | |
|---|---|
| Daily budget | £3 (configurable) |
| Conviction threshold | 45+ to buy |
| Stop-loss | -35% |
| Profit target | +75% (after 72h) |
| Trailing stop | 35% from peak |
| Max auto-buys/day | 3 (from MarketMonitor) |
| Coin re-analysis cooldown | 6h |
| Monthly cost | ~£2.50 |

## Files

```
ml/scan_loop.py             # Full scan pipeline
ml/market_monitor.py        # Between-scan monitoring
ml/agents/official/         # 5 Gemini agents + orchestrator
ml/trading_engine.py        # Proposals, approval, execution
ml/exchange_manager.py      # Kraken routing + FX
ml/sell_automation.py       # Exit triggers + RL feedback
ml/q_learning.py            # RL agent
ml/portfolio_tracker.py     # Holdings + P&L
ml/enhanced_gem_detector.py # Local ML scoring
ml/training_pipeline.py     # Model training + ONNX export
ml/scheduler.py             # Weekly retrain + reports
routes/trading.py           # API + web UI
services/app_state.py       # Singleton init
src/core/                   # CoinMarketCap fetching
src/web/                    # Frontend
```
