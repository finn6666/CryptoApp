"""
RL Integration for CryptoApp
Integrates Reinforcement Learning with existing gem detection system

This module shows how to:
1. Train RL agent from historical data
2. Use RL for live trading decisions  
3. Learn from real outcomes to improve performance
4. Track and optimize RL agent performance
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.reinforcement_learning_engine import RLGemDetector
from ml.enhanced_gem_detector import HiddenGemDetector
from ml.advanced_alpha_features import AdvancedAlphaFeatures
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Tuple, Optional

class RLCryptoTrainer:
    """
    Handles training and backtesting of RL gem detection system
    """
    
    def __init__(self):
        # Initialize base gem detector with advanced features
        self.base_detector = HiddenGemDetector()
        self.alpha_features = AdvancedAlphaFeatures()
        
        # Initialize RL detector
        self.rl_detector = RLGemDetector(
            base_gem_detector=self.base_detector,
            learning_enabled=True
        )
        
        self.logger = logging.getLogger(__name__)
        
    def backtest_rl_strategy(self, historical_data: List[Dict], 
                           lookback_days: int = 30) -> Dict:
        """
        Backtest RL strategy on historical crypto data
        
        Args:
            historical_data: List of crypto data points with OHLCV + features
            lookback_days: Number of days to hold positions for backtesting
            
        Returns:
            Comprehensive backtest results
        """
        
        results = {
            'total_trades': 0,
            'winning_trades': 0,
            'total_return': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'trades': [],
            'learning_progress': []
        }
        
        # Sort data by timestamp
        historical_data.sort(key=lambda x: x.get('timestamp', ''))
        
        # Process each data point
        for i, data_point in enumerate(historical_data[:-lookback_days]):
            
            # Analyze with RL
            analysis = self.rl_detector.analyze_coin_with_rl(
                data_point, 
                market_context={'market_phase': 'historical_backtest'}
            )
            
            # If RL recommends buy, simulate trade
            if analysis['rl_recommendation'] == 'buy' and analysis['rl_confidence'] > 0.6:
                
                # Find outcome after holding period
                future_data = historical_data[i + lookback_days]
                entry_price = float(data_point.get('price', 0))
                exit_price = float(future_data.get('price', entry_price))
                
                if entry_price > 0:
                    profit_loss = ((exit_price - entry_price) / entry_price) * 100
                    
                    # Learn from this outcome
                    reward = self.rl_detector.learn_from_real_outcome(
                        symbol=data_point.get('symbol', 'UNKNOWN'),
                        entry_price=entry_price,
                        current_price=exit_price,
                        days_held=lookback_days,
                        initial_features=analysis
                    )
                    
                    # Track results
                    trade_result = {
                        'symbol': data_point.get('symbol'),
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'profit_loss_percent': profit_loss,
                        'rl_confidence': analysis['rl_confidence'],
                        'gem_score': analysis.get('gem_score', 0),
                        'reward': reward
                    }
                    
                    results['trades'].append(trade_result)
                    results['total_trades'] += 1
                    
                    if profit_loss > 0:
                        results['winning_trades'] += 1
                    
                    results['total_return'] += profit_loss
            
            # Track learning progress every 50 data points
            if i % 50 == 0:
                metrics = self.rl_detector.get_performance_metrics()
                metrics['data_point'] = i
                results['learning_progress'].append(metrics)
        
        # Calculate final metrics
        if results['total_trades'] > 0:
            results['win_rate'] = results['winning_trades'] / results['total_trades']
            
            returns = [trade['profit_loss_percent'] for trade in results['trades']]
            results['average_return'] = np.mean(returns)
            results['return_std'] = np.std(returns)
            
            if results['return_std'] > 0:
                results['sharpe_ratio'] = results['average_return'] / results['return_std']
            
            # Calculate max drawdown
            cumulative_returns = np.cumsum(returns)
            peak = np.maximum.accumulate(cumulative_returns)
            drawdown = peak - cumulative_returns
            results['max_drawdown'] = np.max(drawdown)
        
        return results
    
    def train_from_csv(self, csv_filepath: str) -> Dict:
        """Train RL agent from CSV file of historical crypto data"""
        
        try:
            df = pd.read_csv(csv_filepath)
            
            # Convert DataFrame to list of dicts
            historical_data = []
            for _, row in df.iterrows():
                data_point = {
                    'symbol': row.get('symbol', 'UNKNOWN'),
                    'price': row.get('close', row.get('price', 0)),
                    'volume': row.get('volume', 0),
                    'market_cap': row.get('market_cap', 0),
                    'timestamp': row.get('timestamp', datetime.now().isoformat())
                }
                
                # Add any additional features from CSV
                for col in df.columns:
                    if col not in data_point:
                        data_point[col] = row.get(col, 0)
                
                historical_data.append(data_point)
            
            self.logger.info(f"Training RL agent on {len(historical_data)} data points")
            
            # Run backtest training
            results = self.backtest_rl_strategy(historical_data)
            
            self.logger.info(f"Training complete. Win rate: {results.get('win_rate', 0):.2f}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error training from CSV: {e}")
            return {'error': str(e)}

class RLLiveTrading:
    """
    Handles live trading with RL-enhanced gem detection
    """
    
    def __init__(self, model_filepath: Optional[str] = None):
        # Initialize RL detector
        self.base_detector = HiddenGemDetector()
        self.rl_detector = RLGemDetector(
            base_gem_detector=self.base_detector,
            learning_enabled=True  # Continue learning from live trades
        )
        
        # Load pre-trained model if available
        if model_filepath and os.path.exists(model_filepath):
            self.rl_detector.load_model(model_filepath)
        
        self.active_positions = {}
        self.trade_log = []
        
        self.logger = logging.getLogger(__name__)
    
    def analyze_live_coin(self, coin_data: Dict, market_context: Optional[Dict] = None) -> Dict:
        """
        Analyze coin with RL-enhanced detection for live trading
        
        Returns comprehensive analysis including RL recommendations
        """
        
        # Get RL analysis
        analysis = self.rl_detector.analyze_coin_with_rl(coin_data, market_context)
        
        # Add risk assessment
        analysis['risk_assessment'] = self._assess_risk(analysis, coin_data)
        
        # Add position sizing recommendation
        analysis['position_size_percent'] = self._calculate_position_size(analysis)
        
        # Add timing analysis
        analysis['timing_signals'] = self._analyze_timing(coin_data, market_context)
        
        return analysis
    
    def _assess_risk(self, analysis: Dict, coin_data: Dict) -> Dict:
        """Assess risk level of potential trade"""
        
        risk_factors = []
        risk_score = 0.5  # Start with medium risk
        
        # Market cap risk
        market_cap = coin_data.get('market_cap', 0)
        if market_cap < 10_000_000:  # < $10M = high risk
            risk_factors.append("Very low market cap")
            risk_score += 0.2
        elif market_cap < 100_000_000:  # < $100M = medium risk
            risk_factors.append("Low market cap")
            risk_score += 0.1
        
        # Volume risk
        volume_24h = coin_data.get('volume_24h', 0)
        if volume_24h < 100_000:  # < $100k volume = illiquid
            risk_factors.append("Low liquidity")
            risk_score += 0.15
        
        # RL confidence risk
        if analysis['rl_confidence'] < 0.5:
            risk_factors.append("Low RL confidence")
            risk_score += 0.1
        
        # Gem score risk
        if analysis.get('gem_score', 0) < 50:
            risk_factors.append("Low gem score")
            risk_score += 0.1
        
        return {
            'risk_score': min(1.0, risk_score),
            'risk_level': 'High' if risk_score > 0.7 else 'Medium' if risk_score > 0.4 else 'Low',
            'risk_factors': risk_factors
        }
    
    def _calculate_position_size(self, analysis: Dict) -> float:
        """Calculate recommended position size as percentage of portfolio"""
        
        base_size = 5.0  # Base 5% position
        
        # Adjust for RL confidence
        confidence_multiplier = analysis['rl_confidence']
        
        # Adjust for gem score
        gem_score_multiplier = analysis.get('gem_score', 50) / 100
        
        # Adjust for risk
        risk_score = analysis['risk_assessment']['risk_score']
        risk_multiplier = 1.0 - (risk_score * 0.5)  # Reduce size for higher risk
        
        # Calculate final size
        position_size = base_size * confidence_multiplier * gem_score_multiplier * risk_multiplier
        
        # Cap at reasonable limits
        return np.clip(position_size, 0.5, 10.0)  # 0.5% to 10% max
    
    def _analyze_timing(self, coin_data: Dict, market_context: Optional[Dict]) -> Dict:
        """Analyze entry timing signals"""
        
        signals = {
            'immediate_entry': False,
            'wait_for_dip': False,
            'strong_momentum': False,
            'timing_score': 0.5
        }
        
        # Check for volume surge (good timing)
        volume_ratio = coin_data.get('volume_surge_ratio', 1.0)
        if volume_ratio > 3.0:
            signals['strong_momentum'] = True
            signals['immediate_entry'] = True
            signals['timing_score'] += 0.2
        
        # Check for price momentum
        price_change_24h = coin_data.get('price_change_24h', 0)
        if price_change_24h > 10:  # Strong upward momentum
            signals['strong_momentum'] = True
            signals['timing_score'] += 0.15
        elif price_change_24h < -5:  # Potential dip buying opportunity
            signals['wait_for_dip'] = True
            signals['timing_score'] += 0.1
        
        # Market context timing
        if market_context:
            market_sentiment = market_context.get('market_sentiment', 'neutral')
            if market_sentiment == 'bullish':
                signals['timing_score'] += 0.1
            elif market_sentiment == 'bearish':
                signals['timing_score'] -= 0.1
        
        signals['timing_score'] = np.clip(signals['timing_score'], 0, 1)
        
        return signals
    
    def record_trade_outcome(self, symbol: str, entry_price: float, 
                           current_price: float, entry_date: datetime) -> Dict:
        """
        Record actual trade outcome for RL learning
        
        This should be called when you actually sell a position
        """
        
        days_held = (datetime.now() - entry_date).days
        
        # Learn from outcome
        reward = self.rl_detector.learn_from_real_outcome(
            symbol=symbol,
            entry_price=entry_price,
            current_price=current_price,
            days_held=days_held,
            initial_features={}  # Could store original features if available
        )
        
        profit_loss_percent = ((current_price - entry_price) / entry_price) * 100
        
        # Log trade
        trade_record = {
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': current_price,
            'profit_loss_percent': profit_loss_percent,
            'days_held': days_held,
            'reward': reward,
            'timestamp': datetime.now().isoformat()
        }
        
        self.trade_log.append(trade_record)
        
        self.logger.info(f"Recorded trade: {symbol} {profit_loss_percent:.2f}% in {days_held} days")
        
        return trade_record
    
    def get_rl_performance_summary(self) -> Dict:
        """Get comprehensive RL performance summary"""
        
        base_metrics = self.rl_detector.get_performance_metrics()
        
        # Add live trading specific metrics
        if self.trade_log:
            recent_trades = self.trade_log[-20:]  # Last 20 trades
            
            live_win_rate = sum(1 for t in recent_trades if t['profit_loss_percent'] > 0) / len(recent_trades)
            live_avg_return = np.mean([t['profit_loss_percent'] for t in recent_trades])
            live_total_return = sum([t['profit_loss_percent'] for t in recent_trades])
            
            base_metrics.update({
                'live_trades_count': len(self.trade_log),
                'live_win_rate': live_win_rate,
                'live_average_return': live_avg_return,
                'live_total_return': live_total_return,
                'active_positions': len(self.active_positions)
            })
        
        return base_metrics
    
    def save_rl_model(self, filepath: str):
        """Save trained RL model"""
        return self.rl_detector.save_model(filepath)

# Example usage functions

def example_backtest():
    """Example of how to backtest RL strategy"""
    
    trainer = RLCryptoTrainer()
    
    # Train on sample data (in real use, load your historical data)
    sample_data = [
        {
            'symbol': 'BTC',
            'price': 50000 + i * 100 + np.random.normal(0, 500),
            'volume': 1000000 + np.random.normal(0, 100000),
            'market_cap': 1000000000,
            'timestamp': (datetime.now() - timedelta(days=365-i)).isoformat()
        }
        for i in range(365)
    ]
    
    results = trainer.backtest_rl_strategy(sample_data)
    print(f"Backtest Results:")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results.get('win_rate', 0):.2%}")
    print(f"Total Return: {results['total_return']:.2f}%")
    print(f"Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
    
    return results

def example_live_analysis():
    """Example of live coin analysis with RL"""
    
    live_trader = RLLiveTrading()
    
    # Example coin data
    coin_data = {
        'symbol': 'ETH',
        'price': 3000,
        'volume_24h': 1000000,
        'market_cap': 360000000000,
        'price_change_24h': 5.2,
        'volume_surge_ratio': 2.1
    }
    
    market_context = {
        'market_sentiment': 'bullish',
        'btc_dominance': 45.2
    }
    
    analysis = live_trader.analyze_live_coin(coin_data, market_context)
    
    print("RL Analysis Results:")
    print(f"Recommendation: {analysis['rl_recommendation']}")
    print(f"Confidence: {analysis['rl_confidence']:.2f}")
    print(f"Risk Level: {analysis['risk_assessment']['risk_level']}")
    print(f"Position Size: {analysis['position_size_percent']:.1f}%")
    print(f"Timing Score: {analysis['timing_signals']['timing_score']:.2f}")
    
    return analysis

if __name__ == "__main__":
    # Run examples
    print("=== RL Backtest Example ===")
    example_backtest()
    
    print("\n=== Live Analysis Example ===")
    example_live_analysis()