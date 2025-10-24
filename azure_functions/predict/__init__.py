import azure.functions as func
import json
import logging
import joblib
import numpy as np
import redis
import hashlib
from datetime import datetime, timedelta
import os
import requests
import pandas as pd

# Global variables for model caching
_model = None
_scaler = None
_redis_client = None

def init_models():
    """Initialize models and cache connection"""
    global _model, _scaler, _redis_client
    
    if _model is None:
        try:
            # Load models from mounted storage
            model_path = os.environ.get('MODEL_PATH', '/home/site/wwwroot/models')
            _model = joblib.load(f'{model_path}/crypto_model.pkl')
            _scaler = joblib.load(f'{model_path}/scaler.pkl')
            logging.info("Models loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load models: {e}")
            raise
    
    if _redis_client is None:
        try:
            redis_url = os.environ.get('REDIS_CONNECTION_STRING')
            if redis_url:
                _redis_client = redis.Redis.from_url(redis_url)
                logging.info("Redis connection established")
        except Exception as e:
            logging.warning(f"Redis connection failed: {e}")

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Crypto prediction function triggered')
    
    try:
        init_models()
        
        # Parse request
        req_body = req.get_json()
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        symbol = req_body.get('symbol', 'BTC')
        
        # Check if features are provided or need to be fetched
        features = req_body.get('features')
        
        if not features:
            # Fetch live data and calculate features
            try:
                features = fetch_and_calculate_features(symbol)
            except Exception as e:
                return func.HttpResponse(
                    json.dumps({"error": f"Failed to fetch data for {symbol}: {str(e)}"}),
                    status_code=400,
                    mimetype="application/json"
                )
        
        if not isinstance(features, dict):
            return func.HttpResponse(
                json.dumps({"error": "Features must be a dictionary"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Check cache
        cache_key = generate_cache_key(features, symbol)
        cached_result = get_cached_prediction(cache_key)
        
        if cached_result:
            logging.info("Returning cached prediction")
            return func.HttpResponse(
                json.dumps(cached_result),
                mimetype="application/json"
            )
        
        # Make prediction
        prediction = make_prediction(features)
        
        result = {
            "symbol": symbol,
            "prediction": float(prediction),
            "prediction_type": "price_change_next_hour",
            "confidence": calculate_confidence(features),
            "timestamp": datetime.utcnow().isoformat(),
            "features_used": list(features.keys()),
            "cached": False
        }
        
        # Cache result
        cache_prediction(cache_key, result)
        
        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Prediction error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

def fetch_and_calculate_features(symbol):
    """Fetch live crypto data and calculate ML features"""
    crypto_api_base = os.environ.get('CRYPTO_API_BASE_URL', 'https://your-cryptoapp-api.azurewebsites.net')
    
    try:
        # Try primary API first
        data = fetch_from_primary_api(crypto_api_base, symbol)
        
        # Fallback to external APIs if primary fails
        if not data:
            data = fetch_from_fallback_apis(symbol)
            
        if not data:
            raise Exception("No data sources available")
        
        # Convert to DataFrame for calculations
        df = pd.DataFrame(data['prices'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Calculate features using the same logic as training pipeline
        features = calculate_technical_features(df)
        
        return features
        
    except Exception as e:
        logging.error(f"Feature calculation failed: {e}")
        raise Exception(f"Failed to calculate features: {str(e)}")

def fetch_from_primary_api(api_base, symbol):
    """Fetch from your CryptoApp API"""
    try:
        response = requests.get(
            f"{api_base}/api/crypto/{symbol}/historical",
            params={"days": 30, "interval": "1h"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except:
        return None

def fetch_from_fallback_apis(symbol):
    """Fallback to external APIs (CoinGecko, etc.)"""
    try:
        # Example with CoinGecko API
        coingecko_id = get_coingecko_id(symbol)
        response = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/market_chart",
            params={"vs_currency": "usd", "days": "30", "interval": "hourly"},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        prices = []
        
        for i, (timestamp, price) in enumerate(data['prices']):
            volume = data['total_volumes'][i][1] if i < len(data['total_volumes']) else 0
            prices.append({
                'timestamp': timestamp,
                'close': price,
                'volume': volume
            })
        
        return {'prices': prices}
    except:
        return None

def get_coingecko_id(symbol):
    """Map symbol to CoinGecko ID"""
    mapping = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'ADA': 'cardano',
        'SOL': 'solana'
        # Add more mappings as needed
    }
    return mapping.get(symbol.upper(), symbol.lower())

def calculate_technical_features(df):
    """Calculate technical indicators from price data"""
    if len(df) < 30:
        raise ValueError("Insufficient data for feature calculation (minimum 30 data points)")
    
    # Get latest values for features
    latest_idx = -1
    
    # Price changes
    price_change_1h = df['close'].pct_change(periods=1).iloc[latest_idx]
    price_change_24h = df['close'].pct_change(periods=24).iloc[latest_idx] if len(df) >= 24 else 0
    
    # Volume change
    volume_change_24h = df['volume'].pct_change(periods=24).iloc[latest_idx] if 'volume' in df.columns and len(df) >= 24 else 0
    
    # Market cap change (if available)
    market_cap_change_24h = 0
    if 'market_cap' in df.columns and len(df) >= 24:
        market_cap_change_24h = df['market_cap'].pct_change(periods=24).iloc[latest_idx]
    
    # RSI
    rsi = calculate_rsi(df['close']).iloc[latest_idx]
    
    # MACD
    macd = calculate_macd(df['close']).iloc[latest_idx]
    
    # Moving averages
    moving_avg_7d = df['close'].rolling(window=min(7, len(df))).mean().iloc[latest_idx]
    moving_avg_30d = df['close'].rolling(window=min(30, len(df))).mean().iloc[latest_idx]
    
    features = {
        'price_change_1h': float(price_change_1h) if not pd.isna(price_change_1h) else 0.0,
        'price_change_24h': float(price_change_24h) if not pd.isna(price_change_24h) else 0.0,
        'volume_change_24h': float(volume_change_24h) if not pd.isna(volume_change_24h) else 0.0,
        'market_cap_change_24h': float(market_cap_change_24h) if not pd.isna(market_cap_change_24h) else 0.0,
        'rsi': float(rsi) if not pd.isna(rsi) else 50.0,
        'macd': float(macd) if not pd.isna(macd) else 0.0,
        'moving_avg_7d': float(moving_avg_7d) if not pd.isna(moving_avg_7d) else float(df['close'].iloc[latest_idx]),
        'moving_avg_30d': float(moving_avg_30d) if not pd.isna(moving_avg_30d) else float(df['close'].iloc[latest_idx])
    }
    
    return features

def calculate_rsi(prices, window=14):
    """Calculate RSI technical indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(prices, fast=12, slow=26):
    """Calculate MACD technical indicator"""
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    return ema_fast - ema_slow

def generate_cache_key(features, symbol):
    """Generate cache key from features and symbol"""
    feature_str = json.dumps(features, sort_keys=True)
    return f"prediction:{symbol}:{hashlib.md5(feature_str.encode()).hexdigest()}"

def get_cached_prediction(cache_key):
    """Get prediction from cache"""
    if _redis_client is None:
        return None
    
    try:
        cached_data = _redis_client.get(cache_key)
        if cached_data:
            result = json.loads(cached_data)
            result['cached'] = True
            return result
    except Exception as e:
        logging.warning(f"Cache read error: {e}")
    return None

def cache_prediction(cache_key, result, ttl=300):
    """Cache prediction for 5 minutes"""
    if _redis_client is None:
        return
    
    try:
        _redis_client.setex(cache_key, ttl, json.dumps(result))
    except Exception as e:
        logging.warning(f"Cache write error: {e}")

def make_prediction(features):
    """Make prediction using loaded model"""
    required_features = ['price_change_1h', 'price_change_24h', 'volume_change_24h', 
                        'market_cap_change_24h', 'rsi', 'macd', 'moving_avg_7d', 'moving_avg_30d']
    
    # Validate features
    missing = [f for f in required_features if f not in features]
    if missing:
        raise ValueError(f"Missing features: {missing}")
    
    # Check for invalid values
    for key, value in features.items():
        if not isinstance(value, (int, float)) or pd.isna(value):
            logging.warning(f"Invalid feature value for {key}: {value}, using default")
            features[key] = 0.0
    
    # Prepare feature array
    feature_array = np.array([features[f] for f in required_features]).reshape(1, -1)
    
    # Scale and predict
    scaled_features = _scaler.transform(feature_array)
    prediction = _model.predict(scaled_features)[0]
    
    return prediction

def calculate_confidence(features):
    """Calculate prediction confidence based on data quality"""
    try:
        values = list(features.values())
        
        # Check for default/zero values (indicates missing data)
        zero_count = sum(1 for v in values if abs(v) < 1e-6)
        data_quality = max(0.1, 1.0 - (zero_count / len(values)))
        
        # Factor in feature variance
        variance = np.var(values)
        variance_factor = max(0.1, min(0.9, 1.0 / (1.0 + abs(variance))))
        
        # Combined confidence score
        confidence = (data_quality + variance_factor) / 2
        return round(confidence, 3)
    except:
        return 0.5
