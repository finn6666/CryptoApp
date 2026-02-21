"""
Sell-Side Automation
Monitors holdings for exit triggers and automatically proposes sell trades.

Exit triggers:
- Profit target hit (configurable, default 20%)
- Stop-loss triggered (configurable, default -15%)
- Trailing stop (locks in gains, default 10% from peak)
- Agent re-analysis recommends SELL/AVOID
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

SELL_STATE_FILE = Path("data/trades/sell_automation_state.json")


class SellAutomation:
    """
    Automated sell-side logic.

    Runs periodically (triggered by scan loop or standalone) to check all
    holdings against exit criteria. When a trigger fires, it proposes a sell
    trade via the TradingEngine's standard approval flow.
    """

    def __init__(self):
        # Exit thresholds (from env or defaults)
        self.profit_target_pct = float(os.getenv("SELL_PROFIT_TARGET_PCT", "20.0"))
        self.stop_loss_pct = float(os.getenv("SELL_STOP_LOSS_PCT", "-15.0"))
        self.trailing_stop_pct = float(os.getenv("SELL_TRAILING_STOP_PCT", "10.0"))
        self.enable_agent_recheck = os.getenv("SELL_AGENT_RECHECK", "true").lower() in ("1", "true", "yes")
        self.recheck_interval_hours = int(os.getenv("SELL_RECHECK_HOURS", "24"))

        # Track peak prices for trailing stop
        self._peak_prices: Dict[str, float] = {}
        self._last_recheck: Dict[str, str] = {}  # symbol → ISO timestamp

        self._load_state()

        logger.info(
            f"Sell automation: profit_target={self.profit_target_pct}%, "
            f"stop_loss={self.stop_loss_pct}%, trailing_stop={self.trailing_stop_pct}%"
        )

    # ─── Main Check ───────────────────────────────────────────

    def check_and_propose_sells(
        self,
        live_prices: Dict[str, float],
        force_agent_recheck: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Check all holdings against exit criteria and propose sells.

        Returns list of proposed sell actions.
        """
        from ml.portfolio_tracker import get_portfolio_tracker
        from ml.trading_engine import get_trading_engine

        tracker = get_portfolio_tracker()
        engine = get_trading_engine()

        if engine.kill_switch:
            logger.info("Sell automation skipped — kill switch active")
            return []

        holdings = tracker.get_holdings(live_prices)
        if not holdings:
            return []

        proposals = []

        for holding in holdings:
            symbol = holding["symbol"]
            if symbol not in live_prices:
                continue

            current_price = live_prices[symbol]
            entry_price = holding.get("avg_entry_price", 0)
            quantity = holding.get("quantity", 0)
            if entry_price <= 0 or quantity <= 0:
                continue

            pnl_pct = ((current_price - entry_price) / entry_price) * 100

            # Update peak price for trailing stop
            if symbol not in self._peak_prices or current_price > self._peak_prices[symbol]:
                self._peak_prices[symbol] = current_price

            trigger = self._evaluate_exit(symbol, current_price, entry_price, pnl_pct)

            if trigger:
                amount_gbp = current_price * quantity
                result = engine.propose_trade(
                    symbol=symbol,
                    side="sell",
                    amount_gbp=amount_gbp,
                    current_price=current_price,
                    reason=trigger["reason"],
                    confidence=trigger["confidence"],
                    recommendation="SELL",
                )
                proposals.append({
                    "symbol": symbol,
                    "trigger": trigger["type"],
                    "pnl_pct": round(pnl_pct, 2),
                    "proposal": result,
                })
                logger.info(
                    f"SELL proposed: {symbol} — {trigger['type']} "
                    f"(PnL: {pnl_pct:.1f}%)"
                )

        # Optionally re-analyse with agents
        if (self.enable_agent_recheck or force_agent_recheck) and holdings:
            agent_sells = self._agent_recheck(holdings, live_prices)
            proposals.extend(agent_sells)

        self._save_state()
        return proposals

    # ─── Exit Evaluation ──────────────────────────────────────

    def _evaluate_exit(
        self,
        symbol: str,
        current_price: float,
        entry_price: float,
        pnl_pct: float,
    ) -> Optional[Dict[str, Any]]:
        """Evaluate a single holding against exit triggers."""

        # 1. Profit target
        if pnl_pct >= self.profit_target_pct:
            return {
                "type": "profit_target",
                "reason": (
                    f"Profit target reached: {pnl_pct:.1f}% gain "
                    f"(target: {self.profit_target_pct}%). "
                    f"Entry: £{entry_price:.6f} → Current: £{current_price:.6f}"
                ),
                "confidence": 85,
            }

        # 2. Stop loss
        if pnl_pct <= self.stop_loss_pct:
            return {
                "type": "stop_loss",
                "reason": (
                    f"Stop-loss triggered: {pnl_pct:.1f}% loss "
                    f"(limit: {self.stop_loss_pct}%). "
                    f"Entry: £{entry_price:.6f} → Current: £{current_price:.6f}"
                ),
                "confidence": 90,
            }

        # 3. Trailing stop
        peak = self._peak_prices.get(symbol, current_price)
        if peak > entry_price:
            drop_from_peak_pct = ((peak - current_price) / peak) * 100
            if drop_from_peak_pct >= self.trailing_stop_pct:
                return {
                    "type": "trailing_stop",
                    "reason": (
                        f"Trailing stop triggered: dropped {drop_from_peak_pct:.1f}% "
                        f"from peak £{peak:.6f} (trail: {self.trailing_stop_pct}%). "
                        f"Current: £{current_price:.6f}"
                    ),
                    "confidence": 80,
                }

        return None

    # ─── Agent Re-analysis ────────────────────────────────────

    def _agent_recheck(
        self,
        holdings: List[Dict],
        live_prices: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """
        Re-analyse held coins with the ADK orchestrator.
        If agents now recommend SELL/AVOID, propose a sell.
        """
        proposals = []
        now = datetime.utcnow()

        for holding in holdings:
            symbol = holding["symbol"]

            # Throttle: only recheck once per interval
            last = self._last_recheck.get(symbol)
            if last:
                elapsed = (now - datetime.fromisoformat(last)).total_seconds() / 3600
                if elapsed < self.recheck_interval_hours:
                    continue

            try:
                import asyncio
                from ml.agents.official.orchestrator import analyze_crypto

                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(
                    analyze_crypto(symbol, coin_data=holding)
                )
                loop.close()

                self._last_recheck[symbol] = now.isoformat()

                recommendation = result.get("recommendation", "").upper()
                if recommendation in ("SELL", "AVOID"):
                    confidence = result.get("confidence", 70)
                    from ml.trading_engine import get_trading_engine
                    engine = get_trading_engine()
                    current_price = live_prices.get(symbol, 0)
                    quantity = holding.get("quantity", 0)

                    prop = engine.propose_trade(
                        symbol=symbol,
                        side="sell",
                        amount_gbp=current_price * quantity,
                        current_price=current_price,
                        reason=f"Agent re-analysis recommends {recommendation}: {result.get('action_plan', 'Exit position')}",
                        confidence=confidence,
                        recommendation="SELL",
                    )
                    proposals.append({
                        "symbol": symbol,
                        "trigger": "agent_recheck",
                        "proposal": prop,
                    })
            except Exception as e:
                logger.debug(f"Agent recheck failed for {symbol}: {e}")

        return proposals

    # ─── Status ───────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return current sell automation status."""
        return {
            "profit_target_pct": self.profit_target_pct,
            "stop_loss_pct": self.stop_loss_pct,
            "trailing_stop_pct": self.trailing_stop_pct,
            "agent_recheck_enabled": self.enable_agent_recheck,
            "recheck_interval_hours": self.recheck_interval_hours,
            "tracked_peaks": {k: round(v, 8) for k, v in self._peak_prices.items()},
            "last_rechecks": self._last_recheck,
        }

    # ─── Persistence ──────────────────────────────────────────

    def _save_state(self):
        import json
        try:
            SELL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "peak_prices": self._peak_prices,
                "last_recheck": self._last_recheck,
            }
            with open(SELL_STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sell state: {e}")

    def _load_state(self):
        import json
        if not SELL_STATE_FILE.exists():
            return
        try:
            with open(SELL_STATE_FILE) as f:
                state = json.load(f)
            self._peak_prices = state.get("peak_prices", {})
            self._last_recheck = state.get("last_recheck", {})
        except Exception as e:
            logger.error(f"Failed to load sell state: {e}")


# ─── Singleton ────────────────────────────────────────────────

_sell_automation: Optional[SellAutomation] = None


def get_sell_automation() -> SellAutomation:
    """Get or create the singleton sell automation."""
    global _sell_automation
    if _sell_automation is None:
        _sell_automation = SellAutomation()
    return _sell_automation
