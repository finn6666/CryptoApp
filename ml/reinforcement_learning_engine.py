"""
Reinforcement Learning Engine for CryptoApp
Uses RL to learn from trading success/failures and optimize gem detection strategies

Key Innovation: Instead of just predicting prices, the RL agent learns from actual
trading outcomes to continuously improve its gem identification strategy.

RL Components:
1. Environment: Crypto market with real price movements
2. Agent: Gem detection algorithm that takes actions
3. Actions: Buy/Sell/Hold decisions on identified gems  
4. Rewards: Actual profit/loss from those decisions
5. Learning: Agent improves strategy based on outcomes
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import pickle
from collections import deque
import random
from dataclasses import dataclass
import logging
import os

# RL specific imports
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    # PyTorch not available - use fallback implementation
    torch = None
    nn = None
    optim = None
    F = None
    TORCH_AVAILABLE = False
    print("Warning: PyTorch not available. Using simplified RL implementation.")

@dataclass
class TradingAction:
    """Represents a trading action taken by the RL agent"""
    timestamp: datetime
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    confidence: float  # 0-1 confidence in the decision
    price: float
    gem_score: float
    features: Dict[str, float]
    
@dataclass
class TradingOutcome:
    """Represents the outcome of a trading action"""
    action: TradingAction
    final_price: float
    holding_period_days: int
    profit_loss_percent: float
    reward: float
    success: bool

class CryptoTradingEnvironment:
    """
    RL Environment for cryptocurrency trading
    Simulates market conditions and provides rewards based on actual outcomes
    """
    
    def __init__(self, initial_balance: float = 10000):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.positions = {}  # symbol: {'quantity': float, 'entry_price': float, 'entry_date': datetime}
        self.trade_history = []
        self.market_data = {}
        self.current_step = 0
        
    def reset(self):
        """Reset environment for new episode"""
        self.current_balance = self.initial_balance
        self.positions = {}
        self.current_step = 0
        return self._get_state()
    
    def step(self, action: TradingAction) -> Tuple[Dict, float, bool, Dict]:
        """
        Execute action and return new state, reward, done, info
        
        Returns:
            state: Current market state
            reward: Immediate reward from action
            done: Whether episode is finished
            info: Additional information
        """
        reward = self._execute_action(action)
        self.current_step += 1
        
        state = self._get_state()
        done = self._is_episode_done()
        info = {
            'balance': self.current_balance,
            'positions': len(self.positions),
            'total_return': (self.current_balance / self.initial_balance - 1) * 100
        }
        
        return state, reward, done, info
    
    def _execute_action(self, action: TradingAction) -> float:
        """Execute trading action and calculate immediate reward"""
        symbol = action.symbol
        
        if action.action == 'buy':
            return self._execute_buy(action)
        elif action.action == 'sell':
            return self._execute_sell(action)
        else:  # hold
            return self._calculate_hold_reward(action)
    
    def _execute_buy(self, action: TradingAction) -> float:
        """Execute buy order"""
        # Calculate position size based on confidence and risk management
        risk_percent = min(action.confidence * 0.1, 0.05)  # Max 5% per trade
        position_value = self.current_balance * risk_percent
        
        if position_value < self.current_balance * 0.01:  # Min 1% position
            return -0.1  # Small penalty for tiny positions
        
        quantity = position_value / action.price
        
        # Update positions
        if action.symbol in self.positions:
            # Average down/up
            existing = self.positions[action.symbol]
            total_quantity = existing['quantity'] + quantity
            avg_price = (existing['quantity'] * existing['entry_price'] + 
                        quantity * action.price) / total_quantity
            
            self.positions[action.symbol] = {
                'quantity': total_quantity,
                'entry_price': avg_price,
                'entry_date': existing['entry_date']  # Keep original date
            }
        else:
            self.positions[action.symbol] = {
                'quantity': quantity,
                'entry_price': action.price,
                'entry_date': action.timestamp
            }
        
        self.current_balance -= position_value
        
        # Immediate reward based on confidence and gem score
        immediate_reward = (action.confidence * action.gem_score / 100) * 0.1
        return immediate_reward
    
    def _execute_sell(self, action: TradingAction) -> float:
        """Execute sell order"""
        symbol = action.symbol
        
        if symbol not in self.positions:
            return -0.5  # Penalty for trying to sell non-existent position
        
        position = self.positions[symbol]
        sell_value = position['quantity'] * action.price
        
        # Calculate profit/loss
        entry_value = position['quantity'] * position['entry_price']
        profit_loss = sell_value - entry_value
        profit_loss_percent = (profit_loss / entry_value) * 100
        
        # Calculate holding period
        holding_days = (action.timestamp - position['entry_date']).days
        
        # Update balance
        self.current_balance += sell_value
        
        # Calculate reward based on actual performance
        reward = self._calculate_sell_reward(profit_loss_percent, holding_days, action.confidence)
        
        # Record trade outcome
        outcome = TradingOutcome(
            action=action,
            final_price=action.price,
            holding_period_days=holding_days,
            profit_loss_percent=profit_loss_percent,
            reward=reward,
            success=profit_loss_percent > 0
        )
        self.trade_history.append(outcome)
        
        # Remove position
        del self.positions[symbol]
        
        return reward
    
    def _calculate_sell_reward(self, profit_loss_percent: float, holding_days: int, confidence: float) -> float:
        """Calculate reward for sell action based on actual performance"""
        
        # Base reward from profit/loss (scaled)
        base_reward = np.tanh(profit_loss_percent / 50)  # Normalize to -1 to +1
        
        # Time decay factor (prefer shorter holding periods for same return)
        time_factor = max(0.5, 1 - (holding_days / 365) * 0.5)  # Decay over year
        
        # Confidence alignment bonus (reward being right with high confidence)
        if profit_loss_percent > 0 and confidence > 0.7:
            confidence_bonus = 0.2
        elif profit_loss_percent < 0 and confidence < 0.3:
            confidence_bonus = 0.1  # Small bonus for low confidence on losers
        else:
            confidence_bonus = 0
        
        total_reward = base_reward * time_factor + confidence_bonus
        
        return np.clip(total_reward, -2, 2)  # Clip to prevent extreme rewards
    
    def _calculate_hold_reward(self, action: TradingAction) -> float:
        """Calculate reward for hold action"""
        # Small negative reward to encourage action
        # But positive if we're avoiding a bad trade
        
        if action.gem_score < 50:  # Avoiding low-quality gem = good
            return 0.05
        elif action.gem_score > 80:  # Missing high-quality gem = bad
            return -0.1
        else:
            return -0.02  # Small penalty for inaction
    
    def _get_state(self) -> Dict:
        """Get current environment state"""
        return {
            'balance': self.current_balance,
            'positions_count': len(self.positions),
            'total_portfolio_value': self._calculate_portfolio_value(),
            'available_cash_ratio': self.current_balance / self.initial_balance,
            'step': self.current_step
        }
    
    def _calculate_portfolio_value(self) -> float:
        """Calculate total portfolio value including positions"""
        # In real implementation, would use current market prices
        # For now, use entry prices (conservative estimate)
        positions_value = sum(
            pos['quantity'] * pos['entry_price'] 
            for pos in self.positions.values()
        )
        return self.current_balance + positions_value
    
    def _is_episode_done(self) -> bool:
        """Check if episode is complete"""
        # Episode done if:
        # 1. Too many steps (time limit)
        # 2. Balance too low (risk management)
        # 3. Achieved target return
        
        if self.current_step >= 1000:  # Time limit
            return True
        
        if self.current_balance < self.initial_balance * 0.2:  # Lost 80%
            return True
        
        total_value = self._calculate_portfolio_value()
        if total_value > self.initial_balance * 2.0:  # 100% return achieved
            return True
        
        return False

class DQNAgent:
    """
    Deep Q-Network agent for cryptocurrency trading
    Learns optimal trading strategies through experience
    """
    
    def __init__(self, state_size: int, action_size: int, learning_rate: float = 0.001):
        self.state_size = state_size
        self.action_size = action_size  # buy, sell, hold
        self.memory = deque(maxlen=10000)
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = learning_rate
        
        if TORCH_AVAILABLE and optim is not None:
            self.q_network = self._build_model()
            self.target_network = self._build_model()
            if self.q_network is not None and optim is not None:
                self.optimizer = optim.Adam(self.q_network.parameters(), lr=learning_rate)
            else:
                self.optimizer = None
        else:
            # Fallback to simple Q-table for basic functionality
            self.q_table = {}
            self.q_network = None
            self.target_network = None
            self.optimizer = None
    
    def _build_model(self):
        """Build neural network for DQN"""
        if not TORCH_AVAILABLE or nn is None:
            return None
            
        model = nn.Sequential(
            nn.Linear(self.state_size, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, self.action_size)
        )
        return model
    
    def remember(self, state: Dict, action: int, reward: float, next_state: Dict, done: bool):
        """Store experience in replay memory"""
        self.memory.append((state, action, reward, next_state, done))
    
    def act(self, state: Dict, coin_features: Dict) -> Tuple[int, float]:
        """
        Choose action based on current state and coin features
        
        Returns:
            action: 0=hold, 1=buy, 2=sell
            confidence: confidence level in decision
        """
        # Convert state and features to model input
        state_vector = self._state_to_vector(state, coin_features)
        
        # Epsilon-greedy action selection
        if np.random.random() <= self.epsilon:
            action = random.randrange(self.action_size)
            confidence = 0.5  # Random actions have medium confidence
        else:
            if TORCH_AVAILABLE and self.q_network and torch is not None:
                with torch.no_grad():
                    state_tensor = torch.FloatTensor(state_vector).unsqueeze(0)
                    q_values = self.q_network(state_tensor)
                    action = q_values.argmax().item()
                    
                    # Calculate confidence based on Q-value distribution
                    q_values_np = q_values.numpy()[0]
                    max_q = np.max(q_values_np)
                    confidence = torch.softmax(q_values, dim=1).max().item()
            else:
                # Fallback: simple heuristic-based decisions
                action, confidence = self._heuristic_action(coin_features)
        
        return action, confidence
    
    def _state_to_vector(self, state: Dict, coin_features: Dict) -> np.ndarray:
        """Convert state and coin features to input vector"""
        # Combine environment state with coin features
        state_values = [
            state.get('balance', 0) / 10000,  # Normalize
            state.get('positions_count', 0) / 10,  # Normalize
            state.get('available_cash_ratio', 0),
            state.get('step', 0) / 1000  # Normalize
        ]
        
        # Add key coin features (normalized)
        feature_values = [
            coin_features.get('gem_score', 0) / 100,
            coin_features.get('fear_opportunity_score', 0),
            coin_features.get('volume_surge_anomaly', 0),
            coin_features.get('whale_accumulation_score', 0),
            coin_features.get('ecosystem_beta_score', 0),
            coin_features.get('asymmetric_payoff_score', 0)
        ]
        
        return np.array(state_values + feature_values)
    
    def _heuristic_action(self, coin_features: Dict) -> Tuple[int, float]:
        """Fallback heuristic when neural network unavailable"""
        gem_score = coin_features.get('gem_score', 0)
        fear_score = coin_features.get('fear_opportunity_score', 0)
        volume_anomaly = coin_features.get('volume_surge_anomaly', 0)
        
        # Simple scoring system
        buy_score = (gem_score / 100 + fear_score + volume_anomaly) / 3
        
        if buy_score > 0.7:
            return 1, buy_score  # Buy
        elif buy_score < 0.3:
            return 2, 1 - buy_score  # Sell
        else:
            return 0, 0.5  # Hold
    
    def replay(self, batch_size: int = 32):
        """Train the model on a batch of experiences"""
        if not TORCH_AVAILABLE or len(self.memory) < batch_size or self.q_network is None or torch is None:
            return
        
        batch = random.sample(self.memory, batch_size)
        states = torch.FloatTensor([self._state_to_vector(e[0], {}) for e in batch])
        actions = torch.LongTensor([e[1] for e in batch])
        rewards = torch.FloatTensor([e[2] for e in batch])
        next_states = torch.FloatTensor([self._state_to_vector(e[3], {}) for e in batch])
        dones = torch.BoolTensor([e[4] for e in batch])
        
        current_q_values = self.q_network(states).gather(1, actions.unsqueeze(1))
        next_q_values = self.target_network(next_states).max(1)[0].detach()
        target_q_values = rewards + (0.95 * next_q_values * ~dones)
        
        loss = F.mse_loss(current_q_values.squeeze(), target_q_values)
        
        if self.optimizer:
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
        
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
    
    def update_target_network(self):
        """Update target network with current network weights"""
        if TORCH_AVAILABLE and self.q_network is not None and self.target_network is not None:
            self.target_network.load_state_dict(self.q_network.state_dict())

class RLGemDetector:
    """
    Reinforcement Learning Gem Detector
    Integrates RL agent with existing gem detection system
    """
    
    def __init__(self, base_gem_detector, learning_enabled: bool = True):
        self.base_gem_detector = base_gem_detector
        self.learning_enabled = learning_enabled
        
        # RL components
        self.environment = CryptoTradingEnvironment()
        self.agent = DQNAgent(state_size=10, action_size=3)  # hold, buy, sell
        
        # Performance tracking
        self.performance_history = []
        self.learning_episodes = 0
        
        # Active positions for real-time learning
        self.active_positions = {}
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def analyze_coin_with_rl(self, coin_data: Dict, market_context: Optional[Dict] = None) -> Dict:
        """
        Analyze coin using base detector + RL decision making
        
        Returns enhanced analysis with RL-based recommendations
        """
        # Get base gem analysis
        base_analysis = self.base_gem_detector.predict_hidden_gem(
            coin_data, market_context
        )
        
        # Get current environment state
        env_state = self.environment._get_state()
        
        # Extract features for RL agent
        features = self.base_gem_detector.extract_advanced_features(coin_data, market_context)
        
        # Get RL agent recommendation
        rl_action, confidence = self.agent.act(env_state, features)
        
        # Translate action to recommendation
        action_map = {0: 'hold', 1: 'buy', 2: 'sell'}
        rl_recommendation = action_map[rl_action]
        
        # Enhanced analysis combining base + RL
        if base_analysis is not None:
            enhanced_analysis = base_analysis.copy()
        else:
            # Fallback when base model isn't available
            enhanced_analysis = {
                'is_hidden_gem': False,
                'gem_probability': 0.5,
                'confidence': 0.5,
                'gem_score': 50.0,
                'risk_level': 'Medium',
                'risk_score': 0.5,
                'key_strengths': [],
                'key_weaknesses': ['Base model not available'],
                'recommendation': 'No recommendation available'
            }
        enhanced_analysis.update({
            'rl_recommendation': rl_recommendation,
            'rl_confidence': confidence,
            'rl_reasoning': self._generate_rl_reasoning(rl_action, features, confidence),
            'learning_episode': self.learning_episodes,
            'agent_experience_level': len(self.agent.memory)
        })
        
        # If learning enabled, simulate taking the action for learning
        if self.learning_enabled:
            self._simulate_action_for_learning(coin_data, rl_action, confidence, features)
        
        return enhanced_analysis
    
    def _generate_rl_reasoning(self, action: int, features: Dict, confidence: float) -> str:
        """Generate human-readable reasoning for RL decision"""
        action_names = ['Hold', 'Buy', 'Sell']
        action_name = action_names[action]
        
        # Key factors influencing decision
        key_factors = []
        
        gem_score = features.get('gem_score', 0)
        if gem_score > 80:
            key_factors.append(f"High gem score ({gem_score:.1f})")
        elif gem_score < 40:
            key_factors.append(f"Low gem score ({gem_score:.1f})")
        
        fear_score = features.get('fear_opportunity_score', 0)
        if fear_score > 0.7:
            key_factors.append("Strong fear opportunity detected")
        
        volume_anomaly = features.get('volume_surge_anomaly', 0)
        if volume_anomaly > 0.7:
            key_factors.append("Volume surge anomaly detected")
        
        whale_score = features.get('whale_accumulation_score', 0)
        if whale_score > 0.7:
            key_factors.append("Whale accumulation pattern detected")
        
        reasoning = f"RL Agent recommends {action_name} (confidence: {confidence:.1f})"
        if key_factors:
            reasoning += f". Key factors: {', '.join(key_factors)}"
        
        return reasoning
    
    def _simulate_action_for_learning(self, coin_data: Dict, action: int, 
                                    confidence: float, features: Dict):
        """Simulate taking action to generate learning experience"""
        symbol = coin_data.get('symbol', 'UNKNOWN')
        price = float(coin_data.get('price', 0))
        
        if price == 0:
            return  # Skip if no valid price
        
        # Create trading action
        trading_action = TradingAction(
            timestamp=datetime.now(),
            symbol=symbol,
            action=['hold', 'buy', 'sell'][action],
            confidence=confidence,
            price=price,
            gem_score=features.get('gem_score', 0),
            features=features
        )
        
        # Execute in environment and get reward
        state = self.environment._get_state()
        next_state, reward, done, info = self.environment.step(trading_action)
        
        # Store experience for learning
        self.agent.remember(state, action, reward, next_state, done)
        
        # Train periodically
        if len(self.agent.memory) > 100 and len(self.agent.memory) % 10 == 0:
            self.agent.replay()
        
        # Update target network periodically
        if len(self.agent.memory) % 100 == 0:
            self.agent.update_target_network()
    
    def learn_from_real_outcome(self, symbol: str, entry_price: float, 
                               current_price: float, days_held: int, 
                               initial_features: Dict):
        """Learn from real trading outcomes"""
        
        profit_loss_percent = ((current_price - entry_price) / entry_price) * 100
        
        # Calculate reward based on actual outcome
        time_factor = max(0.5, 1 - (days_held / 365) * 0.5)
        base_reward = np.tanh(profit_loss_percent / 50)
        actual_reward = base_reward * time_factor
        
        # Store this as high-value learning experience
        # (In full implementation, would reconstruct the state and action)
        
        # Update performance tracking
        outcome = {
            'symbol': symbol,
            'profit_loss_percent': profit_loss_percent,
            'days_held': days_held,
            'reward': actual_reward,
            'timestamp': datetime.now()
        }
        self.performance_history.append(outcome)
        
        # Log learning
        self.logger.info(f"Learned from {symbol}: {profit_loss_percent:.1f}% in {days_held} days")
        
        return actual_reward
    
    def get_performance_metrics(self) -> Dict:
        """Get RL agent performance metrics"""
        if not self.performance_history:
            return {'status': 'No trading history yet'}
        
        recent_trades = self.performance_history[-50:]  # Last 50 trades
        
        win_rate = sum(1 for t in recent_trades if t['profit_loss_percent'] > 0) / len(recent_trades)
        avg_return = np.mean([t['profit_loss_percent'] for t in recent_trades])
        avg_holding_period = np.mean([t['days_held'] for t in recent_trades])
        total_return = sum([t['profit_loss_percent'] for t in recent_trades])
        
        return {
            'total_trades': len(self.performance_history),
            'recent_win_rate': win_rate,
            'average_return_percent': avg_return,
            'average_holding_days': avg_holding_period,
            'total_return_percent': total_return,
            'learning_episodes': self.learning_episodes,
            'agent_epsilon': self.agent.epsilon,
            'experience_buffer_size': len(self.agent.memory)
        }
    
    def save_model(self, filepath: str):
        """Save RL model and experience"""
        model_data = {
            'performance_history': self.performance_history,
            'learning_episodes': self.learning_episodes,
            'agent_epsilon': self.agent.epsilon,
            'environment_balance': self.environment.current_balance
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        if TORCH_AVAILABLE and self.agent.q_network and torch is not None:
            torch.save(self.agent.q_network.state_dict(), 
                      filepath.replace('.pkl', '_network.pth'))
    
    def load_model(self, filepath: str):
        """Load RL model and experience"""
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.performance_history = model_data.get('performance_history', [])
            self.learning_episodes = model_data.get('learning_episodes', 0)
            self.agent.epsilon = model_data.get('agent_epsilon', 1.0)
            self.environment.current_balance = model_data.get('environment_balance', 10000)
            
            if TORCH_AVAILABLE and self.agent.q_network and torch is not None:
                network_path = filepath.replace('.pkl', '_network.pth')
                if os.path.exists(network_path):
                    self.agent.q_network.load_state_dict(torch.load(network_path))
                    self.agent.update_target_network()
            
            self.logger.info(f"Loaded RL model with {len(self.performance_history)} trade history")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load RL model: {e}")
            return False