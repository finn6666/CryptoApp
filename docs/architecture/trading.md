# Trading Engine

Trade proposals, budget management, multi-exchange execution, and portfolio tracking.

For current thresholds, env vars, and defaults, see [trading.instructions.md](../../.github/instructions/trading.instructions.md).

## Trade Lifecycle

```
Agent recommends BUY/SELL
    |
    v
propose_trade()
    |- budget check (daily cap + per-trade max)
    |- cooldown check (per-side)
    |- min order size check
    |- sellability gate (can the position be exited later?)
    |
    v
Auto-approve decision
    |- Mechanical sell triggers --> always auto-execute
    |- Buys within threshold --> auto-execute if BUY_AUTO_APPROVE
    |- Above threshold --> email approval (HMAC-signed links, 1h expiry)
    |
    v
_execute_trade()
    |- ExchangeManager routes to best-price exchange
    |- Falls back to legacy single-exchange if manager unavailable
    |- PortfolioTracker.record_trade()
    |- Confirmation email sent
    |- Post-sell: triggers background recycle scan
```

## Sell Automation

SellAutomation runs after each scan and during market monitor checks. It evaluates every holding against exit triggers in priority order -- the first matching trigger fires.

**Design philosophy**: Thresholds are intentionally wide because small-cap coins swing 20-40%/day. Tight stops would cause constant premature exits. Instead, tiered profit-taking banks partial gains while letting winners run, and agent re-analysis handles fundamental deterioration.

Exit trigger priority:
1. **Stop-loss** -- capital protection floor, always fires (bypasses min hold)
2. **Tier 1 profit** -- partial sell, tightens trailing stop
3. **Tier 2 profit** -- second partial sell, tightens trailing further
4. **Trailing stop** -- full exit on drop from peak (uses tightened value after tiers)
5. **Stagnation** -- flat positions with low conviction after extended hold
6. **Agent re-analysis** -- full exit if agents now recommend SELL/AVOID

Mechanical triggers (1-4) auto-execute regardless of approval settings. Discretionary triggers (5-6) respect `SELL_REQUIRE_APPROVAL`.

## Multi-Exchange Routing

ExchangeManager tries all configured exchanges to find the best price for each trade. Quote currency priority: GBP -> USD -> USDT -> USDC -> EUR -> BTC. Pair lists are cached with a TTL to avoid hammering exchange APIs.

If the exchange manager fails, the trading engine falls back to a legacy single-exchange path (Kraken-only via direct ccxt).

## Budget System

Buy-side spending is capped daily. Sells don't consume buy budget but are tracked separately. The budget resets at midnight. Conviction-tiered sizing scales position size up for high-confidence signals.

A sellability gate at proposal time rejects buys that would create positions too small to exit (e.g., if the smallest partial sell would be below the exchange minimum order size).

## State Files

All state is persisted as JSON with atomic writes (`.tmp` then `os.replace`). The trading engine prunes expired proposals (>7 days) and old daily budgets (>30 days) on each save to prevent unbounded growth.

| File | Purpose |
|------|---------|
| `data/trades/trading_state.json` | Proposals, daily budgets, kill switch state |
| `data/trades/sell_automation_state.json` | Peak prices, recheck timestamps, tier state |
| `data/portfolio.json` | Holdings, trade history, closed positions |
| `data/trades/audit_log.jsonl` | Full audit trail (JSONL) |
