"""
ML Monitoring for CryptoApp
Persistent logging, performance tracking, and alerting thresholds.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

MONITOR_LOG_FILE = Path("data/ml_monitor.jsonl")
MONITOR_ALERTS_FILE = Path("data/ml_alerts.json")


class MLMonitor:
    """
    ML performance monitor with persistent logging and alerting.

    - Logs predictions to disk (JSONL) for historical analysis
    - Tracks in-memory stats for fast dashboard access
    - Fires alerts when thresholds are breached
    """

    # ─── Alerting Thresholds ──────────────────────────────────
    ALERT_HIGH_ERROR_RATE = 0.25       # >25% prediction errors
    ALERT_SLOW_RESPONSE_MS = 5000      # >5s average response
    ALERT_LOW_CACHE_HIT = 0.10         # <10% cache hits (when >50 predictions)
    ALERT_CONSECUTIVE_ERRORS = 5       # 5 errors in a row

    def __init__(self):
        self.performance_log: List[Dict] = []
        self.logger = logging.getLogger(__name__)
        self._consecutive_errors = 0
        self._alerts: List[Dict] = []
        MONITOR_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._load_alerts()

    # ─── Prediction Logging ───────────────────────────────────

    def log_prediction(
        self,
        symbol: str,
        prediction: float,
        actual: Optional[float] = None,
        response_time: float = 0,
        cached: bool = False,
    ):
        """Log a prediction — persists to disk and keeps in-memory window."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "prediction": prediction,
            "actual": actual,
            "response_time": response_time,
            "cached": cached,
            "error": (
                actual is not None and abs(prediction - actual) > 0.05
            ) if actual else None,
        }

        # In-memory (last 500)
        self.performance_log.append(entry)
        if len(self.performance_log) > 500:
            self.performance_log = self.performance_log[-500:]

        # Persistent (JSONL append)
        try:
            with open(MONITOR_LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            self.logger.debug(f"Could not persist monitor log: {e}")

        # Reset consecutive error counter on success
        self._consecutive_errors = 0

        self.logger.info(f"ML prediction logged for {symbol}: {prediction}")

    # ─── Error Logging ────────────────────────────────────────

    def log_error(self, error_type: str, error_message: str, symbol: str = None):
        """Log an ML-related error and check alert thresholds."""
        self.logger.error(
            f"ML Error [{error_type}] for {symbol or 'N/A'}: {error_message}"
        )
        self._consecutive_errors += 1

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "error_type": error_type,
            "error_message": error_message,
        }
        try:
            with open(MONITOR_LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

        # Consecutive-error alert
        if self._consecutive_errors >= self.ALERT_CONSECUTIVE_ERRORS:
            self._fire_alert(
                "consecutive_errors",
                f"{self._consecutive_errors} consecutive ML errors — latest: {error_type}: {error_message}",
            )

    # ─── Statistics ───────────────────────────────────────────

    def get_basic_stats(self, hours: int = 24) -> Dict:
        """Get performance statistics for the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [
            log for log in self.performance_log
            if datetime.fromisoformat(log["timestamp"]) >= cutoff
        ]

        if not recent:
            return {"message": "No recent predictions logged"}

        total = len(recent)
        cached = sum(1 for log in recent if log.get("cached", False))
        errors = sum(1 for log in recent if log.get("error") is True)
        avg_rt = sum(log.get("response_time", 0) for log in recent) / total

        stats = {
            "total_predictions": total,
            "cache_hit_rate": round(cached / total, 3) if total else 0,
            "error_rate": round(errors / total, 3) if total else 0,
            "avg_response_time": round(avg_rt, 3),
            "period_hours": hours,
            "consecutive_errors": self._consecutive_errors,
            "active_alerts": len([a for a in self._alerts if not a.get("resolved")]),
        }

        # Check thresholds and fire alerts
        self._check_thresholds(stats)

        return stats

    def get_detailed_stats(self, hours: int = 24) -> Dict:
        """Extended stats including per-symbol breakdown and alert history."""
        basic = self.get_basic_stats(hours)
        if "message" in basic:
            return basic

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [
            log for log in self.performance_log
            if datetime.fromisoformat(log["timestamp"]) >= cutoff
        ]

        # Per-symbol breakdown
        symbols: Dict[str, Dict] = {}
        for log in recent:
            sym = log.get("symbol", "unknown")
            if sym not in symbols:
                symbols[sym] = {"count": 0, "errors": 0, "total_rt": 0}
            symbols[sym]["count"] += 1
            if log.get("error"):
                symbols[sym]["errors"] += 1
            symbols[sym]["total_rt"] += log.get("response_time", 0)

        per_symbol = {}
        for sym, data in symbols.items():
            per_symbol[sym] = {
                "predictions": data["count"],
                "error_rate": round(data["errors"] / data["count"], 3),
                "avg_response_time": round(data["total_rt"] / data["count"], 3),
            }

        return {
            **basic,
            "per_symbol": per_symbol,
            "alerts": self._alerts[-20:],  # Last 20 alerts
        }

    def get_persistent_history(self, limit: int = 200) -> List[Dict]:
        """Read recent entries from the persistent JSONL log."""
        if not MONITOR_LOG_FILE.exists():
            return []
        try:
            lines = MONITOR_LOG_FILE.read_text().strip().split("\n")
            entries = [json.loads(line) for line in lines[-limit:] if line.strip()]
            return list(reversed(entries))
        except Exception as e:
            self.logger.error(f"Failed to read monitor log: {e}")
            return []

    # ─── Alerting ─────────────────────────────────────────────

    def _check_thresholds(self, stats: Dict):
        """Check stats against alert thresholds."""
        if stats.get("error_rate", 0) > self.ALERT_HIGH_ERROR_RATE:
            self._fire_alert(
                "high_error_rate",
                f"Error rate {stats['error_rate']*100:.1f}% exceeds {self.ALERT_HIGH_ERROR_RATE*100:.0f}% threshold",
            )

        if stats.get("avg_response_time", 0) > self.ALERT_SLOW_RESPONSE_MS / 1000:
            self._fire_alert(
                "slow_response",
                f"Avg response {stats['avg_response_time']:.1f}s exceeds {self.ALERT_SLOW_RESPONSE_MS/1000:.0f}s threshold",
            )

        total = stats.get("total_predictions", 0)
        if total > 50 and stats.get("cache_hit_rate", 1) < self.ALERT_LOW_CACHE_HIT:
            self._fire_alert(
                "low_cache_hit",
                f"Cache hit rate {stats['cache_hit_rate']*100:.1f}% below {self.ALERT_LOW_CACHE_HIT*100:.0f}% threshold",
            )

    def _fire_alert(self, alert_type: str, message: str):
        """Record an alert. Deduplicates within 1-hour windows."""
        now = datetime.utcnow()
        # Deduplicate: don't re-fire same type within 1 hour
        for alert in self._alerts:
            if (
                alert["type"] == alert_type
                and not alert.get("resolved")
                and (now - datetime.fromisoformat(alert["fired_at"])).total_seconds() < 3600
            ):
                return

        alert = {
            "type": alert_type,
            "message": message,
            "fired_at": now.isoformat(),
            "resolved": False,
        }
        self._alerts.append(alert)
        self._save_alerts()
        self.logger.warning(f"ML ALERT [{alert_type}]: {message}")

        # Try email alert (non-blocking)
        try:
            from ml.error_handling import send_error_alert
            send_error_alert(
                subject=f"ML Alert: {alert_type}",
                body=message,
                category=f"ml_monitor_{alert_type}",
            )
        except Exception:
            pass

    def resolve_alert(self, alert_type: str):
        """Mark alerts of a given type as resolved."""
        for alert in self._alerts:
            if alert["type"] == alert_type and not alert.get("resolved"):
                alert["resolved"] = True
                alert["resolved_at"] = datetime.utcnow().isoformat()
        self._save_alerts()

    def get_alerts(self, include_resolved: bool = False) -> List[Dict]:
        """Get current alerts."""
        if include_resolved:
            return self._alerts[-50:]
        return [a for a in self._alerts if not a.get("resolved")][-50:]

    # ─── Persistence ──────────────────────────────────────────

    def _save_alerts(self):
        try:
            with open(MONITOR_ALERTS_FILE, "w") as f:
                json.dump(self._alerts[-100:], f, indent=2)
        except Exception:
            pass

    def _load_alerts(self):
        if MONITOR_ALERTS_FILE.exists():
            try:
                with open(MONITOR_ALERTS_FILE) as f:
                    self._alerts = json.load(f)
            except Exception:
                self._alerts = []


# Global monitor instance
ml_monitor = MLMonitor()
