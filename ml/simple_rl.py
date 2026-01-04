"""
Lightweight RL System for CryptoApp
Simple Q-learning based gem detection that learns from outcomes WITHOUT PyTorch

Key Features:
- No heavy dependencies (no PyTorch/TensorFlow)
- Simple Q-table learning (fast, interpretable)
- Persists learning to JSON (survives restarts)
- Works perfectly with intermittent server usage
- Minimal code, easy to maintain

How It Works:
1. Track which gem features lead to good outcomes
2. Adjust confidence in features based on real results
3. Save learned patterns to disk
4. Use learned patterns to boost/reduce gem scores
"""

import numpy as np
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class SimpleRLGemLearner:
    """
    Lightweight RL that learns which gem features correlate with success
    Uses simple Q-learning with feature-based state representation
    """
    
    def __init__(self, learning_rate: float = 0.1, discount_factor: float = 0.9):
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        
        # Feature weights learned over time
        # Format: {feature_name: {action: q_value}}
        self.feature_weights = defaultdict(lambda: {'buy': 0.5, 'hold': 0.5})
        
        # Track outcomes for statistics
        self.trade_history = []
        self.success_rate = 0.5
        self.total_trades = 0
        self.winning_trades = 0
        
        # File paths
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.save_dir = os.path.join(project_root, 'models')
        self.save_path = os.path.join(self.save_dir, 'rl_simple_learner.json')
        
        # Load existing learning if available
        self.load_learning()
    
    def get_recommendation(self, gem_score: float, features: Dict[str, float]) -> Dict:
        """
        Get RL recommendation based on learned feature weights
        
        Args:
            gem_score: Base gem score from ML model (0-100)
            features: Dictionary of gem features
        
        Returns:
            {
                'action': 'buy' or 'hold',
                'confidence': 0.0-1.0,
                'rl_boost': adjustment to gem_score,
                'reasoning': why this recommendation
            }
        """
        # Calculate Q-values for buy vs hold based on features
        q_buy = self._calculate_q_value('buy', features)
        q_hold = self._calculate_q_value('hold', features)
        
        # Determine action and confidence
        if q_buy > q_hold:
            action = 'buy'
            confidence = self._normalize_confidence(q_buy - q_hold)
            boost = confidence * 10  # Up to +10 points boost
        else:
            action = 'hold'
            confidence = self._normalize_confidence(q_hold - q_buy)
            boost = -confidence * 5  # Up to -5 points penalty
        
        # Generate reasoning
        reasoning = self._generate_reasoning(action, features, q_buy, q_hold)
        
        return {
            'action': action,
            'confidence': round(confidence, 3),
            'rl_boost': round(boost, 2),
            'q_buy': round(q_buy, 3),
            'q_hold': round(q_hold, 3),
            'reasoning': reasoning,
            'success_rate': self.success_rate,
            'total_trades': self.total_trades
        }
    
    def learn_from_outcome(self, 
                          features: Dict[str, float], 
                          action: str,
                          profit_pct: float,
                          days_held: int,
                          symbol: str = None,
                          entry_price: float = None,
                          exit_price: float = None,
                          notes: str = None) -> Dict:
        """
        Learn from actual trading outcome
        
        Args:
            features: Features that led to the decision
            action: Action taken ('buy' or 'hold')
            profit_pct: Profit/loss percentage
            days_held: How long position was held
            symbol: Coin symbol (optional, for tracking)
            entry_price: Entry price (optional, for tracking)
            exit_price: Exit price (optional, for tracking)
            notes: User notes about trade (optional, for tracking)
        
        Returns:
            Learning summary
        """
        # Calculate reward
        reward = self._calculate_reward(profit_pct, days_held)
        
        # Update Q-values for each feature
        updates_made = 0
        for feature_name, feature_value in features.items():
            if abs(feature_value) > 0.01:  # Only learn from meaningful features
                self._update_feature_weight(feature_name, action, reward, feature_value)
                updates_made += 1
        
        # Track outcome statistics
        success = profit_pct > 0
        self.total_trades += 1
        if success:
            self.winning_trades += 1
        self.success_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0.5
        
        # Save trade to history with full details
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'profit_pct': round(profit_pct, 2),
            'reward': round(reward, 3),
            'success': success,
            'days_held': days_held
        }
        
        # Add optional tracking fields
        if symbol:
            trade_record['symbol'] = symbol
        if entry_price is not None:
            trade_record['entry_price'] = entry_price
        if exit_price is not None:
            trade_record['exit_price'] = exit_price
        if notes:
            trade_record['notes'] = notes
        
        self.trade_history.append(trade_record)
        
        # Keep only recent history
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]
        
        # Save updated learning
        self.save_learning()
        
        logger.info(f"RL learned from {action}: {profit_pct:+.1f}% profit, reward: {reward:.2f}")
        
        return {
            'reward': reward,
            'success': success,
            'updates_made': updates_made,
            'new_success_rate': self.success_rate,
            'total_experience': self.total_trades
        }
    
    def _calculate_q_value(self, action: str, features: Dict[str, float]) -> float:
        """Calculate Q-value for an action given features"""
        q_value = 0.5  # Start at neutral
        
        # Aggregate weighted feature values
        for feature_name, feature_value in features.items():
            if feature_name in self.feature_weights:
                weight = self.feature_weights[feature_name][action]
                # Weight feature value by learned weight
                q_value += feature_value * weight * 0.1  # Scale down contribution
        
        # Normalize to 0-1 range
        return max(0.0, min(1.0, q_value))
    
    def _update_feature_weight(self, feature_name: str, action: str, 
                              reward: float, feature_value: float):
        """Update feature weight using Q-learning update rule"""
        current_q = self.feature_weights[feature_name][action]
        
        # Simple Q-learning update: Q(s,a) = Q(s,a) + α[reward - Q(s,a)]
        # Weight update by feature importance (magnitude)
        importance = abs(feature_value)
        new_q = current_q + self.learning_rate * importance * (reward - current_q)
        
        # Clamp to reasonable range
        self.feature_weights[feature_name][action] = max(0.0, min(1.0, new_q))
    
    def _calculate_reward(self, profit_pct: float, days_held: int) -> float:
        """Calculate reward from outcome"""
        # Base reward from profit (normalized to -1 to +1)
        base_reward = np.tanh(profit_pct / 50)
        
        # Time decay (prefer quicker returns)
        time_factor = max(0.5, 1.0 - (days_held / 365) * 0.5)
        
        return base_reward * time_factor
    
    def _normalize_confidence(self, q_diff: float) -> float:
        """Normalize Q-value difference to confidence score"""
        # Map Q difference to 0-1 confidence
        return min(1.0, abs(q_diff) * 2)
    
    def _generate_reasoning(self, action: str, features: Dict, 
                           q_buy: float, q_hold: float) -> str:
        """Generate human-readable reasoning"""
        top_features = sorted(features.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
        
        if action == 'buy':
            return f"RL suggests BUY (Q={q_buy:.2f} vs {q_hold:.2f}). Strong features: {[f[0] for f in top_features]}"
        else:
            return f"RL suggests HOLD (Q={q_hold:.2f} vs {q_buy:.2f}). Learned to be cautious with these features."
    
    def save_learning(self):
        """Save learned weights to disk"""
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            
            data = {
                'feature_weights': dict(self.feature_weights),
                'success_rate': self.success_rate,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'trade_history': self.trade_history[-50:],  # Save recent 50
                'last_updated': datetime.now().isoformat(),
                'version': '1.0-simple'
            }
            
            with open(self.save_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"RL learning saved: {self.total_trades} trades, {self.success_rate:.1%} success")
        except Exception as e:
            logger.error(f"Failed to save RL learning: {e}")
    
    def load_learning(self):
        """Load previously learned weights from disk"""
        try:
            if not os.path.exists(self.save_path):
                logger.info("No previous RL learning found, starting fresh")
                return
            
            with open(self.save_path, 'r') as f:
                data = json.load(f)
            
            # Load weights
            self.feature_weights = defaultdict(
                lambda: {'buy': 0.5, 'hold': 0.5},
                data.get('feature_weights', {})
            )
            
            # Load statistics
            self.success_rate = data.get('success_rate', 0.5)
            self.total_trades = data.get('total_trades', 0)
            self.winning_trades = data.get('winning_trades', 0)
            self.trade_history = data.get('trade_history', [])
            
            logger.info(f"RL learning loaded: {self.total_trades} trades, {self.success_rate:.1%} success")
        except Exception as e:
            logger.warning(f"Failed to load RL learning: {e}, starting fresh")
    
    def get_stats(self) -> Dict:
        """Get learning statistics"""
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.total_trades - self.winning_trades,
            'success_rate': round(self.success_rate * 100, 2),
            'features_learned': len(self.feature_weights),
            'recent_trades': self.trade_history[-10:] if self.trade_history else []
        }
    
    def reset_learning(self):
        """Reset all learned weights (fresh start)"""
        self.feature_weights = defaultdict(lambda: {'buy': 0.5, 'hold': 0.5})
        self.trade_history = []
        self.success_rate = 0.5
        self.total_trades = 0
        self.winning_trades = 0
        self.save_learning()
        logger.info("RL learning reset to defaults")

# Global instance for easy import
simple_rl_learner = SimpleRLGemLearner()
