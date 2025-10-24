import unittest
import pandas as pd
import numpy as np
import tempfile
import os
from unittest.mock import Mock, patch
import sys
sys.path.append('/Users/finnbryant/Dev/CryptoApp')

from ml.training_pipeline import CryptoMLPipeline
from services.ml_service import MLService
from ml.data_pipeline import CryptoDataPipeline

class TestMLIntegration(unittest.TestCase):
    
    def setUp(self):
        self.pipeline = CryptoMLPipeline()
        self.ml_service = MLService()
        self.data_pipeline = CryptoDataPipeline()
        
        # Create sample data
        self.sample_data = self._create_sample_data()
    
    def _create_sample_data(self):
        """Create sample cryptocurrency data for testing"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1H')
        
        # Generate realistic price data
        np.random.seed(42)
        prices = 50000 + np.cumsum(np.random.randn(100) * 100)
        volumes = np.random.uniform(1000000, 10000000, 100)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'volume': volumes,
            'market_cap': prices * 19000000  # Approximate BTC market cap
        })
        
        return df
    
    def test_feature_calculation(self):
        """Test technical indicator calculations"""
        features = self.pipeline.prepare_features(self.sample_data)
        
        # Check all expected features are present
        expected_features = ['price_change_1h', 'price_change_24h', 'volume_change_24h', 
                           'market_cap_change_24h', 'rsi', 'macd', 'moving_avg_7d', 'moving_avg_30d']
        
        for feature in expected_features:
            self.assertIn(feature, features.columns)
        
        # Check no NaN values in final features
        self.assertFalse(features.isnull().any().any())
    
    def test_model_training(self):
        """Test model training pipeline"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            self.sample_data.to_csv(f.name, index=False)
            
            try:
                metrics = self.pipeline.train_model(f.name)
                
                # Check training completed
                self.assertIsNotNone(self.pipeline.model)
                self.assertIn('mse', metrics)
                self.assertIn('r2', metrics)
                
                # Check model can make predictions
                sample_features = {
                    'price_change_1h': 0.01,
                    'price_change_24h': 0.05,
                    'volume_change_24h': 0.1,
                    'market_cap_change_24h': 0.03,
                    'rsi': 65.0,
                    'macd': 100.0,
                    'moving_avg_7d': 50000.0,
                    'moving_avg_30d': 49500.0
                }
                
                prediction = self.pipeline.predict(sample_features)
                self.assertIsInstance(prediction, (int, float))
                
            finally:
                os.unlink(f.name)
    
    @patch('requests.Session.post')
    def test_ml_service_prediction(self, mock_post):
        """Test ML service API calls"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "symbol": "BTC",
            "prediction": 0.025,
            "confidence": 0.75,
            "timestamp": "2024-01-01T12:00:00Z"
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Test prediction call
        result = self.ml_service.get_price_prediction("BTC")
        
        self.assertIn("interpretation", result)
        self.assertIn("direction", result["interpretation"])
        self.assertIn("recommendation", result["interpretation"])
    
    def test_prediction_interpretation(self):
        """Test prediction interpretation logic"""
        # Test bullish prediction
        result = {"prediction": 0.025, "confidence": 0.8}
        interpretation = self.ml_service._interpret_prediction(result)
        
        self.assertEqual(interpretation["direction"], "bullish")
        self.assertEqual(interpretation["confidence_level"], "high")
        
        # Test bearish prediction
        result = {"prediction": -0.015, "confidence": 0.6}
        interpretation = self.ml_service._interpret_prediction(result)
        
        self.assertEqual(interpretation["direction"], "bearish")
        self.assertEqual(interpretation["confidence_level"], "medium")

if __name__ == '__main__':
    unittest.main()
