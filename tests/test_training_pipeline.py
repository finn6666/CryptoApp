"""
Unit tests for the ML training pipeline.
"""

import os
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from ml.training_pipeline import CryptoMLPipeline


class TestCryptoMLPipeline:
    """Tests for CryptoMLPipeline."""

    @pytest.fixture
    def pipeline(self):
        return CryptoMLPipeline()

    def test_initial_state(self, pipeline):
        assert pipeline.model is None
        assert pipeline.model_loaded is False
        assert len(pipeline.feature_columns) == 8

    def test_calculate_rsi(self, pipeline):
        prices = pd.Series(np.random.uniform(40000, 60000, 50))
        rsi = pipeline.calculate_rsi(prices)
        # RSI should be between 0 and 100 (after warm-up)
        valid = rsi.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_calculate_macd(self, pipeline):
        prices = pd.Series(np.random.uniform(40000, 60000, 50))
        macd = pipeline.calculate_macd(prices)
        assert len(macd) == len(prices)

    def test_create_sample_data(self, pipeline):
        df = pipeline.create_sample_data("BTC", days=7)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "close" in df.columns
        assert "volume" in df.columns
        assert "market_cap" in df.columns
        assert (df["close"] > 0).all()

    def test_prepare_features(self, pipeline):
        df = pipeline.create_sample_data("BTC", days=7)
        features = pipeline.prepare_features(df)
        assert len(features) > 0
        assert list(features.columns) == pipeline.feature_columns
        assert not features.isnull().any().any()

    def test_prepare_features_missing_columns(self, pipeline):
        df = pd.DataFrame({"close": [1, 2, 3]})
        with pytest.raises(ValueError, match="Missing required columns"):
            pipeline.prepare_features(df)

    def test_train_model(self, pipeline, tmp_path):
        df = pipeline.create_sample_data("BTC", days=30)
        data_path = tmp_path / "training_data.csv"
        df.to_csv(data_path, index=False)
        metrics = pipeline.train_model(str(data_path))
        assert "mse" in metrics
        assert "r2" in metrics
        assert pipeline.model_loaded is True

    def test_predict_without_model(self, pipeline):
        pipeline._onnx_engine = None  # Disable ONNX fast path
        pipeline.model = None
        with pytest.raises(ValueError, match="Model not trained"):
            pipeline.predict({"price_change_1h": 0.01})

    def test_predict_with_trained_model(self, pipeline, tmp_path):
        df = pipeline.create_sample_data("BTC", days=30)
        data_path = tmp_path / "training_data.csv"
        df.to_csv(data_path, index=False)
        pipeline.train_model(str(data_path))

        features = {col: 0.01 for col in pipeline.feature_columns}
        features["rsi"] = 50.0
        features["macd"] = 100.0
        features["moving_avg_7d"] = 50000.0
        features["moving_avg_30d"] = 49000.0

        prediction = pipeline.predict(features)
        assert isinstance(prediction, (int, float, np.floating))

    def test_predict_with_validation(self, pipeline, tmp_path):
        df = pipeline.create_sample_data("BTC", days=30)
        data_path = tmp_path / "training_data.csv"
        df.to_csv(data_path, index=False)
        pipeline.train_model(str(data_path))

        features = {col: 0.01 for col in pipeline.feature_columns}
        features["rsi"] = 50.0
        features["macd"] = 100.0
        features["moving_avg_7d"] = 50000.0
        features["moving_avg_30d"] = 49000.0

        result = pipeline.predict_with_validation(features)
        assert "prediction" in result
        assert "confidence" in result
        assert "timestamp" in result

    def test_predict_with_validation_missing_features(self, pipeline, tmp_path):
        df = pipeline.create_sample_data("BTC", days=30)
        data_path = tmp_path / "training_data.csv"
        df.to_csv(data_path, index=False)
        pipeline.train_model(str(data_path))

        with pytest.raises(ValueError, match="Missing required features"):
            pipeline.predict_with_validation({"rsi": 50})

    def test_export_model(self, pipeline, tmp_path):
        df = pipeline.create_sample_data("BTC", days=30)
        data_path = tmp_path / "training_data.csv"
        df.to_csv(data_path, index=False)
        pipeline.train_model(str(data_path))

        model_dir = str(tmp_path / "models")
        pipeline.export_model(model_dir)
        assert os.path.exists(f"{model_dir}/crypto_model.pkl")
        assert os.path.exists(f"{model_dir}/scaler.pkl")
        assert os.path.exists(f"{model_dir}/crypto_model.onnx")

    def test_get_status(self, pipeline):
        status = pipeline.get_status()
        assert "model_loaded" in status
        assert "feature_columns" in status

    def test_get_quick_prediction_no_model(self, pipeline):
        result = pipeline.get_quick_prediction(50000)
        assert result["available"] is False

    def test_estimate_confidence(self, pipeline):
        features = {col: 0.01 for col in pipeline.feature_columns}
        conf = pipeline._estimate_confidence(features)
        assert 0 <= conf <= 1

    def test_check_functionality(self, pipeline):
        result = pipeline.check_functionality()
        assert "overall_status" in result
        assert "checks" in result
        assert "summary" in result
