"""
Backtesting Framework
Validates trading strategies against historical data.

Supports:
- Replay of historical price data through the gem detector + agent pipeline
- Simulated trade execution with budget constraints
- P&L tracking and performance metrics (Sharpe, drawdown, win rate)
- Comparison of different strategy configurations
"""

import logging
import json
import numpy as np
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

BACKTEST_RESULTS_DIR = Path("data/backtest_results")


@dataclass
class BacktestTrade:
    """A simulated trade in a backtest."""
    symbol: str
    side: str
    price: float
    quantity: float
    amount_gbp: float
    timestamp: str
    reason: str
    confidence: int
    pnl_gbp: float = 0.0
    pnl_pct: float = 0.0
    exit_price: Optional[float] = None
    exit_timestamp: Optional[str] = None
    hold_days: int = 0


@dataclass
class BacktestResult:
    """Results of a backtest run."""
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital_gbp: float
    final_capital_gbp: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win_pct: float
    avg_loss_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    profit_factor: float
    trades: List[Dict[str, Any]] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


class BacktestEngine:
    """
    Backtesting engine for crypto trading strategies.

    Replays historical data through the analysis pipeline and simulates
    trades with realistic constraints (budget, fees, slippage).
    """

    def __init__(
        self,
        initial_capital_gbp: float = 1.0,
        daily_budget_gbp: float = 0.05,
        fee_pct: float = 0.5,
        slippage_pct: float = 0.1,
        profit_target_pct: float = 20.0,
        stop_loss_pct: float = -15.0,
    ):
        self.initial_capital = initial_capital_gbp
        self.daily_budget = daily_budget_gbp
        self.fee_pct = fee_pct / 100
        self.slippage_pct = slippage_pct / 100
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct

        BACKTEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    def run_backtest(
        self,
        historical_data: List[Dict[str, Any]],
        strategy_name: str = "default",
        min_confidence: int = 75,
        use_gem_detector: bool = True,
    ) -> BacktestResult:
        """
        Run a backtest against historical price data.

        Args:
            historical_data: List of daily snapshots, each containing:
                - date: ISO date string
                - coins: List of {symbol, price, volume_24h, market_cap, ...}
            strategy_name: Label for this backtest run
            min_confidence: Minimum confidence to enter a trade
            use_gem_detector: Whether to use gem detector for scoring

        Returns:
            BacktestResult with full performance metrics
        """
        logger.info(
            f"Starting backtest '{strategy_name}' — "
            f"{len(historical_data)} days, capital=£{self.initial_capital}"
        )

        capital = self.initial_capital
        holdings: Dict[str, Dict] = {}  # symbol → {quantity, entry_price, entry_date}
        trades: List[BacktestTrade] = []
        equity_curve: List[Dict] = []
        daily_spent: Dict[str, float] = {}  # date → spent

        for day_data in historical_data:
            day_date = day_data.get("date", "unknown")
            coins = day_data.get("coins", [])
            if not coins:
                continue

            # Build price lookup
            prices = {c["symbol"]: c.get("price", 0) for c in coins if c.get("price", 0) > 0}

            # Check holdings for exits
            for symbol in list(holdings.keys()):
                if symbol not in prices:
                    continue
                h = holdings[symbol]
                current_price = prices[symbol]
                pnl_pct = ((current_price - h["entry_price"]) / h["entry_price"]) * 100

                should_sell = False
                reason = ""

                if pnl_pct >= self.profit_target_pct:
                    should_sell = True
                    reason = f"Profit target hit: {pnl_pct:.1f}%"
                elif pnl_pct <= self.stop_loss_pct:
                    should_sell = True
                    reason = f"Stop loss triggered: {pnl_pct:.1f}%"

                if should_sell:
                    # Simulate sell with fees + slippage
                    sell_price = current_price * (1 - self.slippage_pct)
                    proceeds = h["quantity"] * sell_price * (1 - self.fee_pct)
                    pnl_gbp = proceeds - h["cost_gbp"]
                    capital += proceeds

                    entry_dt = datetime.fromisoformat(h["entry_date"])
                    exit_dt = datetime.fromisoformat(day_date) if day_date != "unknown" else datetime.utcnow()
                    hold_days = max(1, (exit_dt - entry_dt).days)

                    trade = BacktestTrade(
                        symbol=symbol,
                        side="sell",
                        price=sell_price,
                        quantity=h["quantity"],
                        amount_gbp=proceeds,
                        timestamp=day_date,
                        reason=reason,
                        confidence=0,
                        pnl_gbp=round(pnl_gbp, 6),
                        pnl_pct=round(pnl_pct, 2),
                        exit_price=sell_price,
                        exit_timestamp=day_date,
                        hold_days=hold_days,
                    )
                    trades.append(trade)
                    del holdings[symbol]

            # Evaluate coins for buying
            budget_remaining = self.daily_budget - daily_spent.get(day_date, 0)
            if budget_remaining <= 0:
                pass
            else:
                scored_coins = self._score_coins(coins, use_gem_detector)

                for scored in scored_coins:
                    if budget_remaining <= 0:
                        break
                    symbol = scored["symbol"]
                    confidence = scored["confidence"]
                    if confidence < min_confidence:
                        continue
                    if symbol in holdings:
                        continue  # Already holding

                    price = prices.get(symbol, 0)
                    if price <= 0:
                        continue

                    # Simulate buy with fees + slippage
                    buy_amount = min(budget_remaining, self.daily_budget * 0.5)
                    buy_price = price * (1 + self.slippage_pct)
                    quantity = (buy_amount * (1 - self.fee_pct)) / buy_price

                    capital -= buy_amount
                    budget_remaining -= buy_amount
                    daily_spent[day_date] = daily_spent.get(day_date, 0) + buy_amount

                    holdings[symbol] = {
                        "quantity": quantity,
                        "entry_price": buy_price,
                        "entry_date": day_date,
                        "cost_gbp": buy_amount,
                    }

                    trade = BacktestTrade(
                        symbol=symbol,
                        side="buy",
                        price=buy_price,
                        quantity=quantity,
                        amount_gbp=buy_amount,
                        timestamp=day_date,
                        reason=scored.get("reason", ""),
                        confidence=confidence,
                    )
                    trades.append(trade)

            # Calculate equity (capital + holdings value)
            holdings_value = sum(
                h["quantity"] * prices.get(sym, h["entry_price"])
                for sym, h in holdings.items()
            )
            equity = capital + holdings_value
            equity_curve.append({
                "date": day_date,
                "equity": round(equity, 6),
                "capital": round(capital, 6),
                "holdings_value": round(holdings_value, 6),
                "num_holdings": len(holdings),
            })

        # Final metrics
        final_equity = equity_curve[-1]["equity"] if equity_curve else self.initial_capital
        metrics = self._calculate_metrics(trades, equity_curve, final_equity)

        result = BacktestResult(
            strategy_name=strategy_name,
            start_date=historical_data[0].get("date", "") if historical_data else "",
            end_date=historical_data[-1].get("date", "") if historical_data else "",
            initial_capital_gbp=self.initial_capital,
            final_capital_gbp=round(final_equity, 6),
            total_return_pct=metrics["total_return_pct"],
            total_trades=metrics["total_trades"],
            winning_trades=metrics["winning_trades"],
            losing_trades=metrics["losing_trades"],
            win_rate=metrics["win_rate"],
            avg_win_pct=metrics["avg_win_pct"],
            avg_loss_pct=metrics["avg_loss_pct"],
            max_drawdown_pct=metrics["max_drawdown_pct"],
            sharpe_ratio=metrics["sharpe_ratio"],
            profit_factor=metrics["profit_factor"],
            trades=[asdict(t) for t in trades],
            equity_curve=equity_curve,
            config={
                "initial_capital": self.initial_capital,
                "daily_budget": self.daily_budget,
                "fee_pct": self.fee_pct * 100,
                "slippage_pct": self.slippage_pct * 100,
                "profit_target_pct": self.profit_target_pct,
                "stop_loss_pct": self.stop_loss_pct,
                "min_confidence": min_confidence,
            },
        )

        self._save_result(result)

        logger.info(
            f"Backtest '{strategy_name}' complete — "
            f"Return: {result.total_return_pct:.2f}%, "
            f"Win rate: {result.win_rate:.1f}%, "
            f"Sharpe: {result.sharpe_ratio:.2f}"
        )

        return result

    # ─── Scoring ──────────────────────────────────────────────

    def _score_coins(
        self,
        coins: List[Dict],
        use_gem_detector: bool,
    ) -> List[Dict[str, Any]]:
        """
        Score coins for buying potential. Uses gem detector if available,
        otherwise falls back to heuristic scoring.
        """
        scored = []

        for coin in coins:
            price = coin.get("price", 0)
            if price <= 0 or price > 1.25:
                continue  # Only low-cap coins

            confidence = 0
            reason = ""

            if use_gem_detector:
                try:
                    from ml.enhanced_gem_detector import HiddenGemDetector
                    detector = HiddenGemDetector()
                    result = detector._heuristic_gem_score(coin)
                    confidence = int(result.get("gem_probability", 0) * 100)
                    reason = f"Gem score: {result.get('gem_score', 0):.1f}"
                except Exception:
                    confidence = self._heuristic_score(coin)
                    reason = "Heuristic scoring"
            else:
                confidence = self._heuristic_score(coin)
                reason = "Heuristic scoring"

            scored.append({
                "symbol": coin["symbol"],
                "confidence": confidence,
                "reason": reason,
            })

        scored.sort(key=lambda x: x["confidence"], reverse=True)
        return scored[:5]  # Top 5

    @staticmethod
    def _heuristic_score(coin: Dict) -> int:
        """Simple heuristic scoring based on price action."""
        score = 50
        pct_24h = coin.get("percent_change_24h", 0)
        vol = coin.get("volume_24h", 0)
        mcap = coin.get("market_cap", 0)

        if pct_24h > 5:
            score += 15
        elif pct_24h > 0:
            score += 5
        elif pct_24h < -10:
            score -= 10

        if vol > 100000:
            score += 10
        if mcap and 100000 < mcap < 50000000:
            score += 10

        return max(0, min(100, score))

    # ─── Metrics ──────────────────────────────────────────────

    def _calculate_metrics(
        self,
        trades: List[BacktestTrade],
        equity_curve: List[Dict],
        final_equity: float,
    ) -> Dict[str, Any]:
        """Calculate performance metrics from backtest trades."""
        sell_trades = [t for t in trades if t.side == "sell"]
        wins = [t for t in sell_trades if t.pnl_gbp > 0]
        losses = [t for t in sell_trades if t.pnl_gbp <= 0]

        total_return_pct = ((final_equity - self.initial_capital) / self.initial_capital) * 100

        # Win rate
        win_rate = (len(wins) / len(sell_trades) * 100) if sell_trades else 0

        # Average win/loss
        avg_win = np.mean([t.pnl_pct for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl_pct for t in losses]) if losses else 0

        # Max drawdown
        if equity_curve:
            equities = [e["equity"] for e in equity_curve]
            peak = equities[0]
            max_dd = 0
            for eq in equities:
                if eq > peak:
                    peak = eq
                dd = ((peak - eq) / peak) * 100 if peak > 0 else 0
                max_dd = max(max_dd, dd)
        else:
            max_dd = 0

        # Sharpe ratio (daily returns, annualised)
        if len(equity_curve) > 1:
            equities = [e["equity"] for e in equity_curve]
            daily_returns = np.diff(equities) / equities[:-1]
            if np.std(daily_returns) > 0:
                sharpe = (np.mean(daily_returns) / np.std(daily_returns)) * np.sqrt(365)
            else:
                sharpe = 0
        else:
            sharpe = 0

        # Profit factor
        total_wins = sum(t.pnl_gbp for t in wins)
        total_losses = abs(sum(t.pnl_gbp for t in losses))
        profit_factor = total_wins / total_losses if total_losses > 0 else float("inf") if total_wins > 0 else 0

        return {
            "total_return_pct": round(total_return_pct, 2),
            "total_trades": len(trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": round(win_rate, 1),
            "avg_win_pct": round(avg_win, 2),
            "avg_loss_pct": round(avg_loss, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else 999.0,
        }

    # ─── Synthetic Data ──────────────────────────────────────

    @staticmethod
    def generate_synthetic_data(
        symbols: List[str] = None,
        days: int = 90,
        volatility: float = 0.05,
    ) -> List[Dict[str, Any]]:
        """
        Generate synthetic historical data for backtesting.
        Useful for testing the framework without real data.
        """
        if symbols is None:
            symbols = ["ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON"]

        np.random.seed(42)
        data = []
        base_prices = {sym: np.random.uniform(0.001, 0.50) for sym in symbols}

        for day in range(days):
            day_date = (datetime.now(timezone.utc) - timedelta(days=days - day)).strftime("%Y-%m-%d")
            coins = []
            for sym in symbols:
                # Random walk
                change = np.random.normal(0, volatility)
                base_prices[sym] *= (1 + change)
                base_prices[sym] = max(base_prices[sym], 0.0001)
                coins.append({
                    "symbol": sym,
                    "price": round(base_prices[sym], 8),
                    "volume_24h": round(np.random.uniform(10000, 500000), 2),
                    "market_cap": round(base_prices[sym] * np.random.uniform(1e6, 1e8), 2),
                    "percent_change_24h": round(change * 100, 2),
                })
            data.append({"date": day_date, "coins": coins})

        return data

    # ─── Persistence ──────────────────────────────────────────

    def _save_result(self, result: BacktestResult):
        """Save backtest result to disk."""
        filename = f"backtest_{result.strategy_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        filepath = BACKTEST_RESULTS_DIR / filename
        try:
            with open(filepath, "w") as f:
                json.dump(asdict(result), f, indent=2, default=str)
            logger.info(f"Backtest result saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save backtest result: {e}")

    @staticmethod
    def list_results() -> List[Dict[str, Any]]:
        """List available backtest results."""
        if not BACKTEST_RESULTS_DIR.exists():
            return []
        results = []
        for f in sorted(BACKTEST_RESULTS_DIR.glob("backtest_*.json"), reverse=True):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                results.append({
                    "file": f.name,
                    "strategy": data.get("strategy_name"),
                    "return_pct": data.get("total_return_pct"),
                    "win_rate": data.get("win_rate"),
                    "sharpe": data.get("sharpe_ratio"),
                    "trades": data.get("total_trades"),
                    "period": f"{data.get('start_date', '?')} → {data.get('end_date', '?')}",
                })
            except Exception:
                pass
        return results
