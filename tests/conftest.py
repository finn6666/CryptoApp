"""
Shared test fixtures for CryptoApp test suite.
"""

import os
import json
import pytest
import tempfile
import shutil
from unittest.mock import MagicMock, patch
from datetime import datetime

# Ensure test env vars are set before any imports
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("GOOGLE_API_KEY", "test-google-key")
os.environ.setdefault("TRADING_API_KEY", "test-trading-key")


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Provide a temporary data directory for tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "trades").mkdir()
    (data_dir / "agent_memory").mkdir()
    (data_dir / "scan_logs").mkdir()
    return data_dir


@pytest.fixture
def sample_coin_data():
    """Sample coin data dict as used throughout the app."""
    return {
        "symbol": "TEST",
        "name": "TestCoin",
        "price": 0.05,
        "market_cap": 500000,
        "volume_24h": 120000,
        "percent_change_1h": 2.5,
        "percent_change_24h": 10.0,
        "percent_change_7d": -5.0,
        "circulating_supply": 10000000,
        "total_supply": 50000000,
        "max_supply": 100000000,
    }


@pytest.fixture
def sample_trade_proposal():
    """Sample TradeProposal data."""
    return {
        "symbol": "TEST",
        "side": "buy",
        "amount_gbp": 0.02,
        "current_price": 0.05,
        "reason": "Strong fundamentals and technical setup",
        "confidence": 80,
        "recommendation": "BUY",
    }


@pytest.fixture
def mock_exchange():
    """Mock ccxt exchange for trading tests."""
    exchange = MagicMock()
    exchange.markets = {
        "TEST/GBP": {"symbol": "TEST/GBP"},
        "TEST/USD": {"symbol": "TEST/USD"},
        "BTC/GBP": {"symbol": "BTC/GBP"},
    }
    exchange.fetch_ticker.return_value = {"last": 0.05, "bid": 0.049, "ask": 0.051}
    exchange.create_market_buy_order.return_value = {
        "id": "order-123",
        "filled": 0.4,
        "average": 0.05,
        "status": "closed",
    }
    exchange.create_market_sell_order.return_value = {
        "id": "order-456",
        "filled": 0.4,
        "average": 0.05,
        "status": "closed",
    }
    exchange.load_markets.return_value = exchange.markets
    return exchange


@pytest.fixture
def mock_ccxt(mock_exchange):
    """Patch ccxt to return mock exchange."""
    with patch.dict("sys.modules", {"ccxt": MagicMock()}):
        import sys
        ccxt_mock = sys.modules["ccxt"]
        ccxt_mock.kraken.return_value = mock_exchange
        yield ccxt_mock


@pytest.fixture
def live_prices():
    """Sample live prices dict."""
    return {
        "TEST": 0.06,
        "BTC": 45000.0,
        "ETH": 3000.0,
        "DOGE": 0.08,
    }
