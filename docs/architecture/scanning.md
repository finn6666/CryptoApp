# Scanning & Scheduling

How coins are discovered, filtered, analysed, and fed into the trading pipeline.

For current thresholds, intervals, and env vars, see [scanning.instructions.md](../../.github/instructions/scanning.instructions.md).

## Scan Pipeline

The scan loop runs periodically and is the primary way new trades get proposed.

```
1. Refresh data       -- pull latest prices from CoinGecko
2. Filter tradeable   -- remove stablecoins, check exchange pair availability
3. Select candidates  -- prioritise user favorites, then rank by attractiveness score
4. Quick screen       -- Tier 1: single Gemini call per coin, regime-aware threshold
5. Full debate        -- Tier 2: 3-agent debate for survivors, capped per scan
6. Propose trades     -- winners go through TradingEngine.propose_and_auto_execute()
7. Check sells        -- SellAutomation evaluates all holdings against exit triggers
```

**Why two tiers?** Full debate analysis costs 3 Gemini calls per coin. Quick screen costs 1. The two-tier approach lets the system evaluate more candidates cheaply and only spend the full budget on promising ones.

## Regime-Aware Thresholds

Market regime (bull/neutral/bear) is determined by BTC's recent performance. Both the quick-screen pass threshold and the conviction threshold for proposing trades adjust based on regime:

- **Bull**: lower thresholds -- more coins pass through, more trades proposed
- **Bear**: higher thresholds -- stricter filtering saves API budget on weak candidates

This is a cost control mechanism as much as a quality control one.

## Market Monitor

Runs continuously between scans in a background thread. Three jobs at different intervals:

- **Price check** (frequent): triggers stop-loss and profit-target sells for held coins
- **Momentum check** (moderate): alerts on significant momentum changes in holdings
- **Quick opportunity scan** (less frequent): scores all coins by attractiveness, can auto-buy opportunistically

The monitor handles the "what if something happens between scans" problem without running full agent analysis.

## ML Scheduler

Separate from the scan scheduler. Handles weekly maintenance:
- Model retraining (scikit-learn -> ONNX export) from trade outcomes
- Performance report emails

## Key Files

| File | Role |
|------|------|
| `ml/scan_loop.py` | Scan pipeline orchestration |
| `ml/market_monitor.py` | Between-scan continuous monitoring |
| `ml/scheduler.py` | Weekly retrain and report jobs |
