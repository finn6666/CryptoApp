"""
Automated Daily Scan Loop
Runs a scheduled scan: refresh → filter tradeable → analyse → propose → email.
Supports configurable scan time and on-demand triggering.
"""

import os
import json
import logging
import threading
import time
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional

from ml.error_handling import alert_scan_failure, alert_api_quota

logger = logging.getLogger(__name__)

SCAN_LOGS_DIR = Path("data/scan_logs")
AUDIT_LOG_FILE = Path("data/trades/audit_log.jsonl")


class ScanLoop:
    """
    Automated trading scan loop.

    Pipeline:
    1. Refresh coin data from CoinMarketCap
    2. Filter to tradeable coins (coins listed on configured exchanges)
    3. Run orchestrator on top N tradeable coins (favorites + high-scoring gems)
    4. Feed results into auto-evaluate → auto-execute (propose + email)
    5. Log everything to audit trail + daily scan log
    """

    def __init__(self):
        self.scan_time = os.getenv("SCAN_TIME", "12:00")
        # Interval-based scanning: run every N hours (0 = once-daily at scan_time only)
        # 12h balances Gemini API cost (~$0.84/day) with discovery frequency
        self.scan_interval_hours = float(os.getenv("SCAN_INTERVAL_HOURS", "12"))
        self.max_coins_per_scan = int(os.getenv("SCAN_MAX_COINS", "25"))
        self.min_gem_score = float(os.getenv("SCAN_MIN_GEM_SCORE", "6.0"))
        self.quick_screen_min_confidence = int(os.getenv("SCAN_QUICK_SCREEN_MIN", "60"))
        self.scan_running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Safety: max trades per scan
        self.max_proposals_per_scan = int(os.getenv("SCAN_MAX_PROPOSALS", "3"))

        # Cooldown: minimum hours between scans
        self.cooldown_hours = float(os.getenv("SCAN_COOLDOWN_HOURS", "1"))
        self._last_scan_time: Optional[datetime] = None
        self._scheduler_started_at: Optional[datetime] = None

        SCAN_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        interval_desc = f"every {self.scan_interval_hours}h" if self.scan_interval_hours > 0 else f"daily at {self.scan_time}"
        logger.info(
            f"Scan loop initialised — schedule={interval_desc}, "
            f"max_coins={self.max_coins_per_scan}, "
            f"quick_screen_min={self.quick_screen_min_confidence}%, "
            f"max_proposals={self.max_proposals_per_scan}"
        )

    # ─── Core Scan Pipeline ──────────────────────────────────

    def run_scan(self, triggered_by: str = "manual") -> Dict[str, Any]:
        """
        Run the full scan pipeline.
        Returns a summary dict with results.
        """
        if self.scan_running:
            return {"success": False, "error": "Scan already in progress"}

        # Cooldown check
        if self._last_scan_time:
            elapsed = (datetime.utcnow() - self._last_scan_time).total_seconds() / 3600
            if elapsed < self.cooldown_hours:
                remaining = self.cooldown_hours - elapsed
                return {
                    "success": False,
                    "error": f"Cooldown active — next scan in {remaining:.1f}h",
                }

        self.scan_running = True
        scan_start = datetime.utcnow()
        scan_id = scan_start.strftime("%Y%m%d_%H%M%S")

        scan_result = {
            "scan_id": scan_id,
            "triggered_by": triggered_by,
            "started_at": scan_start.isoformat(),
            "coins_refreshed": 0,
            "coins_tradeable": 0,
            "coins_analysed": 0,
            "coins_quick_screened": 0,
            "coins_passed_screen": 0,
            "proposals_made": 0,
            "proposals_skipped": 0,
            "errors": [],
            "analyses": [],
        }

        try:
            # ── Step 1: Refresh coin data ──
            logger.info(f"[Scan {scan_id}] Step 1: Refreshing coin data...")
            refresh_ok = self._refresh_data()
            if not refresh_ok:
                scan_result["errors"].append("Data refresh failed — using cached data")
            self._audit("scan_start", {"scan_id": scan_id, "triggered_by": triggered_by})

            # ── Step 2: Get tradeable coins ──
            logger.info(f"[Scan {scan_id}] Step 2: Filtering tradeable coins...")
            tradeable_coins = self._get_tradeable_coins()
            scan_result["coins_tradeable"] = len(tradeable_coins)

            if not tradeable_coins:
                scan_result["errors"].append("No tradeable coins found")
                self._audit("scan_no_coins", {"scan_id": scan_id})
                return scan_result

            # ── Step 3: Select top candidates ──
            logger.info(f"[Scan {scan_id}] Step 3: Selecting top {self.max_coins_per_scan} candidates...")
            candidates = self._select_candidates(tradeable_coins)

            # ── Step 4: Quick screen (Tier 1 — 1 Gemini call each) ──
            logger.info(f"[Scan {scan_id}] Step 4: Quick-screening {len(candidates)} candidates...")
            screened_candidates = self._quick_screen_candidates(candidates, scan_id)
            scan_result["coins_quick_screened"] = len(candidates)
            scan_result["coins_passed_screen"] = len(screened_candidates)
            scan_result["coins_analysed"] = len(screened_candidates)
            logger.info(
                f"[Scan {scan_id}] Quick screen: {len(screened_candidates)}/{len(candidates)} "
                f"passed (saved {len(candidates) - len(screened_candidates)} full analyses)"
            )

            # ── Step 5: Full multi-agent analysis (Tier 2 — 6 Gemini calls each) ──
            logger.info(f"[Scan {scan_id}] Step 5: Full analysis on {len(screened_candidates)} coins...")
            proposals_made = 0

            for coin_data in screened_candidates:
                if proposals_made >= self.max_proposals_per_scan:
                    logger.info(f"[Scan {scan_id}] Hit max proposals ({self.max_proposals_per_scan})")
                    break

                # Check budget before each coin to avoid wasting API calls
                try:
                    from ml.trading_engine import get_trading_engine
                    _engine = get_trading_engine()
                    if _engine.is_budget_exhausted():
                        logger.info(f"[Scan {scan_id}] Daily budget exhausted — stopping scan")
                        self._audit("budget_exhausted", {"scan_id": scan_id})
                        break
                    if _engine.kill_switch:
                        logger.info(f"[Scan {scan_id}] Kill switch active — stopping scan")
                        break
                except Exception:
                    pass

                symbol = coin_data["symbol"]
                try:
                    result = self._analyse_and_evaluate(coin_data)
                    scan_result["analyses"].append({
                        "symbol": symbol,
                        "result": result.get("outcome", "skipped"),
                        "reason": result.get("reason", ""),
                    })

                    if result.get("proposed"):
                        proposals_made += 1
                        scan_result["proposals_made"] += 1
                        self._audit("proposal", {
                            "scan_id": scan_id,
                            "symbol": symbol,
                            "confidence": result.get("confidence", 0),
                        })

                        # Re-check budget after a successful trade/proposal
                        try:
                            if _engine.is_budget_exhausted():
                                logger.info(
                                    f"[Scan {scan_id}] Daily budget now exhausted after "
                                    f"{symbol} trade — stopping scan"
                                )
                                self._audit("budget_exhausted", {
                                    "scan_id": scan_id,
                                    "after_symbol": symbol,
                                })
                                break
                        except Exception:
                            pass
                    else:
                        scan_result["proposals_skipped"] += 1
                        self._audit("skip", {
                            "scan_id": scan_id,
                            "symbol": symbol,
                            "reason": result.get("reason", "Agent decided not to trade"),
                        })

                except Exception as e:
                    logger.error(f"[Scan {scan_id}] Analysis failed for {symbol}: {e}")
                    scan_result["errors"].append(f"{symbol}: {str(e)}")
                    self._audit("error", {"scan_id": scan_id, "symbol": symbol, "error": str(e)})

            scan_result["completed_at"] = datetime.utcnow().isoformat()
            scan_result["success"] = True
            self._last_scan_time = datetime.utcnow()

            # ── Step 6: Sell-side automation ──
            try:
                from ml.sell_automation import get_sell_automation
                sell_auto = get_sell_automation()

                # Build live prices from analyser
                import services.app_state as state
                live_prices = {}
                if state.analyzer and state.analyzer.coins:
                    for coin in state.analyzer.coins:
                        live_prices[coin.symbol.upper()] = getattr(coin, "price", 0)

                if live_prices:
                    sell_proposals = sell_auto.check_and_propose_sells(live_prices)
                    scan_result["sell_proposals"] = len(sell_proposals)
                    for sp in sell_proposals:
                        self._audit("sell_proposal", {
                            "scan_id": scan_id,
                            "symbol": sp.get("symbol"),
                            "trigger": sp.get("trigger"),
                        })
                    logger.info(f"[Scan {scan_id}] Sell check: {len(sell_proposals)} sell proposals")
            except Exception as e:
                logger.warning(f"[Scan {scan_id}] Sell automation error: {e}")
                scan_result["errors"].append(f"Sell automation: {str(e)}")

        except Exception as e:
            logger.error(f"[Scan {scan_id}] Scan failed: {e}")
            scan_result["errors"].append(str(e))
            scan_result["success"] = False
            alert_scan_failure(str(e))

        finally:
            self.scan_running = False
            self._save_scan_log(scan_result)
            self._audit("scan_complete", {
                "scan_id": scan_id,
                "coins_screened": scan_result.get("coins_quick_screened", 0),
                "coins_analysed": scan_result["coins_analysed"],
                "proposals": scan_result["proposals_made"],
                "errors": len(scan_result["errors"]),
            })

        logger.info(
            f"[Scan {scan_id}] Complete — "
            f"{scan_result.get('coins_quick_screened', 0)} screened, "
            f"{scan_result['coins_analysed']} fully analysed, "
            f"{scan_result['proposals_made']} proposals, "
            f"{len(scan_result['errors'])} errors"
        )
        return scan_result

    # ─── Pipeline Steps ───────────────────────────────────────

    def _refresh_data(self) -> bool:
        """Step 1: Refresh coin data from CoinMarketCap."""
        try:
            from src.core.live_data_fetcher import fetch_and_update_data
            import services.app_state as state

            live_data = fetch_and_update_data()
            if live_data:
                # Also fetch any pipeline-tracked symbols
                if state.SYMBOLS_AVAILABLE and state.data_pipeline:
                    current_symbols = [c.symbol for c in state.analyzer.coins]
                    for symbol in state.data_pipeline.supported_symbols:
                        if symbol not in current_symbols:
                            try:
                                state.fetch_and_add_new_symbol_data(symbol)
                            except Exception:
                                pass
                state.analyzer.load_data()
                logger.info(f"Data refreshed — {len(state.analyzer.coins)} coins loaded")
                return True
            return False
        except Exception as e:
            logger.error(f"Data refresh failed: {e}")
            return False

    def _get_tradeable_coins(self) -> List[Dict[str, Any]]:
        """Step 2: Get coins that are tradeable on at least one exchange."""
        import services.app_state as state
        from ml.exchange_manager import get_exchange_manager

        if not state.analyzer or not state.analyzer.coins:
            return []

        exchange_mgr = get_exchange_manager()
        tradeable = []

        for coin in state.analyzer.coins:
            symbol = coin.symbol.upper()

            # Skip stablecoins
            if symbol in state.STABLECOINS:
                continue

            # Check if tradeable
            exchanges = exchange_mgr.get_exchanges_for_coin(symbol)
            if exchanges:
                coin_dict = state.coin_to_dict(coin)
                coin_dict["tradeable_exchanges"] = exchanges
                coin_dict["primary_exchange"] = exchanges[0]
                tradeable.append(coin_dict)

        logger.info(f"Found {len(tradeable)} tradeable coins")
        return tradeable

    def _select_candidates(self, tradeable_coins: List[Dict]) -> List[Dict]:
        """Step 3: Select top N candidates from tradeable coins."""
        import services.app_state as state

        candidates = []

        # Priority 1: Favorites that are tradeable
        favorites = state.load_favorites()
        fav_symbols = {f.upper() for f in favorites}

        for coin in tradeable_coins:
            if coin["symbol"] in fav_symbols:
                candidates.append(coin)

        # Priority 2: High gem scores (if gem detector is available)
        if state.GEM_DETECTOR_AVAILABLE and state.gem_detector:
            scored = []
            for coin in tradeable_coins:
                if coin["symbol"] in fav_symbols:
                    continue  # Already included
                try:
                    gem_result = state.gem_detector.predict_hidden_gem(coin)
                    gem_score = gem_result.get("gem_score", 0)
                    if gem_score >= self.min_gem_score:
                        coin["gem_score"] = gem_score
                        coin["gem_probability"] = gem_result.get("gem_probability", 0)
                        scored.append(coin)
                except Exception:
                    pass

            # Sort by gem score descending
            scored.sort(key=lambda c: c.get("gem_score", 0), reverse=True)
            candidates.extend(scored)

        # Priority 3: High attractiveness score fallback
        if len(candidates) < self.max_coins_per_scan:
            remaining = [
                c for c in tradeable_coins
                if c["symbol"] not in {x["symbol"] for x in candidates}
            ]
            remaining.sort(
                key=lambda c: c.get("attractiveness_score", 0), reverse=True
            )
            candidates.extend(remaining)

        # Cap to max
        return candidates[: self.max_coins_per_scan]

    def _quick_screen_candidates(
        self, candidates: List[Dict], scan_id: str
    ) -> List[Dict]:
        """
        Tier 1: Run a single-call quick LLM screen on each candidate.
        Only coins that pass (confidence >= threshold) proceed to the full
        multi-agent pipeline, saving ~5 Gemini calls per filtered coin.
        """
        import services.app_state as state

        if not state.official_adk_available:
            # If ADK isn't available, skip screening — let gem detector handle it
            return candidates

        # Build trade history context once (shared across all screens)
        try:
            from ml.agents.official.orchestrator import _build_trade_history_context
            trade_ctx = _build_trade_history_context()
        except Exception:
            trade_ctx = ""

        passed = []

        for coin in candidates:
            symbol = coin["symbol"]

            try:
                from ml.agents.official.quick_screen import quick_screen_coin
                result = state.run_async(
                    quick_screen_coin(symbol, coin, trade_ctx)
                )

                did_pass = result.get("pass", True)
                confidence = result.get("confidence", 0)
                one_liner = result.get("one_liner", "")

                if did_pass and confidence >= self.quick_screen_min_confidence:
                    logger.info(
                        f"[Scan {scan_id}] {symbol}: PASS ({confidence}%) — {one_liner}"
                    )
                    coin["screen_confidence"] = confidence
                    coin["screen_note"] = one_liner
                    passed.append(coin)
                else:
                    logger.info(
                        f"[Scan {scan_id}] {symbol}: SKIP ({confidence}%) — {one_liner}"
                    )
                    self._audit("quick_screen_skip", {
                        "scan_id": scan_id,
                        "symbol": symbol,
                        "confidence": confidence,
                        "reason": one_liner,
                    })

            except Exception as e:
                # On failure, pass through to avoid missing opportunities
                logger.warning(f"[Scan {scan_id}] Quick screen error for {symbol}: {e} — passing")
                passed.append(coin)

        return passed

    def _analyse_and_evaluate(self, coin_data: Dict) -> Dict[str, Any]:
        """Step 4: Run ADK analysis + trading agent evaluation on a single coin."""
        import services.app_state as state
        from ml.trading_engine import get_trading_engine

        symbol = coin_data["symbol"]
        engine = get_trading_engine()

        # Check budget before spending API credits
        if engine.is_budget_exhausted():
            return {"outcome": "skipped", "reason": "Daily budget exhausted", "proposed": False}

        if engine.kill_switch:
            return {"outcome": "skipped", "reason": "Kill switch active", "proposed": False}

        # Run orchestrator analysis (with fallback to gem detector)
        analysis = None
        analysis_source = None

        # Try 1: Official ADK orchestrator (Gemini)
        if state.official_adk_available and state.analyze_crypto_adk:
            try:
                analysis = state.run_async(
                    state.analyze_crypto_adk(symbol, coin_data)
                )
                if analysis and analysis.get("success"):
                    analysis_source = "adk_orchestrator"
            except Exception as e:
                logger.warning(f"ADK analysis failed for {symbol}: {e}")
                analysis = None
                # Alert if it looks like a quota/rate limit issue
                err_str = str(e).lower()
                if "quota" in err_str or "rate" in err_str or "429" in err_str:
                    alert_api_quota("Gemini ADK", str(e))

        # Try 2: Gem Detector fallback (no API call — local ML)
        if (not analysis or not analysis.get("success")) and state.GEM_DETECTOR_AVAILABLE and state.gem_detector:
            try:
                gem_result = state.gem_detector.predict_hidden_gem(coin_data)
                if gem_result:
                    gem_prob = gem_result.get("gem_probability", 0)
                    gem_score = gem_result.get("gem_score", 0)
                    recommendation = "BUY" if gem_prob > 0.6 else "HOLD" if gem_prob > 0.3 else "AVOID"
                    strengths = gem_result.get("key_strengths", [])
                    analysis = {
                        "success": True,
                        "symbol": symbol,
                        "recommendation": recommendation,
                        "confidence": int(gem_prob * 100),
                        "analysis": (
                            f"Gem detector: {gem_prob*100:.0f}% gem probability, "
                            f"score {gem_score:.1f}/100. "
                            f"Strengths: {', '.join(strengths[:3]) if strengths else 'None identified'}."
                        ),
                        "orchestrator": "gem_detector_fallback",
                    }
                    analysis_source = "gem_detector"
                    logger.info(f"Using gem detector fallback for {symbol} (ADK unavailable)")
            except Exception as e:
                logger.warning(f"Gem detector fallback also failed for {symbol}: {e}")

        if not analysis or not analysis.get("success"):
            return {
                "outcome": "skipped",
                "reason": "All analysis methods failed (ADK + gem detector)",
                "proposed": False,
            }

        # Cache the analysis
        state.cache_analysis(symbol, {
            "analysis": analysis,
            "source": analysis_source,
        })

        # Record gem score history
        try:
            from ml.gem_score_tracker import get_gem_score_tracker
            tracker = get_gem_score_tracker()
            tracker.record_score(
                symbol=symbol,
                gem_probability=analysis.get("confidence", 0) / 100,
                gem_score=analysis.get("confidence", 0),
                recommendation=analysis.get("recommendation", "UNKNOWN"),
                source=analysis_source or "unknown",
            )
        except Exception as e:
            logger.debug(f"Gem score tracking failed for {symbol}: {e}")

        # Extract trade decision from the multi-agent orchestrator output
        # The trading_specialist is now a sub-agent of the orchestrator, so its
        # decision is extracted and mapped by the orchestrator wrapper.
        try:
            trade_decision = analysis.get("trade_decision", {})

            should_trade = trade_decision.get("should_trade", False)
            conviction = trade_decision.get("trade_conviction", 0)
            allocation_pct = trade_decision.get("trade_allocation_pct", 0)
            trade_reasoning = trade_decision.get("trade_reasoning", "")
            trade_side = trade_decision.get("trade_side", "buy")

            # Fallback: if ADK didn't produce a trade_decision, check analysis text
            if not trade_decision and analysis_source == "adk_orchestrator":
                import re
                import json as _json
                analysis_text = analysis.get("analysis", "")
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', analysis_text, re.DOTALL)
                if json_match:
                    try:
                        parsed = _json.loads(json_match.group())
                        should_trade = parsed.get("should_trade", False)
                        conviction = parsed.get("trade_conviction", parsed.get("conviction", 0))
                        allocation_pct = parsed.get("trade_allocation_pct", parsed.get("suggested_allocation_pct", 0))
                        trade_reasoning = parsed.get("trade_reasoning", parsed.get("reasoning", ""))
                        trade_side = parsed.get("trade_side", parsed.get("side", "buy"))
                    except _json.JSONDecodeError:
                        pass

            # Fallback for gem detector: check recommendation + confidence
            if not should_trade and analysis_source == "gem_detector":
                rec = analysis.get("recommendation", "HOLD").upper()
                conf = analysis.get("confidence", 0)
                if rec == "BUY" and conf >= 45:
                    should_trade = True
                    conviction = conf
                    allocation_pct = min(80, conf - 10)
                    trade_reasoning = analysis.get("analysis", "Gem detector recommended trade")[:500]

            # ── Q-learning adjustment ──
            # Let the RL agent nudge conviction based on past outcomes
            # for this coin's state pattern (gem tier, vol, weekly change, mcap)
            try:
                from ml.q_learning import get_q_learner
                ql = get_q_learner()
                ql_adjust = ql.confidence_adjustment(coin_data)
                if ql_adjust != 0:
                    original_conviction = conviction
                    conviction = max(0, min(100, conviction + ql_adjust))
                    logger.info(
                        f"[QL] {symbol}: conviction {original_conviction} → "
                        f"{conviction} (adjustment {ql_adjust:+d})"
                    )

                # Also check if Q-learning outright recommends skipping
                should_ql_skip, skip_reason = ql.should_skip(coin_data)
                if should_ql_skip and conviction < 80:
                    # High-conviction agent calls can override Q-learning skip
                    logger.info(f"[QL] {symbol}: {skip_reason}")
                    return {
                        "outcome": "skipped",
                        "proposed": False,
                        "reason": skip_reason,
                    }
            except Exception as e:
                logger.debug(f"Q-learning adjustment skipped: {e}")

            if should_trade and conviction >= 45:
                remaining = engine.get_remaining_budget()
                if remaining < engine.min_useful_budget_gbp:
                    return {"outcome": "skipped", "proposed": False, "reason": "Daily budget exhausted"}

                # Check exchange minimum before wasting an API proposal
                min_order = engine._get_min_order_gbp(symbol)
                max_trade = min(remaining, engine.daily_budget_gbp * engine.max_trade_pct)
                if min_order > 0 and min_order > max_trade:
                    return {
                        "outcome": "skipped", "proposed": False,
                        "reason": f"Exchange minimum £{min_order:.2f} exceeds max trade £{max_trade:.2f}",
                    }

                amount = remaining * (allocation_pct / 100)
                amount = min(amount, remaining)

                # Use auto-execute for scheduled scans so trades don't
                # sit waiting for manual approval overnight.
                result = engine.propose_and_auto_execute(
                    symbol=symbol,
                    side=trade_side,
                    amount_gbp=round(amount, 2),
                    current_price=coin_data.get("price") or 0,
                    reason=trade_reasoning[:500] if trade_reasoning else "Multi-agent orchestrator recommended trade",
                    confidence=conviction,
                    recommendation=analysis.get("recommendation", "BUY"),
                    coin_name=coin_data.get("name", ""),
                )

                outcome = "executed" if result.get("auto_approved") else "proposed"
                return {
                    "outcome": outcome,
                    "proposed": result.get("success", False),
                    "auto_approved": result.get("auto_approved", False),
                    "confidence": conviction,
                    "reason": trade_reasoning,
                    "proposal_id": result.get("proposal_id"),
                }
            else:
                return {
                    "outcome": "skipped",
                    "proposed": False,
                    "reason": trade_reasoning or "Multi-agent system decided not to trade",
                }

        except Exception as e:
            logger.error(f"Trade decision extraction failed for {symbol}: {e}")
            return {"outcome": "error", "reason": str(e), "proposed": False}

    # ─── Audit Trail ──────────────────────────────────────────

    def _audit(self, event: str, data: Dict[str, Any]):
        """Append an event to the persistent audit log (JSONL)."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event,
            **data,
        }
        try:
            with open(AUDIT_LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def _save_scan_log(self, scan_result: Dict):
        """Save daily scan log to disk."""
        today = date.today().isoformat()
        log_file = SCAN_LOGS_DIR / f"scan_{today}.json"

        # Append to daily scan log (list of scans)
        logs = []
        if log_file.exists():
            try:
                with open(log_file) as f:
                    logs = json.load(f)
            except Exception:
                logs = []

        logs.append(scan_result)

        try:
            with open(log_file, "w") as f:
                json.dump(logs, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save scan log: {e}")

    # ─── Scheduler Thread ─────────────────────────────────────

    def start_scheduler(self):
        """Start the background scheduler that runs scans at the configured time."""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            logger.warning("Scanner scheduler already running")
            return

        self._stop_event.clear()
        self._scheduler_started_at = datetime.utcnow()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True, name="scan-scheduler"
        )
        self._scheduler_thread.start()
        if self.scan_interval_hours > 0:
            logger.info(f"📊 Scan scheduler started — scanning every {self.scan_interval_hours}h")
        else:
            logger.info(f"📊 Scan scheduler started — daily scan at {self.scan_time}")

        # Start the lightweight market monitor between deep scans
        monitor_enabled = os.getenv("MONITOR_ENABLED", "true").lower() in ("1", "true", "yes")
        if monitor_enabled:
            try:
                from ml.market_monitor import get_market_monitor
                monitor = get_market_monitor()
                monitor.start()
            except Exception as e:
                logger.warning(f"Market monitor not started: {e}")

    def stop_scheduler(self):
        """Stop the background scheduler."""
        self._stop_event.set()

        # Also stop the market monitor
        try:
            from ml.market_monitor import get_market_monitor
            monitor = get_market_monitor()
            monitor.stop()
        except Exception:
            pass

        logger.info("Scan scheduler stopped")

    def _scheduler_loop(self):
        """Background loop that triggers scans at the configured interval."""
        import schedule

        if self.scan_interval_hours > 0:
            # Interval mode: scan every N hours
            interval_min = int(self.scan_interval_hours * 60)
            schedule.every(interval_min).minutes.do(
                lambda: self.run_scan(triggered_by="scheduled")
            )
            logger.info(f"Scan scheduled every {self.scan_interval_hours}h ({interval_min} min)")
        else:
            # Legacy mode: once daily at a fixed time
            schedule.every().day.at(self.scan_time).do(
                lambda: self.run_scan(triggered_by="scheduled")
            )
            logger.info(f"Scan scheduled daily at {self.scan_time}")

        while not self._stop_event.is_set():
            schedule.run_pending()
            self._stop_event.wait(30)  # Check every 30 seconds

    # ─── Status ───────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get scan loop status."""
        # Include market monitor status
        monitor_status = None
        try:
            from ml.market_monitor import get_market_monitor
            monitor = get_market_monitor()
            monitor_status = monitor.get_status()
        except Exception:
            pass

        return {
            "scan_time": self.scan_time,
            "scan_interval_hours": self.scan_interval_hours,
            "scan_running": self.scan_running,
            "scheduler_running": (
                self._scheduler_thread is not None
                and self._scheduler_thread.is_alive()
            ),
            "scheduler_active": (
                self._scheduler_thread is not None
                and self._scheduler_thread.is_alive()
            ),
            "max_coins_per_scan": self.max_coins_per_scan,
            "max_proposals_per_scan": self.max_proposals_per_scan,
            "last_scan": (
                self._last_scan_time.isoformat() if self._last_scan_time else None
            ),
            "next_scan": self._estimate_next_scan(),
            "cooldown_hours": self.cooldown_hours,
            "market_monitor": monitor_status,
        }

    def _estimate_next_scan(self) -> Optional[str]:
        """Estimate when the next scan will fire."""
        from datetime import timedelta
        if self.scan_interval_hours > 0:
            if self._last_scan_time:
                return (self._last_scan_time + timedelta(hours=self.scan_interval_hours)).isoformat()
            elif self._scheduler_started_at:
                # No scan yet — first scan fires one interval after scheduler start
                return (self._scheduler_started_at + timedelta(hours=self.scan_interval_hours)).isoformat()
        elif self.scan_time:
            # Daily mode — next occurrence of scan_time today or tomorrow
            now = datetime.utcnow()
            h, m = map(int, self.scan_time.split(":"))
            target = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target.isoformat()
        return None

    def get_recent_logs(self, days: int = 7) -> List[Dict]:
        """Get recent scan logs."""
        logs = []
        for i in range(days):
            d = date.today()
            d = date(d.year, d.month, d.day)
            from datetime import timedelta
            target = d - timedelta(days=i)
            log_file = SCAN_LOGS_DIR / f"scan_{target.isoformat()}.json"
            if log_file.exists():
                try:
                    with open(log_file) as f:
                        day_logs = json.load(f)
                    logs.extend(day_logs)
                except Exception:
                    pass
        return logs

    def get_audit_trail(self, limit: int = 100) -> List[Dict]:
        """Get recent audit trail entries (reads only the tail of the file)."""
        if not AUDIT_LOG_FILE.exists():
            return []
        try:
            import collections
            tail: collections.deque = collections.deque(maxlen=limit)
            with open(AUDIT_LOG_FILE) as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        tail.append(stripped)
            entries = []
            for line in reversed(tail):
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
            return entries
        except Exception:
            return []


# ─── Singleton ────────────────────────────────────────────────

_scan_loop: Optional[ScanLoop] = None


def get_scan_loop() -> ScanLoop:
    """Get or create the singleton scan loop."""
    global _scan_loop
    if _scan_loop is None:
        _scan_loop = ScanLoop()
    return _scan_loop
