"""
Unit tests for the Exchange Manager.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from ml.exchange_manager import ExchangeManager


class TestExchangeManager:
    """Tests for ExchangeManager."""

    @pytest.fixture
    def manager(self, tmp_data_dir):
        """Create an ExchangeManager with mocked env."""
        with patch.dict(os.environ, {"EXCHANGE_PRIORITY": "kraken"}):
            with patch("ml.exchange_manager.PAIRS_CACHE_FILE", tmp_data_dir / "pairs.json"):
                mgr = ExchangeManager()
        return mgr

    def test_init_priority(self, manager):
        assert manager.exchange_priority == ["kraken"]

    def test_get_exchange_config_kraken(self, manager):
        with patch.dict(os.environ, {
            "KRAKEN_API_KEY": "kkey",
            "KRAKEN_PRIVATE_KEY": "ksecret",
        }):
            config = manager._get_exchange_config("kraken")
        assert config is not None
        assert config["apiKey"] == "kkey"

    def test_get_exchange_config_missing(self, manager):
        with patch.dict(os.environ, {}, clear=True):
            config = manager._get_exchange_config("kraken")
        assert config is None

    def test_is_tradeable(self, manager):
        manager._pairs = {
            "kraken": {"BTC/GBP", "ETH/GBP", "TEST/USD"},
        }
        manager._pairs_loaded = True
        manager._rebuild_coin_exchange_map()
        assert manager.is_tradeable("BTC") is True
        assert manager.is_tradeable("UNKNOWN") is False

    def test_get_exchanges_for_coin(self, manager):
        manager._pairs = {
            "kraken": {"BTC/GBP", "BTC/USD", "ETH/USD"},
        }
        manager._pairs_loaded = True
        manager._rebuild_coin_exchange_map()
        exchanges = manager.get_exchanges_for_coin("BTC")
        assert "kraken" in exchanges

    def test_filter_tradeable_coins(self, manager):
        manager._pairs = {
            "kraken": {"BTC/GBP", "ETH/GBP"},
        }
        manager._pairs_loaded = True
        manager._rebuild_coin_exchange_map()
        result = manager.filter_tradeable_coins(["BTC", "ETH", "FAKECOIN"])
        assert len(result) == 2
        symbols = [r["symbol"] for r in result]
        assert "BTC" in symbols
        assert "ETH" in symbols

    def test_find_best_pair(self, manager):
        manager._pairs = {
            "kraken": {"BTC/GBP", "BTC/USD"},
        }
        manager._pairs_loaded = True
        manager._rebuild_coin_exchange_map()
        result = manager.find_best_pair("BTC")
        assert result is not None
        assert result[0] == "kraken"
        assert result[1] == "BTC/GBP"  # GBP preferred

    def test_find_best_pair_usd_fallback(self, manager):
        manager._pairs = {
            "kraken": {"BTC/USD"},
        }
        manager._pairs_loaded = True
        manager._rebuild_coin_exchange_map()
        result = manager.find_best_pair("BTC")
        assert result is not None
        assert result[1] == "BTC/USD"

    def test_find_best_pair_not_found(self, manager):
        manager._pairs = {"kraken": {"BTC/GBP"}}
        manager._pairs_loaded = True
        manager._rebuild_coin_exchange_map()
        result = manager.find_best_pair("UNKNOWN")
        assert result is None

    def test_get_tradeable_summary(self, manager):
        manager._pairs = {
            "kraken": {"BTC/GBP", "ETH/GBP", "BTC/USD"},
        }
        manager._pairs_loaded = True
        manager._rebuild_coin_exchange_map()
        summary = manager.get_tradeable_summary()
        assert summary["exchanges"]["kraken"] == 3
        assert summary["total_tradeable_coins"] >= 2

    def test_pairs_cache_save_load(self, manager, tmp_data_dir):
        cache_path = tmp_data_dir / "pairs.json"
        with patch("ml.exchange_manager.PAIRS_CACHE_FILE", cache_path):
            manager._pairs = {"kraken": {"BTC/GBP", "ETH/GBP"}}
            manager._save_pairs_cache()
            assert cache_path.exists()

            manager._pairs = {}
            loaded = manager._load_pairs_cache()
            assert loaded is True
            assert "BTC/GBP" in manager._pairs.get("kraken", set())
