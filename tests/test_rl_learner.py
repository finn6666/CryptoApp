"""
Unit tests for the SimpleRLGemLearner.
"""

import os
import json
import pytest
from collections import defaultdict
from unittest.mock import patch

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from ml.simple_rl import SimpleRLGemLearner


class TestSimpleRLGemLearner:
    """Tests for the RL learner."""

    @pytest.fixture
    def learner(self, tmp_path):
        """Create a learner with temp persistence."""
        with patch.object(SimpleRLGemLearner, "__init__", lambda self, **kw: None):
            rl = SimpleRLGemLearner.__new__(SimpleRLGemLearner)
        rl.learning_rate = 0.1
        rl.discount_factor = 0.9
        rl.feature_weights = defaultdict(lambda: {'buy': 0.5, 'hold': 0.5})
        rl.trade_history = []
        rl.success_rate = 0.0
        rl.total_trades = 0
        rl.winning_trades = 0
        rl.save_dir = str(tmp_path)
        rl.save_path = str(tmp_path / "rl_learner.json")
        rl.logger = __import__("logging").getLogger("test_rl")
        return rl

    def test_calculate_reward_positive(self, learner):
        reward = learner._calculate_reward(profit_pct=10.0, days_held=5)
        assert reward > 0

    def test_calculate_reward_negative(self, learner):
        reward = learner._calculate_reward(profit_pct=-20.0, days_held=5)
        assert reward < 0

    def test_calculate_reward_time_decay(self, learner):
        short_hold = learner._calculate_reward(profit_pct=10.0, days_held=1)
        long_hold = learner._calculate_reward(profit_pct=10.0, days_held=30)
        # Shorter hold should get higher reward for same profit
        assert short_hold >= long_hold

    def test_get_recommendation(self, learner):
        features = {
            "volume_price_ratio": 0.5,
            "momentum_score": 0.7,
            "volatility_score": 0.3,
        }
        rec = learner.get_recommendation(gem_score=7.5, features=features)
        assert "action" in rec
        assert "confidence" in rec
        assert rec["action"] in ["buy", "hold"]

    def test_learn_from_outcome(self, learner):
        features = {"volume_price_ratio": 0.5, "momentum_score": 0.7}
        result = learner.learn_from_outcome(
            features=features, action="buy",
            profit_pct=15.0, days_held=7,
            symbol="TEST", entry_price=0.05, exit_price=0.06,
        )
        assert result is not None
        assert "reward" in result

    def test_save_and_load(self, learner):
        features = {"volume_price_ratio": 0.5}
        learner.learn_from_outcome(
            features=features, action="buy",
            profit_pct=10.0, days_held=5,
        )
        learner.save_learning()

        # Create new learner
        learner2 = SimpleRLGemLearner.__new__(SimpleRLGemLearner)
        learner2.learning_rate = 0.1
        learner2.discount_factor = 0.9
        learner2.feature_weights = defaultdict(lambda: {'buy': 0.5, 'hold': 0.5})
        learner2.trade_history = []
        learner2.success_rate = 0.0
        learner2.total_trades = 0
        learner2.winning_trades = 0
        learner2.save_path = learner.save_path
        learner2.logger = learner.logger
        learner2.load_learning()

        assert learner2.feature_weights == learner.feature_weights

    def test_get_stats(self, learner):
        stats = learner.get_stats()
        assert "total_trades" in stats
        assert "winning_trades" in stats

    def test_reset_learning(self, learner):
        features = {"volume_price_ratio": 0.5}
        learner.learn_from_outcome(
            features=features, action="buy",
            profit_pct=10.0, days_held=5,
        )
        learner.reset_learning()
        assert learner.feature_weights == {}
        assert learner.total_trades == 0
