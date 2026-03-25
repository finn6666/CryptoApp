---
description: Trading engine, exchange manager, sell automation, and portfolio tracking.
applyTo: "ml/trading_engine.py,ml/sell_automation.py,ml/exchange_manager.py,ml/portfolio_tracker.py"
---

# Trading Engine

## Modules

| Module | Class | Singleton |
|--------|-------|-----------|
| `ml/trading_engine.py` | `TradingEngine` | `get_trading_engine()` |
| `ml/exchange_manager.py` | `ExchangeManager` | `get_exchange_manager()` |
| `ml/sell_automation.py` | `SellAutomation` | `get_sell_automation()` |
| `ml/portfolio_tracker.py` | `PortfolioTracker` | `get_portfolio_tracker()` |

## Trade Flow

```
propose_and_auto_execute(symbol, side, amount, price, reason, confidence)
    → propose_trade()         [budget check, cooldown, min order]
    → BUY_AUTO_APPROVE=true → approve_trade() immediately
    → else → _send_approval_email() [HMAC-signed links, 1h expiry]
    → approve_trade()
        → _execute_trade()
            → ExchangeManager.execute_order() [FX, balance, retry, fallback]
            → PortfolioTracker.record_trade()
            → _send_execution_email()
```

## SellAutomation Exit Triggers

| Trigger | Setting | Notes |
|---------|---------|-------|
| Stop-loss | -80% | Intentionally loose — emergency floor only, not a normal exit |
| Trailing stop | -45% from peak | Very wide — won't fire on normal volatility |
| Profit target | 9999% (disabled) | Agents decide when to take profit via re-checks |
| Agent re-analysis | variable | Primary sell mechanism — `SELL_RECHECK_HOURS` (24h) |

**Strategy:** Stop-loss and trailing stop are set wide intentionally. Normal crypto volatility (-25% to -40%) should NOT trigger auto-sells. The agent re-analysis cycle is the primary exit mechanism. Hard stops only protect against catastrophic/near-total loss.

Sells do **not** require email approval (`SELL_REQUIRE_APPROVAL=false`). Manual approval only applies to trades above `APPROVAL_THRESHOLD_GBP=50.0`.

## ExchangeManager Routing

- Quote currency priority: GBP → USD → USDT → USDC → EUR → BTC
- Pair cache: 6h TTL in `data/exchange_pairs_cache.json`
- FX conversion: hardcoded approximate rates as fallback (GBP/USD = 1.27)
- `execute_order` adds 5% buffer above exchange minimum order size

## Environment Variables

| Var | Default | Purpose |
|-----|---------|---------|
| `DAILY_TRADE_BUDGET_GBP` | `5.00` | Max daily buy spend |
| `MAX_TRADE_PCT` | `50` | Max single trade as % of daily budget |
| `TRADE_COOLDOWN_MIN` | `60` | Minutes between proposals per side |
| `BUY_AUTO_APPROVE` | `true` | Buys auto-execute without email |
| `SELL_REQUIRE_APPROVAL` | `true` | Sells always need manual approval |
| `SELL_PROFIT_TARGET_PCT` | `50.0` | Take-profit % |
| `SELL_STOP_LOSS_PCT` | `-20.0` | Stop-loss % |
| `SELL_TRAILING_STOP_PCT` | `20.0` | Drop-from-peak % |
| `SELL_MIN_HOLD_HOURS` | `48.0` | Min hold before profit/trailing triggers |
| `SELL_AGENT_RECHECK` | `true` | Re-analyse holdings with agents |
| `SELL_RECHECK_HOURS` | `24` | Throttle between agent rechecks |
| `EXCHANGE_PRIORITY` | `kraken` | Comma-separated exchange priority |
| `SECRET_KEY` | (required) | HMAC token signing |
| `TRADE_NOTIFICATION_EMAIL` | (empty) | Approval email recipient |

## State Files

| File | Contents |
|------|----------|
| `data/trades/trading_state.json` | Proposals, daily budgets |
| `data/trades/sell_automation_state.json` | Peak prices, last recheck times |
| `data/portfolio.json` | Holdings, trade history, closed positions |
| `data/exchange_pairs_cache.json` | Cached exchange pairs |

## Gotchas

- Stop-loss fires even within min hold period — capital protection always wins
- Proposals expire after 1 hour — late approval returns error
- Balance check failure is non-blocking — order proceeds (exchange rejects if insufficient)
- Kill switch rejects all pending proposals immediately
- Sells **never** auto-execute regardless of `BUY_AUTO_APPROVE`
