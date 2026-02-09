"""
Portfolio Tracker
Auto-records every trade execution, tracks holdings, and calculates P&L.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

PORTFOLIO_FILE = Path("data/portfolio.json")


class PortfolioTracker:
    """
    Tracks all agent trades automatically.

    - Records every execution into a portfolio ledger
    - Tracks current holdings with cost basis
    - Calculates unrealised P&L using live prices
    - Informs sell decisions when confidence drops or profit target hit
    """

    def __init__(self):
        self.holdings: Dict[str, Dict[str, Any]] = {}  # symbol → holding
        self.trade_log: List[Dict[str, Any]] = []
        PORTFOLIO_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._load()
        logger.info(
            f"Portfolio tracker loaded — {len(self.holdings)} holdings, "
            f"{len(self.trade_log)} trades"
        )

    # ─── Trade Recording ──────────────────────────────────────

    def record_trade(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        amount_gbp: float,
        exchange: str = "coinbase",
        order_id: str = "",
        reasoning: str = "",
        confidence: int = 0,
        proposal_id: str = "",
    ) -> Dict[str, Any]:
        """
        Record a trade execution and update holdings.
        Called automatically by the trading engine after execution.
        """
        trade = {
            "id": f"trade_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{symbol}",
            "symbol": symbol.upper(),
            "side": side.lower(),
            "quantity": quantity,
            "price": price,
            "amount_gbp": amount_gbp,
            "exchange": exchange,
            "order_id": order_id,
            "reasoning": reasoning,
            "confidence": confidence,
            "proposal_id": proposal_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.trade_log.append(trade)

        # Update holdings
        sym = symbol.upper()
        if side.lower() == "buy":
            if sym in self.holdings:
                # Average in
                h = self.holdings[sym]
                total_qty = h["quantity"] + quantity
                total_cost = h["total_cost_gbp"] + amount_gbp
                h["quantity"] = total_qty
                h["total_cost_gbp"] = total_cost
                h["avg_entry_price"] = total_cost / total_qty if total_qty > 0 else 0
                h["last_buy_price"] = price
                h["last_buy_at"] = trade["timestamp"]
                h["trades"] += 1
            else:
                self.holdings[sym] = {
                    "symbol": sym,
                    "quantity": quantity,
                    "total_cost_gbp": amount_gbp,
                    "avg_entry_price": price,
                    "first_buy_at": trade["timestamp"],
                    "last_buy_at": trade["timestamp"],
                    "last_buy_price": price,
                    "exchange": exchange,
                    "trades": 1,
                }
        elif side.lower() == "sell":
            if sym in self.holdings:
                h = self.holdings[sym]
                h["quantity"] -= quantity
                realised_pnl = (price - h["avg_entry_price"]) * quantity
                h.setdefault("realised_pnl_gbp", 0)
                h["realised_pnl_gbp"] += realised_pnl
                h["last_sell_at"] = trade["timestamp"]
                h["last_sell_price"] = price
                trade["realised_pnl_gbp"] = realised_pnl

                # Remove if fully sold
                if h["quantity"] <= 0:
                    h["quantity"] = 0
                    h["closed_at"] = trade["timestamp"]

        self._save()

        logger.info(
            f"📒 Recorded: {side.upper()} {quantity:.8f} {sym} @ £{price:.6f} "
            f"(£{amount_gbp:.4f}) on {exchange}"
        )
        return trade

    # ─── Holdings & P&L ───────────────────────────────────────

    def get_holdings(self, live_prices: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        Get current holdings with unrealised P&L.
        Pass live_prices as {symbol: price} for P&L calculation.
        """
        result = []
        for sym, h in self.holdings.items():
            if h["quantity"] <= 0:
                continue  # Skip fully sold

            holding = {**h}

            if live_prices and sym in live_prices:
                current_price = live_prices[sym]
                holding["current_price"] = current_price
                holding["current_value_gbp"] = current_price * h["quantity"]
                holding["unrealised_pnl_gbp"] = (
                    (current_price - h["avg_entry_price"]) * h["quantity"]
                )
                holding["unrealised_pnl_pct"] = (
                    ((current_price - h["avg_entry_price"]) / h["avg_entry_price"] * 100)
                    if h["avg_entry_price"] > 0
                    else 0
                )

            result.append(holding)

        return result

    def get_total_value(self, live_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Get total portfolio value and P&L summary."""
        holdings = self.get_holdings(live_prices)

        total_cost = sum(h.get("total_cost_gbp", 0) for h in holdings)
        total_value = sum(h.get("current_value_gbp", 0) for h in holdings)
        total_unrealised = sum(h.get("unrealised_pnl_gbp", 0) for h in holdings)
        total_realised = sum(
            h.get("realised_pnl_gbp", 0) for h in self.holdings.values()
        )

        return {
            "total_cost_gbp": round(total_cost, 4),
            "total_value_gbp": round(total_value, 4),
            "unrealised_pnl_gbp": round(total_unrealised, 4),
            "realised_pnl_gbp": round(total_realised, 4),
            "total_pnl_gbp": round(total_unrealised + total_realised, 4),
            "active_holdings": len(holdings),
            "total_trades": len(self.trade_log),
        }

    def get_trade_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get full trade log, most recent first."""
        return list(reversed(self.trade_log[-limit:]))

    # ─── Sell Signal Detection ────────────────────────────────

    def check_sell_signals(
        self, live_prices: Dict[str, float], profit_target_pct: float = 20.0
    ) -> List[Dict[str, Any]]:
        """
        Check holdings for sell signals.
        Returns list of holdings that should be considered for selling.
        """
        signals = []
        for sym, h in self.holdings.items():
            if h["quantity"] <= 0:
                continue
            if sym not in live_prices:
                continue

            current_price = live_prices[sym]
            entry = h["avg_entry_price"]
            if entry <= 0:
                continue

            pnl_pct = ((current_price - entry) / entry) * 100

            signal = {
                "symbol": sym,
                "entry_price": entry,
                "current_price": current_price,
                "pnl_pct": round(pnl_pct, 2),
                "quantity": h["quantity"],
                "reason": None,
            }

            if pnl_pct >= profit_target_pct:
                signal["reason"] = f"Profit target hit ({pnl_pct:.1f}% > {profit_target_pct}%)"
                signals.append(signal)
            elif pnl_pct <= -15:
                signal["reason"] = f"Stop loss triggered ({pnl_pct:.1f}% loss)"
                signals.append(signal)

        return signals

    # ─── Persistence ──────────────────────────────────────────

    def _save(self):
        """Save portfolio state to disk."""
        state = {
            "holdings": self.holdings,
            "trade_log": self.trade_log,
            "last_updated": datetime.utcnow().isoformat(),
        }
        try:
            with open(PORTFOLIO_FILE, "w") as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save portfolio: {e}")

    def _load(self):
        """Load portfolio state from disk."""
        if not PORTFOLIO_FILE.exists():
            return
        try:
            with open(PORTFOLIO_FILE) as f:
                state = json.load(f)
            self.holdings = state.get("holdings", {})
            self.trade_log = state.get("trade_log", [])
        except Exception as e:
            logger.error(f"Failed to load portfolio: {e}")


# ─── Singleton ────────────────────────────────────────────────

_tracker: Optional[PortfolioTracker] = None


def get_portfolio_tracker() -> PortfolioTracker:
    """Get or create the singleton portfolio tracker."""
    global _tracker
    if _tracker is None:
        _tracker = PortfolioTracker()
    return _tracker
