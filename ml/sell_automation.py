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

import asyncio
import json
import os
import logging
from datetime import datetime
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
        # 12h recheck balances signal quality vs. API cost. With 30+ holdings the
        # 6h default generated 120+ calls/day (~£0.74). At 12h = 60 calls/day (~£0.37).
        # Stop-loss and trailing stop handle urgent exits mechanistically, so 12h
        # agent checks remain sufficient to catch fundamental deterioration.
        self.recheck_interval_hours = int(os.getenv("SELL_RECHECK_HOURS", "12"))
        # Minimum cooldown for sharp-drawdown bypasses — 4h prevents the whole
        # portfolio burning budget in a broad market dip; stop-loss fires immediately
        # at -50% regardless, so 4h is safe.
        self.drawdown_recheck_min_hours = float(os.getenv("SELL_DRAWDOWN_RECHECK_MIN_HOURS", "4.0"))

        # Minimum hold period in hours before ANY sell trigger (except stop-loss) fires.
        # 72h lets positions ride out short-term volatility before evaluating exits.
        self.min_hold_hours = float(os.getenv("SELL_MIN_HOLD_HOURS", "72.0"))

        # Tiered profit-taking: partial sells that let winners run.
        # Tier 1 (75%): take 33% off the table, tighten trailing to 20%.
        # Tier 2 (150%): take 50% of remaining off, tighten trailing to 15%.
        # Full exit via trailing stop or stop-loss only — no nuclear profit cap.
        self.tier1_pct = float(os.getenv("SELL_TIER1_PCT", "75.0"))
        self.tier2_pct = float(os.getenv("SELL_TIER2_PCT", "150.0"))
        self.tier1_fraction = float(os.getenv("SELL_TIER1_FRACTION", "0.33"))
        self.tier2_fraction = float(os.getenv("SELL_TIER2_FRACTION", "0.50"))
        self.tier1_trailing_pct = float(os.getenv("SELL_TIER1_TRAILING_PCT", "20.0"))
        self.tier2_trailing_pct = float(os.getenv("SELL_TIER2_TRAILING_PCT", "15.0"))

        # Track peak prices for trailing stop
        self._peak_prices: Dict[str, float] = {}
        self._last_recheck: Dict[str, str] = {}  # symbol → ISO timestamp
        self._last_drawdown_recheck: Dict[str, str] = {}  # symbol → ISO timestamp (sharp drawdown bypass)
        # Most recent agent conviction from recheck (stored for all outcomes, not just SELLs)
        self._last_recheck_conviction: Dict[str, float] = {}
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
                    cooldown_secs = float(os.getenv("SELL_PROPOSAL_COOLDOWN_HOURS", "4")) * 3600
                    created = datetime.fromisoformat(p.created_at)
                    if (datetime.utcnow() - created).total_seconds() < cooldown_secs:
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
            dust_min_gbp = float(os.getenv("SELL_DUST_MIN_GBP", "0.50"))
            if holding_value_gbp < dust_min_gbp:
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

            trigger = self._evaluate_exit(
                symbol, current_price, entry_price, pnl_pct, hold_hours,
                trade_mode=holding.get("trade_mode", "accumulate"),
            )

            # Skip if there's already a pending/recent proposal for the same trigger type.
            # Tier triggers are also deduplicated via _tiers_taken.
            if trigger:
                pending_for_sym = pending_sell_triggers.get(symbol, set())
                if trigger["type"] in pending_for_sym:
                    logger.info(
                        f"Sell trigger ({trigger['type']}) for {symbol} — already pending, skipping"
                    )
                    trigger = None

            # ── Stagnation exit — check flat positions after extended hold ──
            if not trigger:
                conviction_val = self._last_recheck_conviction.get(symbol)
                stagnation = self._check_stagnation(symbol, pnl_pct, hold_hours, conviction_val, coin_data=holding)
                if stagnation:
                    pending_for_sym = pending_sell_triggers.get(symbol, set())
                    if stagnation["type"] not in pending_for_sym:
                        trigger = stagnation

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

                # ── Pre-check: skip if position is too small to meet exchange minimum ──
                try:
                    from ml.exchange_manager import get_exchange_manager
                    min_gbp = get_exchange_manager().get_min_order_gbp(symbol)
                    if min_gbp > 0 and amount_gbp < min_gbp:
                        logger.info(
                            f"{symbol}: skipping sell — position value £{amount_gbp:.4f} "
                            f"below exchange minimum £{min_gbp:.4f}"
                        )
                        trigger = None
                except Exception:
                    pass

            if trigger:

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
                    sell_quantity=quantity * sell_fraction,
                    trigger_type=trigger["type"],
                )
                # ── Update tier state only if proposal was successfully created ──
                if result.get("success"):
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
        trade_mode: str = "accumulate",
    ) -> Optional[Dict[str, Any]]:
        """Evaluate a single holding against exit triggers.

        Returns a trigger dict with a sell_fraction field (0–1.0).
        sell_fraction < 1.0 means a partial sell; 1.0 means full exit.
        Respects minimum hold period for all triggers except stop-loss.
        """
        effective_min_hold = self.min_hold_hours
        effective_trailing_pct = self.trailing_stop_pct
        effective_tier1_pct = self.tier1_pct

        within_hold_period = hold_hours < effective_min_hold
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
        if pnl_pct >= effective_tier1_pct and 1 not in tiers_taken:
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

        # 4. Trailing stop — use tightened value if we're in runner mode after a tier
        peak = self._peak_prices.get(symbol, current_price)
        trailing_pct = self._tightened_trailing.get(symbol, effective_trailing_pct)
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

    # ─── Stagnation & Drawdown Helpers ────────────────────────

    def _check_stagnation(
        self,
        symbol: str,
        pnl_pct: float,
        hold_hours: float,
        conviction: Optional[float],
        coin_data: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Detect positions going nowhere after an extended hold.

        Two paths:
        1. Fast path (SELL_STAGNATION_EARLY_DAYS, default 7): no agent recheck required.
           Uses CMC weekly price change to detect genuinely flat positions without
           burning Gemini budget. Tight P&L window avoids exiting positions building a base.
        2. Standard path (SELL_STAGNATION_DAYS, default 14): requires prior agent recheck.
           If no recheck has ever run, treats conviction as 0 (no thesis support).

        Returns a trigger dict if criteria are met, else None.
        """
        stagnation_days = float(os.getenv("SELL_STAGNATION_DAYS", "14"))
        pnl_min = float(os.getenv("SELL_STAGNATION_PNL_MIN", "-15.0"))
        pnl_max = float(os.getenv("SELL_STAGNATION_PNL_MAX", "15.0"))
        conviction_max = float(os.getenv("SELL_STAGNATION_CONVICTION_MAX", "50.0"))

        # Fast path: truly flat position at 7 days — no agent API call needed.
        # P&L window is tight (-5% to +10%) to avoid exiting coins building a base.
        early_days = float(os.getenv("SELL_STAGNATION_EARLY_DAYS", "7"))
        early_pnl_min = float(os.getenv("SELL_STAGNATION_EARLY_PNL_MIN", "-5.0"))
        early_pnl_max = float(os.getenv("SELL_STAGNATION_EARLY_PNL_MAX", "10.0"))
        if hold_hours >= early_days * 24 and early_pnl_min <= pnl_pct <= early_pnl_max:
            weekly_drift = (coin_data or {}).get("price_change_7d")
            if weekly_drift is not None:
                try:
                    if abs(float(weekly_drift)) < 8.0:
                        return {
                            "type": "stagnation_exit",
                            "reason": (
                                f"Early stagnation exit: held {hold_hours/24:.1f} days with "
                                f"P&L {pnl_pct:.1f}% and 7d market drift {float(weekly_drift):.1f}% "
                                f"(<8% — no momentum). Capital redeployed to better opportunities."
                            ),
                            "confidence": 68,
                            "sell_fraction": 1.0,
                        }
                except (TypeError, ValueError):
                    pass

        # Standard path: extended hold with low agent conviction.
        # If no recheck has ever run, treat conviction as 0 (no thesis support remaining).
        if hold_hours < stagnation_days * 24:
            return None
        if not (pnl_min <= pnl_pct <= pnl_max):
            return None
        effective_conviction = conviction if conviction is not None else 0.0
        if effective_conviction >= conviction_max:
            return None

        return {
            "type": "stagnation_exit",
            "reason": (
                f"Stagnation exit: held {hold_hours/24:.1f} days with P&L {pnl_pct:.1f}% "
                f"(flat window {pnl_min}% to {pnl_max}%) and agent conviction "
                f"{effective_conviction:.0f}% below threshold {conviction_max}%. "
                f"Capital redeployed to better opportunities."
            ),
            "confidence": 70,
            "sell_fraction": 1.0,
        }

    def _needs_sharp_drawdown_recheck(self, symbol: str, pnl_pct: float) -> bool:
        """
        Returns True if a position has dropped sharply enough to bypass
        the normal recheck throttle. Fires when P&L drops below
        SELL_SHARP_DRAWDOWN_RECHECK_PCT but is still above the stop-loss.
        """
        threshold = float(os.getenv("SELL_SHARP_DRAWDOWN_RECHECK_PCT", "-20.0"))
        return pnl_pct <= threshold and pnl_pct > self.stop_loss_pct

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
        from ml.exchange_manager import get_exchange_manager
        from ml.trading_engine import get_trading_engine
        from ml.agents.official.orchestrator import analyze_crypto
        from services.gemini_budget import get_gemini_budget, BudgetExceededError

        proposals = []
        now = datetime.utcnow()
        exchange_mgr = get_exchange_manager()

        for holding in holdings:
            symbol = holding["symbol"]

            # Throttle: only recheck once per interval (bypass on sharp drawdown)
            last = self._last_recheck.get(symbol)
            if last:
                elapsed = (now - datetime.fromisoformat(last)).total_seconds() / 3600
                if elapsed < self.recheck_interval_hours:
                    pnl_for_sym = holding.get("unrealised_pnl_pct", 0) or 0
                    if not self._needs_sharp_drawdown_recheck(symbol, pnl_for_sym):
                        continue
                    # Enforce a minimum cooldown even for drawdown bypasses to
                    # prevent re-analysing every holding every 5-min monitor tick.
                    last_dd = self._last_drawdown_recheck.get(symbol)
                    if last_dd:
                        dd_elapsed = (now - datetime.fromisoformat(last_dd)).total_seconds() / 3600
                        if dd_elapsed < self.drawdown_recheck_min_hours:
                            continue
                    logger.info(
                        f"{symbol}: bypassing recheck throttle — sharp drawdown "
                        f"({pnl_for_sym:.1f}%)"
                    )
                    self._last_drawdown_recheck[symbol] = now.isoformat()

            try:
                # Pre-check: skip positions too small to sell before spending API budget.
                # Uses the same live price data passed into this method, so no extra I/O.
                _pre_price = live_prices.get(symbol, 0)
                _pre_qty = holding.get("quantity", 0)
                _pre_val = _pre_price * _pre_qty
                if _pre_price > 0:
                    try:
                        _min_gbp = exchange_mgr.get_min_order_gbp(symbol)
                    except Exception:
                        _min_gbp = 1.0
                    if _min_gbp > 0 and _pre_val < _min_gbp:
                        continue
                try:
                    get_gemini_budget().check_and_record("agent_recheck")
                except BudgetExceededError as _be:
                    logger.warning("%s: skipping agent_recheck — Gemini budget exceeded: %s", symbol, _be)
                    continue

                async def _run_recheck():
                    return await asyncio.wait_for(
                        analyze_crypto(symbol, coin_data=holding),
                        timeout=60.0,
                    )

                try:
                    result = asyncio.run(_run_recheck())
                except asyncio.TimeoutError:
                    logger.warning(f"{symbol}: agent recheck timed out after 60s — skipping")
                    continue

                self._last_recheck[symbol] = now.isoformat()

                # analyze_crypto returns a trade_decision dict, not a top-level
                # recommendation string. The top-level "recommendation" field is
                # always "Analysis completed" — never SELL — so we must read the
                # actual trading decision from trade_decision.
                trade_decision = result.get("trade_decision", {})
                # Store conviction for ALL outcomes (HOLD and SELL) so stagnation
                # detection has data even when the agent recommends holding.
                recheck_conviction = trade_decision.get("trade_conviction")
                if recheck_conviction is not None:
                    self._last_recheck_conviction[symbol] = float(recheck_conviction)
                should_sell = (
                    trade_decision.get("should_trade", False)
                    and trade_decision.get("trade_side", "buy").lower() == "sell"
                )
                if should_sell:
                    confidence = trade_decision.get("trade_conviction", 70)
                    reason_text = trade_decision.get("trade_reasoning", "Agent re-analysis recommends exit")
                    engine = get_trading_engine()
                    current_price = live_prices.get(symbol, 0)
                    quantity = holding.get("quantity", 0)
                    amount_gbp = current_price * quantity

                    # Q-learning: record outcome for agent-recommended full exits.
                    # Agent recheck always exits the full position, so this is terminal.
                    try:
                        from ml.q_learning import get_q_learner
                        avg_entry = holding.get("avg_entry_price", 0)
                        pnl_pct = ((current_price - avg_entry) / avg_entry * 100) if avg_entry > 0 else 0
                        first_buy_str = holding.get("first_buy_at", "")
                        hold_hours = 0.0
                        if first_buy_str:
                            first_buy = datetime.fromisoformat(first_buy_str.replace("Z", "+00:00"))
                            hold_hours = (datetime.now(first_buy.tzinfo) - first_buy).total_seconds() / 3600
                        get_q_learner().record_outcome(
                            symbol=symbol,
                            coin_data=holding,
                            action="buy",
                            pnl_pct=pnl_pct,
                            hold_hours=hold_hours,
                            exit_trigger="agent_recheck",
                        )
                    except Exception as _qe:
                        logger.debug(f"Q-learning agent_recheck outcome failed: {_qe}")

                    # Skip if position is too small to meet exchange minimum
                    try:
                        min_gbp = exchange_mgr.get_min_order_gbp(symbol)
                        if min_gbp > 0 and amount_gbp < min_gbp:
                            logger.info(
                                f"{symbol}: skipping agent_recheck sell — position value "
                                f"£{amount_gbp:.4f} below exchange minimum £{min_gbp:.4f}"
                            )
                            continue
                    except Exception:
                        pass

                    # Skip if a sell was recently rejected for this symbol
                    # (e.g. volume minimum not met) — avoid hammering the exchange
                    pending_for_sym: set = set()
                    for p in engine.proposals.values():
                        if p.side == "sell" and p.symbol == symbol and p.created_at:
                            try:
                                cooldown_secs = float(os.getenv("SELL_PROPOSAL_COOLDOWN_HOURS", "4")) * 3600
                                created = datetime.fromisoformat(p.created_at)
                                if (datetime.utcnow() - created).total_seconds() < cooldown_secs:
                                    pending_for_sym.add(p.status)
                            except Exception:
                                pass
                    if "pending" in pending_for_sym or "rejected" in pending_for_sym:
                        logger.info(
                            f"{symbol}: skipping agent_recheck sell — recent proposal still active/rejected"
                        )
                        continue

                    prop = engine.propose_and_auto_execute(
                        symbol=symbol,
                        side="sell",
                        amount_gbp=amount_gbp,
                        current_price=current_price,
                        reason=f"Agent re-analysis recommends SELL: {reason_text}",
                        confidence=confidence,
                        recommendation="SELL",
                        sell_quantity=quantity,
                        trigger_type="agent_recheck",
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
        try:
            SELL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "peak_prices": self._peak_prices,
                "last_recheck": self._last_recheck,
                "last_recheck_conviction": self._last_recheck_conviction,
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
        if not SELL_STATE_FILE.exists():
            return
        try:
            with open(SELL_STATE_FILE) as f:
                state = json.load(f)
            self._peak_prices = state.get("peak_prices", {})
            self._last_recheck = state.get("last_recheck", {})
            self._last_recheck_conviction = state.get("last_recheck_conviction", {})
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
