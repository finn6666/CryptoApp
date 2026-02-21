import schedule
import time
import logging
import asyncio
import threading
from datetime import datetime
from ml.training_pipeline import CryptoMLPipeline
from ml.weekly_report import WeeklyReportGenerator
import os

logger = logging.getLogger(__name__)


class MLScheduler:
    def __init__(self):
        self.pipeline = CryptoMLPipeline()
        self.weekly_reporter = WeeklyReportGenerator()

        # Use relative paths that work anywhere
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(project_root, "data")
        self.model_dir = os.path.join(project_root, "models")

        # Will be set when integrated with the main app
        self.gem_detector = None
        self.analyzer = None

        self._thread = None
        self._running = False
        self._last_retrain = None
        self._last_retrain_status = None

    def weekly_retrain(self):
        """Weekly retraining job — fetches latest data, retrains, exports ONNX."""
        logger.info(f"Starting weekly retrain at {datetime.utcnow().isoformat()}")

        try:
            # Fetch latest data via the data pipeline
            data_file = self.fetch_latest_data()

            # Retrain model
            metrics = self.pipeline.train_model(data_file)

            # Export updated models (sklearn + ONNX)
            self.pipeline.export_model(self.model_dir)

            # Reload ONNX engine if available
            try:
                from ml.onnx_inference import get_onnx_engine
                engine = get_onnx_engine()
                engine._load()
                logger.info("ONNX engine reloaded after retraining")
            except Exception as onnx_err:
                logger.debug(f"ONNX reload skipped: {onnx_err}")

            self._last_retrain = datetime.utcnow().isoformat()
            self._last_retrain_status = {"success": True, "metrics": metrics}
            logger.info(f"Retraining completed. Metrics: {metrics}")

        except Exception as e:
            self._last_retrain = datetime.utcnow().isoformat()
            self._last_retrain_status = {"success": False, "error": str(e)}
            logger.error(f"Retraining failed: {e}")
            self.send_alert(f"ML retraining failed: {e}")

    def fetch_latest_data(self) -> str:
        """
        Fetch latest crypto data for training.
        Tries the CryptoDataPipeline first, then falls back to existing files.
        """
        # Try collecting fresh data via the data pipeline
        try:
            from ml.data_pipeline import CryptoDataPipeline
            dp = CryptoDataPipeline()
            loop = asyncio.new_event_loop()
            data_file = loop.run_until_complete(dp.collect_training_data(days=30))
            loop.close()
            logger.info(f"Fetched fresh training data: {data_file}")
            return data_file
        except Exception as e:
            logger.warning(f"Live data fetch failed ({e}), trying existing files")

        # Fall back to the latest existing training file
        try:
            from ml.data_pipeline import CryptoDataPipeline
            dp = CryptoDataPipeline()
            return dp.get_latest_training_file()
        except FileNotFoundError:
            pass

        # Last resort: sample training data
        sample = os.path.join(self.model_dir, "sample_training_data.csv")
        if os.path.exists(sample):
            logger.warning("Using sample training data — no live data available")
            return sample

        raise FileNotFoundError("No training data available")

    def send_alert(self, message: str):
        """Send alert for failed operations via error_handling module."""
        try:
            from ml.error_handling import send_email_alert
            send_email_alert("ML Scheduler Alert", message)
        except Exception:
            logger.error(f"ALERT (email failed): {message}")

    def weekly_report_job(self):
        """Generate and send weekly email report."""
        logger.info(f"Starting weekly report generation at {datetime.utcnow().isoformat()}")

        try:
            if not self.gem_detector or not self.analyzer:
                logger.warning("Gem detector or analyzer not initialized for weekly report")
                return

            result = self.weekly_reporter.generate_and_send_report(
                self.gem_detector,
                self.analyzer
            )

            if result['success']:
                logger.info(f"Weekly report sent. Opportunities: {result['opportunities_count']}")
            else:
                logger.error(f"Weekly report failed: {result.get('error', 'Unknown')}")

        except Exception as e:
            logger.error(f"Weekly report generation failed: {e}")
            self.send_alert(f"Weekly report failed: {e}")

    def start_scheduler(self):
        """Start the ML retraining scheduler in a background thread."""
        if self._running:
            logger.info("ML scheduler already running")
            return

        # Schedule retraining every Sunday at 2 AM
        schedule.every().sunday.at("02:00").do(self.weekly_retrain)

        # Schedule weekly report every Monday at 9 AM
        schedule.every().monday.at("09:00").do(self.weekly_report_job)

        logger.info("ML Scheduler started:")
        logger.info("  - Model retraining: Every Sunday at 2:00 AM")
        logger.info("  - Weekly report: Every Monday at 9:00 AM")

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
            "last_retrain": self._last_retrain,
            "last_retrain_status": self._last_retrain_status,
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
