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
        self.max_coins_per_scan = int(os.getenv("SCAN_MAX_COINS", "10"))
        self.min_gem_score = float(os.getenv("SCAN_MIN_GEM_SCORE", "5.0"))
        self.scan_running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Safety: max trades per scan
        self.max_proposals_per_scan = int(os.getenv("SCAN_MAX_PROPOSALS", "3"))

        # Cooldown: minimum hours between scans
        self.cooldown_hours = float(os.getenv("SCAN_COOLDOWN_HOURS", "1"))
        self._last_scan_time: Optional[datetime] = None

        SCAN_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Scan loop initialised — time={self.scan_time}, "
            f"max_coins={self.max_coins_per_scan}, "
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
            scan_result["coins_analysed"] = len(candidates)

            # ── Step 4: Analyse + propose ──
            logger.info(f"[Scan {scan_id}] Step 4: Running analysis pipeline on {len(candidates)} coins...")
            proposals_made = 0

            for coin_data in candidates:
                if proposals_made >= self.max_proposals_per_scan:
                    logger.info(f"[Scan {scan_id}] Hit max proposals ({self.max_proposals_per_scan})")
                    break

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

            # ── Step 5: Sell-side automation ──
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
                "proposals": scan_result["proposals_made"],
                "errors": len(scan_result["errors"]),
            })

        logger.info(
            f"[Scan {scan_id}] Complete — "
            f"{scan_result['coins_analysed']} analysed, "
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

    def _analyse_and_evaluate(self, coin_data: Dict) -> Dict[str, Any]:
        """Step 4: Run ADK analysis + trading agent evaluation on a single coin."""
        import services.app_state as state
        from ml.trading_engine import get_trading_engine

        symbol = coin_data["symbol"]
        engine = get_trading_engine()

        # Check budget before spending API credits
        remaining = engine.get_remaining_budget()
        if remaining <= 0:
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
                if rec == "BUY" and conf >= 75:
                    should_trade = True
                    conviction = conf
                    allocation_pct = min(50, conf - 25)
                    trade_reasoning = analysis.get("analysis", "Gem detector recommended trade")[:500]

            if should_trade and conviction >= 75:
                amount = remaining * (allocation_pct / 100)
                amount = min(amount, remaining)

                result = engine.propose_trade(
                    symbol=symbol,
                    side=trade_side,
                    amount_gbp=round(amount, 4),
                    current_price=coin_data.get("price", 0),
                    reason=trade_reasoning[:500] if trade_reasoning else "Multi-agent orchestrator recommended trade",
                    confidence=conviction,
                    recommendation=analysis.get("recommendation", "BUY"),
                )

                return {
                    "outcome": "proposed",
                    "proposed": result.get("success", False),
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
            "timestamp": datetime.utcnow().isoformat(),
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
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True, name="scan-scheduler"
        )
        self._scheduler_thread.start()
        logger.info(f"📊 Scan scheduler started — daily scan at {self.scan_time}")

    def stop_scheduler(self):
        """Stop the background scheduler."""
        self._stop_event.set()
        logger.info("Scan scheduler stopped")

    def _scheduler_loop(self):
        """Background loop that triggers scans at the configured time."""
        import schedule

        # Parse scan time
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
        return {
            "scan_time": self.scan_time,
            "scan_running": self.scan_running,
            "scheduler_active": (
                self._scheduler_thread is not None
                and self._scheduler_thread.is_alive()
            ),
            "max_coins_per_scan": self.max_coins_per_scan,
            "max_proposals_per_scan": self.max_proposals_per_scan,
            "last_scan": (
                self._last_scan_time.isoformat() if self._last_scan_time else None
            ),
            "cooldown_hours": self.cooldown_hours,
        }

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
        """Get recent audit trail entries."""
        if not AUDIT_LOG_FILE.exists():
            return []
        try:
            with open(AUDIT_LOG_FILE) as f:
                lines = f.readlines()
            entries = []
            for line in reversed(lines[-limit:]):
                try:
                    entries.append(json.loads(line.strip()))
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
