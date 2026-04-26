import schedule
import time
import logging
import threading
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)


class MLScheduler:
    def __init__(self):
        self._thread = None
        self._running = False

    def send_alert(self, message: str):
        """Send alert for failed operations via error_handling module."""
        try:
            from ml.error_handling import send_email_alert
            send_email_alert("ML Scheduler Alert", message)
        except Exception:
            logger.error(f"ALERT (email failed): {message}")

    def weekly_report_job(self):
        """Weekly performance report emailed Monday 9 AM."""
        logger.info("Generating weekly performance report")
        try:
            report = self._build_weekly_report()
            from ml.error_handling import send_error_alert
            sent = send_error_alert(
                subject="Weekly Performance Report",
                body=report,
                category="weekly_report",
                force=True,
            )
            if sent:
                logger.info("Weekly report email sent")
            else:
                logger.warning("Weekly report email not sent (SMTP not configured?)")
        except Exception as e:
            logger.error(f"Weekly report failed: {e}")

    def _build_weekly_report(self) -> str:
        """Collect data from portfolio, trading engine, and scans into a report."""
        lines = []
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        lines.append(f"Weekly Report: {week_ago.strftime('%d %b')} - {now.strftime('%d %b %Y')}")
        lines.append("")

        # ── Portfolio summary ──
        try:
            from ml.portfolio_tracker import get_portfolio_tracker
            pt = get_portfolio_tracker()
            totals = pt.get_total_value()
            perf = pt.get_performance_summary()
            lines.append("-- PORTFOLIO --")
            lines.append(f"Active holdings: {totals.get('active_holdings', 0)}")
            lines.append(f"Total cost: GBP {totals.get('total_cost_gbp', 0):.2f}")
            lines.append(f"Unrealised P&L: GBP {totals.get('unrealised_pnl_gbp', 0):.2f}")
            lines.append(f"Realised P&L: GBP {totals.get('realised_pnl_gbp', 0):.2f}")
            lines.append(f"Total fees: GBP {totals.get('total_fees_gbp', 0):.2f}")
            lines.append(f"Win rate: {perf.get('win_rate_pct', 0)}%")
            if perf.get("best_trade"):
                lines.append(f"Best trade: {perf['best_trade']['symbol']} (+GBP {perf['best_trade']['pnl_gbp']:.2f})")
            if perf.get("worst_trade"):
                lines.append(f"Worst trade: {perf['worst_trade']['symbol']} (GBP {perf['worst_trade']['pnl_gbp']:.2f})")
            lines.append("")
        except Exception as e:
            lines.append(f"Portfolio data unavailable: {e}")
            lines.append("")

        # ── This week's trades ──
        try:
            from ml.portfolio_tracker import get_portfolio_tracker
            pt = get_portfolio_tracker()
            history = pt.get_trade_history(limit=200)
            week_trades = [
                t for t in history
                if t.get("timestamp", "") >= week_ago.isoformat()
            ]
            buys = [t for t in week_trades if t.get("side") == "buy"]
            sells = [t for t in week_trades if t.get("side") == "sell"]
            lines.append("-- TRADES THIS WEEK --")
            lines.append(f"Buys: {len(buys)}  |  Sells: {len(sells)}")
            for t in week_trades:
                side = t.get("side", "?").upper()
                sym = t.get("symbol", "?")
                amt = t.get("amount_gbp", 0)
                pnl = t.get("realised_pnl_gbp")
                pnl_str = f"  P&L: GBP {pnl:.2f}" if pnl is not None else ""
                lines.append(f"  {side} {sym} GBP {amt:.2f}{pnl_str}")
            if not week_trades:
                lines.append("  No trades this week")
            lines.append("")
        except Exception as e:
            lines.append(f"Trade history unavailable: {e}")
            lines.append("")

        # ── Trading engine status ──
        try:
            from ml.trading_engine import get_trading_engine
            te = get_trading_engine()
            status = te.get_status()
            lines.append("-- TRADING ENGINE --")
            lines.append(f"Active: {status.get('active', False)}")
            lines.append(f"Daily budget: GBP {status.get('daily_budget_gbp', 0):.2f}")
            lines.append(f"Remaining today: GBP {status.get('remaining_today_gbp', 0):.2f}")
            lines.append("")
        except Exception as e:
            lines.append(f"Trading engine data unavailable: {e}")
            lines.append("")

        # ── Gemini budget ──
        try:
            from services.gemini_budget import get_gemini_budget
            gb = get_gemini_budget()
            gs = gb.get_status()
            lines.append("-- GEMINI BUDGET (today) --")
            lines.append(f"Spent: GBP {gs.get('estimated_spent_gbp', 0):.4f} / {gs.get('daily_limit_gbp', 0):.2f}")
            lines.append(f"Usage: {gs.get('pct_used', 0)}%")
            calls = gs.get("calls", {})
            if calls:
                lines.append(f"Calls: {calls}")
            lines.append("")
        except Exception as e:
            lines.append(f"Gemini budget data unavailable: {e}")
            lines.append("")

        # ── Scan status ──
        try:
            from ml.scan_loop import get_scan_loop
            sl = get_scan_loop()
            ss = sl.get_status()
            lines.append("-- SCAN LOOP --")
            lines.append(f"Scheduler running: {ss.get('scheduler_running', False)}")
            lines.append(f"Last scan: {ss.get('last_scan', 'never')}")
            lines.append(f"Next scan: {ss.get('next_scan', 'unknown')}")
            lines.append("")
        except Exception as e:
            lines.append(f"Scan data unavailable: {e}")
            lines.append("")

        return "\n".join(lines)

    def cleanup_old_logs(self, max_age_days: int = 30):
        """Delete log files older than max_age_days to prevent disk bloat on Pi."""
        import glob
        from pathlib import Path

        log_dirs = [
            "data/agent_runner_logs",
            "data/monitor_logs",
            "data/scan_logs",
        ]
        cutoff = time.time() - (max_age_days * 86400)
        total_removed = 0

        for log_dir in log_dirs:
            dirpath = Path(log_dir)
            if not dirpath.exists():
                continue
            for f in dirpath.iterdir():
                if f.is_file() and f.stat().st_mtime < cutoff:
                    try:
                        f.unlink()
                        total_removed += 1
                    except OSError:
                        pass

        # Also remove old training data CSVs (keep only the newest)
        training_files = sorted(glob.glob("data/training_data_*.csv"))
        if len(training_files) > 1:
            for old_file in training_files[:-1]:
                try:
                    Path(old_file).unlink()
                    total_removed += 1
                except OSError:
                    pass

        if total_removed:
            logger.info(f"Log cleanup: removed {total_removed} old files")

    def start_scheduler(self):
        """Start the ML retraining scheduler in a background thread."""
        if self._running:
            logger.info("ML scheduler already running")
            return

        # Schedule weekly performance report every Monday at 9 AM
        schedule.every().monday.at("09:00").do(self.weekly_report_job)

        # Schedule log cleanup every Sunday at 3 AM
        schedule.every().sunday.at("03:00").do(self.cleanup_old_logs)

        logger.info("ML Scheduler started:")
        logger.info("  - Weekly report: Every Monday at 9:00 AM")
        logger.info("  - Log cleanup: Every Sunday at 3:00 AM")

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        """Background loop that checks for pending scheduled jobs."""
        while self._running:
            try:
                schedule.run_pending()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            time.sleep(60)  # Check every minute

    def stop_scheduler(self):
        """Stop the scheduler."""
        self._running = False
        schedule.clear()
        logger.info("ML Scheduler stopped")

    def get_status(self) -> dict:
        """Get scheduler status."""
        jobs = []
        for job in schedule.get_jobs():
            jobs.append({
                "job": str(job),
                "next_run": str(job.next_run) if job.next_run else None,
            })
        return {
            "running": self._running,
            "scheduled_jobs": jobs,
        }


# ─── Singleton ────────────────────────────────────────────────

_scheduler = None


def get_ml_scheduler() -> MLScheduler:
    """Get or create the singleton ML scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = MLScheduler()
    return _scheduler
