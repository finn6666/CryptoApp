"""
Enhanced ML model specifically designed to identify cryptocurrency hidden gems
Focuses on patterns and signals that indicate undervalued opportunities with high potential
Now includes advanced alpha detection features that others typically miss
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
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Import our advanced alpha features
from .advanced_alpha_features import AdvancedAlphaFeatures

class HiddenGemDetector:
    """
    Enhanced ML model specifically designed to identify hidden gems
    
    Key Innovation: Uses advanced alpha features that detect opportunities
    others miss by analyzing:
    - Market psychology patterns (fear/greed contrarian signals)
    - Timing anomalies (market inefficiency windows)  
    - Cross-asset relationships (network effects)
    - Smart money vs crowd behavior patterns
    - Asymmetric risk-reward opportunities
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
        
        # Create models directory if it doesn't exist
        os.makedirs(model_dir, exist_ok=True)
        
    def extract_advanced_features(self, coin_data: Dict, market_context: Optional[Dict] = None) -> Dict:
        """Extract advanced features that indicate hidden gem potential"""
        features = {}
        
        # Basic price and market features
        features['current_price'] = float(coin_data.get('price', 0))
        features['price_change_24h'] = float(coin_data.get('price_change_24h', {}).get('usd', 0))
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
            price_change = coin_data.get('price_change_24h', {}).get('usd', 0)
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
            price_change = coin_data.get('price_change_24h', {}).get('usd', 0)
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
            price_change = abs(coin_data.get('price_change_24h', {}).get('usd', 0))
            
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
            price_change = abs(coin_data.get('price_change_24h', {}).get('usd', 0))
            return max(0, 1 - (price_change / 100))  # Lower volatility = higher stability
        except:
            return 0.5
    
    def _calculate_momentum_score(self, coin_data: Dict) -> float:
        """Calculate positive momentum score"""
        try:
            price_change = coin_data.get('price_change_24h', {}).get('usd', 0)
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
            price_change = coin_data.get('price_change_24h', {}).get('usd', 0)
            
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
            price_change = coin_data.get('price_change_24h', {}).get('usd', 0)
            
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
            price_change = coin_data.get('price_change_24h', {}).get('usd', 0)
            
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
        
        print(f"✅ Created dataset with {len(df)} samples and {len(df.columns)} features")
        print(f"   Hidden gems identified: {sum(labels)} ({sum(labels)/len(labels)*100:.1f}%)")
        
        return df, labels
    
    def _create_hidden_gem_labels(self, df: pd.DataFrame) -> List[int]:
        """Create sophisticated labels for hidden gems based on multiple criteria"""
        labels = []
        
        for _, row in df.iterrows():
            score = 0
            
            # Core hidden gem criteria (weighted scoring)
            
            # 1. Market cap positioning (25% weight)
            if row['is_nano_cap']:
                score += 0.15  # Highest potential
            elif row['is_micro_cap']:
                score += 0.12
            elif row['is_low_cap']:
                score += 0.08
            
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
            
            # 5. Social and community momentum (10% weight)
            if row['social_momentum'] > 0.7 and row['community_growth'] > 0.6:
                score += 0.08  # Growing community
            elif row['developer_activity'] > 0.7:
                score += 0.04  # Active development
            
            # 6. Risk-reward profile (5% weight)
            if row['upside_potential'] > 0.8 and row['risk_reward_ratio'] > 0.6:
                score += 0.05  # Excellent risk-reward
            
            # Bonus criteria
            # Perfect storm: low cap + high activity + technical setup + innovation
            if (row['is_micro_cap'] and row['volume_price_ratio'] > 0.1 and 
                row['breakout_potential'] > 0.6 and row['technology_score'] > 0.6):
                score += 0.1  # Bonus for perfect setup
            
            # Momentum play: strong social momentum + price discovery
            if row['social_momentum'] > 0.8 and row['price_discovery_phase'] > 0.7:
                score += 0.08  # Momentum bonus
            
            # Innovation play: high tech score + utility + narrative
            if (row['technology_score'] > 0.8 and row['utility_score'] > 0.7 and 
                row['narrative_strength'] > 0.7):
                score += 0.08  # Innovation bonus
            
            # Conservative threshold for hidden gem classification
            # Require score > 0.65 to be classified as hidden gem
            labels.append(1 if score > 0.65 else 0)
        
        return labels
    
    def train_model(self, training_data: pd.DataFrame, labels: List[int]) -> Optional[Dict]:
        """Train the enhanced hidden gem detection model"""
        try:
            print("🏋️ Training Hidden Gem Detection Model...")
            
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
            
            print(f"✅ Model trained successfully!")
            print(f"   Accuracy: {accuracy:.3f}")
            print(f"   AUC Score: {auc_score:.3f}")
            print(f"   CV Score: {cv_scores.mean():.3f} (±{cv_scores.std():.3f})")
            
            return result
            
        except Exception as e:
            print(f"❌ Error training model: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def predict_hidden_gem(self, coin_data: Dict, market_context: Optional[Dict] = None) -> Optional[Dict]:
        """Predict if a coin is a hidden gem with detailed analysis"""
        if not self.model_loaded or self.model is None:
            return None
        
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
            
            # Get detailed feature analysis
            feature_analysis = self._analyze_features(features)
            top_features = self._get_top_contributing_features(features)
            risk_assessment = self._assess_investment_risk(features)
            
            return {
                'is_hidden_gem': bool(prediction),
                'gem_probability': float(probability[1]),
                'confidence': float(max(probability)),
                'gem_score': float(probability[1] * 100),  # 0-100 score
                'risk_level': risk_assessment['level'],
                'risk_score': risk_assessment['score'],
                'key_strengths': feature_analysis['strengths'],
                'key_weaknesses': feature_analysis['weaknesses'],
                'top_features': top_features,
                'recommendation': self._generate_recommendation(features, probability[1]),
                'feature_breakdown': {
                    'market_position': features['market_cap_rank'],
                    'volume_activity': features['volume_price_ratio'],
                    'technical_setup': features['breakout_potential'],
                    'innovation_score': features['technology_score'],
                    'community_strength': features['community_growth']
                }
            }
            
        except Exception as e:
            print(f"❌ Error making prediction: {e}")
            return None
    
    def _analyze_features(self, features: Dict) -> Dict:
        """Analyze features to identify key strengths and weaknesses"""
        strengths = []
        weaknesses = []
        
        # Market positioning
        if features['is_nano_cap']:
            strengths.append("Ultra-low market cap with extreme upside potential")
        elif features['is_micro_cap']:
            strengths.append("Micro-cap positioning with high growth potential")
        elif features['is_low_cap']:
            strengths.append("Low market cap with good growth opportunity")
        else:
            weaknesses.append("Higher market cap limits explosive growth potential")
        
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
        
        # Risk factors
        if features['whale_concentration_risk'] > 0.7:
            weaknesses.append("High whale concentration increases volatility risk")
        if features['exchange_diversity_score'] < 0.4:
            weaknesses.append("Limited exchange listings reduce liquidity")
        
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
        """Assess investment risk level"""
        risk_score = 0
        
        # Market cap risk (higher for lower caps)
        if features['is_nano_cap']:
            risk_score += 0.4
        elif features['is_micro_cap']:
            risk_score += 0.3
        elif features['is_low_cap']:
            risk_score += 0.2
        
        # Liquidity risk
        if features['liquidity_score'] < 0.3:
            risk_score += 0.2
        elif features['exchange_diversity_score'] < 0.4:
            risk_score += 0.15
        
        # Volatility risk
        if features['volatility_score'] > 0.8:
            risk_score += 0.1
        
        # Whale concentration risk
        risk_score += features['whale_concentration_risk'] * 0.2
        
        # Determine risk level
        if risk_score > 0.7:
            level = "Very High"
        elif risk_score > 0.5:
            level = "High"
        elif risk_score > 0.3:
            level = "Medium"
        else:
            level = "Low"
        
        return {
            'score': risk_score,
            'level': level
        }
    
    def _generate_recommendation(self, features: Dict, gem_probability: float) -> str:
        """Generate investment recommendation"""
        if gem_probability > 0.8:
            return "STRONG BUY - Exceptional hidden gem potential with multiple positive indicators"
        elif gem_probability > 0.7:
            return "BUY - Strong hidden gem characteristics, consider position sizing"
        elif gem_probability > 0.6:
            return "MODERATE BUY - Good potential but monitor key metrics closely"
        elif gem_probability > 0.4:
            return "WATCH - Some positive signals but needs further analysis"
        else:
            return "PASS - Limited hidden gem characteristics detected"
    
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
                print(f"✅ Model saved to {filepath}")
                return True
            else:
                print("❌ No trained model to save")
                return False
        except Exception as e:
            print(f"❌ Error saving model: {e}")
            return False
    
    def load_model(self, filepath: Optional[str] = None) -> bool:
        """Load a trained model"""
        try:
            if filepath is None:
                filepath = self.model_path
                
            if not os.path.exists(filepath):
                print(f"❌ Model file not found: {filepath}")
                return False
                
            model_data = joblib.load(filepath)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_importance = model_data['feature_importance']
            self.feature_names = model_data['feature_names']
            self.model_loaded = True
            
            trained_date = model_data.get('trained_date', 'Unknown')
            model_version = model_data.get('model_version', '1.0')
            
            print(f"✅ Hidden Gem Detector model loaded successfully")
            print(f"   Version: {model_version}")
            print(f"   Trained: {trained_date}")
            print(f"   Features: {len(self.feature_names)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            return False

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