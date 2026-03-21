"""
Live Trading Engine with Safety Rails
Executes real trades on Kraken via ccxt with strict daily budget limits
and email-based approval workflow.
"""

import os
import json
import uuid
import math
import logging
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

logger = logging.getLogger(__name__)

# ─── Data Models ───────────────────────────────────────────────

@dataclass
class TradeProposal:
    """A proposed trade awaiting approval."""
    id: str
    symbol: str
    side: str  # "buy" or "sell"
    amount_gbp: float  # how much GBP to spend
    price_at_proposal: float
    reason: str  # agent's explanation
    confidence: int  # 0-100
    agent_recommendation: str  # BUY/SELL/HOLD
    coin_name: str = ""  # human-readable name (e.g. "Vaulta")
    created_at: str = ""
    status: str = "pending"  # pending / approved / rejected / executed / expired
    executed_at: Optional[str] = None
    execution_price: Optional[float] = None
    quantity: Optional[float] = None
    order_id: Optional[str] = None
    error: Optional[str] = None
    sell_quantity: Optional[float] = None  # Exact coin qty to sell (bypasses amount→qty reconversion)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class DailyBudget:
    """Track daily spending (buys and sells tracked separately)."""
    date: str
    spent_gbp: float = 0.0  # buy-side spend only
    trades_executed: int = 0
    trades_proposed: int = 0
    sell_proceeds_gbp: float = 0.0  # sell-side total
    sells_executed: int = 0
    fees_gbp: float = 0.0  # total exchange fees paid


# ─── Trading Engine ───────────────────────────────────────────

