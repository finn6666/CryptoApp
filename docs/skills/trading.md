# Skill: Trading Engine

## Overview

The trading subsystem handles trade proposals, budget management, approval workflows, exchange execution, and portfolio tracking. Four tightly coupled modules work together.

## Modules

| Module | Class | Singleton | Lines |
|--------|-------|-----------|-------|
| `ml/trading_engine.py` | `TradingEngine` | `get_trading_engine()` | ~926 |
| `ml/exchange_manager.py` | `ExchangeManager` | `get_exchange_manager()` | ~667 |
| `ml/sell_automation.py` | `SellAutomation` | `get_sell_automation()` | ~320 |
| `ml/portfolio_tracker.py` | `PortfolioTracker` | `get_portfolio_tracker()` | ~367 |

## Data Models

**`TradeProposal`** (dataclass):
- Fields: `id`, `symbol`, `side`, `amount_gbp`, `price_at_proposal`, `reason`, `confidence`, `agent_recommendation`, `status`, `executed_at`, `execution_price`, `quantity`, `order_id`, `error`
- Status values: `pending` → `approved` / `rejected` / `executed` / `expired`

**`DailyBudget`** (dataclass):
- Fields: `date`, `spent_gbp`, `trades_executed`, `trades_proposed`, `sell_proceeds_gbp`, `sells_executed`, `fees_gbp`
- Resets at midnight

## TradingEngine — Key Methods

| Method | Purpose |
|--------|---------|
| `propose_trade(symbol, side, amount_gbp, ...)` | Create proposal — enforces budget, cooldown, min order size |
| `propose_and_auto_execute(...)` | Wraps `propose_trade` + auto-approves buys if `BUY_AUTO_APPROVE=true` |
| `approve_trade(proposal_id)` | Verify not expired (1h), re-check budget, execute |
| `reject_trade(proposal_id)` | Mark proposal rejected |
| `_execute_trade(proposal)` | Route to ExchangeManager, handle FX, record to portfolio, email confirmation |
| `activate_kill_switch()` | Emergency halt — rejects all pending proposals |
| `sign_proposal_token(id, action)` | HMAC-signed URL token for email approve/reject links |
| `verify_proposal_token(token)` | Verify HMAC token (max age 1h) |
| `get_remaining_budget()` | Daily budget minus today's spend |
| `get_status()` | Full engine status dict |

## ExchangeManager — Key Methods

| Method | Purpose |
|--------|---------|
| `load_pairs(force_refresh)` | Disk-cached pair list (6h TTL) from `data/exchange_pairs_cache.json` |
| `is_tradeable(symbol)` | Check if coin has a trading pair on any exchange |
| `find_best_pair(symbol)` | Try quote currencies: GBP → USD → USDT → USDC → EUR → BTC |
| `execute_order(symbol, side, amount_gbp)` | Full order routing: FX conversion, min order check, balance verify, retry, fallback |
| `filter_tradeable_coins(symbols)` | Batch filter with exchange mapping |
| `get_min_order_gbp(symbol)` | Exchange minimum + 5% buffer |

## SellAutomation — Exit Triggers

| Trigger | Default | Fires When |
|---------|---------|------------|
| Stop-loss | -20% | Always (ignores min hold) |
| Profit target | +50% | After 48h min hold |
| Trailing stop | -20% from peak | After 48h min hold |
| Agent re-analysis | Variable | After `SELL_RECHECK_HOURS` (24h) |

Sells **always** require manual email approval regardless of `BUY_AUTO_APPROVE`.

## PortfolioTracker — Key Methods

| Method | Purpose |
|--------|---------|
| `record_trade(...)` | Buy: average in cost basis. Sell: calculate realised P&L, deduct fees |
| `get_holdings(live_prices)` | Current holdings with unrealised P&L |
| `get_total_value(live_prices)` | Total cost, value, unrealised/realised P&L, fees |
| `get_performance_summary()` | Win rate, avg trade, best/worst, unique coins |
| `get_closed_positions()` | Fully sold positions with win/loss flag |

## Environment Variables

| Var | Default | Purpose |
|-----|---------|---------|
| `DAILY_TRADE_BUDGET_GBP` | `3.00` | Max daily buy spend |
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

## Data Flow

```
propose_and_auto_execute(symbol, side, amount, price, reason, confidence)
    → propose_trade() [budget check, cooldown, min order]
    → If BUY_AUTO_APPROVE and side=buy → approve_trade() immediately
    → Else → _send_approval_email() [HMAC-signed links, 1h expiry]
    → User clicks link → approve_trade()
        → _execute_trade()
            → ExchangeManager.execute_order() [FX, balance, retry, fallback]
            → PortfolioTracker.record_trade()
            → _send_execution_email()
```

## State Files

| File | Contents |
|------|----------|
| `data/trades/trading_state.json` | Proposals, daily budgets |
| `data/trades/sell_automation_state.json` | Peak prices, last recheck times |
| `data/portfolio.json` | Holdings, trade history, closed positions |
| `data/exchange_pairs_cache.json` | Cached exchange pairs (6h TTL) |

## Gotchas

- Sells **never** auto-execute regardless of `BUY_AUTO_APPROVE`
- Stop-loss fires **even within min hold period** (capital protection)
- Proposals expire after **1 hour** — late approval returns error
- FX conversion uses **approximate hardcoded rates** as fallback (GBP/USD = 1.27)
- Min order gets a **5% buffer** above exchange minimum
- Balance check failure is **non-blocking** — order proceeds (exchange rejects if insufficient)
- Kill switch **rejects all pending proposals** immediately
