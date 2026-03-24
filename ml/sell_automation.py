"""
Sell-Side Automation
Monitors holdings for exit triggers and automatically proposes sell trades.

Exit triggers (in priority order):
- Stop-loss (-50%)         — always fires for capital protection, full exit
- Tier 1 profit (75%)      — partial sell (33%), tightens trailing stop to 20%
- Tier 2 profit (150%)     — partial sell (50% of remaining), tightens trailing to 15%
- Trailing stop            — full exit, uses tightened value after tiers fire
- Nuclear profit (300%)    — full exit if position reaches extreme levels
- Agent re-analysis        — full exit if agents recommend SELL/AVOID

All profit/trailing triggers respect a minimum 72h hold period.
Tier thresholds and fractions are configurable via env vars (SELL_TIER1_PCT, etc.).
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
        # Exit thresholds — intentionally wide for crypto volatility.
        # Small-cap coins routinely swing 20-30%/day; tight stops cause premature exits.
        self.stop_loss_pct = float(os.getenv("SELL_STOP_LOSS_PCT", "-50.0"))
        self.trailing_stop_pct = float(os.getenv("SELL_TRAILING_STOP_PCT", "45.0"))
        self.enable_agent_recheck = os.getenv("SELL_AGENT_RECHECK", "true").lower() in ("1", "true", "yes")
        # 12h recheck keeps close tabs on held positions while scan frequency is reduced.
        # Each recheck = 6 Gemini calls per held coin, so with ~3 holdings = ~18 calls/12h.
        self.recheck_interval_hours = int(os.getenv("SELL_RECHECK_HOURS", "12"))

        # Minimum hold period in hours before ANY sell trigger (except stop-loss) fires.
        # 72h lets positions ride out short-term volatility before evaluating exits.
        self.min_hold_hours = float(os.getenv("SELL_MIN_HOLD_HOURS", "72.0"))

        # Tiered profit-taking: partial sells that let winners run.
        # Tier 1 (75%): take 33% off the table, tighten trailing to 20%.
        # Tier 2 (150%): take 50% of remaining off, tighten trailing to 15%.
        # Full exit only via trailing stop, stop-loss, or the nuclear SELL_PROFIT_TARGET_PCT.
        self.tier1_pct = float(os.getenv("SELL_TIER1_PCT", "75.0"))
        self.tier2_pct = float(os.getenv("SELL_TIER2_PCT", "150.0"))
        self.tier1_fraction = float(os.getenv("SELL_TIER1_FRACTION", "0.33"))
        self.tier2_fraction = float(os.getenv("SELL_TIER2_FRACTION", "0.50"))
        self.tier1_trailing_pct = float(os.getenv("SELL_TIER1_TRAILING_PCT", "20.0"))
        self.tier2_trailing_pct = float(os.getenv("SELL_TIER2_TRAILING_PCT", "15.0"))
        # Nuclear full-exit if profit goes extreme (default 300% — very rare, last resort).
        self.profit_target_pct = float(os.getenv("SELL_PROFIT_TARGET_PCT", "300.0"))

        # Track peak prices for trailing stop
        self._peak_prices: Dict[str, float] = {}
        self._last_recheck: Dict[str, str] = {}  # symbol → ISO timestamp
        # Track which profit tiers have already been taken per symbol
        self._tiers_taken: Dict[str, set] = {}
        # Per-symbol trailing stop override (tightens after each tier)
        self._tightened_trailing: Dict[str, float] = {}

        self._load_state()

        logger.info(
            f"Sell automation: tier1={self.tier1_pct}%({self.tier1_fraction*100:.0f}%), "
            f"tier2={self.tier2_pct}%({self.tier2_fraction*100:.0f}%), "
            f"stop_loss={self.stop_loss_pct}%, trailing_stop={self.trailing_stop_pct}%, "
            f"min_hold={self.min_hold_hours}h"
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

        # Build a map of symbol → set of trigger types that are already pending or
        # recently actioned, to avoid duplicate proposals for the same trigger.
        # Tier triggers use _tiers_taken for deduplication, but stop-loss/trailing/
        # full-exit triggers still use this map.
        pending_sell_triggers: Dict[str, set] = {}
        for p in engine.proposals.values():
            if p.side != "sell":
                continue
            sym = p.symbol
            trigger_type = getattr(p, "trigger_type", "unknown")
            if p.status == "pending":
                pending_sell_triggers.setdefault(sym, set()).add(trigger_type)
            elif p.status in ("rejected", "executed") and p.created_at:
                try:
                    created = datetime.fromisoformat(p.created_at)
                    if (datetime.utcnow() - created).total_seconds() < 3600:
                        pending_sell_triggers.setdefault(sym, set()).add(trigger_type)
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

            # Skip if there's already a pending/recent proposal for the same trigger type.
            # Tier triggers are also deduplicated via _tiers_taken.
            if trigger:
                pending_for_sym = pending_sell_triggers.get(symbol, set())
                if trigger["type"] in pending_for_sym:
                    logger.info(
                        f"Sell trigger ({trigger['type']}) for {symbol} — already pending, skipping"
                    )
                    trigger = None

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
                sell_fraction = trigger.get("sell_fraction", 1.0)
                amount_gbp = current_price * quantity * sell_fraction

                # ── Update tier state before proposing ──
                if trigger["type"] == "profit_tier_1":
                    self._tiers_taken.setdefault(symbol, set()).add(1)
                    self._tightened_trailing[symbol] = self.tier1_trailing_pct
                    logger.info(
                        f"{symbol}: Tier 1 taken — trailing stop tightened to {self.tier1_trailing_pct}%"
                    )
                elif trigger["type"] == "profit_tier_2":
                    self._tiers_taken.setdefault(symbol, set()).add(2)
                    self._tightened_trailing[symbol] = self.tier2_trailing_pct
                    logger.info(
                        f"{symbol}: Tier 2 taken — trailing stop tightened to {self.tier2_trailing_pct}%"
                    )
                elif sell_fraction >= 1.0:
                    # Full exit — clear all tier/peak state for this symbol
                    self._tiers_taken.pop(symbol, None)
                    self._tightened_trailing.pop(symbol, None)
                    self._peak_prices.pop(symbol, None)

                # ── Q-learning: record closed position outcome (full exits only) ──
                if sell_fraction >= 1.0:
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

                result = engine.propose_and_auto_execute(
                    symbol=symbol,
                    side="sell",
                    amount_gbp=amount_gbp,
                    current_price=current_price,
                    reason=trigger["reason"],
                    confidence=trigger["confidence"],
                    recommendation="SELL",
                )
                outcome = "auto-executed" if result.get("auto_approved") else "proposed"
                partial_label = f" ({sell_fraction*100:.0f}%)" if sell_fraction < 1.0 else ""
                proposals.append({
                    "symbol": symbol,
                    "trigger": trigger["type"],
                    "pnl_pct": round(pnl_pct, 2),
                    "sell_fraction": sell_fraction,
                    "proposal": result,
                })
                logger.info(
                    f"SELL{partial_label} {outcome}: {symbol} — {trigger['type']} "
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

        Returns a trigger dict with a sell_fraction field (0–1.0).
        sell_fraction < 1.0 means a partial sell; 1.0 means full exit.
        Respects minimum hold period for all triggers except stop-loss.
        """

        within_hold_period = hold_hours < self.min_hold_hours
        tiers_taken = self._tiers_taken.get(symbol, set())

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
                "sell_fraction": 1.0,
            }

        # Skip profit-taking triggers during minimum hold period
        if within_hold_period:
            return None

        # 2. Tier 1 — first partial take-profit, then switch to tighter trailing
        if pnl_pct >= self.tier1_pct and 1 not in tiers_taken:
            return {
                "type": "profit_tier_1",
                "reason": (
                    f"Tier 1 profit: {pnl_pct:.1f}% gain — taking {self.tier1_fraction*100:.0f}% off the table, "
                    f"tightening trailing stop to {self.tier1_trailing_pct}% to let the rest run. "
                    f"Entry: £{entry_price:.6f} → Current: £{current_price:.6f}"
                ),
                "confidence": 82,
                "sell_fraction": self.tier1_fraction,
            }

        # 3. Tier 2 — second partial take-profit, tighten trailing further
        if pnl_pct >= self.tier2_pct and 2 not in tiers_taken:
            return {
                "type": "profit_tier_2",
                "reason": (
                    f"Tier 2 profit: {pnl_pct:.1f}% gain — taking {self.tier2_fraction*100:.0f}% of remaining off, "
                    f"tightening trailing stop to {self.tier2_trailing_pct}%. "
                    f"Entry: £{entry_price:.6f} → Current: £{current_price:.6f}"
                ),
                "confidence": 84,
                "sell_fraction": self.tier2_fraction,
            }

        # 4. Nuclear full exit — extreme profit level (last resort, default 300%)
        if pnl_pct >= self.profit_target_pct:
            return {
                "type": "profit_target",
                "reason": (
                    f"Extreme profit target reached: {pnl_pct:.1f}% gain "
                    f"(target: {self.profit_target_pct}%). Full exit. "
                    f"Entry: £{entry_price:.6f} → Current: £{current_price:.6f}"
                ),
                "confidence": 85,
                "sell_fraction": 1.0,
            }

        # 5. Trailing stop — use tightened value if we're in runner mode after a tier
        peak = self._peak_prices.get(symbol, current_price)
        trailing_pct = self._tightened_trailing.get(symbol, self.trailing_stop_pct)
        if peak > entry_price:
            drop_from_peak_pct = ((peak - current_price) / peak) * 100
            if drop_from_peak_pct >= trailing_pct:
                return {
                    "type": "trailing_stop",
                    "reason": (
                        f"Trailing stop triggered: dropped {drop_from_peak_pct:.1f}% "
                        f"from peak £{peak:.6f} (trail: {trailing_pct}%). "
                        f"Current: £{current_price:.6f}"
                    ),
                    "confidence": 80,
                    "sell_fraction": 1.0,
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
            "tier1_pct": self.tier1_pct,
            "tier1_fraction": self.tier1_fraction,
            "tier1_trailing_pct": self.tier1_trailing_pct,
            "tier2_pct": self.tier2_pct,
            "tier2_fraction": self.tier2_fraction,
            "tier2_trailing_pct": self.tier2_trailing_pct,
            "profit_target_pct": self.profit_target_pct,
            "stop_loss_pct": self.stop_loss_pct,
            "trailing_stop_pct": self.trailing_stop_pct,
            "min_hold_hours": self.min_hold_hours,
            "agent_recheck_enabled": self.enable_agent_recheck,
            "recheck_interval_hours": self.recheck_interval_hours,
            "tracked_peaks": {k: round(v, 8) for k, v in self._peak_prices.items()},
            "tiers_taken": {k: sorted(v) for k, v in self._tiers_taken.items()},
            "tightened_trailing": self._tightened_trailing,
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
                "tiers_taken": {k: list(v) for k, v in self._tiers_taken.items()},
                "tightened_trailing": self._tightened_trailing,
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
            self._tiers_taken = {
                k: set(v) for k, v in state.get("tiers_taken", {}).items()
            }
            self._tightened_trailing = state.get("tightened_trailing", {})
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