class TradingEngine:
    """
    Core trading engine with safety limits and email approval.
    
    Safety features:
    - Hard daily spend limit (from DAILY_TRADE_BUDGET_GBP env var)
    - Per-trade max (never exceed daily limit in one trade)
    - Email approval required before execution
    - Proposals expire after 1 hour
    - All trades logged to disk
    - Kill switch to halt all trading
    """

    def __init__(
        self,
        daily_budget_gbp: float = None,
        exchange_id: str = None,
        data_dir: str = "data/trades",
        server_url: str = "http://localhost:5001",
    ):
        if daily_budget_gbp is None:
            daily_budget_gbp = float(os.getenv("DAILY_TRADE_BUDGET_GBP", "3.00"))
        self.daily_budget_gbp = daily_budget_gbp
        # Default exchange from env
        self.exchange_id = exchange_id or os.getenv("EXCHANGE_PRIORITY", "kraken").split(",")[0].strip()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.server_url = server_url

        # State
        self.proposals: Dict[str, TradeProposal] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self.daily_budgets: Dict[str, DailyBudget] = {}
        self.kill_switch = False  # Emergency stop

        # Safety: max single trade = 50% of daily budget
        self.max_trade_pct = float(os.getenv("MAX_TRADE_PCT", "50")) / 100
        # Minimum useful budget: if remaining is below this, treat as exhausted.
        # Most exchanges have a minimum order of ~£0.50, so anything below that
        # will always fail.  Default 0.50 — override via env if your exchange
        # has a different floor.
        self.min_useful_budget_gbp = float(os.getenv("MIN_USEFUL_BUDGET_GBP", "0.50"))
        # Cooldown: minimum minutes between proposals (per-side)
        self.trade_cooldown_min = int(os.getenv("TRADE_COOLDOWN_MIN", "60"))
        self._last_buy_proposal_time: Optional[datetime] = None
        self._last_sell_proposal_time: Optional[datetime] = None

        # Email config (from env)
        self.email_to = os.getenv("TRADE_NOTIFICATION_EMAIL", "")
        if not self.email_to:
            logger.warning("⚠️  TRADE_NOTIFICATION_EMAIL not set — trade approval emails will not be sent")
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")  # Gmail app password
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))

        # Buy-side auto-approve: buys within budget execute immediately
        self.buy_auto_approve = os.getenv(
            "BUY_AUTO_APPROVE", "true"
        ).lower() in ("1", "true", "yes")
        if self.buy_auto_approve:
            logger.info("🤖 Buy-side: auto-approve ENABLED — buys within budget execute immediately")

        # Sell-side control
        self.sell_require_approval = os.getenv(
            "SELL_REQUIRE_APPROVAL", "false"
        ).lower() in ("1", "true", "yes")
        if self.sell_require_approval:
            logger.info("🔒 Sell-side: manual approval REQUIRED for ALL sells")
        else:
            logger.info("🤖 Sell-side: auto-approve ENABLED for all sells")

        # Manual approval threshold: trades above this amount always require approval
        self.approval_threshold_gbp = float(os.getenv("APPROVAL_THRESHOLD_GBP", "50.0"))

        # Exchange (lazy init — prefers ExchangeManager for multi-exchange)
        self._exchange = None

        # Token signing for approve/reject links
        secret = os.getenv('SECRET_KEY')
        if not secret:
            logger.error('SECRET_KEY not set — trade approval tokens will be insecure!')
            secret = os.urandom(32).hex()  # random per-instance; tokens won't survive restarts
        self._serializer = URLSafeTimedSerializer(secret, salt='trade-approval')

        # Load persisted state
        self._load_state()

        logger.info(
            f"Trading engine initialized: budget=£{daily_budget_gbp}/day, "
            f"exchange={exchange_id}, email={self.email_to}"
        )
        logger.info(
            f"Safety: max_trade={self.max_trade_pct*100:.0f}% of budget, "
            f"cooldown={self.trade_cooldown_min}min between proposals"
        )

    # ─── Exchange Connection ──────────────────────────────────

    def _get_exchange(self):
        """Lazy-initialize exchange connection via ExchangeManager (multi-exchange)."""
        if self._exchange is None:
            try:
                from ml.exchange_manager import get_exchange_manager
                mgr = get_exchange_manager()
                self._exchange = mgr.get_exchange(self.exchange_id)
                if self._exchange:
                    logger.info(f"{self.exchange_id} exchange connected via ExchangeManager")
                    return self._exchange
            except Exception as e:
                logger.debug(f"ExchangeManager fallback: {e}")

            # Fallback: direct ccxt connection
            try:
                import ccxt

                config = {}
                if self.exchange_id == "kraken":
                    config = {
                        "apiKey": os.getenv("KRAKEN_API_KEY", ""),
                        "secret": os.getenv("KRAKEN_PRIVATE_KEY", ""),
                    }

                if not config.get("apiKey") or not config.get("secret"):
                    logger.warning(f"Exchange API keys not configured for {self.exchange_id} — trades will fail")

                exchange_class = getattr(ccxt, self.exchange_id)
                self._exchange = exchange_class({
                    **config,
                    "enableRateLimit": True,
                })
                self._exchange.load_markets()
                logger.info(f"{self.exchange_id} exchange connected directly via ccxt")
            except ImportError:
                logger.error("ccxt not installed — run: pip install ccxt")
                raise
            except Exception as e:
                logger.error(f"Exchange connection failed: {e}")
                raise
        return self._exchange

    # ─── Budget Tracking ──────────────────────────────────────

    def _get_today_budget(self) -> DailyBudget:
        """Get or create today's budget tracker."""
        today = date.today().isoformat()
        if today not in self.daily_budgets:
            self.daily_budgets[today] = DailyBudget(date=today)
        return self.daily_budgets[today]

    def get_remaining_budget(self) -> float:
        """How much GBP is left to spend today."""
        budget = self._get_today_budget()
        return max(0, self.daily_budget_gbp - budget.spent_gbp)

    def is_budget_exhausted(self) -> bool:
        """True when remaining budget is too small for any practical trade."""
        return self.get_remaining_budget() < self.min_useful_budget_gbp

    def can_afford_trade(self, amount_gbp: float, side: str = "buy") -> bool:
        """Check if a trade fits within today's budget. Sells are always affordable."""
        if self.kill_switch:
            return False
        if side == "sell":
            return True  # Sells don't consume buy budget
        remaining = self.get_remaining_budget()
        if remaining < self.min_useful_budget_gbp:
            return False
        return amount_gbp <= remaining

    # ─── Trade Proposal ───────────────────────────────────────

    def propose_trade(
        self,
        symbol: str,
        side: str,
        amount_gbp: float,
        current_price: float,
        reason: str,
        confidence: int,
        recommendation: str,
        coin_name: str = "",
        sell_quantity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Create a trade proposal and send approval email.
        
        Returns dict with proposal status.
        """
        if self.kill_switch:
            return {"success": False, "error": "Trading is halted (kill switch active)"}

        is_sell = side.lower() == "sell"

        # Budget checks only apply to buys — sells don't consume buy budget
        if not is_sell:
            remaining = self.get_remaining_budget()
            if remaining < self.min_useful_budget_gbp:
                return {
                    "success": False,
                    "error": (
                        f"Daily budget effectively exhausted "
                        f"(£{remaining:.4f} remaining, minimum useful £{self.min_useful_budget_gbp:.2f})"
                    ),
                }

            if amount_gbp > remaining:
                amount_gbp = remaining
                logger.info(f"Capped trade to remaining budget: £{amount_gbp:.4f}")

            # Hard cap — never exceed daily budget in a single trade
            amount_gbp = min(amount_gbp, self.daily_budget_gbp)

            # Safety: cap single trade to max_trade_pct of daily budget
            max_single = self.daily_budget_gbp * self.max_trade_pct
            if amount_gbp > max_single:
                amount_gbp = max_single
                logger.info(f"Capped trade to max single trade: £{amount_gbp:.4f}")

            # Enforce exchange minimum order size — bump up if needed
            min_order_gbp = self._get_min_order_gbp(symbol)
            if min_order_gbp > 0 and amount_gbp < min_order_gbp:
                if min_order_gbp <= remaining:
                    logger.info(
                        f"Bumping trade from £{amount_gbp:.4f} to exchange minimum £{min_order_gbp:.4f}"
                    )
                    amount_gbp = min_order_gbp
                else:
                    return {
                        "success": False,
                        "error": (
                            f"Trade amount £{amount_gbp:.4f} below exchange minimum £{min_order_gbp:.4f} "
                            f"and remaining budget £{remaining:.4f} cannot cover it"
                        ),
                    }

        # Per-side cooldown check (buys and sells have independent cooldowns)
        last_time = self._last_sell_proposal_time if is_sell else self._last_buy_proposal_time
        if last_time:
            elapsed = (datetime.utcnow() - last_time).total_seconds() / 60
            if elapsed < self.trade_cooldown_min:
                remaining_min = self.trade_cooldown_min - elapsed
                return {
                    "success": False,
                    "error": f"{'Sell' if is_sell else 'Buy'} cooldown active — wait {remaining_min:.0f} more minutes",
                }

        # Reject if no valid price (can happen if coin data has price=None)
        if not current_price or current_price <= 0:
            return {
                "success": False,
                "error": f"No valid price for {symbol} — cannot propose trade",
            }

        # Use 4dp rounding to avoid tiny amounts becoming £0.00
        rounded_amount = round(amount_gbp, 4)
        if rounded_amount < 0.01:
            return {
                "success": False,
                "error": f"Trade amount too small (£{amount_gbp:.6f}) — dust position",
            }

        proposal = TradeProposal(
            id=uuid.uuid4().hex[:12],
            symbol=symbol.upper(),
            side=side.lower(),
            amount_gbp=rounded_amount,
            price_at_proposal=current_price,
            reason=reason,
            confidence=confidence,
            agent_recommendation=recommendation,
            coin_name=coin_name,
            sell_quantity=sell_quantity,
        )

        self.proposals[proposal.id] = proposal
        if proposal.side == "sell":
            self._last_sell_proposal_time = datetime.utcnow()
        else:
            self._last_buy_proposal_time = datetime.utcnow()

        # Update daily counter
        budget = self._get_today_budget()
        budget.trades_proposed += 1

        # Send approval email only when manual approval is needed.
        # Auto-approved trades skip this — the execution email covers it.
        will_auto_approve = False
        if is_sell:
            will_auto_approve = not self.sell_require_approval
        else:
            will_auto_approve = self.buy_auto_approve

        email_sent = False
        if not will_auto_approve:
            email_sent = self._send_approval_email(proposal)

        self._save_state()

        return {
            "success": True,
            "proposal_id": proposal.id,
            "symbol": symbol,
            "side": side,
            "amount_gbp": proposal.amount_gbp,
            "price": current_price,
            "email_sent": email_sent,
        }

    # ─── Auto-Approve ────────────────────────────────────────

    def propose_and_auto_execute(
        self,
        symbol: str,
        side: str,
        amount_gbp: float,
        current_price: float,
        reason: str,
        confidence: int,
        recommendation: str,
        coin_name: str = "",
        sell_quantity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Propose a trade and, if auto-approve is enabled for that side,
        immediately approve and execute it.  Falls back to the normal
        email-approval flow when auto-approve is off.

        Sells auto-execute unless SELL_REQUIRE_APPROVAL is set.
        """
        result = self.propose_trade(
            symbol=symbol,
            side=side,
            amount_gbp=amount_gbp,
            current_price=current_price,
            reason=reason,
            confidence=confidence,
            recommendation=recommendation,
            coin_name=coin_name,
            sell_quantity=sell_quantity,
        )

        if not result.get("success"):
            return result

        proposal_id = result["proposal_id"]
        is_sell = side.lower() == "sell"

        # Determine whether to auto-approve this trade
        should_auto = False
        if is_sell:
            should_auto = not self.sell_require_approval
        else:
            # Buys: honour existing buy_auto_approve flag
            should_auto = self.buy_auto_approve

        # Override: trades above approval threshold always require manual approval
        if amount_gbp > self.approval_threshold_gbp:
            logger.info(
                f"Trade £{amount_gbp:.2f} exceeds approval threshold "
                f"£{self.approval_threshold_gbp:.2f} — requiring manual approval"
            )
            should_auto = False

        if not should_auto:
            return result  # normal email-approval flow

        # Auto-approve: execute immediately
        side_label = "SELL" if is_sell else "BUY"
        logger.info(
            f"🤖 Auto-approving {side_label} {symbol} £{amount_gbp:.4f} "
            f"(confidence {confidence}%)"
        )
        exec_result = self.approve_trade(proposal_id)
        exec_result["auto_approved"] = True
        return exec_result

    # ─── Approval / Rejection ─────────────────────────────────

    def approve_trade(self, proposal_id: str) -> Dict[str, Any]:
        """Approve and execute a pending trade."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return {"success": False, "error": "Proposal not found"}

        if proposal.status != "pending":
            return {"success": False, "error": f"Proposal already {proposal.status}"}

        # Check if expired (1 hour)
        created = datetime.fromisoformat(proposal.created_at)
        if datetime.utcnow() - created > timedelta(hours=1):
            proposal.status = "expired"
            self._save_state()
            return {"success": False, "error": "Proposal expired (>1 hour old)"}

        # Check budget again (might have been spent since proposal) — only for buys
        if not self.can_afford_trade(proposal.amount_gbp, side=proposal.side):
            proposal.status = "rejected"
            proposal.error = "Budget exhausted since proposal"
            self._save_state()
            return {"success": False, "error": "Daily budget now exhausted"}

        # Execute!
        proposal.status = "approved"
        result = self._execute_trade(proposal)

        self._save_state()
        return result

    def reject_trade(self, proposal_id: str) -> Dict[str, Any]:
        """Reject a pending trade."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return {"success": False, "error": "Proposal not found"}

        if proposal.status != "pending":
            return {"success": False, "error": f"Proposal already {proposal.status}"}

        proposal.status = "rejected"
        self._save_state()

        return {"success": True, "proposal_id": proposal_id, "status": "rejected"}

    # ─── Trade Execution ──────────────────────────────────────

    def _execute_trade(self, proposal: TradeProposal) -> Dict[str, Any]:
        """Execute a trade using multi-exchange routing (ExchangeManager → fallback to legacy)."""
        try:
            # Try multi-exchange routing first
            exchange_used = self.exchange_id
            order_result = self._execute_via_exchange_manager(proposal)

            if order_result:
                proposal.status = "executed"
                proposal.executed_at = datetime.utcnow().isoformat()
                proposal.execution_price = order_result.get("price") or proposal.price_at_proposal or 0
                proposal.quantity = order_result.get("quantity") or 0
                proposal.order_id = order_result.get("order_id") or "unknown"
                exchange_used = order_result.get("exchange") or self.exchange_id

                # Fallback: if quantity still 0, calculate from amount/price
                if not proposal.quantity and proposal.execution_price and proposal.execution_price > 0:
                    proposal.quantity = proposal.amount_gbp / proposal.execution_price
                    logger.warning(
                        f"Quantity was 0 from exchange — calculated fallback: "
                        f"{(proposal.quantity or 0):.8f} from £{proposal.amount_gbp:.4f} / £{(proposal.execution_price or 0):.6f}"
                    )
            else:
                # Fallback to legacy single-exchange
                exchange = self._get_exchange()
                symbol_pair = self._find_market_pair(proposal.symbol)
                if not symbol_pair:
                    proposal.status = "rejected"
                    proposal.error = f"No trading pair found for {proposal.symbol}"
                    return {"success": False, "error": proposal.error}

                ticker = exchange.fetch_ticker(symbol_pair)
                current_price = ticker.get("last") or ticker.get("close") or 0
                if not current_price:
                    proposal.status = "rejected"
                    proposal.error = f"No current price for {symbol_pair} (ticker returned None)"
                    return {"success": False, "error": proposal.error}

                # FX conversion: if pair isn't GBP-quoted, convert amount
                quote_currency = symbol_pair.split("/")[1] if "/" in symbol_pair else "GBP"
                amount_in_quote = proposal.amount_gbp
                if quote_currency != "GBP":
                    # Approximate GBP → quote conversion
                    approx_fx = {"USD": 1.27, "USDT": 1.27, "USDC": 1.27, "EUR": 1.17}
                    fx_rate = approx_fx.get(quote_currency, 1.27)
                    amount_in_quote = proposal.amount_gbp * fx_rate
                    logger.info(f"Legacy FX: £{proposal.amount_gbp:.4f} → {amount_in_quote:.4f} {quote_currency} (rate {fx_rate})")

                if proposal.side == "sell" and proposal.sell_quantity:
                    # For sells: use the explicit coin qty to avoid price-drift errors
                    quantity = proposal.sell_quantity
                    logger.info(f"Legacy sell: using explicit quantity {quantity:.8f} {proposal.symbol}")
                else:
                    quantity = amount_in_quote / current_price

                # Enforce exchange minimum order quantity (buy-side only)
                if proposal.side != "sell":
                    try:
                        market = exchange.market(symbol_pair)
                        min_qty = (market.get("limits", {}).get("amount", {}).get("min", 0) or 0)
                        min_cost = (market.get("limits", {}).get("cost", {}).get("min", 0) or 0)
                        if min_qty and quantity < min_qty:
                            quantity = min_qty * 1.02  # 2% buffer
                            logger.info(f"Legacy: bumped quantity to min {quantity:.8f} (min={min_qty:.8f})")
                        if min_cost and (quantity * current_price) < min_cost:
                            quantity = (min_cost * 1.02) / current_price
                            logger.info(f"Legacy: bumped quantity to meet cost min {min_cost:.4f}")
                    except Exception as e:
                        logger.debug(f"Could not check min order for {symbol_pair}: {e}")

                if proposal.side == "buy":
                    order = exchange.create_market_buy_order(symbol_pair, quantity)
                else:
                    order = exchange.create_market_sell_order(symbol_pair, quantity)

                proposal.status = "executed"
                proposal.executed_at = datetime.utcnow().isoformat()
                proposal.execution_price = order.get("average") or current_price or 0
                proposal.quantity = order.get("filled") or quantity or 0
                proposal.order_id = order.get("id", "unknown")

            # Extract fee info from order result
            fee_gbp = 0.0
            if order_result:
                fee_gbp = order_result.get("fee_gbp", 0.0)

            # Update daily budget — buys consume budget, sells track separately
            budget = self._get_today_budget()
            if proposal.side == "buy":
                budget.spent_gbp += proposal.amount_gbp
            else:
                budget.sell_proceeds_gbp += proposal.amount_gbp
                budget.sells_executed += 1
            budget.trades_executed += 1
            budget.fees_gbp += fee_gbp

            # Log trade to history
            trade_record = {
                "proposal_id": proposal.id,
                "symbol": proposal.symbol,
                "side": proposal.side,
                "amount_gbp": proposal.amount_gbp,
                "quantity": proposal.quantity,
                "price": proposal.execution_price,
                "order_id": proposal.order_id,
                "reason": proposal.reason,
                "confidence": proposal.confidence,
                "timestamp": proposal.executed_at,
                "exchange": exchange_used,
                "fee_gbp": fee_gbp,
            }
            self.trade_history.append(trade_record)

            # Auto-record to portfolio tracker
            self._record_to_portfolio(proposal, exchange_used, fee_gbp=fee_gbp)

            # Send confirmation email
            self._send_execution_email(proposal)

            logger.info(
                f"TRADE EXECUTED: {proposal.side.upper()} {(proposal.quantity or 0):.6f} "
                f"{proposal.symbol} @ £{(proposal.execution_price or 0):.6f} "
                f"(£{proposal.amount_gbp:.4f}) on {exchange_used}"
            )

            # Write to shared audit log for Activity Log UI
            self._write_audit("trade_executed", {
                "symbol": proposal.symbol,
                "side": proposal.side,
                "amount_gbp": round(proposal.amount_gbp, 2),
                "price": proposal.execution_price,
                "exchange": exchange_used,
                "confidence": proposal.confidence,
            })

            return {
                "success": True,
                "proposal_id": proposal.id,
                "order_id": proposal.order_id,
                "side": proposal.side,
                "symbol": proposal.symbol,
                "quantity": proposal.quantity,
                "price": proposal.execution_price,
                "amount_gbp": proposal.amount_gbp,
                "exchange": exchange_used,
            }

        except Exception as e:
            proposal.status = "rejected"
            proposal.error = str(e)
            logger.error(f"Trade execution failed: {e}")

            # Write to shared audit log for Activity Log UI
            self._write_audit("trade_failed", {
                "symbol": proposal.symbol,
                "side": proposal.side,
                "amount_gbp": round(proposal.amount_gbp, 2),
                "error": str(e),
                "confidence": proposal.confidence,
            })

            # Notify by email so the user knows about the failure
            self._send_failure_email(proposal, str(e))

            return {"success": False, "error": str(e)}

    def _write_audit(self, event: str, data: Dict[str, Any]):
        """Append an event to the shared audit log (JSONL) for the Activity Log UI."""
        from pathlib import Path
        import json as _json
        audit_file = Path("data/trades/audit_log.jsonl")
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event,
            **data,
        }
        try:
            audit_file.parent.mkdir(parents=True, exist_ok=True)
            with open(audit_file, "a") as f:
                f.write(_json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def _execute_via_exchange_manager(self, proposal: TradeProposal) -> Optional[Dict[str, Any]]:
        """Try executing via the multi-exchange manager.
        
        Returns the result dict on success, raises on insufficient funds
        (so the caller doesn't fall through to the legacy path), or
        returns None when the manager is unavailable.
        """
        try:
            from ml.exchange_manager import get_exchange_manager
            mgr = get_exchange_manager()
            remaining = self.get_remaining_budget() if proposal.side == "buy" else None
            result = mgr.execute_order(
                symbol=proposal.symbol,
                side=proposal.side,
                amount_gbp=proposal.amount_gbp,
                max_amount_gbp=remaining,
                quantity=proposal.sell_quantity,
            )
            if result.get("success"):
                return result
            # If the exchange explicitly rejected (balance/budget), propagate
            # instead of falling through to legacy which would just fail again.
            error = result.get("error", "")
            if "nsufficient" in error or "budget" in error or "minimum" in error:
                raise RuntimeError(error)
            return None
        except RuntimeError:
            raise  # re-raise our own insufficient-funds errors
        except Exception as e:
            logger.debug(f"Exchange manager not available, using legacy: {e}")
            return None

    def _record_to_portfolio(self, proposal: TradeProposal, exchange: str, fee_gbp: float = 0.0):
        """Auto-record executed trade to portfolio tracker."""
        try:
            from ml.portfolio_tracker import get_portfolio_tracker
            tracker = get_portfolio_tracker()
            tracker.record_trade(
                symbol=proposal.symbol,
                side=proposal.side,
                quantity=proposal.quantity or 0,
                price=proposal.execution_price or proposal.price_at_proposal or 0,
                amount_gbp=proposal.amount_gbp,
                exchange=exchange,
                order_id=proposal.order_id or "",
                reasoning=proposal.reason,
                confidence=proposal.confidence,
                proposal_id=proposal.id,
                fee_gbp=fee_gbp,
                coin_name=proposal.coin_name or "",
            )
        except Exception as e:
            logger.error(f"Failed to record trade to portfolio: {e}")

    def _find_market_pair(self, symbol: str) -> Optional[str]:
        """Find a valid trading pair for a symbol on the exchange."""
        exchange = self._get_exchange()
        # Try GBP pair first, then USD, then USDT
        for quote in ["GBP", "USD", "USDT"]:
            pair = f"{symbol}/{quote}"
            if pair in exchange.markets:
                return pair
        return None

    def _get_min_order_gbp(self, symbol: str) -> float:
        """
        Get the minimum order size in GBP for a symbol.
        Tries ExchangeManager first (live data), falls back to exchange direct query.
        Returns 0 if unknown.
        """
        try:
            from ml.exchange_manager import get_exchange_manager
            mgr = get_exchange_manager()
            return mgr.get_min_order_gbp(symbol)
        except Exception:
            pass

        # Fallback: query the exchange directly
        try:
            exchange = self._get_exchange()
            pair = self._find_market_pair(symbol)
            if not pair:
                return 0

            market = exchange.market(pair)
            ticker = exchange.fetch_ticker(pair)
            price = ticker.get("last") or ticker.get("close") or 0
            if not price:
                return 0

            quote = pair.split("/")[1] if "/" in pair else "GBP"
            approx_fx = {"USD": 1.27, "USDT": 1.27, "USDC": 1.27, "EUR": 1.17}
            fx_rate = approx_fx.get(quote, 1.0) if quote != "GBP" else 1.0

            min_qty = (market.get("limits", {}).get("amount", {}).get("min", 0) or 0)
            min_cost = (market.get("limits", {}).get("cost", {}).get("min", 0) or 0)

            min_gbp_qty = (min_qty * price / fx_rate) if min_qty else 0
            min_gbp_cost = (min_cost / fx_rate) if min_cost else 0

            min_gbp = max(min_gbp_qty, min_gbp_cost)
            if min_gbp > 0:
                min_gbp *= 1.05  # 5% safety buffer
            return round(min_gbp, 2)
        except Exception as e:
            logger.debug(f"Could not determine min order GBP for {symbol}: {e}")
            return 0

    # ─── Token Signing ─────────────────────────────────────────

    def sign_proposal_token(self, proposal_id: str, action: str) -> str:
        """Create a signed token for approve/reject links (HMAC, 1-hour expiry)."""
        return self._serializer.dumps({'id': proposal_id, 'action': action})

    def verify_proposal_token(self, token: str, max_age: int = 3600) -> Dict[str, str]:
        """Verify a signed proposal token. Returns {'id': ..., 'action': ...} or raises."""
        return self._serializer.loads(token, max_age=max_age)

    # ─── Email Notifications ──────────────────────────────────

    def _send_approval_email(self, proposal: TradeProposal) -> bool:
        """Send trade approval email with signed approve/reject links."""
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP not configured — skipping approval email")
            return False

        approve_token = self.sign_proposal_token(proposal.id, 'approve')
        reject_token = self.sign_proposal_token(proposal.id, 'reject')
        approve_url = f"{self.server_url}/api/trades/confirm/{approve_token}"
        reject_url = f"{self.server_url}/api/trades/confirm/{reject_token}"

        subject = f"{'[SELL]' if proposal.side == 'sell' else '[Trade]'} Proposal: {proposal.side.upper()} {proposal.symbol}{' (' + proposal.coin_name + ')' if proposal.coin_name else ''} - GBP {proposal.amount_gbp:.4f}"

        is_sell = proposal.side == "sell"
        header_gradient = "linear-gradient(90deg, #e53e3e, #c53030)" if is_sell else "linear-gradient(90deg, #667eea, #764ba2)"
        display_name = f"{proposal.symbol} ({proposal.coin_name})" if proposal.coin_name else proposal.symbol
        _p = proposal.price_at_proposal
        _price_dp = max(6, -int(math.floor(math.log10(_p))) + 3) if _p > 0 else 6
        price_str = f"{_p:.{_price_dp}f}"
        sell_warning = ""
        if is_sell:
            sell_warning = """
                    <div style="background: rgba(229,62,62,0.15); border: 1px solid rgba(229,62,62,0.4); border-radius: 8px; padding: 12px; margin: 12px 0; font-size: 13px; color: #fc8181;">
                        &#9888;&#65039; <strong>SELL order</strong> &#8212; This will liquidate your position. Review carefully before approving.
                    </div>"""

        body = f"""
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d0d14; color: #e2e8f0; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; background: #151520; border-radius: 12px; border: 1px solid #2d3748; overflow: hidden;">
                <div style="background: {header_gradient}; padding: 16px 20px;">
                    <h2 style="margin: 0; color: white; font-size: 18px;">
                        {'&#x1F7E2;' if proposal.side == 'buy' else '&#x1F534;'} {proposal.side.upper()} {display_name}
                    </h2>
                </div>
                
                <div style="padding: 20px;">
                    {sell_warning}
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #a0aec0;">Amount</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: 700;">&#163;{proposal.amount_gbp:.4f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #a0aec0;">Price</td>
                            <td style="padding: 8px 0; text-align: right;">&#163;{price_str}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #a0aec0;">Confidence</td>
                            <td style="padding: 8px 0; text-align: right;">{proposal.confidence}%</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #a0aec0;">Recommendation</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: 700;">{proposal.agent_recommendation}</td>
                        </tr>
                    </table>
                    
                    <div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 12px; margin: 16px 0; border-left: 3px solid #667eea;">
                        <div style="font-size: 11px; color: #a0aec0; text-transform: uppercase; margin-bottom: 4px;">Agent Reasoning</div>
                        <div style="font-size: 13px; line-height: 1.5;">{proposal.reason}</div>
                    </div>
                    
                    <div style="font-size: 11px; color: #a0aec0; margin-bottom: 16px;">
                        Daily budget remaining: &#163;{self.get_remaining_budget():.4f} / &#163;{self.daily_budget_gbp:.4f}<br>
                        Expires in 1 hour. Proposal ID: {proposal.id}
                    </div>
                    
                    <div style="display: flex; gap: 12px;">
                        <a href="{approve_url}" style="flex: 1; display: block; text-align: center; padding: 14px; background: linear-gradient(135deg, #38a169, #48bb78); color: white; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 15px;">
                            APPROVE
                        </a>
                        <a href="{reject_url}" style="flex: 1; display: block; text-align: center; padding: 14px; background: linear-gradient(135deg, #e53e3e, #fc8181); color: white; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 15px;">
                            REJECT
                        </a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return self._send_email(subject, body)

    def _send_execution_email(self, proposal: TradeProposal) -> bool:
        """Send trade execution confirmation email."""
        if not self.smtp_user or not self.smtp_password:
            return False

        subject = f"Trade Executed: {proposal.side.upper()} {proposal.symbol}{' (' + proposal.coin_name + ')' if proposal.coin_name else ''} - GBP {proposal.amount_gbp:.4f}"
        display_name = f"{proposal.symbol} ({proposal.coin_name})" if proposal.coin_name else proposal.symbol
        _ep = proposal.execution_price or proposal.price_at_proposal or 0
        _exec_dp = max(6, -int(math.floor(math.log10(_ep))) + 3) if _ep > 0 else 6
        exec_price_str = f"{_ep:.{_exec_dp}f}"

        body = f"""
        <html>        <head><meta charset="utf-8"></head>        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d0d14; color: #e2e8f0; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; background: #151520; border-radius: 12px; border: 1px solid #2d3748; padding: 20px;">
                <h2 style="color: #48bb78; margin-top: 0;">Trade Executed</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td style="padding: 6px 0; color: #a0aec0;">Symbol</td><td style="text-align: right; font-weight: 700;">{display_name}</td></tr>
                    <tr><td style="padding: 6px 0; color: #a0aec0;">Side</td><td style="text-align: right;">{proposal.side.upper()}</td></tr>
                    <tr><td style="padding: 6px 0; color: #a0aec0;">Amount</td><td style="text-align: right;">&#163;{proposal.amount_gbp:.4f}</td></tr>
                    <tr><td style="padding: 6px 0; color: #a0aec0;">Quantity</td><td style="text-align: right;">{(proposal.quantity or 0):.8f}</td></tr>
                    <tr><td style="padding: 6px 0; color: #a0aec0;">Price</td><td style="text-align: right;">&#163;{exec_price_str}</td></tr>
                    <tr><td style="padding: 6px 0; color: #a0aec0;">Order ID</td><td style="text-align: right; font-size: 11px;">{proposal.order_id}</td></tr>
                </table>
                <div style="margin-top: 16px; font-size: 12px; color: #a0aec0;">
                    Remaining daily budget: &#163;{self.get_remaining_budget():.4f}
                </div>
            </div>
        </body>
        </html>
        """

        return self._send_email(subject, body)

    def _send_failure_email(self, proposal: TradeProposal, error: str) -> bool:
        """Send trade failure notification email."""
        if not self.smtp_user or not self.smtp_password:
            return False

        subject = f"[FAILED] {proposal.side.upper()} {proposal.symbol}{' (' + proposal.coin_name + ')' if proposal.coin_name else ''} - GBP {proposal.amount_gbp:.4f}"
        display_name = f"{proposal.symbol} ({proposal.coin_name})" if proposal.coin_name else proposal.symbol

        body = f"""
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d0d14; color: #e2e8f0; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; background: #151520; border-radius: 12px; border: 1px solid #2d3748; overflow: hidden;">
                <div style="background: linear-gradient(90deg, #e53e3e, #c53030); padding: 16px 20px;">
                    <h2 style="margin: 0; color: white; font-size: 18px;">&#x274C; Trade Failed</h2>
                </div>
                <div style="padding: 20px;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="padding: 6px 0; color: #a0aec0;">Symbol</td><td style="text-align: right; font-weight: 700;">{display_name}</td></tr>
                        <tr><td style="padding: 6px 0; color: #a0aec0;">Side</td><td style="text-align: right;">{proposal.side.upper()}</td></tr>
                        <tr><td style="padding: 6px 0; color: #a0aec0;">Amount</td><td style="text-align: right;">&#163;{proposal.amount_gbp:.4f}</td></tr>
                        <tr><td style="padding: 6px 0; color: #a0aec0;">Confidence</td><td style="text-align: right;">{proposal.confidence}%</td></tr>
                    </table>
                    <div style="background: rgba(229,62,62,0.15); border: 1px solid rgba(229,62,62,0.4); border-radius: 8px; padding: 12px; margin: 16px 0;">
                        <div style="font-size: 11px; color: #fc8181; text-transform: uppercase; margin-bottom: 4px;">Error</div>
                        <div style="font-size: 13px; color: #fc8181;">{error}</div>
                    </div>
                    <div style="font-size: 12px; color: #a0aec0;">
                        Remaining daily budget: &#163;{self.get_remaining_budget():.4f}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return self._send_email(subject, body)

    def _send_email(self, subject: str, html_body: str) -> bool:
        """Send an HTML email."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_user
            msg["To"] = self.email_to
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, self.email_to, msg.as_string())

            logger.info(f"Email sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    # ─── Kill Switch ──────────────────────────────────────────

    def activate_kill_switch(self) -> Dict[str, Any]:
        """Emergency halt all trading."""
        self.kill_switch = True
        # Reject all pending proposals
        rejected = 0
        for proposal in self.proposals.values():
            if proposal.status == "pending":
                proposal.status = "rejected"
                proposal.error = "Kill switch activated"
                rejected += 1
        self._save_state()
        logger.warning(f"KILL SWITCH ACTIVATED — {rejected} pending proposals rejected")
        return {"success": True, "proposals_rejected": rejected}

    def deactivate_kill_switch(self) -> Dict[str, Any]:
        """Resume trading."""
        self.kill_switch = False
        self._save_state()
        logger.info("Kill switch deactivated — trading resumed")
        return {"success": True, "trading_active": True}

    # ─── Status & History ─────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get current trading engine status."""
        budget = self._get_today_budget()
        pending = [p for p in self.proposals.values() if p.status == "pending"]

        # Multi-exchange status
        exchange_info = {"primary": self.exchange_id}
        try:
            from ml.exchange_manager import get_exchange_manager
            mgr = get_exchange_manager()
            exchange_info = mgr.get_tradeable_summary()
        except Exception:
            pass

        return {
            "active": not self.kill_switch,
            "daily_budget_gbp": self.daily_budget_gbp,
            "spent_today_gbp": round(budget.spent_gbp, 2),
            "remaining_today_gbp": round(self.get_remaining_budget(), 2),
            "sell_proceeds_today_gbp": round(budget.sell_proceeds_gbp, 2),
            "sells_today": budget.sells_executed,
            "fees_today_gbp": round(budget.fees_gbp, 2),
            "trades_today": budget.trades_executed,
            "proposals_today": budget.trades_proposed,
            "pending_proposals": len(pending),
            "total_trades": len(self.trade_history),
            "exchange": exchange_info,
            "email_configured": bool(self.smtp_user and self.smtp_password),
            "exchange_configured": bool(
                os.getenv("KRAKEN_API_KEY") and os.getenv("KRAKEN_PRIVATE_KEY")
            ),
            "max_trade_pct": self.max_trade_pct * 100,
            "trade_cooldown_min": self.trade_cooldown_min,
        }

    def get_pending_proposals(self) -> List[Dict[str, Any]]:
        """Get all pending trade proposals."""
        # Expire old proposals
        now = datetime.utcnow()
        for proposal in self.proposals.values():
            if proposal.status == "pending":
                created = datetime.fromisoformat(proposal.created_at)
                if now - created > timedelta(hours=1):
                    proposal.status = "expired"

        pending = [
            asdict(p) for p in self.proposals.values() if p.status == "pending"
        ]
        return sorted(pending, key=lambda x: x["created_at"], reverse=True)

    def get_trade_history(self) -> List[Dict[str, Any]]:
        """Get all executed trades."""
        return list(reversed(self.trade_history[-50:]))

    # ─── Persistence ──────────────────────────────────────────

    def _save_state(self):
        """Save engine state to disk (atomic write to prevent corruption)."""
        state = {
            "proposals": {k: asdict(v) for k, v in self.proposals.items()},
            "trade_history": self.trade_history,
            "daily_budgets": {k: asdict(v) for k, v in self.daily_budgets.items()},
            "kill_switch": self.kill_switch,
        }
        state_file = self.data_dir / "trading_state.json"
        tmp = state_file.with_suffix(".tmp")
        try:
            with open(tmp, "w") as f:
                json.dump(state, f, indent=2, default=str)
            os.replace(tmp, state_file)
        except Exception as e:
            logger.error(f"Failed to save trading state: {e}")
            if tmp.exists():
                tmp.unlink()

    def _load_state(self):
        """Load engine state from disk."""
        state_file = self.data_dir / "trading_state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file) as f:
                state = json.load(f)

            # Restore proposals
            for pid, pdata in state.get("proposals", {}).items():
                self.proposals[pid] = TradeProposal(**{
                    k: v for k, v in pdata.items()
                    if k in TradeProposal.__dataclass_fields__
                })

            self.trade_history = state.get("trade_history", [])
            self.kill_switch = state.get("kill_switch", False)

            for did, ddata in state.get("daily_budgets", {}).items():
                self.daily_budgets[did] = DailyBudget(**ddata)

            logger.info(
                f"Loaded trading state: {len(self.trade_history)} trades, "
                f"{len(self.proposals)} proposals"
            )
        except Exception as e:
            logger.error(f"Failed to load trading state: {e}")


# ─── Allocation Helper ────────────────────────────────────────

def compute_allocation_pct(
    conviction: int,
    agent_suggested_pct: float,
    coin_data: Dict[str, Any],
) -> float:
    """
    Compute the % of remaining budget to allocate to a trade.

    Layers applied in order:
    1. Base — agent's suggested % if non-zero, otherwise conviction-derived tiers
    2. Market cap tier — scale down slightly for micro-caps, up for large-caps
    3. Q-learning state — nudge size based on observed win/loss for this pattern
    4. Portfolio concentration — reduce add-ons when already meaningfully exposed

    Returns a float in [15.0, 100.0].
    """
    # 1. Base percentage
    if agent_suggested_pct > 0:
        base_pct = float(max(15.0, min(100.0, agent_suggested_pct)))
    else:
        # Deterministic fallback when agent returned 0
        if conviction >= 85:
            base_pct = 85.0
        elif conviction >= 70:
            base_pct = 65.0
        elif conviction >= 55:
            base_pct = 45.0
        else:  # 45-54 (fear-mode threshold)
            base_pct = 30.0

    # 2. Market cap tier scaling
    mcap = coin_data.get("market_cap", 0) or 0
    if mcap > 0:
        if mcap < 5_000_000:        # micro-cap: higher uncertainty, smaller size
            base_pct *= 0.85
        elif mcap >= 500_000_000:   # large/mid-cap: more liquid, allow larger position
            base_pct *= 1.15

    # 3. Q-learning state performance scaling
    # Only fires when the state has been visited enough times to be reliable
    try:
        from ml.q_learning import get_q_learner, discretise_state
        ql = get_q_learner()
        ql_state = discretise_state(coin_data)
        total_visits = sum(ql.visit_counts[ql_state].values())
        if total_visits >= ql.min_visits_to_act * 2:
            q_buy = ql.q_table[ql_state]["buy"]
            if q_buy > 0.15:
                base_pct *= 1.2    # proven winning pattern — size up
            elif q_buy < -0.15:
                base_pct *= 0.75   # proven losing pattern — size down
    except Exception:
        pass

    # 4. Portfolio concentration cap
    # When we already have a meaningful holding, reduce the add-on size
    try:
        from ml.portfolio_tracker import get_portfolio_tracker
        sym = coin_data.get("symbol", "").upper()
        tracker = get_portfolio_tracker()
        holding = tracker.holdings.get(sym)
        if holding and holding.get("quantity", 0) > 0:
            existing_cost = holding.get("total_cost_gbp", 0)
            if existing_cost >= 2.0:
                base_pct *= 0.5   # meaningful position already — halve the add-on
    except Exception:
        pass

    result = max(15.0, min(100.0, round(base_pct, 1)))
    logger.debug(
        f"[Allocation] conviction={conviction} agent={agent_suggested_pct:.0f}% "
        f"mcap={mcap:.0f} → {result:.1f}%"
    )
    return result


# ─── Singleton ────────────────────────────────────────────────

_engine: Optional[TradingEngine] = None


def get_trading_engine() -> TradingEngine:
    """Get or create the singleton trading engine."""
    global _engine
    if _engine is None:
        daily_budget = float(os.getenv("DAILY_TRADE_BUDGET_GBP", "3.00"))
        server_url = os.getenv("TRADE_SERVER_URL", "http://localhost:5001")
        # Use first exchange from EXCHANGE_PRIORITY (default: kraken)
        priority = os.getenv("EXCHANGE_PRIORITY", "kraken")
        exchange_id = priority.split(",")[0].strip().lower()
        _engine = TradingEngine(
            daily_budget_gbp=daily_budget,
            exchange_id=exchange_id,
            server_url=server_url,
        )
    return _engine
