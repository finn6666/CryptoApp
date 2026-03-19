# Trading Engine

Trade proposals, budget management, exchange execution, and portfolio tracking.

## Modules

| Module | Class | Singleton | Purpose |
|--------|-------|-----------|---------|
| `ml/trading_engine.py` | `TradingEngine` | `get_trading_engine()` | Proposals, budget, approval, execution |
| `ml/exchange_manager.py` | `ExchangeManager` | `get_exchange_manager()` | Kraken routing, FX, pair cache |
| `ml/sell_automation.py` | `SellAutomation` | `get_sell_automation()` | Exit triggers, stop-loss, trailing stop |
| `ml/portfolio_tracker.py` | `PortfolioTracker` | `get_portfolio_tracker()` | Holdings, cost basis, P&L |

## Trade Flow

```
propose_and_auto_execute(symbol, side, amount_gbp, price, reason, confidence)
    │
    ├─ propose_trade()
    │   ├─ budget check (daily cap + per-trade max %)
    │   ├─ cooldown check (60 min default)
    │   └─ min order size check
    │
    ├─ BUY + BUY_AUTO_APPROVE=true → approve_trade() immediately
    └─ else → _send_approval_email() [HMAC-signed links, 1h expiry]
              → user clicks link → approve_trade()
                  → _execute_trade()
                      → ExchangeManager.execute_order()
                      → PortfolioTracker.record_trade()
                      → _send_execution_email()
```

## SellAutomation Exit Triggers

| Trigger | Threshold | Min Hold |
|---------|-----------|----------|
| Stop-loss | -20% | None (always fires) |
| Profit target | +50% | 48h |
| Trailing stop | -20% from peak | 48h |
| Agent re-analysis | variable | SELL_RECHECK_HOURS (24h) |

Sells **always** require email approval — `BUY_AUTO_APPROVE` does not affect sells.

## ExchangeManager

- Quote currency priority: GBP → USD → USDT → USDC → EUR → BTC
- Pair cache: 6h TTL at `data/exchange_pairs_cache.json`
- `execute_order` adds 5% buffer above exchange minimum
- FX rates: live lookup with hardcoded fallback (GBP/USD = 1.27)
- Balance check failure is **non-blocking** (order proceeds; exchange rejects if insufficient)

## HMAC Approval Tokens

Approval email links are signed: `SECRET_KEY` + proposal ID + action → SHA-256 HMAC. Max age 1 hour.

```python
token = engine.sign_proposal_token(proposal_id, action)   # sign
engine.verify_proposal_token(token)                        # verify + extract
```

## State Files

| File | Contents |
|------|----------|
| `data/trades/trading_state.json` | Proposals, daily budgets |
| `data/trades/sell_automation_state.json` | Peak prices, last recheck timestamps |
| `data/portfolio.json` | Holdings, trade history, closed positions |
| `data/exchange_pairs_cache.json` | Kraken pair list |

## Environment Variables

| Var | Default | Purpose |
|-----|---------|---------|
| `DAILY_TRADE_BUDGET_GBP` | `3.00` | Max daily buy spend |
| `MAX_TRADE_PCT` | `50` | Max single trade as % of daily budget |
| `TRADE_COOLDOWN_MIN` | `60` | Minutes between proposals per side |
| `BUY_AUTO_APPROVE` | `true` | Buys auto-execute without email |
| `SELL_PROFIT_TARGET_PCT` | `50.0` | Take-profit % |
| `SELL_STOP_LOSS_PCT` | `-20.0` | Stop-loss % |
| `SELL_TRAILING_STOP_PCT` | `20.0` | Drop-from-peak % |
| `SELL_MIN_HOLD_HOURS` | `48.0` | Min hold before profit/trailing triggers |
| `SELL_AGENT_RECHECK` | `true` | Re-analyse holdings with agents |
| `SELL_RECHECK_HOURS` | `24` | Hours between agent rechecks per coin |
| `EXCHANGE_PRIORITY` | `kraken` | Comma-separated exchange priority |
| `SECRET_KEY` | (required) | HMAC signing key |
| `TRADE_NOTIFICATION_EMAIL` | (empty) | Approval email recipient |

## Gotchas

- Stop-loss fires even within min hold period — capital protection overrides hold time
- Proposals expire after 1 hour — late approvals return an error
- Kill switch rejects all pending proposals immediately and halts new ones
- Single exchange (Kraken) — `EXCHANGE_PRIORITY` exists for future expansion
