"""
Sell-Side Automation
Monitors holdings for exit triggers and automatically proposes sell trades.

Exit triggers (in priority order):
1. Stop-loss (-80% default) — dead-coin safety net, fires immediately regardless of hold period.
2. Partial sell on massive gain (default +300%) — sells a fraction (default 50%) of the position
   once per holding to lock in some profit; the remainder rides on trailing stop + agent recheck.
3. Trailing stop (45% drop from peak, default) — primary lock-in mechanism for normal runs.
4. Agent re-analysis every 12h — fundamental/sentiment check; SELL/AVOID recommendation exits.
5. Hard profit ceiling (SELL_PROFIT_TARGET_PCT, default 9999% = effectively disabled) — last resort.

The flat profit target is intentionally set near-infinite so the system never bails out of a
strong uptrend early. The trailing stop captures most of each run; the partial sell on massive
gains locks in some profit without fully closing a rocket position.
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
        # Hard profit ceiling — set near-infinite so the system never bails early.
        # Primary exits are trailing stop + agent recheck; this is a last-resort cap only.
        self.profit_target_pct = float(os.getenv("SELL_PROFIT_TARGET_PCT", "9999.0"))

        # Partial sell on massive gains — locks in profit without fully closing a rocket.
        # Sells SELL_PARTIAL_FRACTION of the position once per holding when gain hits this %.
        # The remainder rides on trailing stop + agent recheck.
        self.partial_sell_threshold_pct = float(os.getenv("SELL_PARTIAL_THRESHOLD_PCT", "300.0"))
        self.partial_sell_fraction = float(os.getenv("SELL_PARTIAL_FRACTION", "0.5"))

        # -80% default: stop loss is a last resort for genuinely dead coins only.
        # Crypto routinely swings 30-50%; tight stops cause premature full exits.
        # The agent recheck (every 12h) handles deteriorating fundamentals before
        # a coin loses 80%, so this threshold should rarely trigger in practice.
        self.stop_loss_pct = float(os.getenv("SELL_STOP_LOSS_PCT", "-80.0"))
        self.trailing_stop_pct = float(os.getenv("SELL_TRAILING_STOP_PCT", "45.0"))
        self.enable_agent_recheck = os.getenv("SELL_AGENT_RECHECK", "true").lower() in ("1", "true", "yes")
        # 12h recheck keeps close tabs on held positions while scan frequency is reduced.
        # Each recheck = 6 Gemini calls per held coin, so with ~3 holdings = ~18 calls/12h.
        self.recheck_interval_hours = int(os.getenv("SELL_RECHECK_HOURS", "12"))

        # Minimum hold period in hours before profit/trailing triggers fire.
        # Default is 0 (disabled) — the agent decides when to exit. Set via
        # SELL_MIN_HOLD_HOURS env var only if you specifically want a forced hold.
        self.min_hold_hours = float(os.getenv("SELL_MIN_HOLD_HOURS", "0.0"))

        # Track peak prices for trailing stop
        self._peak_prices: Dict[str, float] = {}
        self._last_recheck: Dict[str, str] = {}  # symbol → ISO timestamp
        # Symbols that have already had a partial sell — prevents double-firing
        self._partial_sells_done: set = set()

        self._load_state()

        logger.info(
            f"Sell automation: profit_target={self.profit_target_pct}% (effectively disabled), "
            f"partial_sell={self.partial_sell_threshold_pct}% "
            f"({self.partial_sell_fraction*100:.0f}% of position), "
            f"stop_loss={self.stop_loss_pct}%, trailing_stop={self.trailing_stop_pct}%, "
            f"min_hold={self.min_hold_hours}h (0=disabled), "
            f"agent_recheck={self.enable_agent_recheck}"
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

        # Build set of symbols that already have a pending OR recently failed sell
        # to avoid creating duplicates on every run
        pending_sell_symbols = set()
        for p in engine.proposals.values():
            if p.side != "sell":
                continue
            if p.status == "pending":
                pending_sell_symbols.add(p.symbol)
            elif p.status in ("rejected", "executed") and p.created_at:
                try:
                    created = datetime.fromisoformat(p.created_at)
                    if (datetime.utcnow() - created).total_seconds() < 3600:
                        pending_sell_symbols.add(p.symbol)
                except Exception:
                    pass

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

            # Skip dust positions — not worth selling if below exchange minimum
            holding_value_gbp = current_price * quantity
            if holding_value_gbp < 0.50:
                logger.debug(f"Skipping {symbol}: dust position worth £{holding_value_gbp:.4f}")
                continue

            pnl_pct = ((current_price - entry_price) / entry_price) * 100

            # Calculate hold duration
            first_buy = holding.get("first_buy_at")
            hold_hours = 0.0
            if first_buy:
                try:
                    buy_time = datetime.fromisoformat(first_buy.replace("Z", "+00:00"))
                    hold_hours = (datetime.now(buy_time.tzinfo or None) - buy_time).total_seconds() / 3600
                except Exception:
                    pass

            # Update peak price for trailing stop
            if symbol not in self._peak_prices or current_price > self._peak_prices[symbol]:
                self._peak_prices[symbol] = current_price

            trigger = self._evaluate_exit(symbol, current_price, entry_price, pnl_pct, hold_hours)

            # Skip if there's already a pending sell for this symbol
            if trigger and symbol in pending_sell_symbols:
                logger.info(f"Sell trigger ({trigger['type']}) for {symbol} — already has a pending sell proposal, skipping")
                continue

            # ── Q-learning: checkpoint unrealised P&L for open positions ──
            if not trigger:
                try:
                    from ml.q_learning import get_q_learner
                    ql = get_q_learner()
                    ql.record_unrealised_checkpoint(
                        symbol=symbol,
                        coin_data=holding,
                        pnl_pct=pnl_pct,
                        hold_hours=hold_hours,
                    )
                except Exception:
                    pass

            if trigger:
                # ── Q-learning: record closed position outcome ──
                try:
                    from ml.q_learning import get_q_learner
                    ql = get_q_learner()
                    ql.record_outcome(
                        symbol=symbol,
                        coin_data=holding,
                        action="buy",
                        pnl_pct=pnl_pct,
                        hold_hours=hold_hours,
                        exit_trigger=trigger["type"],
                    )
                except Exception as e:
                    logger.debug(f"Q-learning outcome recording failed: {e}")

                # Partial sell: only sell the configured fraction of the position.
                # Mark done so this fires only once per holding.
                if trigger["type"] == "partial_profit":
                    sell_quantity = quantity * self.partial_sell_fraction
                    self._partial_sells_done.add(symbol)
                    logger.info(
                        f"Partial sell triggered for {symbol}: "
                        f"selling {self.partial_sell_fraction*100:.0f}% "
                        f"({sell_quantity:.6f} of {quantity:.6f}) at +{pnl_pct:.1f}%"
                    )
                else:
                    sell_quantity = quantity

                amount_gbp = current_price * sell_quantity
                result = engine.propose_and_auto_execute(
                    symbol=symbol,
                    side="sell",
                    amount_gbp=amount_gbp,
                    current_price=current_price,
                    reason=trigger["reason"],
                    confidence=trigger["confidence"],
                    recommendation="SELL",
                    sell_quantity=sell_quantity,
                )
                outcome = "auto-executed" if result.get("auto_approved") else "proposed"
                proposals.append({
                    "symbol": symbol,
                    "trigger": trigger["type"],
                    "pnl_pct": round(pnl_pct, 2),
                    "proposal": result,
                })
                logger.info(
                    f"SELL {outcome}: {symbol} — {trigger['type']} "
                    f"(PnL: {pnl_pct:.1f}%, £{amount_gbp:.4f})"
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
        hold_hours: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        """Evaluate a single holding against exit triggers.
        Respects minimum hold period for all triggers except stop-loss."""

        within_hold_period = hold_hours < self.min_hold_hours

        # 1. Stop-loss — always fires regardless of hold period (capital protection)
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

        # Skip profit-taking triggers during minimum hold period
        if within_hold_period:
            return None

        # 2. Partial sell on massive gains — fires once per holding to lock in profit.
        # The remaining position continues to ride on trailing stop + agent recheck.
        if (
            symbol not in self._partial_sells_done
            and pnl_pct >= self.partial_sell_threshold_pct
        ):
            return {
                "type": "partial_profit",
                "reason": (
                    f"Massive gain: {pnl_pct:.1f}% — partial exit "
                    f"({self.partial_sell_fraction * 100:.0f}% of position). "
                    f"Remaining {100 - self.partial_sell_fraction * 100:.0f}% rides on "
                    f"trailing stop + agent recheck. "
                    f"Entry: £{entry_price:.6f} → Current: £{current_price:.6f}"
                ),
                "confidence": 85,
            }

        # 3. Hard profit ceiling (default 9999% — effectively disabled)
        if pnl_pct >= self.profit_target_pct:
            return {
                "type": "profit_target",
                "reason": (
                    f"Hard profit ceiling reached: {pnl_pct:.1f}% gain "
                    f"(ceiling: {self.profit_target_pct}%). "
                    f"Entry: £{entry_price:.6f} → Current: £{current_price:.6f}"
                ),
                "confidence": 85,
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

                    prop = engine.propose_and_auto_execute(
                        symbol=symbol,
                        side="sell",
                        amount_gbp=current_price * quantity,
                        current_price=current_price,
                        reason=f"Agent re-analysis recommends {recommendation}: {result.get('action_plan', 'Exit position')}",
                        confidence=confidence,
                        recommendation="SELL",
                        sell_quantity=quantity,
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
            "partial_sell_threshold_pct": self.partial_sell_threshold_pct,
            "partial_sell_fraction": self.partial_sell_fraction,
            "partial_sells_done": list(self._partial_sells_done),
            "stop_loss_pct": self.stop_loss_pct,
            "trailing_stop_pct": self.trailing_stop_pct,
            "min_hold_hours": self.min_hold_hours,
            "agent_recheck_enabled": self.enable_agent_recheck,
            "recheck_interval_hours": self.recheck_interval_hours,
            "tracked_peaks": {k: round(v, 8) for k, v in self._peak_prices.items()},
            "last_rechecks": self._last_recheck,
        }

    # ─── Persistence ──────────────────────────────────────────

    def _save_state(self):
        import json
        import os
        try:
            SELL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "peak_prices": self._peak_prices,
                "last_recheck": self._last_recheck,
                "partial_sells_done": list(self._partial_sells_done),
            }
            tmp = SELL_STATE_FILE.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump(state, f, indent=2)
            os.replace(tmp, SELL_STATE_FILE)
        except Exception as e:
            logger.error(f"Failed to save sell state: {e}")
            tmp = SELL_STATE_FILE.with_suffix(".tmp")
            if tmp.exists():
                tmp.unlink()

    def _load_state(self):
        import json
        if not SELL_STATE_FILE.exists():
            return
        try:
            with open(SELL_STATE_FILE) as f:
                state = json.load(f)
            self._peak_prices = state.get("peak_prices", {})
            self._last_recheck = state.get("last_recheck", {})
            self._partial_sells_done = set(state.get("partial_sells_done", []))
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
