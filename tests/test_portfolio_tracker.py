"""
Unit tests for the Portfolio Tracker.
"""

import os
import json
import pytest
from unittest.mock import patch
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from ml.portfolio_tracker import PortfolioTracker


class TestPortfolioTracker:
    """Tests for the PortfolioTracker class."""

    @pytest.fixture
    def tracker(self, tmp_data_dir):
        """Create a PortfolioTracker with temp storage."""
        with patch("ml.portfolio_tracker.PORTFOLIO_FILE", tmp_data_dir / "portfolio.json"):
            yield PortfolioTracker()

    def test_initial_state(self, tracker):
        assert tracker.holdings == {}
        assert tracker.trade_log == []

    def test_record_buy(self, tracker):
        trade = tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.05, amount_gbp=5.0, exchange="kraken",
        )
        assert trade["symbol"] == "TEST"
        assert trade["side"] == "buy"
        assert "TEST" in tracker.holdings
        assert tracker.holdings["TEST"]["quantity"] == 100

    def test_record_multiple_buys_averages(self, tracker):
        tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.05, amount_gbp=5.0,
        )
        tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.10, amount_gbp=10.0,
        )
        h = tracker.holdings["TEST"]
        assert h["quantity"] == 200
        assert h["total_cost_gbp"] == 15.0
        assert h["avg_entry_price"] == 15.0 / 200

    def test_record_sell(self, tracker):
        tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.05, amount_gbp=5.0,
        )
        trade = tracker.record_trade(
            symbol="TEST", side="sell", quantity=50,
            price=0.10, amount_gbp=5.0,
        )
        assert tracker.holdings["TEST"]["quantity"] == 50
        assert "realised_pnl_gbp" in trade

    def test_full_sell_closes_position(self, tracker):
        tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.05, amount_gbp=5.0,
        )
        tracker.record_trade(
            symbol="TEST", side="sell", quantity=100,
            price=0.10, amount_gbp=10.0,
        )
        assert tracker.holdings["TEST"]["quantity"] == 0
        assert "closed_at" in tracker.holdings["TEST"]

    def test_get_holdings_empty(self, tracker):
        holdings = tracker.get_holdings()
        assert holdings == []

    def test_get_holdings_with_live_prices(self, tracker, live_prices):
        tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.05, amount_gbp=5.0,
        )
        holdings = tracker.get_holdings(live_prices)
        assert len(holdings) == 1
        assert "unrealised_pnl_gbp" in holdings[0]
        assert "current_value_gbp" in holdings[0]

    def test_get_total_value(self, tracker, live_prices):
        tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.05, amount_gbp=5.0,
        )
        total = tracker.get_total_value(live_prices)
        assert "total_cost_gbp" in total
        assert "total_value_gbp" in total
        assert total["active_holdings"] == 1

    def test_check_sell_signals_profit_target(self, tracker):
        tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.05, amount_gbp=5.0,
        )
        # Price doubled → 100% gain > 20% target
        signals = tracker.check_sell_signals({"TEST": 0.10})
        assert len(signals) == 1
        assert "Profit target" in signals[0]["reason"]

    def test_check_sell_signals_stop_loss(self, tracker):
        tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.05, amount_gbp=5.0,
        )
        # Price dropped 50%
        signals = tracker.check_sell_signals({"TEST": 0.025})
        assert len(signals) == 1
        assert "Stop loss" in signals[0]["reason"]

    def test_check_sell_signals_no_signal(self, tracker):
        tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.05, amount_gbp=5.0,
        )
        # Price slightly up — no signal
        signals = tracker.check_sell_signals({"TEST": 0.055})
        assert len(signals) == 0

    def test_trade_history(self, tracker):
        tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.05, amount_gbp=5.0,
        )
        history = tracker.get_trade_history()
        assert len(history) == 1
        assert history[0]["symbol"] == "TEST"

    def test_persistence(self, tracker, tmp_data_dir):
        tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.05, amount_gbp=5.0,
        )
        # Create new tracker pointing to same file
        with patch("ml.portfolio_tracker.PORTFOLIO_FILE", tmp_data_dir / "portfolio.json"):
            tracker2 = PortfolioTracker()
        assert "TEST" in tracker2.holdings
        assert len(tracker2.trade_log) == 1

    def test_get_closed_positions_empty(self, tracker):
        assert tracker.get_closed_positions() == []

    def test_get_closed_positions_after_full_sell(self, tracker):
        tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.05, amount_gbp=5.0, fee_gbp=0.01,
        )
        tracker.record_trade(
            symbol="TEST", side="sell", quantity=100,
            price=0.10, amount_gbp=10.0, fee_gbp=0.02,
        )
        closed = tracker.get_closed_positions()
        assert len(closed) == 1
        assert closed[0]["symbol"] == "TEST"
        assert closed[0]["won"] is True
        assert closed[0]["total_fees_gbp"] == 0.03
        assert "closed_at" in closed[0]

    def test_get_closed_positions_excludes_open(self, tracker):
        tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.05, amount_gbp=5.0,
        )
        closed = tracker.get_closed_positions()
        assert len(closed) == 0

    def test_performance_summary_empty(self, tracker):
        perf = tracker.get_performance_summary()
        assert perf["total_trades"] == 0
        assert perf["win_rate_pct"] == 0
        assert perf["best_trade"] is None

    def test_performance_summary_with_trades(self, tracker):
        # Buy and sell at profit
        tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.05, amount_gbp=5.0, fee_gbp=0.01,
        )
        tracker.record_trade(
            symbol="TEST", side="sell", quantity=100,
            price=0.10, amount_gbp=10.0, fee_gbp=0.02,
        )
        perf = tracker.get_performance_summary()
        assert perf["total_trades"] == 2
        assert perf["total_buys"] == 1
        assert perf["total_sells"] == 1
        assert perf["winning_trades"] == 1
        assert perf["losing_trades"] == 0
        assert perf["win_rate_pct"] == 100.0
        assert perf["unique_coins_traded"] == 1
        assert perf["best_trade"] is not None
        assert perf["best_trade"]["symbol"] == "TEST"
        assert perf["total_fees_gbp"] == 0.03

    def test_performance_summary_losing_trade(self, tracker):
        tracker.record_trade(
            symbol="TEST", side="buy", quantity=100,
            price=0.10, amount_gbp=10.0,
        )
        tracker.record_trade(
            symbol="TEST", side="sell", quantity=100,
            price=0.05, amount_gbp=5.0,
        )
        perf = tracker.get_performance_summary()
        assert perf["winning_trades"] == 0
        assert perf["losing_trades"] == 1
        assert perf["win_rate_pct"] == 0
        assert perf["worst_trade"]["symbol"] == "TEST"
