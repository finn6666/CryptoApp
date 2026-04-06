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

Priority order (first matching trigger fires):

| Trigger | Default | Notes |
|---------|---------|-------|
| Stop-loss | -50% | Always fires — ignores min hold period. Capital protection floor only, not a normal exit |
| Tier 1 profit | +75% | Partial sell (33% of position), tightens trailing stop to 20% |
| Tier 2 profit | +150% | Partial sell (50% of remaining), tightens trailing stop to 15% |
| Trailing stop | -45% from peak | Wide — won't fire on normal volatility; tightens after each profit tier |
| Nuclear profit | +300% | Full exit at extreme levels — last resort |
| Agent re-analysis | every 12h | Primary exit mechanism — full exit if agents recommend SELL/AVOID |

All triggers except stop-loss respect a **72h minimum hold period**.

**Strategy:** Stop-loss and trailing stop are set wide intentionally — small-cap coins routinely swing 20–40%/day. Tiered profit-taking lets winners run while banking partial gains. Agent re-analysis is the primary full-exit mechanism for fundamental deterioration.

Sells require email approval by default (`SELL_REQUIRE_APPROVAL=true`). The `APPROVAL_THRESHOLD_GBP` (£50) means trades above that value always require approval regardless of `BUY_AUTO_APPROVE`.

## Swing Trade Mode

When `SWING_TRADE_ENABLED=true`, positions tagged as `trade_mode="swing"` use tighter exits:

| Setting | Swing default | Accumulate default |
|---------|--------------|-------------------|
| Min hold | 8h | 72h |
| Trailing stop | 15% | 45% |
| Tier 1 profit | 25% | 75% |
| Tier 1 fraction | 50% | 33% |

`SWING_BULL_REGIME=true` tags all new buys as swing trades automatically (useful in bull markets).

## ExchangeManager Routing

- Quote currency priority: GBP → USD → USDT → USDC → EUR → BTC
- Pair cache: 6h TTL in `data/exchange_pairs_cache.json`
- FX conversion: hardcoded approximate rates as fallback (GBP/USD = 1.27)
- `execute_order` adds 5% buffer above exchange minimum order size

## Environment Variables

| Var | Default | Purpose |
|-----|---------|---------|
| `DAILY_TRADE_BUDGET_GBP` | `3.00` | Max daily buy spend |
| `MAX_TRADE_PCT` | `50` | Max single trade as % of daily budget |
| `APPROVAL_THRESHOLD_GBP` | `50.0` | Trades above this always require email approval |
| `TRADE_COOLDOWN_MIN` | `60` | Minutes between proposals per side |
| `BUY_AUTO_APPROVE` | `true` | Buys auto-execute without email |
| `SELL_REQUIRE_APPROVAL` | `true` | Sells always need manual approval |
| `SELL_STOP_LOSS_PCT` | `-50.0` | Stop-loss % (full exit, bypasses min hold) |
| `SELL_TRAILING_STOP_PCT` | `45.0` | Drop-from-peak % for trailing stop |
| `SELL_MIN_HOLD_HOURS` | `72.0` | Min hold before profit/trailing triggers |
| `SELL_TIER1_PCT` | `75.0` | Tier 1 partial-sell profit threshold |
| `SELL_TIER1_FRACTION` | `0.33` | Fraction to sell at Tier 1 |
| `SELL_TIER1_TRAILING_PCT` | `20.0` | Trailing stop tightened to this after Tier 1 |
| `SELL_TIER2_PCT` | `150.0` | Tier 2 partial-sell profit threshold |
| `SELL_TIER2_FRACTION` | `0.50` | Fraction of remaining to sell at Tier 2 |
| `SELL_TIER2_TRAILING_PCT` | `15.0` | Trailing stop tightened to this after Tier 2 |
| `SELL_PROFIT_TARGET_PCT` | `300.0` | Nuclear full-exit threshold |
| `SELL_AGENT_RECHECK` | `true` | Re-analyse holdings with agents |
| `SELL_RECHECK_HOURS` | `12` | Hours between agent rechecks per coin |
| `SWING_TRADE_ENABLED` | `false` | Enable tighter exits for swing-tagged positions |
| `SWING_BULL_REGIME` | `false` | Tag all new buys as swing trades |
| `SWING_MIN_HOLD_HOURS` | `8` | Min hold for swing positions |
| `SWING_TRAILING_STOP_PCT` | `15.0` | Trailing stop for swing positions |
| `SWING_TIER1_PCT` | `25.0` | Tier 1 threshold for swing positions |
| `SWING_TIER1_FRACTION` | `0.50` | Fraction to sell at swing Tier 1 |
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
- Best-price routing fetches live ask/bid from all exchanges listing the coin at execution time — falls back to `EXCHANGE_PRIORITY` order if all price fetches fail
