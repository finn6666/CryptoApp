"""
Historical Gem Score Tracker
Logs every gem detector prediction to a JSONL file for tracking
detector accuracy over time.
"""

import json
import logging
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

SCORE_LOG_FILE = Path("data/gem_score_history.jsonl")
DAILY_SUMMARY_DIR = Path("data/gem_score_summaries")


class GemScoreTracker:
    """Tracks historical gem scores for accuracy analysis."""

    def __init__(self):
        SCORE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        DAILY_SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    def record_score(
        self,
        symbol: str,
        gem_probability: float,
        gem_score: float,
        recommendation: str,
        source: str = "gem_detector",
        extra: Optional[Dict] = None,
    ):
        """Log a single gem detector prediction."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "date": date.today().isoformat(),
            "symbol": symbol,
            "gem_probability": round(gem_probability, 4),
            "gem_score": round(gem_score, 2),
            "recommendation": recommendation,
            "source": source,
        }
        if extra:
            entry["extra"] = extra
        try:
            with open(SCORE_LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.warning(f"Failed to record gem score for {symbol}: {e}")

    def get_history(
        self,
        symbol: Optional[str] = None,
        days: int = 30,
        limit: int = 500,
    ) -> List[Dict]:
        """
        Get historical gem scores, optionally filtered by symbol.
        Returns newest first.
        """
        if not SCORE_LOG_FILE.exists():
            return []
        try:
            entries = []
            with open(SCORE_LOG_FILE) as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if symbol and entry.get("symbol") != symbol.upper():
                            continue
                        entries.append(entry)
                    except Exception:
                        pass
            # Newest first, apply limit
            return list(reversed(entries[-limit:]))
        except Exception as e:
            logger.warning(f"Failed to read gem score history: {e}")
            return []

    def get_symbol_trend(self, symbol: str, limit: int = 50) -> Dict[str, Any]:
        """Get trend data for a specific symbol's gem scores over time."""
        history = self.get_history(symbol=symbol, limit=limit)
        if not history:
            return {"symbol": symbol, "entries": 0}

        scores = [h["gem_score"] for h in history]
        probs = [h["gem_probability"] for h in history]

        return {
            "symbol": symbol,
            "entries": len(history),
            "latest_score": scores[0] if scores else 0,
            "avg_score": round(sum(scores) / len(scores), 2),
            "min_score": round(min(scores), 2),
            "max_score": round(max(scores), 2),
            "latest_probability": probs[0] if probs else 0,
            "avg_probability": round(sum(probs) / len(probs), 4),
            "trend": "improving" if len(scores) >= 2 and scores[0] > scores[-1] else "declining" if len(scores) >= 2 and scores[0] < scores[-1] else "stable",
            "first_seen": history[-1].get("timestamp"),
            "last_seen": history[0].get("timestamp"),
        }

    def get_accuracy_report(self) -> Dict[str, Any]:
        """
        Compare historic gem predictions against actual outcomes.
        Requires RL outcome data to be available in portfolio.
        """
        history = self.get_history(limit=1000)
        if not history:
            return {"total_predictions": 0}

        buy_predictions = [h for h in history if h.get("recommendation") == "BUY"]
        hold_predictions = [h for h in history if h.get("recommendation") in ("HOLD", "WATCH")]
        avoid_predictions = [h for h in history if h.get("recommendation") == "AVOID"]

        scores = [h["gem_score"] for h in history]
        symbols = set(h["symbol"] for h in history)

        return {
            "total_predictions": len(history),
            "unique_symbols": len(symbols),
            "buy_calls": len(buy_predictions),
            "hold_calls": len(hold_predictions),
            "avoid_calls": len(avoid_predictions),
            "avg_gem_score": round(sum(scores) / len(scores), 2) if scores else 0,
            "date_range": {
                "earliest": history[-1].get("date") if history else None,
                "latest": history[0].get("date") if history else None,
            },
        }

    def generate_daily_summary(self) -> Dict[str, Any]:
        """Generate a summary of today's predictions."""
        today = date.today().isoformat()
        history = self.get_history(limit=500)
        today_entries = [h for h in history if h.get("date") == today]

        if not today_entries:
            return {"date": today, "predictions": 0}

        summary = {
            "date": today,
            "predictions": len(today_entries),
            "avg_gem_score": round(
                sum(h["gem_score"] for h in today_entries) / len(today_entries), 2
            ),
            "buy_calls": len([h for h in today_entries if h.get("recommendation") == "BUY"]),
            "symbols": list(set(h["symbol"] for h in today_entries)),
        }

        # Save to daily file
        try:
            summary_file = DAILY_SUMMARY_DIR / f"{today}.json"
            with open(summary_file, "w") as f:
                json.dump(summary, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save daily summary: {e}")

        return summary


# ─── Singleton ────────────────────────────────────────────────

_tracker: Optional[GemScoreTracker] = None


def get_gem_score_tracker() -> GemScoreTracker:
    global _tracker
    if _tracker is None:
        _tracker = GemScoreTracker()
    return _tracker
