"""Tests for the backtesting framework."""

import json
import pytest
from pathlib import Path
from ml.backtesting import BacktestEngine, BacktestResult


class TestBacktestEngine:
    """Tests for BacktestEngine."""

    def test_synthetic_data_generation(self):
        data = BacktestEngine.generate_synthetic_data(
            symbols=["A", "B"], days=30
        )
        assert len(data) == 30
        assert all("date" in d and "coins" in d for d in data)
        assert all(len(d["coins"]) == 2 for d in data)

    def test_heuristic_score_range(self):
        coin = {"symbol": "TEST", "price": 0.01, "volume_24h": 200000,
                "market_cap": 5000000, "percent_change_24h": 8}
        score = BacktestEngine._heuristic_score(coin)
        assert 0 <= score <= 100

    def test_heuristic_score_negative_change(self):
        coin = {"symbol": "X", "price": 0.01, "percent_change_24h": -15,
                "volume_24h": 500, "market_cap": 0}
        score = BacktestEngine._heuristic_score(coin)
        assert score < 50

    def test_backtest_runs_with_synthetic(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ml.backtesting.BACKTEST_RESULTS_DIR", tmp_path)
        engine = BacktestEngine(initial_capital_gbp=1.0)
        data = BacktestEngine.generate_synthetic_data(days=30)
        result = engine.run_backtest(data, strategy_name="test_run", min_confidence=50,
                                     use_gem_detector=False)
        assert isinstance(result, BacktestResult)
        assert result.strategy_name == "test_run"
        assert result.initial_capital_gbp == 1.0

    def test_no_trades_high_confidence(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ml.backtesting.BACKTEST_RESULTS_DIR", tmp_path)
        engine = BacktestEngine(initial_capital_gbp=1.0)
        data = BacktestEngine.generate_synthetic_data(days=10)
        result = engine.run_backtest(data, strategy_name="strict",
                                     min_confidence=99, use_gem_detector=False)
        # Very high confidence threshold should result in few/no trades
        assert result.total_trades <= len(data)

    def test_equity_curve_length(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ml.backtesting.BACKTEST_RESULTS_DIR", tmp_path)
        engine = BacktestEngine()
        data = BacktestEngine.generate_synthetic_data(days=20)
        result = engine.run_backtest(data, strategy_name="eq",
                                     min_confidence=50, use_gem_detector=False)
        assert len(result.equity_curve) == 20

    def test_result_saved_to_disk(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ml.backtesting.BACKTEST_RESULTS_DIR", tmp_path)
        engine = BacktestEngine()
        data = BacktestEngine.generate_synthetic_data(days=5)
        engine.run_backtest(data, strategy_name="persist", min_confidence=50,
                            use_gem_detector=False)
        saved = list(tmp_path.glob("backtest_persist_*.json"))
        assert len(saved) == 1
        with open(saved[0]) as f:
            loaded = json.load(f)
        assert loaded["strategy_name"] == "persist"

    def test_list_results(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ml.backtesting.BACKTEST_RESULTS_DIR", tmp_path)
        engine = BacktestEngine()
        data = BacktestEngine.generate_synthetic_data(days=5)
        engine.run_backtest(data, strategy_name="list_test", min_confidence=50,
                            use_gem_detector=False)
        results = BacktestEngine.list_results()
        assert len(results) == 1
        assert results[0]["strategy"] == "list_test"

    def test_profit_target_exit(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ml.backtesting.BACKTEST_RESULTS_DIR", tmp_path)
        # Create data where price rises 50% (well above 20% target)
        data = [
            {"date": "2024-01-01", "coins": [
                {"symbol": "MOON", "price": 0.01, "volume_24h": 200000,
                 "market_cap": 5000000, "percent_change_24h": 10}
            ]},
            {"date": "2024-01-02", "coins": [
                {"symbol": "MOON", "price": 0.015, "volume_24h": 200000,
                 "market_cap": 7500000, "percent_change_24h": 50}
            ]},
        ]
        engine = BacktestEngine(profit_target_pct=20.0)
        result = engine.run_backtest(data, strategy_name="moon", min_confidence=50,
                                     use_gem_detector=False)
        sells = [t for t in result.trades if t["side"] == "sell"]
        assert len(sells) == 1
        assert "Profit target" in sells[0]["reason"]

    def test_stop_loss_exit(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ml.backtesting.BACKTEST_RESULTS_DIR", tmp_path)
        data = [
            {"date": "2024-01-01", "coins": [
                {"symbol": "TANK", "price": 0.10, "volume_24h": 300000,
                 "market_cap": 10000000, "percent_change_24h": 5}
            ]},
            {"date": "2024-01-02", "coins": [
                {"symbol": "TANK", "price": 0.05, "volume_24h": 300000,
                 "market_cap": 5000000, "percent_change_24h": -50}
            ]},
        ]
        engine = BacktestEngine(stop_loss_pct=-15.0)
        result = engine.run_backtest(data, strategy_name="tank", min_confidence=50,
                                     use_gem_detector=False)
        sells = [t for t in result.trades if t["side"] == "sell"]
        assert len(sells) == 1
        assert "Stop loss" in sells[0]["reason"]
