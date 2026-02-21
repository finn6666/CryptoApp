"""
Enhanced ML model specifically designed to identify cryptocurrency hidden gems
Focuses on patterns and signals that indicate undervalued opportunities with high potential
Now includes advanced alpha detection features that others typically miss
PHASE 4: Now integrated with multi-agent analysis system
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from datetime import datetime, timedelta
import joblib
import json
import os
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

# Import our advanced alpha features
from .advanced_alpha_features import AdvancedAlphaFeatures

# Import Multi-Agent System (Official Google ADK)
try:
    from .agents.official import analyze_crypto
    MULTI_AGENT_AVAILABLE = True
except ImportError:
    MULTI_AGENT_AVAILABLE = False
    analyze_crypto = None

# Import Simple RL (optional, lightweight learning)
try:
    from .simple_rl import simple_rl_learner
    SIMPLE_RL_AVAILABLE = True
except ImportError:
    SIMPLE_RL_AVAILABLE = False
    simple_rl_learner = None


class OrchestratorWrapper:
    """
    Wrapper to provide orchestrator interface for PortfolioManager
    Uses the official Google ADK's analyze_crypto function
    """
    def __init__(self, analyze_crypto_func):
        self.analyze_crypto_func = analyze_crypto_func
        self.agents = ['Research', 'Technical', 'Risk', 'Sentiment']  # For status reporting
    
    async def analyze_coin(self, symbol: str, coin_data: Dict) -> Dict:
        """
        Analyze coin using official ADK analyze_crypto function
        
        Args:
            symbol: Coin symbol
            coin_data: Coin market data
            
        Returns:
            Analysis result dictionary
        """
        if not self.analyze_crypto_func:
            return {'error': 'Multi-agent not available'}
        
        try:
            result = await self.analyze_crypto_func(
                symbol=symbol,
                coin_data=coin_data,
                session_id=f"portfolio_{symbol}",
                use_memory=False  # Don't use memory for portfolio batch analysis
            )
            return result
        except Exception as e:
            return {'error': str(e)}
    
    def get_metrics(self) -> Dict:
        """Return basic metrics for compatibility"""
        return {
            'agents': len(self.agents),
            'available': True
        }


class HiddenGemDetector:
    """
    Enhanced ML model specifically designed to identify hidden gems
    
    Key Innovation: Uses advanced alpha features + AI sentiment analysis to detect
    opportunities others miss by analyzing:
    - Market psychology patterns (fear/greed contrarian signals)
    - Timing anomalies (market inefficiency windows)  
    - Cross-asset relationships (network effects)
    - Smart money vs crowd behavior patterns
    - Asymmetric risk-reward opportunities
    - AI-powered sentiment analysis (Gemini agent integration)
    """
    
    def __init__(self, model_dir='models'):
        self.model = None
        self.scaler = RobustScaler()  # More robust to outliers than StandardScaler
        self.feature_importance = None
        self.feature_names = None
        self.model_loaded = False
        self.model_dir = model_dir
        self.model_path = os.path.join(model_dir, 'hidden_gem_detector.pkl')
        
        # Initialize advanced alpha feature extractor
        self.alpha_features = AdvancedAlphaFeatures()
        
        # Initialize Multi-Agent System (PHASE 4)
        self.multi_agent_enabled = MULTI_AGENT_AVAILABLE
        self.orchestrator = None  # Will be set if multi-agent is available
        if self.multi_agent_enabled:
            try:
                # Using Official Google ADK - create orchestrator wrapper
                self.orchestrator = OrchestratorWrapper(analyze_crypto)
                # Multi-agent initialized successfully
            except Exception as e:
                logger.warning(f"Multi-Agent System: Failed to initialize - {e}")
                self.multi_agent_enabled = False
        
        # Check Simple RL availability
        self.rl_enabled = SIMPLE_RL_AVAILABLE and simple_rl_learner is not None
        
        # Create models directory if it doesn't exist
        os.makedirs(model_dir, exist_ok=True)
        
    def extract_advanced_features(self, coin_data: Dict, market_context: Optional[Dict] = None) -> Dict:
        """Extract advanced features that indicate hidden gem potential"""
        features = {}
        
        # Basic price and market features
        features['current_price'] = float(coin_data.get('price', 0))
        price_change = coin_data.get('price_change_24h', 0)
        # Handle both float and dict formats
        if isinstance(price_change, dict):
            features['price_change_24h'] = float(price_change.get('usd', 0))
        else:
            features['price_change_24h'] = float(price_change)
        features['market_cap_rank'] = int(coin_data.get('market_cap_rank', 999))
        
        # Hidden gem core indicators
        features['is_low_cap'] = 1 if features['market_cap_rank'] > 100 else 0
        features['is_micro_cap'] = 1 if features['market_cap_rank'] > 300 else 0
        features['is_nano_cap'] = 1 if features['market_cap_rank'] > 500 else 0
        
        # Volume analysis
        features['volume_price_ratio'] = self._calculate_volume_price_ratio(coin_data)
        features['volume_surge'] = self._detect_volume_surge(coin_data)
        
        # Market structure analysis
        features['whale_concentration_risk'] = self._estimate_whale_risk(coin_data)
        features['exchange_diversity_score'] = self._calculate_exchange_diversity(coin_data)
        features['liquidity_score'] = self._calculate_liquidity_score(coin_data)
        
        # Growth potential indicators
        features['price_discovery_phase'] = self._detect_price_discovery(coin_data)
        features['accumulation_pattern'] = self._detect_accumulation(coin_data)
        features['breakout_potential'] = self._calculate_breakout_potential(coin_data)
        
        # Risk assessment
        features['volatility_score'] = self._calculate_volatility_score(coin_data)
        features['stability_score'] = self._calculate_stability_score(coin_data)
        features['momentum_score'] = self._calculate_momentum_score(coin_data)
        
        # Innovation and utility indicators
        features['technology_score'] = self._assess_technology_innovation(coin_data)
        features['utility_score'] = self._assess_token_utility(coin_data)
        features['narrative_strength'] = self._assess_market_narrative(coin_data)
        
        # Social and community indicators
        features['community_growth'] = self._estimate_community_growth(coin_data)
        features['developer_activity'] = self._estimate_dev_activity(coin_data)
        features['social_momentum'] = self._calculate_social_momentum(coin_data)
        
        # Market timing indicators
        features['market_cycle_position'] = self._assess_market_cycle_position(coin_data, market_context)
        features['sector_momentum'] = self._assess_sector_momentum(coin_data)
        features['correlation_score'] = self._calculate_market_correlation(coin_data)
        
        # Risk-reward profile
        features['risk_reward_ratio'] = self._calculate_risk_reward_ratio(coin_data)
        features['downside_protection'] = self._assess_downside_protection(coin_data)
        features['upside_potential'] = self._assess_upside_potential(coin_data)
        
        # ===== ADVANCED ALPHA FEATURES - WHAT OTHERS MISS =====
        # These are the secret sauce that gives us edge over other analyzers
        
        # 1. Behavioral Psychology Signals (Fear/Greed Contrarian Opportunities)
        psychology_features = self.alpha_features.extract_contrarian_psychology_features(coin_data)
        features.update(psychology_features)
        
        # 2. Timing Anomaly Detection (Market Rhythm Breaks)
        timing_features = self.alpha_features.extract_timing_anomaly_features(coin_data)
        features.update(timing_features)
        
        # 3. Network Effect Analysis (Cross-Asset Relationships)
        network_features = self.alpha_features.extract_network_effect_features(coin_data)
        features.update(network_features)
        
        # 4. Smart Money Detection (Institutional vs Retail Patterns)
        smart_money_features = self.alpha_features.extract_smart_money_signals(coin_data)
        features.update(smart_money_features)
        
        # 5. Asymmetric Opportunity Detection (High Upside, Limited Downside)
        asymmetric_features = self.alpha_features.extract_asymmetric_opportunity_features(coin_data)
        features.update(asymmetric_features)
        
        return features
    
    def _calculate_volume_price_ratio(self, coin_data: Dict) -> float:
        """High volume relative to market cap indicates activity"""
        try:
            volume_str = coin_data.get('total_volume', '0')
            market_cap_str = coin_data.get('market_cap', '0')
            
            # Clean and convert volume
            if isinstance(volume_str, str):
                volume = float(volume_str.replace('$', '').replace(',', '').replace('N/A', '0'))
            else:
                volume = float(volume_str or 0)
            
            # Clean and convert market cap
            if isinstance(market_cap_str, str):
                market_cap = float(market_cap_str.replace('$', '').replace(',', '').replace('N/A', '1'))
            else:
                market_cap = float(market_cap_str or 1)
            
            if market_cap > 0:
                ratio = volume / market_cap
                # Normalize to 0-1 range, with 0.1+ being high activity
                return min(ratio * 10, 1.0)
            return 0
        except:
            return 0
    
    def _detect_volume_surge(self, coin_data: Dict) -> float:
        """Detect unusual volume spikes that might indicate hidden gem activity"""
        try:
            volume_str = coin_data.get('total_volume', '0')
            if isinstance(volume_str, str):
                volume = float(volume_str.replace('$', '').replace(',', '').replace('N/A', '0'))
            else:
                volume = float(volume_str or 0)
            
            # Simple heuristic: higher volume relative to market cap rank suggests interest
            rank = coin_data.get('market_cap_rank', 999)
            if rank > 100 and volume > 1000000:  # Low cap with decent volume
                return min((volume / 1000000) / 10, 1.0)
            return 0
        except:
            return 0
    
    def _estimate_whale_risk(self, coin_data: Dict) -> float:
        """Estimate whale concentration risk (lower is better for hidden gems)"""
        try:
            rank = coin_data.get('market_cap_rank', 999)
            # Lower ranked coins typically have higher whale concentration
            if rank > 500:
                return 0.8  # High whale risk
            elif rank > 300:
                return 0.6  # Medium whale risk
            elif rank > 100:
                return 0.4  # Lower whale risk
            else:
                return 0.2  # Established coins have lower whale risk
        except:
            return 0.5
    
    def _calculate_exchange_diversity(self, coin_data: Dict) -> float:
        """Estimate exchange listing diversity (more exchanges = lower risk)"""
        try:
            rank = coin_data.get('market_cap_rank', 999)
            # Heuristic based on market cap rank
            if rank < 50:
                return 0.9  # Major exchanges
            elif rank < 200:
                return 0.6  # Several exchanges
            elif rank < 500:
                return 0.4  # Few exchanges
            else:
                return 0.2  # Limited exchanges
        except:
            return 0.3
    
    def _calculate_liquidity_score(self, coin_data: Dict) -> float:
        """Assess overall liquidity quality"""
        try:
            volume_str = coin_data.get('total_volume', '0')
            if isinstance(volume_str, str):
                volume = float(volume_str.replace('$', '').replace(',', '').replace('N/A', '0'))
            else:
                volume = float(volume_str or 0)
            
            # Logarithmic scale for volume
            if volume > 0:
                return min(np.log10(volume + 1) / 8, 1.0)  # Normalize to 0-1
            return 0
        except:
            return 0
    
    def _detect_price_discovery(self, coin_data: Dict) -> float:
        """Detect if coin is in price discovery phase"""
        try:
            price_change = coin_data.get('price_change_24h', 0)
            rank = coin_data.get('market_cap_rank', 999)
            
            # Coins with moderate positive movement and low rank might be in discovery
            if rank > 200 and 2 < price_change < 15:
                return 0.7
            elif rank > 100 and 5 < price_change < 25:
                return 0.8
            return 0.3
        except:
            return 0.3
    
    def _detect_accumulation(self, coin_data: Dict) -> float:
        """Detect accumulation patterns"""
        try:
            price_change = coin_data.get('price_change_24h', 0)
            volume_ratio = self._calculate_volume_price_ratio(coin_data)
            
            # High volume with low price movement suggests accumulation
            if volume_ratio > 0.1 and abs(price_change) < 5:
                return 0.8
            elif volume_ratio > 0.05 and abs(price_change) < 3:
                return 0.6
            return 0.2
        except:
            return 0.2
    
    def _calculate_breakout_potential(self, coin_data: Dict) -> float:
        """Assess potential for price breakout"""
        try:
            rank = coin_data.get('market_cap_rank', 999)
            volume_ratio = self._calculate_volume_price_ratio(coin_data)
            
            # Lower rank coins with high volume have breakout potential
            if rank > 300 and volume_ratio > 0.1:
                return 0.8
            elif rank > 100 and volume_ratio > 0.05:
                return 0.6
            return 0.3
        except:
            return 0.3
    
    def _calculate_volatility_score(self, coin_data: Dict) -> float:
        """Calculate volatility score (moderate volatility is good for gems)"""
        try:
            price_change = abs(coin_data.get('price_change_24h', 0))
            
            # Sweet spot for hidden gems: 3-20% daily volatility
            if 3 <= price_change <= 20:
                return 0.8
            elif price_change < 3:
                return 0.4  # Too stable
            else:
                return 0.3  # Too volatile
        except:
            return 0.5
    
    def _calculate_stability_score(self, coin_data: Dict) -> float:
        """Calculate price stability score"""
        try:
            price_change = abs(coin_data.get('price_change_24h', 0))
            return max(0, 1 - (price_change / 100))  # Lower volatility = higher stability
        except:
            return 0.5
    
    def _calculate_momentum_score(self, coin_data: Dict) -> float:
        """Calculate positive momentum score"""
        try:
            price_change = coin_data.get('price_change_24h', 0)
            if price_change > 0:
                return min(price_change / 50, 1.0)  # Normalize positive changes
            return 0
        except:
            return 0
    
    def _assess_technology_innovation(self, coin_data: Dict) -> float:
        """Assess technology innovation level"""
        # Simplified heuristic based on naming patterns and market presence
        try:
            name = coin_data.get('name', '').lower()
            symbol = coin_data.get('symbol', '').lower()
            
            # Look for innovation keywords
            innovation_keywords = ['ai', 'defi', 'nft', 'layer', 'bridge', 'cross', 'chain', 
                                 'oracle', 'dao', 'dex', 'yield', 'stake', 'liquid']
            
            score = 0.3  # Base score
            for keyword in innovation_keywords:
                if keyword in name or keyword in symbol:
                    score += 0.1
            
            return min(score, 1.0)
        except:
            return 0.5
    
    def _assess_token_utility(self, coin_data: Dict) -> float:
        """Assess token utility based on available information"""
        try:
            # Heuristic based on market cap rank and activity
            rank = coin_data.get('market_cap_rank', 999)
            volume_ratio = self._calculate_volume_price_ratio(coin_data)
            
            if rank < 100:
                return 0.8  # Established utility
            elif rank < 300 and volume_ratio > 0.05:
                return 0.6  # Emerging utility
            elif volume_ratio > 0.1:
                return 0.7  # High activity suggests utility
            else:
                return 0.4  # Speculative
        except:
            return 0.5
    
    def _assess_market_narrative(self, coin_data: Dict) -> float:
        """Assess strength of market narrative"""
        try:
            # Based on sector trends and timing
            rank = coin_data.get('market_cap_rank', 999)
            price_change = coin_data.get('price_change_24h', 0)
            
            # Strong narrative coins often have sustained interest
            if rank < 200 and price_change > 0:
                return 0.7
            elif rank > 200 and price_change > 5:
                return 0.8  # Emerging narrative
            else:
                return 0.4
        except:
            return 0.5
    
    def _estimate_community_growth(self, coin_data: Dict) -> float:
        """Estimate community growth potential"""
        # Heuristic based on market activity
        try:
            volume_ratio = self._calculate_volume_price_ratio(coin_data)
            rank = coin_data.get('market_cap_rank', 999)
            
            if volume_ratio > 0.1 and rank > 100:
                return 0.8  # High activity in lower cap suggests growing community
            elif volume_ratio > 0.05:
                return 0.6
            else:
                return 0.4
        except:
            return 0.5
    
    def _estimate_dev_activity(self, coin_data: Dict) -> float:
        """Estimate development activity"""
        # Simplified heuristic
        try:
            rank = coin_data.get('market_cap_rank', 999)
            # Assume projects that maintain ranking have some development
            if rank < 100:
                return 0.8
            elif rank < 300:
                return 0.6
            else:
                return 0.4
        except:
            return 0.5
    
    def _calculate_social_momentum(self, coin_data: Dict) -> float:
        """Calculate social momentum indicators"""
        # Heuristic based on market activity
        try:
            volume_ratio = self._calculate_volume_price_ratio(coin_data)
            price_change = coin_data.get('price_change_24h', 0)
            
            # High volume + positive price = social momentum
            if volume_ratio > 0.1 and price_change > 5:
                return 0.9
            elif volume_ratio > 0.05 and price_change > 0:
                return 0.7
            else:
                return 0.4
        except:
            return 0.5
    
    def _assess_market_cycle_position(self, coin_data: Dict, market_context: Optional[Dict]) -> float:
        """Assess position in market cycle"""
        try:
            # Without market context, use basic heuristics
            rank = coin_data.get('market_cap_rank', 999)
            price_change = coin_data.get('price_change_24h', 0)
            
            # Lower cap coins with moderate gains might be in good cycle position
            if rank > 300 and 0 < price_change < 15:
                return 0.7
            elif rank > 100 and price_change > 0:
                return 0.6
            else:
                return 0.4
        except:
            return 0.5
    
    def _assess_sector_momentum(self, coin_data: Dict) -> float:
        """Assess sector momentum"""
        # Simplified based on general market activity
        try:
            volume_ratio = self._calculate_volume_price_ratio(coin_data)
            return min(volume_ratio * 2, 1.0)
        except:
            return 0.5
    
    def _calculate_market_correlation(self, coin_data: Dict) -> float:
        """Calculate correlation with major market movements"""
        # Heuristic: lower correlation might indicate independent potential
        try:
            rank = coin_data.get('market_cap_rank', 999)
            # Lower ranked coins often have lower correlation
            return max(0, 1 - (rank / 1000))
        except:
            return 0.5
    
    def _calculate_risk_reward_ratio(self, coin_data: Dict) -> float:
        """Calculate risk-reward profile"""
        try:
            rank = coin_data.get('market_cap_rank', 999)
            volume_ratio = self._calculate_volume_price_ratio(coin_data)
            
            # Lower rank + high activity = good risk-reward for gems
            if rank > 300 and volume_ratio > 0.1:
                return 0.8
            elif rank > 100 and volume_ratio > 0.05:
                return 0.6
            else:
                return 0.4
        except:
            return 0.5
    
    def _assess_downside_protection(self, coin_data: Dict) -> float:
        """Assess downside protection level"""
        try:
            rank = coin_data.get('market_cap_rank', 999)
            # More established coins have some downside protection
            if rank < 50:
                return 0.8
            elif rank < 200:
                return 0.6
            else:
                return 0.3  # Limited downside protection for micro caps
        except:
            return 0.4
    
    def _assess_upside_potential(self, coin_data: Dict) -> float:
        """Assess upside potential"""
        try:
            rank = coin_data.get('market_cap_rank', 999)
            volume_ratio = self._calculate_volume_price_ratio(coin_data)
            
            # Higher upside potential for lower caps with activity
            if rank > 500:
                return 0.9  # Extreme upside potential
            elif rank > 300:
                return 0.8  # High upside potential
            elif rank > 100 and volume_ratio > 0.05:
                return 0.7  # Good upside potential
            else:
                return 0.5  # Moderate upside potential
        except:
            return 0.6
    
    def create_training_dataset(self, coins_data: List[Dict]) -> Tuple[pd.DataFrame, List[int]]:
        """Create training dataset with enhanced features"""
        features_list = []
        
        print(f"🔄 Processing {len(coins_data)} coins for training...")
        
        for i, coin_data in enumerate(coins_data):
            try:
                features = self.extract_advanced_features(coin_data)
                features_list.append(features)
                
                if (i + 1) % 20 == 0:
                    print(f"   Processed {i + 1}/{len(coins_data)} coins...")
            except Exception as e:
                print(f"   Error processing coin {i}: {e}")
                continue
        
        df = pd.DataFrame(features_list)
        self.feature_names = list(df.columns)
        
        # Create sophisticated labels based on hidden gem criteria
        labels = self._create_hidden_gem_labels(df)
        
        print(f"SUCCESS: Created dataset with {len(df)} samples and {len(df.columns)} features")
        print(f"   Hidden gems identified: {sum(labels)} ({sum(labels)/len(labels)*100:.1f}%)")
        
        return df, labels
    
    def _create_hidden_gem_labels(self, df: pd.DataFrame) -> List[int]:
        """Create sophisticated labels for hidden gems based on multiple criteria"""
        labels = []
        
        for _, row in df.iterrows():
            score = 0
            
            # Core hidden gem criteria (weighted scoring)
            
            # 1. Market cap positioning (30% weight) - FAVOR LOW CAPS MORE
            if row['is_nano_cap']:
                score += 0.25  # Highest potential - extreme moonshot (boosted for better scores)
            elif row['is_micro_cap']:
                score += 0.20  # High potential (boosted)
            elif row['is_low_cap']:
                score += 0.15  # Good potential (boosted)
            
            # 2. Volume and activity signals (25% weight)
            if row['volume_surge'] > 0.6 and row['volume_price_ratio'] > 0.08:
                score += 0.15  # Strong activity surge
            elif row['volume_price_ratio'] > 0.05:
                score += 0.10  # Good activity
            
            # 3. Technical setup (20% weight)
            if row['breakout_potential'] > 0.7 and row['accumulation_pattern'] > 0.6:
                score += 0.12  # Strong technical setup
            elif row['price_discovery_phase'] > 0.6:
                score += 0.08  # In discovery phase
            
            # 4. Innovation and utility (15% weight)
            if row['technology_score'] > 0.7 and row['utility_score'] > 0.6:
                score += 0.10  # Strong fundamentals
            elif row['narrative_strength'] > 0.7:
                score += 0.06  # Strong narrative
            
            # 5. Early signals and smart money (10% weight) - FOCUS ON EARLY DETECTION
            # De-emphasize social momentum (retail indicator), emphasize smart money
            if row['whale_accumulation_score'] > 0.6 and row['quiet_accumulation_signal'] > 0.6:
                score += 0.10  # Smart money accumulating (EARLY SIGNAL)
            elif row['developer_activity'] > 0.7:
                score += 0.05  # Active development (EARLY SIGNAL)
            elif row['social_momentum'] > 0.8:  # Only use if extremely high
                score += 0.02  # Reduced weight - can be retail hype
            
            # 6. Risk-reward profile (5% weight)
            if row['upside_potential'] > 0.8 and row['risk_reward_ratio'] > 0.6:
                score += 0.05  # Excellent risk-reward
            
            # Bonus criteria
            # Perfect storm: low cap + high activity + technical setup + innovation
            if (row['is_micro_cap'] and row['volume_price_ratio'] > 0.1 and 
                row['breakout_potential'] > 0.6 and row['technology_score'] > 0.6):
                score += 0.1  # Bonus for perfect setup
            
            # Early detection bonus: whale activity + quiet accumulation + off-peak signals
            if (row['whale_accumulation_score'] > 0.6 and 
                row['quiet_accumulation_signal'] > 0.6 and 
                row['off_peak_anomaly'] > 0.5):
                score += 0.15  # EARLY SIGNAL BONUS - smart money moving before retail (boosted)
            
            # Innovation play: high tech score + utility + narrative
            if (row['technology_score'] > 0.8 and row['utility_score'] > 0.7 and 
                row['narrative_strength'] > 0.7):
                score += 0.08  # Innovation bonus
            
            # Aggressive threshold for hidden gem classification - favor high-risk plays
            # Lower threshold to catch more speculative opportunities
            labels.append(1 if score > 0.40 else 0)  # Lowered to 0.40 for more moonshot picks
        
        return labels
    
    def train_model(self, training_data: pd.DataFrame, labels: List[int]) -> Optional[Dict]:
        """Train the enhanced hidden gem detection model"""
        try:
            print("Training Hidden Gem Detection Model...")
            
            # Handle any missing values
            training_data = training_data.fillna(0)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                training_data, labels, test_size=0.2, random_state=42, stratify=labels
            )
            
            print(f"   Training set: {len(X_train)} samples")
            print(f"   Test set: {len(X_test)} samples")
            print(f"   Positive samples: {sum(y_train)}/{len(y_train)} ({sum(y_train)/len(y_train)*100:.1f}%)")
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Use Gradient Boosting for better performance on complex patterns
            self.model = GradientBoostingClassifier(
                n_estimators=300,
                learning_rate=0.1,
                max_depth=8,
                min_samples_split=20,
                min_samples_leaf=10,
                subsample=0.8,
                random_state=42,
                validation_fraction=0.1,
                n_iter_no_change=10
            )
            
            # Train model
            print("   Training in progress...")
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.model.predict(X_test_scaled)
            y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
            
            accuracy = np.mean(y_pred == y_test)
            auc_score = roc_auc_score(y_test, y_pred_proba)
            
            # Cross-validation for more robust evaluation
            cv_scores = cross_val_score(self.model, X_train_scaled, y_train, cv=5)
            
            # Store feature importance
            self.feature_importance = dict(zip(
                training_data.columns,
                self.model.feature_importances_
            ))
            
            self.model_loaded = True
            
            result = {
                'accuracy': accuracy,
                'auc_score': auc_score,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'classification_report': classification_report(y_test, y_pred),
                'feature_importance': self.feature_importance,
                'total_samples': len(training_data),
                'hidden_gems_found': sum(labels),
                'model_type': 'GradientBoostingClassifier'
            }
            
            print(f"SUCCESS: Model trained successfully!")
            print(f"   Accuracy: {accuracy:.3f}")
            print(f"   AUC Score: {auc_score:.3f}")
            print(f"   CV Score: {cv_scores.mean():.3f} (±{cv_scores.std():.3f})")
            
            return result
            
        except Exception as e:
            print(f"ERROR: Error training model: {e}")
            return None
    
    def predict_hidden_gem(self, coin_data: Dict, market_context: Optional[Dict] = None) -> Optional[Dict]:
        """Predict if a coin is a hidden gem with detailed analysis"""
        if not self.model_loaded or self.model is None:
            # FALLBACK: Use heuristic-based scoring when model not trained
            return self._heuristic_gem_score(coin_data, market_context)
        
        try:
            # Extract features
            features = self.extract_advanced_features(coin_data, market_context)
            features_df = pd.DataFrame([features])
            
            # Handle missing columns (in case model was trained with different features)
            if self.feature_names:
                for col in self.feature_names:
                    if col not in features_df.columns:
                        features_df[col] = 0
                
                # Reorder columns to match training data
                features_df = features_df[self.feature_names]
            features_df = features_df.fillna(0)
            
            # Scale features
            features_scaled = self.scaler.transform(features_df)
            
            # Get prediction and probability
            prediction = self.model.predict(features_scaled)[0]
            probability = self.model.predict_proba(features_scaled)[0]
            
            # BOOST probability for low-cap coins (favor speculation)
            raw_probability = float(probability[1])
            
            # Apply AGGRESSIVE boost for low caps (user prefers high risk/reward)
            if features.get('is_nano_cap', 0):
                boosted_probability = min(raw_probability + 0.35, 0.98)  # +35% boost for nano-caps (rank >500)
            elif features.get('is_micro_cap', 0):
                boosted_probability = min(raw_probability + 0.30, 0.95)  # +30% boost for micro-caps (rank >300)
            elif features.get('is_low_cap', 0):
                boosted_probability = min(raw_probability + 0.25, 0.90)  # +25% boost for small-caps (rank >100)
            else:
                boosted_probability = raw_probability
            
            # Get detailed feature analysis
            feature_analysis = self._analyze_features(features)
            top_features = self._get_top_contributing_features(features)
            risk_assessment = self._assess_investment_risk(features)
            
            # Base gem score from BOOSTED probability
            base_gem_score = float(boosted_probability * 100)
            
            # Build enhanced data structure
            enhanced_data = {
                'enhanced_score': base_gem_score,
                'sentiment_boost': 0
            }
            
            # Apply RL boost if enabled
            rl_data = {}
            if self.rl_enabled:
                rl_recommendation = simple_rl_learner.get_recommendation(
                    enhanced_data['enhanced_score'], 
                    features
                )
                rl_data = rl_recommendation
                # Apply RL boost to final score
                enhanced_data['enhanced_score'] += rl_recommendation['rl_boost']
                # Clamp to 0-100
                enhanced_data['enhanced_score'] = max(0, min(100, enhanced_data['enhanced_score']))
            
            # Build result with both ML and AI insights
            result = {
                'is_hidden_gem': bool(prediction) or boosted_probability > 0.5,  # More lenient
                'gem_probability': float(boosted_probability),  # Use boosted probability
                'confidence': float(max(boosted_probability, 1 - boosted_probability)),  # Confidence based on boost
                'gem_score': enhanced_data['enhanced_score'],  # AI-enhanced score
                'base_gem_score': base_gem_score,  # Original ML score
                'sentiment_boost': enhanced_data.get('sentiment_boost', 0),  # AI contribution
                'risk_level': risk_assessment['level'],
                'risk_score': risk_assessment['score'],
                'key_strengths': feature_analysis['strengths'],
                'key_weaknesses': feature_analysis['weaknesses'],
                'top_features': top_features,
                'recommendation': self._generate_recommendation(features, boosted_probability),
                'feature_breakdown': {
                    'market_position': features['market_cap_rank'],
                    'volume_activity': features['volume_price_ratio'],
                    'technical_setup': features['breakout_potential'],
                    'innovation_score': features['technology_score'],
                    'community_strength': features['community_growth']
                },
                'ai_sentiment': enhanced_data.get('sentiment'),  # AI insights from agents
                'ai_enabled': enhanced_data.get('ai_enabled', False),
                'rl_recommendation': rl_data.get('action') if self.rl_enabled else None,
                'rl_confidence': rl_data.get('confidence') if self.rl_enabled else None,
                'rl_boost': rl_data.get('rl_boost', 0) if self.rl_enabled else 0,
                'rl_enabled': self.rl_enabled,
                'summary': None  # Personalized summary comes from agent analysis
            }
            
            return result
            
        except Exception as e:
            print(f"ERROR: Error making prediction: {e}")
            return None
    
    def _analyze_features(self, features: Dict) -> Dict:
        """Analyze features to identify key strengths and weaknesses"""
        strengths = []
        weaknesses = []
        
        # Market positioning - emphasize moonshot potential
        if features['is_nano_cap']:
            strengths.append(" Nano-cap moonshot - 100x+ potential if project executes")
        elif features['is_micro_cap']:
            strengths.append("GEM: Micro-cap gem - 50x+ potential with strong execution")
        elif features['is_low_cap']:
            strengths.append("⭐ Small-cap opportunity - 10x+ potential")
        else:
            weaknesses.append("Larger market cap - limited to 2-5x upside")
        
        # Volume and activity
        if features['volume_price_ratio'] > 0.1:
            strengths.append("Exceptional trading volume relative to market cap")
        elif features['volume_price_ratio'] > 0.05:
            strengths.append("Strong trading activity and interest")
        else:
            weaknesses.append("Limited trading volume and market interest")
        
        # Technical setup
        if features['breakout_potential'] > 0.7:
            strengths.append("Strong technical breakout potential")
        elif features['accumulation_pattern'] > 0.6:
            strengths.append("Healthy accumulation pattern detected")
        
        # Innovation and utility
        if features['technology_score'] > 0.7:
            strengths.append("Strong technology innovation profile")
        if features['utility_score'] > 0.6:
            strengths.append("Clear token utility and use case")
        elif features['technology_score'] < 0.4:
            weaknesses.append("Limited innovation or technological differentiation")
        
        # Considerations
        if features['whale_concentration_risk'] > 0.7:
            weaknesses.append("Whale-heavy distribution — watch for large moves")
        if features['exchange_diversity_score'] < 0.4:
            weaknesses.append("Few exchange listings — early stage, watch liquidity")
        
        return {
            'strengths': strengths[:5],  # Top 5 strengths
            'weaknesses': weaknesses[:3]  # Top 3 weaknesses
        }
    
    def _get_top_contributing_features(self, features: Dict) -> List[Dict]:
        """Get top contributing features for this prediction"""
        if not self.feature_importance:
            return []
        
        # Calculate weighted contribution for each feature
        contributions = []
        for feature_name, value in features.items():
            if feature_name in self.feature_importance:
                importance = self.feature_importance[feature_name]
                contribution = importance * value
                contributions.append({
                    'feature': feature_name.replace('_', ' ').title(),
                    'value': round(value, 3),
                    'importance': round(importance, 3),
                    'contribution': round(contribution, 3)
                })
        
        # Sort by contribution and return top 5
        contributions.sort(key=lambda x: x['contribution'], reverse=True)
        return contributions[:5]
    
    def _assess_investment_risk(self, features: Dict) -> Dict:
        """Assess opportunity level - higher score = more upside potential"""
        opportunity_score = 0
        
        # Market cap = upside potential (smaller = more room to grow)
        if features['is_nano_cap']:
            opportunity_score += 0.35
        elif features['is_micro_cap']:
            opportunity_score += 0.25
        elif features['is_low_cap']:
            opportunity_score += 0.15
        
        # Low liquidity = early entry opportunity
        if features['liquidity_score'] < 0.3:
            opportunity_score += 0.2
        elif features['exchange_diversity_score'] < 0.4:
            opportunity_score += 0.15
        
        # High volatility = swing opportunity
        if features['volatility_score'] > 0.8:
            opportunity_score += 0.1
        
        # Low whale concentration = healthier distribution
        opportunity_score += features['whale_concentration_risk'] * 0.2
        
        # Determine opportunity level
        if opportunity_score > 0.7:
            level = "Extreme Moonshot"
        elif opportunity_score > 0.5:
            level = "High Upside"
        elif opportunity_score > 0.3:
            level = "Growth Play"
        else:
            level = "Stable"
        
        return {
            'score': opportunity_score,
            'level': level
        }
    
    def _generate_recommendation(self, features: Dict, gem_probability: float) -> str:
        """Generate investment recommendation - aggressive bias for moonshots"""
        # Check if it's a low cap for bonus bullishness
        is_low_cap = features.get('is_micro_cap', 0) or features.get('is_nano_cap', 0)
        is_nano = features.get('is_nano_cap', 0)
        
        if gem_probability > 0.70:
            return "STRONG BUY - Moonshot potential detected, high conviction play"
        elif gem_probability > 0.55:
            return "BUY - Strong asymmetric upside, position for explosive gains"
        elif gem_probability > 0.40:
            if is_nano:
                return "STRONG BUY - Extreme moonshot, 100x potential if legit"
            elif is_low_cap:
                return "BUY - Speculative play with 10x+ potential, high risk/high reward"
            return "MODERATE BUY - Decent setup, monitor for entry signals"
        elif gem_probability > 0.25:
            if is_low_cap:
                return "BUY - High-risk moonshot opportunity, DCA recommended"
            return "WATCH - Some potential, needs better setup"
        else:
            if is_low_cap:
                return "WATCH - Speculative opportunity, wait for signals"
            return "PASS - Better opportunities available"
    
    def save_model(self, filepath: Optional[str] = None) -> bool:
        """Save the trained model"""
        try:
            if filepath is None:
                filepath = self.model_path
                
            if self.model_loaded and self.model is not None:
                model_data = {
                    'model': self.model,
                    'scaler': self.scaler,
                    'feature_importance': self.feature_importance,
                    'feature_names': self.feature_names,
                    'model_version': '2.0',
                    'trained_date': datetime.now().isoformat()
                }
                
                joblib.dump(model_data, filepath)
                print(f"Model saved to {filepath}")
                return True
            else:
                print("No trained model to save")
                return False
        except Exception as e:
            print(f"Error saving model: {e}")
            return False
    
    def load_model(self, filepath: Optional[str] = None) -> bool:
        """Load a trained model"""
        try:
            if filepath is None:
                filepath = self.model_path
                
            if not os.path.exists(filepath):
                print(f"ERROR: Model file not found: {filepath}")
                return False
                
            model_data = joblib.load(filepath)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_importance = model_data['feature_importance']
            self.feature_names = model_data['feature_names']
            self.model_loaded = True
            
            trained_date = model_data.get('trained_date', 'Unknown')
            model_version = model_data.get('model_version', '1.0')
            
            print(f"Hidden Gem Detector model loaded successfully")
            print(f"   Version: {model_version}")
            print(f"   Trained: {trained_date}")
            print(f"   Features: {len(self.feature_names)}")
            
            return True
            
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    def _heuristic_gem_score(self, coin_data: Dict, market_context: Optional[Dict] = None) -> Dict:
        """
        Heuristic-based gem scoring (NO MODEL NEEDED - AGGRESSIVE MODE)
        Used when ML model isn't trained yet - favors moonshot opportunities
        """
        # Extract features for analysis
        features = self.extract_advanced_features(coin_data, market_context)
        
        # Start with aggressive base score for low-caps
        if features.get('is_nano_cap', 0):
            base_score = 65.0  # Start HIGH for nano-caps (100x potential)
        elif features.get('is_micro_cap', 0):
            base_score = 55.0  # Start HIGH for micro-caps (50x potential)
        elif features.get('is_low_cap', 0):
            base_score = 45.0  # Start GOOD for small-caps (10x potential)
        else:
            base_score = 30.0  # Established coins - limited upside
        
        # Boost for positive price action
        price_change = features.get('price_change_24h', 0)
        if price_change > 10:
            base_score += 15
        elif price_change > 5:
            base_score += 10
        elif price_change > 0:
            base_score += 5
        
        # Boost for volume activity
        volume_ratio = features.get('volume_price_ratio', 0)
        if volume_ratio > 0.1:
            base_score += 15
        elif volume_ratio > 0.05:
            base_score += 10
        
        # Boost for technical setup
        breakout = features.get('breakout_potential', 0)
        if breakout > 0.7:
            base_score += 10
        elif breakout > 0.5:
            base_score += 5
        
        # Cap at 95
        base_score = min(base_score, 95.0)
        gem_probability = base_score / 100.0
        
        # Build aggressive result (using Gemini agents)
        cap_label = ('Nano' if features.get('is_nano_cap') else 
                     'Micro' if features.get('is_micro_cap') else 
                     'Small' if features.get('is_low_cap') else None)
        
        if cap_label:
            cap_strength = f"{cap_label}-cap moonshot opportunity"
            risk_label = "Extreme Moonshot" if features.get('is_nano_cap') else "High Volatility"
        else:
            cap_strength = "Established market position"
            risk_label = "Moderate Risk"
        
        return {
            'is_hidden_gem': gem_probability > 0.40,  # Low threshold
            'gem_probability': gem_probability,
            'confidence': max(0.6, gem_probability),  # Always show decent confidence
            'gem_score': base_score,
            'base_gem_score': base_score,
            'sentiment_boost': 0,
            'risk_level': risk_label,
            'risk_score': 0.7 if cap_label else 0.3,
            'key_strengths': [
                cap_strength,
                f"{abs(price_change):.1f}% 24h price action",
                "Early positioning opportunity - get in before the crowd" if cap_label else "Proven track record and liquidity"
            ],
            'key_weaknesses': ["High volatility", "Speculative play"] if cap_label else ["Limited upside vs small-caps"],
            'top_features': [],
            'recommendation': self._generate_recommendation(features, gem_probability),
            'feature_breakdown': {
                'market_position': features['market_cap_rank'],
                'volume_activity': volume_ratio,
                'technical_setup': breakout,
                'innovation_score': features.get('technology_score', 0.5),
                'community_strength': features.get('community_growth', 0.5)
            },
            'ai_sentiment': None,
            'ai_enabled': False,
            'rl_enabled': False,
            'heuristic_mode': True,  # Flag to indicate heuristic scoring
            'summary': None  # No personalized summary in heuristic mode
        }
    
    async def analyze_with_agents(self, coin_data: Dict) -> Dict:
        """
        PHASE 4: Analyze coin using multi-agent system
        
        This is the new comprehensive analysis method that replaces heuristic scoring
        with AI-powered multi-agent analysis.
        
        Only analyzes coins under £1 (to focus on low-cap opportunities).
        Exception: Favorites are always analyzed regardless of price.
        
        Args:
            coin_data: Coin market data
            
        Returns:
            Comprehensive analysis from all agents
        """
        if not self.multi_agent_enabled or not analyze_crypto:
            # Fallback to heuristic if multi-agent not available
            features = self.extract_advanced_features(coin_data)
            return self._heuristic_gem_score(coin_data)
        
        # Price filter: Only analyze coins under £1 (unless favorite)
        current_price = coin_data.get('price', 0) or coin_data.get('current_price', 0)
        is_favorite = coin_data.get('is_favorite', False) or coin_data.get('status') == 'favorite'
        
        if current_price > 1.0 and not is_favorite:
            logger.info(f"Skipping ADK analysis for {coin_data.get('symbol')} - price £{current_price:.2f} exceeds £1 limit (not a favorite)")
            # Return basic heuristic analysis instead
            return self._heuristic_gem_score(coin_data)
        
        try:
            # Run multi-agent analysis using Official Google ADK
            result = await analyze_crypto(
                symbol=coin_data.get('symbol', 'UNKNOWN'),
                coin_data=coin_data,
                session_id=f"gem_{coin_data.get('symbol', 'UNKNOWN')}",
                use_memory=True
            )
            
            if not result.get('success', False):
                logger.warning(f"Agent analysis returned error for {coin_data.get('symbol')}: {result.get('error')}")
                return self._heuristic_gem_score(coin_data)
            
            # Parse the analysis text — orchestrator returns CryptoAnalysisOutput JSON
            parsed = self._parse_agent_analysis(result, coin_data)
            return parsed
            
        except Exception as e:
            logger.warning(f"Multi-agent analysis failed for {coin_data.get('symbol')}: {e}")
            # Fallback to heuristic
            return self._heuristic_gem_score(coin_data)
    
    def _parse_agent_analysis(self, result: Dict, coin_data: Dict) -> Dict:
        """Parse the raw orchestrator response into structured gem detector format."""
        import json as _json
        import re
        
        analysis_text = result.get('analysis', '')
        confidence_raw = result.get('confidence', 50)
        symbol = coin_data.get('symbol', 'UNKNOWN')
        
        # Try to parse structured JSON from the analysis text
        parsed_json = None
        if analysis_text:
            # Try to extract JSON from the text (may be wrapped in markdown code blocks)
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', analysis_text, re.DOTALL)
            if json_match:
                try:
                    parsed_json = _json.loads(json_match.group(1))
                except _json.JSONDecodeError:
                    pass
            
            if not parsed_json:
                # Try parsing the whole text as JSON
                try:
                    parsed_json = _json.loads(analysis_text)
                except _json.JSONDecodeError:
                    pass
        
        if parsed_json:
            # Successfully parsed structured output from CryptoAnalysisOutput schema
            recommendation = parsed_json.get('overall_recommendation', 'HOLD')
            confidence = parsed_json.get('confidence', confidence_raw)
            gem_score = parsed_json.get('consensus_score', confidence)
            key_insights = parsed_json.get('key_insights', [])
            action_plan = parsed_json.get('action_plan', '')
            risk_summary = parsed_json.get('risk_summary', '')
            
            # Build strengths from insights and summaries
            strengths = []
            if parsed_json.get('research_summary'):
                strengths.append(parsed_json['research_summary'][:120])
            if parsed_json.get('technical_summary'):
                strengths.append(parsed_json['technical_summary'][:120])
            if parsed_json.get('sentiment_summary'):
                strengths.append(parsed_json['sentiment_summary'][:120])
            for insight in key_insights[:2]:
                if insight not in strengths:
                    strengths.append(insight[:120])
            
            # Weaknesses from risk
            weaknesses = []
            if risk_summary:
                weaknesses.append(risk_summary[:120])
            
            # Derive risk level from risk summary text
            risk_text = risk_summary.lower()
            if any(w in risk_text for w in ['very high', 'extreme', 'critical']):
                risk_level = 'Very High'
            elif any(w in risk_text for w in ['high', 'significant']):
                risk_level = 'High'
            elif any(w in risk_text for w in ['moderate', 'medium']):
                risk_level = 'Moderate'
            else:
                risk_level = 'Low'
            
            # Build summary from action plan or key insights
            # Clean any embedded JSON from summaries
            def _clean_agent_text(text):
                if not text or not isinstance(text, str):
                    return text or ''
                text = re.sub(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', text)
                text = re.sub(r'```(?:json)?\s*', '', text)
                return re.sub(r'\s{2,}', ' ', text).strip()
            
            summary = _clean_agent_text(action_plan) if action_plan else ' | '.join(key_insights[:2]) if key_insights else _clean_agent_text(analysis_text[:200])
            # Also clean strengths and weaknesses
            strengths = [_clean_agent_text(s) for s in strengths if _clean_agent_text(s)]
            weaknesses = [_clean_agent_text(w) for w in weaknesses if _clean_agent_text(w)]
            
        else:
            # Fallback: extract useful info from raw text
            recommendation = 'HOLD'
            if re.search(r'\b(STRONG\s+)?BUY\b', analysis_text, re.IGNORECASE):
                recommendation = 'BUY'
            elif re.search(r'\bSELL\b', analysis_text, re.IGNORECASE):
                recommendation = 'SELL'
            
            confidence = confidence_raw
            gem_score = confidence_raw
            
            # Strip embedded JSON from raw text before extracting sentences
            cleaned_text = re.sub(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', analysis_text)
            cleaned_text = re.sub(r'```(?:json)?\s*', '', cleaned_text)
            cleaned_text = re.sub(r'\s{2,}', ' ', cleaned_text).strip()
            
            # Extract sentences as insights (from cleaned text)
            sentences = [s.strip() for s in re.split(r'[.!]', cleaned_text) if len(s.strip()) > 20]
            # Filter out sentences that still look like JSON fragments
            sentences = [s for s in sentences if not s.strip().startswith('{') and '": ' not in s]
            strengths = sentences[:3] if sentences else [f"Agent analysis completed for {symbol}"]
            weaknesses = ["See full analysis for risk details"]
            risk_level = 'Moderate'
            summary = cleaned_text[:300] if cleaned_text else f"Multi-agent analysis for {symbol}"
        
        return {
            'is_hidden_gem': gem_score > 60,
            'gem_probability': gem_score / 100.0,
            'confidence': confidence,
            'gem_score': gem_score,
            'base_gem_score': gem_score,
            'sentiment_boost': 0,
            'risk_level': risk_level,
            'risk_score': {'Very High': 0.9, 'High': 0.7, 'Moderate': 0.5, 'Low': 0.3}.get(risk_level, 0.5),
            'key_strengths': [s for s in strengths if s][:5],
            'key_weaknesses': [w for w in weaknesses if w][:3],
            'top_features': [],
            'recommendation': recommendation,
            'summary': summary,
            'feature_breakdown': {},
            'multi_agent_analysis': result,
            'ai_enabled': True,
            'multi_agent_enabled': True,
            'heuristic_mode': False
        }
    
    def _extract_strengths_from_agents(self, agent_result: Dict) -> List[str]:
        """Extract key strengths from multi-agent analysis"""
        strengths = []
        
        # From sentiment
        if 'sentiment' in agent_result:
            sent = agent_result['sentiment']
            if sent.get('sentiment_score', 0) > 0.5:
                strengths.append(f"Positive sentiment: {sent.get('signal', 'Bullish')}")
        
        # From research
        if 'research' in agent_result:
            res = agent_result['research']
            if res.get('score', 0) > 0.7:
                strengths.append("Strong fundamentals")
        
        # From technical
        if 'technical' in agent_result:
            tech = agent_result['technical']
            if tech.get('score', 0) > 0.7:
                strengths.append("Bullish technical setup")
        
        return strengths if strengths else ["Comprehensive analysis available"]
    
    def _extract_weaknesses_from_agents(self, agent_result: Dict) -> List[str]:
        """Extract key weaknesses from multi-agent analysis"""
        weaknesses = []
        
        # From risk
        if 'risk' in agent_result:
            risk = agent_result['risk']
            risk_level = risk.get('risk_level', '')
            if 'HIGH' in risk_level or 'VERY_HIGH' in risk_level:
                weaknesses.append(f"High risk: {risk_level}")
        
        # From sentiment
        if 'sentiment' in agent_result:
            sent = agent_result['sentiment']
            if sent.get('sentiment_score', 0) < -0.2:
                weaknesses.append("Negative market sentiment")
        
        return weaknesses if weaknesses else ["Standard crypto volatility"]

    def learn_from_outcome(self, symbol: str, entry_price: float, 
                          current_price: float, days_held: int,
                          features: Dict[str, float], notes: str = None) -> Optional[Dict]:
        """
        Teach the RL system from actual trading outcome
        
        Args:
            symbol: Coin symbol (e.g., 'BTC')
            entry_price: Price when you bought
            current_price: Current/exit price
            days_held: Days held
            features: Features from original analysis
            notes: Optional notes about the trade
        
        Returns:
            Learning summary or None if RL disabled
        """
        if not self.rl_enabled:
            return None
        
        # Calculate profit
        profit_pct = ((current_price - entry_price) / entry_price) * 100
        
        # Let RL learn with full trade details
        result = simple_rl_learner.learn_from_outcome(
            features=features,
            action='buy',  # Assume buy if you're tracking outcome
            profit_pct=profit_pct,
            days_held=days_held,
            symbol=symbol,
            entry_price=entry_price,
            exit_price=current_price,
            notes=notes
        )
        
        print(f"RL: RL learned from {symbol}: {profit_pct:+.1f}% over {days_held} days")
        print(f"   New success rate: {result['new_success_rate']:.1%}")
        
        return result

    def get_model_info(self) -> Dict:
        """Get information about the current model"""
        if not self.model_loaded:
            return {'status': 'No model loaded'}
        
        return {
            'status': 'Model loaded',
            'model_type': type(self.model).__name__,
            'features_count': len(self.feature_names) if self.feature_names else 0,
            'feature_names': self.feature_names,
            'top_important_features': sorted(
                self.feature_importance.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10] if self.feature_importance else []
        }