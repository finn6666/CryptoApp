import requests
import json
import logging
from typing import Dict, Optional
from datetime import datetime

class MLService:
    def __init__(self, azure_function_url: str = None):
        self.azure_function_url = azure_function_url or "https://your-ml-function.azurewebsites.net/api/predict"
        self.session = requests.Session()
        self.session.timeout = 30
    
    async def get_price_prediction(self, symbol: str, features: Optional[Dict] = None) -> Dict:
        """Get ML price prediction for a cryptocurrency"""
        try:
            payload = {"symbol": symbol.upper()}
            
            if features:
                payload["features"] = features
            
            response = self.session.post(
                self.azure_function_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Add interpretation
            result["interpretation"] = self._interpret_prediction(result)
            
            return result
            
        except requests.RequestException as e:
            logging.error(f"ML API request failed: {e}")
            return {"error": f"Prediction service unavailable: {str(e)}"}
        except Exception as e:
            logging.error(f"ML prediction error: {e}")
            return {"error": f"Failed to get prediction: {str(e)}"}
    
    def _interpret_prediction(self, result: Dict) -> Dict:
        """Add human-readable interpretation of prediction"""
        prediction = result.get("prediction", 0)
        confidence = result.get("confidence", 0)
        
        # Convert prediction to percentage
        prediction_pct = prediction * 100
        
        if abs(prediction_pct) < 0.5:
            direction = "stable"
            strength = "neutral"
        elif prediction_pct > 0:
            direction = "bullish"
            strength = "strong" if prediction_pct > 2 else "moderate" if prediction_pct > 1 else "weak"
        else:
            direction = "bearish" 
            strength = "strong" if prediction_pct < -2 else "moderate" if prediction_pct < -1 else "weak"
        
        confidence_level = "high" if confidence > 0.7 else "medium" if confidence > 0.4 else "low"
        
        return {
            "direction": direction,
            "strength": strength,
            "confidence_level": confidence_level,
            "percentage_change": round(prediction_pct, 2),
            "recommendation": self._get_recommendation(direction, strength, confidence_level)
        }
    
    def _get_recommendation(self, direction: str, strength: str, confidence_level: str) -> str:
        """Generate trading recommendation"""
        if confidence_level == "low":
            return "Hold - Low confidence prediction"
        
        if direction == "stable":
            return "Hold - Price expected to remain stable"
        elif direction == "bullish" and strength in ["moderate", "strong"]:
            return f"Consider Buy - {strength.title()} upward movement expected"
        elif direction == "bearish" and strength in ["moderate", "strong"]:
            return f"Consider Sell - {strength.title()} downward movement expected"
        else:
            return "Hold - Weak signal detected"
