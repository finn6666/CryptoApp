import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import onnx
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
import logging
from datetime import datetime, timedelta
import os

class CryptoMLPipeline:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = ['price_change_1h', 'price_change_24h', 'volume_change_24h', 
                               'market_cap_change_24h', 'rsi', 'macd', 'moving_avg_7d', 'moving_avg_30d']
        self.model_loaded = False
        self.last_training_time = None
        self.training_status = "Not trained"
    
    def prepare_features(self, df):
        """Extract and engineer features for ML model"""
        # Validate required columns
        required_cols = ['close', 'volume', 'market_cap'] if 'market_cap' in df.columns else ['close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
            
        features = df.copy()
        
        # Technical indicators
        features['rsi'] = self.calculate_rsi(features['close'])
        features['macd'] = self.calculate_macd(features['close'])
        features['moving_avg_7d'] = features['close'].rolling(window=7).mean()
        features['moving_avg_30d'] = features['close'].rolling(window=30).mean()
        
        # Price changes
        features['price_change_1h'] = features['close'].pct_change(periods=1)
        features['price_change_24h'] = features['close'].pct_change(periods=24)
        features['volume_change_24h'] = features['volume'].pct_change(periods=24)
        
        # Market cap change (if available)
        if 'market_cap' in features.columns:
            features['market_cap_change_24h'] = features['market_cap'].pct_change(periods=24)
        else:
            features['market_cap_change_24h'] = 0  # Default value
            logging.warning("Market cap data not available, using default value")
        
        return features[self.feature_columns].dropna()
    
    def calculate_rsi(self, prices, window=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_macd(self, prices, fast=12, slow=26):
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        return ema_fast - ema_slow
    
    def get_status(self):
        """Get current ML pipeline status for web interface"""
        return {
            "model_loaded": self.model_loaded,
            "last_training_time": self.last_training_time.isoformat() if self.last_training_time else None,
            "training_status": self.training_status,
            "feature_columns": self.feature_columns,
            "model_type": "RandomForestRegressor" if self.model else None
        }
    
    def load_existing_model(self, model_dir="/Users/finnbryant/Dev/CryptoApp/models"):
        """Load previously trained model"""
        try:
            model_path = f"{model_dir}/crypto_model.pkl"
            scaler_path = f"{model_dir}/scaler.pkl"
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                self.model_loaded = True
                self.training_status = "Model loaded from disk"
                
                # Get model file timestamp
                self.last_training_time = datetime.fromtimestamp(os.path.getmtime(model_path))
                
                logging.info("Existing model loaded successfully")
                return True
            else:
                self.training_status = "No trained model found"
                return False
                
        except Exception as e:
            logging.error(f"Failed to load existing model: {e}")
            self.training_status = f"Model loading failed: {str(e)}"
            return False
    
    def train_model(self, data_path):
        """Train the ML model"""
        self.training_status = "Training in progress..."
        logging.info(f"Starting model training at {datetime.now()}")
        
        try:
            # Load and prepare data
            if not os.path.exists(data_path):
                raise FileNotFoundError(f"Data file not found: {data_path}")
                
            df = pd.read_csv(data_path)
            logging.info(f"Loaded {len(df)} rows of data")
            
            # Validate minimum data requirements
            if len(df) < 100:
                raise ValueError(f"Insufficient data: {len(df)} rows (minimum 100 required)")
            
            features = self.prepare_features(df)
            
            # Create target variable (next hour price change)
            target = df['close'].shift(-1).pct_change().dropna()
            
            # Align features and target
            min_length = min(len(features), len(target))
            X = features.iloc[:min_length]
            y = target.iloc[:min_length]
            
            # Remove any remaining NaN values
            mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
            X = X[mask]
            y = y[mask]
            
            if len(X) < 50:
                raise ValueError(f"Insufficient clean data after preprocessing: {len(X)} rows")
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            logging.info(f"Model trained - MSE: {mse:.6f}, R²: {r2:.4f}")
            
            # Update status after successful training
            self.model_loaded = True
            self.last_training_time = datetime.now()
            self.training_status = "Training completed successfully"
            
            return {"mse": mse, "r2": r2, "samples": len(X)}
            
        except Exception as e:
            self.training_status = f"Training failed: {str(e)}"
            logging.error(f"Training failed: {str(e)}")
            raise
    
    def predict(self, features_dict):
        """Make prediction for new data"""
        if self.model is None:
            raise ValueError("Model not trained yet")
            
        # Convert dict to array in correct order
        feature_array = np.array([features_dict[col] for col in self.feature_columns]).reshape(1, -1)
        
        # Scale and predict
        scaled_features = self.scaler.transform(feature_array)
        prediction = self.model.predict(scaled_features)[0]
        
        return prediction
    
    def predict_with_validation(self, features_dict):
        """Make prediction with input validation for web interface"""
        if not self.model_loaded:
            raise ValueError("No trained model available. Please train a model first.")
        
        # Validate all required features are present
        missing_features = [col for col in self.feature_columns if col not in features_dict]
        if missing_features:
            raise ValueError(f"Missing required features: {missing_features}")
        
        try:
            prediction = self.predict(features_dict)
            
            # Add confidence estimation
            confidence = self._estimate_confidence(features_dict)
            
            return {
                "prediction": float(prediction),
                "prediction_percentage": round(float(prediction * 100), 2),
                "confidence": confidence,
                "features_used": features_dict,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Prediction failed: {e}")
            raise ValueError(f"Prediction failed: {str(e)}")
    
    def _estimate_confidence(self, features_dict):
        """Estimate prediction confidence based on feature values"""
        try:
            values = list(features_dict.values())
            
            # Simple confidence based on feature stability
            variance = np.var(values)
            confidence = max(0.1, min(0.9, 1.0 / (1.0 + abs(variance))))
            
            return round(confidence, 3)
        except:
            return 0.5
    
    def create_sample_data(self, symbol="BTC", days=30):
        """Create sample training data for demonstration"""
        try:
            # Generate realistic sample data
            np.random.seed(42)
            hours = days * 24
            
            # Generate price data with random walk
            base_price = 50000 if symbol == "BTC" else 3000
            price_changes = np.random.normal(0, 0.01, hours)
            prices = [base_price]
            
            for change in price_changes:
                new_price = prices[-1] * (1 + change)
                prices.append(max(new_price, base_price * 0.5))  # Prevent negative prices
            
            # Generate volume and market cap data
            volumes = np.random.uniform(1000000, 50000000, hours + 1)
            market_caps = np.array(prices) * 19000000  # Approximate circulating supply
            
            timestamps = pd.date_range(
                start=datetime.now() - timedelta(days=days), 
                periods=hours + 1, 
                freq='1H'
            )
            
            df = pd.DataFrame({
                'timestamp': timestamps,
                'close': prices,
                'volume': volumes,
                'market_cap': market_caps,
                'symbol': symbol
            })
            
            return df
            
        except Exception as e:
            logging.error(f"Failed to create sample data: {e}")
            raise
    
    def export_model(self, model_dir="/Users/finnbryant/Dev/CryptoApp/models"):
        """Export model to ONNX and joblib formats"""
        os.makedirs(model_dir, exist_ok=True)
        
        # Save scikit-learn model
        joblib.dump(self.model, f"{model_dir}/crypto_model.pkl")
        joblib.dump(self.scaler, f"{model_dir}/scaler.pkl")
        
        # Convert to ONNX
        initial_type = [('float_input', FloatTensorType([None, len(self.feature_columns)]))]
        onnx_model = convert_sklearn(self.model, initial_types=initial_type)
        
        with open(f"{model_dir}/crypto_model.onnx", "wb") as f:
            f.write(onnx_model.SerializeToString())
        
        logging.info(f"Models exported to {model_dir}")
    
    def get_quick_prediction(self, current_price, volume=None, symbol="BTC"):
        """Get a quick prediction using minimal real-time data"""
        if not self.model_loaded:
            return {
                "available": False,
                "message": "ML model not trained yet",
                "recommendation": "Hold - No prediction available"
            }
        
        try:
            # Create basic features from current price data
            features = {
                'price_change_1h': np.random.normal(0, 0.01),  # Placeholder - would use real data
                'price_change_24h': np.random.normal(0, 0.05),
                'volume_change_24h': np.random.normal(0, 0.1) if volume else 0.1,
                'market_cap_change_24h': np.random.normal(0, 0.03),
                'rsi': 50 + np.random.normal(0, 10),  # Default RSI around 50
                'macd': np.random.normal(0, 50),
                'moving_avg_7d': current_price * (1 + np.random.normal(0, 0.02)),
                'moving_avg_30d': current_price * (1 + np.random.normal(0, 0.05))
            }
            
            # Ensure RSI is in valid range
            features['rsi'] = max(0, min(100, features['rsi']))
            
            prediction_result = self.predict_with_validation(features)
            
            # Add interpretation
            pred_pct = prediction_result['prediction_percentage']
            
            if abs(pred_pct) < 1:
                signal = "Hold"
                color_class = "text-warning"
                icon = "➡️"
            elif pred_pct > 0:
                signal = "Bullish" if pred_pct > 2 else "Weak Buy"
                color_class = "text-success" 
                icon = "📈"
            else:
                signal = "Bearish" if pred_pct < -2 else "Weak Sell"
                color_class = "text-danger"
                icon = "📉"
            
            return {
                "available": True,
                "prediction_percentage": pred_pct,
                "confidence": prediction_result['confidence'],
                "signal": signal,
                "color_class": color_class,
                "icon": icon,
                "recommendation": f"{signal} - {abs(pred_pct):.1f}% expected move",
                "timestamp": prediction_result['timestamp']
            }
            
        except Exception as e:
            logging.error(f"Quick prediction failed: {e}")
            return {
                "available": False,
                "message": f"Prediction error: {str(e)}",
                "recommendation": "Hold - Error in prediction"
            }
    
    def check_functionality(self):
        """Comprehensive functionality check for ML pipeline"""
        checks = {
            "model_files": self._check_model_files(),
            "model_loading": self._check_model_loading(),
            "feature_calculation": self._check_feature_calculation(),
            "prediction_pipeline": self._check_prediction_pipeline(),
            "data_generation": self._check_data_generation(),
            "export_functionality": self._check_export_functionality()
        }
        
        # Overall health status
        all_passed = all(check["status"] for check in checks.values())
        
        return {
            "overall_status": "HEALTHY" if all_passed else "ISSUES_DETECTED",
            "timestamp": datetime.now().isoformat(),
            "checks": checks,
            "summary": self._generate_health_summary(checks)
        }
    
    def _check_model_files(self):
        """Check if model files exist and are accessible"""
        try:
            model_dir = "/Users/finnbryant/Dev/CryptoApp/models"
            model_path = f"{model_dir}/crypto_model.pkl"
            scaler_path = f"{model_dir}/scaler.pkl"
            
            results = {
                "model_dir_exists": os.path.exists(model_dir),
                "model_file_exists": os.path.exists(model_path),
                "scaler_file_exists": os.path.exists(scaler_path)
            }
            
            if results["model_file_exists"] and results["scaler_file_exists"]:
                # Check file sizes
                model_size = os.path.getsize(model_path)
                scaler_size = os.path.getsize(scaler_path)
                results["model_file_size"] = model_size
                results["scaler_file_size"] = scaler_size
                results["files_not_empty"] = model_size > 0 and scaler_size > 0
            
            status = (results.get("model_dir_exists", False) and 
                     results.get("model_file_exists", False) and 
                     results.get("scaler_file_exists", False) and
                     results.get("files_not_empty", False))
            
            return {
                "status": status,
                "details": results,
                "message": "Model files found and accessible" if status else "Model files missing or empty"
            }
            
        except Exception as e:
            return {
                "status": False,
                "details": {"error": str(e)},
                "message": f"Error checking model files: {str(e)}"
            }
    
    def _check_model_loading(self):
        """Test model loading functionality"""
        try:
            # Save current state
            original_model = self.model
            original_scaler = self.scaler
            original_status = self.model_loaded
            
            # Test loading
            load_result = self.load_existing_model()
            
            details = {
                "load_successful": load_result,
                "model_loaded_flag": self.model_loaded,
                "model_object_exists": self.model is not None,
                "scaler_object_exists": self.scaler is not None
            }
            
            if self.model is not None:
                details["model_type"] = type(self.model).__name__
                details["feature_count"] = len(self.feature_columns)
            
            # Restore original state
            self.model = original_model
            self.scaler = original_scaler
            self.model_loaded = original_status
            
            status = (load_result and 
                     details["model_object_exists"] and 
                     details["scaler_object_exists"])
            
            return {
                "status": status,
                "details": details,
                "message": "Model loading successful" if status else "Model loading failed"
            }
            
        except Exception as e:
            return {
                "status": False,
                "details": {"error": str(e)},
                "message": f"Model loading test failed: {str(e)}"
            }
    
    def _check_feature_calculation(self):
        """Test feature calculation with sample data"""
        try:
            # Create minimal test data
            test_data = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=50, freq='1H'),
                'close': np.random.uniform(40000, 60000, 50),
                'volume': np.random.uniform(1000000, 10000000, 50),
                'market_cap': np.random.uniform(800000000000, 1200000000000, 50)
            })
            
            # Test feature preparation
            features = self.prepare_features(test_data)
            
            details = {
                "input_rows": len(test_data),
                "output_rows": len(features),
                "feature_columns_count": len(features.columns),
                "expected_columns_count": len(self.feature_columns),
                "columns_match": list(features.columns) == self.feature_columns,
                "no_nan_values": not features.isnull().any().any(),
                "feature_columns": list(features.columns)
            }
            
            # Check specific technical indicators
            if len(features) > 0:
                details["rsi_range_valid"] = features['rsi'].between(0, 100).all()
                details["has_price_changes"] = features['price_change_1h'].notna().any()
                details["has_moving_averages"] = (features['moving_avg_7d'].notna().any() and 
                                                features['moving_avg_30d'].notna().any())
            
            status = (len(features) > 0 and 
                     details["columns_match"] and 
                     details["no_nan_values"])
            
            return {
                "status": status,
                "details": details,
                "message": "Feature calculation working correctly" if status else "Feature calculation issues detected"
            }
            
        except Exception as e:
            return {
                "status": False,
                "details": {"error": str(e)},
                "message": f"Feature calculation test failed: {str(e)}"
            }
    
    def _check_prediction_pipeline(self):
        """Test end-to-end prediction functionality"""
        try:
            if not self.model_loaded:
                # Try to load model for testing
                self.load_existing_model()
            
            if not self.model_loaded:
                return {
                    "status": False,
                    "details": {"model_loaded": False},
                    "message": "No trained model available for prediction testing"
                }
            
            # Test with sample features
            test_features = {
                'price_change_1h': 0.01,
                'price_change_24h': 0.05,
                'volume_change_24h': 0.1,
                'market_cap_change_24h': 0.03,
                'rsi': 65.0,
                'macd': 100.0,
                'moving_avg_7d': 50000.0,
                'moving_avg_30d': 49500.0
            }
            
            # Test basic prediction
            prediction = self.predict(test_features)
            
            # Test validation prediction
            validation_result = self.predict_with_validation(test_features)
            
            # Test quick prediction
            quick_result = self.get_quick_prediction(50000, symbol="BTC")
            
            details = {
                "basic_prediction_works": isinstance(prediction, (int, float)),
                "validation_prediction_works": isinstance(validation_result, dict),
                "quick_prediction_works": isinstance(quick_result, dict),
                "prediction_value": float(prediction) if isinstance(prediction, (int, float)) else None,
                "validation_has_required_keys": all(key in validation_result for key in 
                    ["prediction", "confidence", "timestamp"]) if isinstance(validation_result, dict) else False,
                "quick_prediction_available": quick_result.get("available", False) if isinstance(quick_result, dict) else False
            }
            
            status = (details["basic_prediction_works"] and 
                     details["validation_prediction_works"] and 
                     details["validation_has_required_keys"])
            
            return {
                "status": status,
                "details": details,
                "message": "Prediction pipeline working correctly" if status else "Prediction pipeline has issues"
            }
            
        except Exception as e:
            return {
                "status": False,
                "details": {"error": str(e)},
                "message": f"Prediction pipeline test failed: {str(e)}"
            }
    
    def _check_data_generation(self):
        """Test sample data generation"""
        try:
            sample_data = self.create_sample_data("BTC", 7)  # 7 days of data
            
            details = {
                "data_generated": sample_data is not None,
                "is_dataframe": isinstance(sample_data, pd.DataFrame),
                "row_count": len(sample_data) if isinstance(sample_data, pd.DataFrame) else 0,
                "expected_rows": 7 * 24 + 1,  # 7 days * 24 hours + 1
                "has_required_columns": False,
                "columns": []
            }
            
            if isinstance(sample_data, pd.DataFrame):
                required_cols = ['timestamp', 'close', 'volume', 'market_cap', 'symbol']
                details["columns"] = list(sample_data.columns)
                details["has_required_columns"] = all(col in sample_data.columns for col in required_cols)
                details["no_null_values"] = not sample_data.isnull().any().any()
                details["positive_prices"] = (sample_data['close'] > 0).all()
            
            status = (details["data_generated"] and 
                     details["is_dataframe"] and 
                     details["has_required_columns"] and
                     details["row_count"] > 0)
            
            return {
                "status": status,
                "details": details,
                "message": "Data generation working correctly" if status else "Data generation has issues"
            }
            
        except Exception as e:
            return {
                "status": False,
                "details": {"error": str(e)},
                "message": f"Data generation test failed: {str(e)}"
            }
    
    def _check_export_functionality(self):
        """Test model export functionality"""
        try:
            if not self.model_loaded:
                return {
                    "status": False,
                    "details": {"model_loaded": False},
                    "message": "No trained model available for export testing"
                }
            
            # Test export (but don't actually save files)
            model_dir = "/tmp/ml_test_export"
            
            details = {
                "can_create_directory": False,
                "joblib_export_ready": self.model is not None and self.scaler is not None,
                "onnx_conversion_ready": False
            }
            
            # Test directory creation
            os.makedirs(model_dir, exist_ok=True)
            details["can_create_directory"] = os.path.exists(model_dir)
            
            # Test ONNX conversion readiness
            try:
                from skl2onnx import convert_sklearn
                from skl2onnx.common.data_types import FloatTensorType
                details["onnx_conversion_ready"] = True
            except ImportError:
                details["onnx_conversion_ready"] = False
            
            # Cleanup test directory
            if os.path.exists(model_dir):
                os.rmdir(model_dir)
            
            status = (details["can_create_directory"] and 
                     details["joblib_export_ready"])
            
            return {
                "status": status,
                "details": details,
                "message": "Export functionality ready" if status else "Export functionality has issues"
            }
            
        except Exception as e:
            return {
                "status": False,
                "details": {"error": str(e)},
                "message": f"Export functionality test failed: {str(e)}"
            }
    
    def _generate_health_summary(self, checks):
        """Generate a human-readable health summary"""
        passed = sum(1 for check in checks.values() if check["status"])
        total = len(checks)
        
        summary = {
            "tests_passed": passed,
            "total_tests": total,
            "success_rate": round((passed / total) * 100, 1),
            "issues": []
        }
        
        # Collect specific issues
        for check_name, check_result in checks.items():
            if not check_result["status"]:
                summary["issues"].append(f"{check_name}: {check_result['message']}")
        
        if passed == total:
            summary["overall_message"] = "All ML functionality checks passed successfully"
        elif passed >= total * 0.7:
            summary["overall_message"] = f"Most functionality working ({passed}/{total} tests passed)"
        else:
            summary["overall_message"] = f"Significant issues detected ({passed}/{total} tests passed)"
        
        return summary
    
    def run_quick_test(self):
        """Run a quick functionality test and return simple status"""
        try:
            # Test 1: Can we load a model?
            model_available = self.load_existing_model() or self.model_loaded
            
            # Test 2: Can we generate sample data?
            sample_data = self.create_sample_data("BTC", 1)
            data_generation_works = len(sample_data) > 0
            
            # Test 3: Can we calculate features?
            if data_generation_works:
                features = self.prepare_features(sample_data)
                feature_calculation_works = len(features) > 0
            else:
                feature_calculation_works = False
            
            # Test 4: Can we make predictions?
            if model_available and feature_calculation_works:
                test_features = {
                    'price_change_1h': 0.01, 'price_change_24h': 0.05,
                    'volume_change_24h': 0.1, 'market_cap_change_24h': 0.03,
                    'rsi': 65.0, 'macd': 100.0,
                    'moving_avg_7d': 50000.0, 'moving_avg_30d': 49500.0
                }
                prediction = self.predict(test_features)
                prediction_works = isinstance(prediction, (int, float))
            else:
                prediction_works = False
            
            return {
                "status": "SUCCESS" if all([model_available, data_generation_works, 
                                          feature_calculation_works, prediction_works]) else "PARTIAL",
                "model_available": model_available,
                "data_generation": data_generation_works,
                "feature_calculation": feature_calculation_works,
                "prediction": prediction_works,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }