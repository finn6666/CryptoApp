"""
Unit tests for the Trading Engine.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from ml.trading_engine import TradingEngine, TradeProposal, DailyBudget


class TestTradeProposal:
    """Tests for the TradeProposal dataclass."""

    def test_create_proposal(self):
        p = TradeProposal(
            id="abc123",
            symbol="TEST",
            side="buy",
            amount_gbp=0.02,
            price_at_proposal=0.05,
            reason="Test reason",
            confidence=80,
            agent_recommendation="BUY",
        )
        assert p.id == "abc123"
        assert p.status == "pending"
        assert p.created_at  # auto-set

    def test_default_status_is_pending(self):
        p = TradeProposal(
            id="x", symbol="X", side="buy", amount_gbp=0.01,
            price_at_proposal=1.0, reason="r", confidence=50,
            agent_recommendation="BUY",
        )
        assert p.status == "pending"


class TestDailyBudget:
    def test_defaults(self):
        b = DailyBudget(date="2026-02-21")
        assert b.spent_gbp == 0.0
        assert b.trades_executed == 0


class TestTradingEngine:
    """Tests for the TradingEngine class."""

    @pytest.fixture
    def engine(self, tmp_data_dir):
        """Create a TradingEngine with temp storage."""
        return TradingEngine(
            daily_budget_gbp=0.05,
            exchange_id="kraken",
            data_dir=str(tmp_data_dir / "trades"),
            server_url="http://localhost:5001",
        )

    def test_initial_state(self, engine):
        assert engine.daily_budget_gbp == 0.05
        assert engine.kill_switch is False
        assert engine.get_remaining_budget() == 0.05

    def test_can_afford_trade(self, engine):
        assert engine.can_afford_trade(0.02) is True
        assert engine.can_afford_trade(0.10) is False

    def test_kill_switch_blocks_trades(self, engine):
        engine.kill_switch = True
        assert engine.can_afford_trade(0.01) is False

    def test_propose_trade_success(self, engine, sample_trade_proposal):
        result = engine.propose_trade(**sample_trade_proposal)
        assert result["success"] is True
        assert "proposal_id" in result
        assert result["amount_gbp"] <= engine.daily_budget_gbp

    def test_propose_trade_kill_switch(self, engine, sample_trade_proposal):
        engine.kill_switch = True
        result = engine.propose_trade(**sample_trade_proposal)
        assert result["success"] is False
        assert "kill switch" in result["error"].lower()

    def test_propose_trade_budget_cap(self, engine):
        """Trade amount should be capped to max_trade_pct of daily budget."""
        result = engine.propose_trade(
            symbol="TEST", side="buy", amount_gbp=1.0,
            current_price=0.05, reason="test", confidence=80,
            recommendation="BUY",
        )
        assert result["success"] is True
        assert result["amount_gbp"] <= engine.daily_budget_gbp * engine.max_trade_pct

    def test_propose_trade_cooldown(self, engine, sample_trade_proposal):
        # First proposal succeeds
        engine.propose_trade(**sample_trade_proposal)
        # Second proposal should hit cooldown
        result = engine.propose_trade(**sample_trade_proposal)
        assert result["success"] is False
        assert "cooldown" in result["error"].lower()

    def test_reject_trade(self, engine, sample_trade_proposal):
        result = engine.propose_trade(**sample_trade_proposal)
        pid = result["proposal_id"]
        reject_result = engine.reject_trade(pid)
        assert reject_result["success"] is True
        assert reject_result["status"] == "rejected"

    def test_reject_nonexistent(self, engine):
        result = engine.reject_trade("nonexistent")
        assert result["success"] is False

    def test_approve_expired_proposal(self, engine, sample_trade_proposal):
        result = engine.propose_trade(**sample_trade_proposal)
        pid = result["proposal_id"]
        # Manually expire the proposal
        engine.proposals[pid].created_at = (
            datetime.utcnow() - timedelta(hours=2)
        ).isoformat()
        approve_result = engine.approve_trade(pid)
        assert approve_result["success"] is False
        assert "expired" in approve_result["error"].lower()

    def test_activate_kill_switch(self, engine, sample_trade_proposal):
        engine.propose_trade(**sample_trade_proposal)
        result = engine.activate_kill_switch()
        assert result["success"] is True
        assert result["proposals_rejected"] >= 1
        assert engine.kill_switch is True

    def test_deactivate_kill_switch(self, engine):
        engine.kill_switch = True
        result = engine.deactivate_kill_switch()
        assert result["success"] is True
        assert engine.kill_switch is False

    def test_get_status(self, engine):
        status = engine.get_status()
        assert "active" in status
        assert "daily_budget_gbp" in status
        assert "remaining_today_gbp" in status

    def test_token_sign_verify(self, engine):
        token = engine.sign_proposal_token("test-id", "approve")
        data = engine.verify_proposal_token(token)
        assert data["id"] == "test-id"
        assert data["action"] == "approve"

    def test_persistence(self, engine, sample_trade_proposal, tmp_data_dir):
        engine.propose_trade(**sample_trade_proposal)
        engine._save_state()

        # Create new engine pointing to same dir
        engine2 = TradingEngine(
            daily_budget_gbp=0.05,
            exchange_id="kraken",
            data_dir=str(tmp_data_dir / "trades"),
        )
        assert len(engine2.proposals) == len(engine.proposals)

    def test_get_pending_proposals(self, engine, sample_trade_proposal):
        engine.propose_trade(**sample_trade_proposal)
        pending = engine.get_pending_proposals()
        assert len(pending) == 1
        assert pending[0]["status"] == "pending"

    def test_get_trade_history_empty(self, engine):
        history = engine.get_trade_history()
        assert history == []
