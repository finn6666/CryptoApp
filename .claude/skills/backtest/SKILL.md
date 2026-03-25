---
name: backtest
description: Run the backtesting framework against historical data
disable-model-invocation: false
---

Run the backtesting framework to evaluate trading strategy performance.

Usage: `/backtest [options]`

Arguments (optional, pass as natural language):
- Coin symbols to test (e.g. "BTC ETH" — defaults to all available data)
- Date range (e.g. "last 30 days" or "2025-01-01 to 2025-03-01")
- Custom thresholds (e.g. "profit target 50%, stop loss 30%")

Steps:
1. Check `ml/backtesting.py` to understand available parameters
2. Run the backtest: `uv run python -c "from ml.backtesting import BacktestEngine; ..."`
   - Parse any arguments from $ARGUMENTS to set profit_target_pct, stop_loss_pct, etc.
3. Display the results summary: win rate, average P&L, Sharpe ratio, max drawdown
4. Compare against the current live thresholds from `sell_automation.py`
5. Call out any parameter combinations that significantly outperform current settings

If no arguments given, run with the current live settings as a baseline.
