"""
Unit tests for Scan Loop.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("SCAN_ENABLED", "false")

from ml.scan_loop import ScanLoop


class TestScanLoop:
    """Tests for the ScanLoop class."""

    @pytest.fixture
    def scan_loop(self, tmp_data_dir):
        with patch.dict(os.environ, {
            "SCAN_TIME": "12:00",
            "SCAN_MAX_COINS": "5",
            "SCAN_MIN_GEM_SCORE": "5.0",
            "SCAN_MAX_PROPOSALS": "2",
        }):
            with patch("ml.scan_loop.SCAN_LOGS_DIR", tmp_data_dir / "scan_logs"):
                with patch("ml.scan_loop.AUDIT_LOG_FILE", tmp_data_dir / "audit.jsonl"):
                    loop = ScanLoop()
        return loop

    def test_init_config(self, scan_loop):
        assert scan_loop.scan_time == "12:00"
        assert scan_loop.max_coins_per_scan == 5
        assert scan_loop.min_gem_score == 5.0
        assert scan_loop.max_proposals_per_scan == 2

    def test_get_status(self, scan_loop):
        status = scan_loop.get_status()
        assert "scan_time" in status
        assert "last_scan" in status

    @patch("ml.scan_loop.ScanLoop._refresh_data", return_value=True)
    @patch("ml.scan_loop.ScanLoop._get_tradeable_coins", return_value=[])
    def test_run_scan_no_coins(self, mock_coins, mock_refresh, scan_loop):
        result = scan_loop.run_scan(triggered_by="test")
        assert result is not None
        assert result.get("coins_scanned", 0) == 0
