"""
Unit tests for ML Monitoring.
"""

import os
import pytest
from datetime import datetime, timedelta

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from ml.monitoring import MLMonitor


class TestMLMonitor:
    """Tests for the MLMonitor class."""

    @pytest.fixture
    def monitor(self):
        return MLMonitor()

    def test_log_prediction(self, monitor):
        monitor.log_prediction("BTC", 0.05, response_time=0.1)
        assert len(monitor.performance_log) == 1

    def test_log_prediction_max_entries(self, monitor):
        for i in range(600):
            monitor.log_prediction(f"COIN{i}", 0.01)
        assert len(monitor.performance_log) == 500

    def test_log_prediction_cached(self, monitor):
        monitor.log_prediction("BTC", 0.05, cached=True)
        assert monitor.performance_log[0]["cached"] is True

    def test_get_basic_stats_empty(self, monitor):
        stats = monitor.get_basic_stats()
        assert "message" in stats or "total_predictions" in stats

    def test_get_basic_stats(self, monitor):
        for _ in range(10):
            monitor.log_prediction("BTC", 0.05, response_time=0.1)
        monitor.log_prediction("ETH", 0.03, response_time=0.2, cached=True)
        stats = monitor.get_basic_stats()
        assert stats["total_predictions"] == 11
        assert stats["cache_hit_rate"] > 0

    def test_log_error(self, monitor):
        # Should not raise
        monitor.log_error("TestError", "Something went wrong", symbol="BTC")
