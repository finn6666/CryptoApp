"""
Advanced Hidden Alpha ML Features for CryptoApp
Extends the existing enhanced_gem_detector with unconventional signals that others overlook

Key Innovation Areas:
1. Market Psychology Patterns - Fear/Greed contrarian signals
2. Timing Anomalies - Market inefficiency windows  
3. Cross-Asset Relationships - Network effects
4. Behavioral Pattern Detection - Smart money vs crowd
5. Asymmetric Risk-Reward Identification
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import math

class AdvancedAlphaFeatures:
    """
    Additional feature extraction methods for detecting hidden alpha opportunities
    Designed to integrate with existing HiddenGemDetector
    """
    
    def __init__(self):
        # Store historical patterns for comparison
        self.volume_history = {}
        self.price_history = {}
        self.sentiment_baselines = {}
        
    def extract_contrarian_psychology_features(self, coin_data: Dict) -> Dict[str, float]:
        """
        BEHAVIORAL PSYCHOLOGY SIGNALS - Look for crowd psychology errors
        
        The Theory: Markets are driven by human psychology. When fear/greed creates
        irrational pricing, opportunities emerge for contrarian investors.
        """
        features = {}
        
        try:
            symbol = coin_data.get('symbol', 'UNKNOWN')
            price_change_24h = coin_data.get('price_change_24h', 0)
            rank = coin_data.get('market_cap_rank', 999)
            
            # 1. FEAR OPPORTUNITY SCORE
            # When quality assets are oversold due to panic
            if rank < 500 and price_change_24h < -15:
                # The better the fundamentals + worse the sentiment = bigger opportunity
                quality_score = max(0, (500 - rank) / 500)  # Higher for better ranks
                fear_intensity = min(abs(price_change_24h) / 30, 1.0)  # Cap at 30% drop
                features['fear_opportunity_score'] = quality_score * fear_intensity
            else:
                features['fear_opportunity_score'] = 0.0
            
            # 2. NEGLECT OPPORTUNITY SCORE  
            # Good projects that the market has forgotten about
            volume_str = str(coin_data.get('total_volume', '0'))
            volume = self._extract_numeric_value(volume_str)
            
            # Low volume despite decent rank = potential neglect
            if 100 < rank < 800 and volume > 0:
                expected_volume = self._estimate_expected_volume(rank)
                if volume < expected_volume * 0.3:  # Much lower volume than expected
                    neglect_score = min((expected_volume / volume) / 10, 0.8)
                    features['neglect_opportunity_score'] = neglect_score
                else:
                    features['neglect_opportunity_score'] = 0.0
            else:
                features['neglect_opportunity_score'] = 0.0
            
            # 3. ANTI-HERD MOMENTUM
            # Coins moving opposite to what you'd expect
            if price_change_24h > 5 and rank > 300:
                # Small cap going up when others going down = potential alpha
                features['anti_herd_momentum'] = min(price_change_24h / 20, 0.8)
            elif price_change_24h < -5 and rank < 100:
                # Large cap going down = potential oversold bounce opportunity  
                features['anti_herd_momentum'] = min(abs(price_change_24h) / 30, 0.6)
            else:
                features['anti_herd_momentum'] = 0.2
                
        except Exception as e:
            # Graceful fallback
            features['fear_opportunity_score'] = 0.0
            features['neglect_opportunity_score'] = 0.0  
            features['anti_herd_momentum'] = 0.2
            
        return features
    
    def extract_timing_anomaly_features(self, coin_data: Dict) -> Dict[str, float]:
        """
        TIMING & RHYTHM ANALYSIS - Detect market timing inefficiencies
        
        The Theory: Markets have rhythms and patterns. Breaks in these patterns
        often signal important changes before they become obvious.
        """
        features = {}
        
        try:
            # 4. VOLUME SURGE ANOMALY
            # Unusual volume spikes often precede major moves
            volume_anomaly = self._calculate_volume_surge_score(coin_data)
            features['volume_surge_anomaly'] = volume_anomaly
            
            # 5. QUIET ACCUMULATION SIGNAL
            # Low volatility with steady volume = smart money accumulating?
            quiet_accumulation = self._detect_quiet_accumulation_pattern(coin_data)
            features['quiet_accumulation_signal'] = quiet_accumulation
            
            # 6. OFF-PEAK ACTIVITY ANOMALY
            # Activity during typically quiet times = something happening
            current_hour = datetime.now().hour
            price_change = coin_data.get('price_change_24h', 0)
            
            # If significant movement during US sleep hours (2-8 AM EST)
            if 6 <= current_hour <= 12:  # Assuming UTC, this is roughly US night
                if abs(price_change) > 8:
                    features['off_peak_anomaly'] = min(abs(price_change) / 15, 0.8)
                else:
                    features['off_peak_anomaly'] = 0.2
            else:
                features['off_peak_anomaly'] = 0.3
                
        except Exception as e:
            features['volume_surge_anomaly'] = 0.3
            features['quiet_accumulation_signal'] = 0.3
            features['off_peak_anomaly'] = 0.3
            
        return features
    
    def extract_network_effect_features(self, coin_data: Dict) -> Dict[str, float]:
        """
        CROSS-ASSET RELATIONSHIPS - Network effects others miss
        
        The Theory: Crypto is an interconnected ecosystem. Coins don't move 
        in isolation - understanding relationships reveals hidden opportunities.
        """
        features = {}
        
        try:
            symbol = coin_data.get('symbol', 'UNKNOWN').upper()
            
            # 7. ECOSYSTEM BETA ANALYSIS
            # How much does this coin benefit when its ecosystem thrives?
            ecosystem_beta = self._calculate_ecosystem_beta(symbol, coin_data)
            features['ecosystem_beta_score'] = ecosystem_beta
            
            # 8. CROSS-CHAIN BRIDGE POTENTIAL
            # Coins positioned to benefit from multi-chain future
            bridge_potential = self._assess_cross_chain_potential(symbol, coin_data)
            features['bridge_potential_score'] = bridge_potential
            
            # 9. SYMBIOTIC RELATIONSHIP STRENGTH
            # Coins that grow stronger together (DeFi protocols, L2s, etc.)
            symbiotic_strength = self._calculate_symbiotic_relationships(symbol)
            features['symbiotic_strength_score'] = symbiotic_strength
            
        except Exception as e:
            features['ecosystem_beta_score'] = 0.4
            features['bridge_potential_score'] = 0.3
            features['symbiotic_strength_score'] = 0.4
            
        return features
    
    def extract_smart_money_signals(self, coin_data: Dict) -> Dict[str, float]:
        """
        SMART MONEY DETECTION - Identify institutional vs retail patterns
        
        The Theory: Smart money (institutions, whales, experienced traders) 
        leaves footprints. Detecting their activity early provides alpha.
        """
        features = {}
        
        try:
            # 10. WHALE ACCUMULATION PATTERN
            # Large, consistent buying without major price impact = smart accumulation
            whale_pattern = self._detect_whale_accumulation_pattern(coin_data)
            features['whale_accumulation_score'] = whale_pattern
            
            # 11. INSTITUTIONAL PREPARATION SIGNALS
            # Signs that institutions are preparing to enter
            institutional_prep = self._detect_institutional_preparation(coin_data)
            features['institutional_prep_score'] = institutional_prep
            
            # 12. RETAIL EXHAUSTION SIGNAL
            # When retail investors give up, smart money often enters
            retail_exhaustion = self._calculate_retail_exhaustion_score(coin_data)
            features['retail_exhaustion_score'] = retail_exhaustion
            
        except Exception as e:
            features['whale_accumulation_score'] = 0.3
            features['institutional_prep_score'] = 0.3
            features['retail_exhaustion_score'] = 0.3
            
        return features
    
    def extract_asymmetric_opportunity_features(self, coin_data: Dict) -> Dict[str, float]:
        """
        ASYMMETRIC RISK-REWARD - High upside, limited downside
        
        The Theory: The best investments have asymmetric payoffs - you risk $1 
        to potentially make $5+. Look for situations with capped downside.
        """
        features = {}
        
        try:
            # 13. LIMITED DOWNSIDE SCORE
            # Coins near strong support levels with limited further downside
            limited_downside = self._calculate_limited_downside_score(coin_data)
            features['limited_downside_score'] = limited_downside
            
            # 14. EXPLOSIVE UPSIDE POTENTIAL
            # Coins with potential for non-linear returns
            explosive_upside = self._calculate_explosive_upside_potential(coin_data)
            features['explosive_upside_score'] = explosive_upside
            
            # 15. BLACK SWAN BENEFICIARY SCORE
            # Coins that could benefit dramatically from unexpected events
            black_swan_score = self._assess_black_swan_beneficiary_potential(coin_data)
            features['black_swan_beneficiary_score'] = black_swan_score
            
            # 16. OPTIONALITY VALUE
            # Value from future possibilities not reflected in current price
            optionality = self._calculate_optionality_value(coin_data)
            features['optionality_value_score'] = optionality
            
        except Exception as e:
            features['limited_downside_score'] = 0.3
            features['explosive_upside_score'] = 0.3
            features['black_swan_beneficiary_score'] = 0.3
            features['optionality_value_score'] = 0.3
            
        return features
    
    # Helper methods implementing the core logic
    
    def _extract_numeric_value(self, value_str: str) -> float:
        """Extract numeric value from string with currency symbols"""
        if isinstance(value_str, (int, float)):
            return float(value_str)
        try:
            # Remove common currency symbols and commas
            cleaned = str(value_str).replace('$', '').replace(',', '').replace('N/A', '0')
            return float(cleaned)
        except:
            return 0.0
    
    def _estimate_expected_volume(self, rank: int) -> float:
        """Estimate expected volume based on market cap rank"""
        # Rough heuristic: higher ranked coins should have more volume
        if rank < 50:
            return 50_000_000  # $50M+ expected
        elif rank < 100:
            return 20_000_000  # $20M+ expected  
        elif rank < 300:
            return 5_000_000   # $5M+ expected
        elif rank < 500:
            return 1_000_000   # $1M+ expected
        else:
            return 100_000     # $100K+ expected
    
    def _calculate_volume_surge_score(self, coin_data: Dict) -> float:
        """Calculate how unusual current volume is"""
        try:
            volume = self._extract_numeric_value(coin_data.get('total_volume', '0'))
            market_cap = self._extract_numeric_value(coin_data.get('market_cap', '0'))
            
            if market_cap > 0:
                volume_ratio = volume / market_cap
                # Normal ratio is 0.05-0.15 for most coins
                if volume_ratio > 0.3:  # Significantly high volume
                    return min(volume_ratio * 2, 1.0)
                elif volume_ratio > 0.2:  # Moderately high volume
                    return min(volume_ratio * 1.5, 0.8)
            return 0.3
        except:
            return 0.3
    
    def _detect_quiet_accumulation_pattern(self, coin_data: Dict) -> float:
        """Detect potential quiet accumulation"""
        try:
            price_change = coin_data.get('price_change_24h', 0)
            volume = self._extract_numeric_value(coin_data.get('total_volume', '0'))
            market_cap = self._extract_numeric_value(coin_data.get('market_cap', '0'))
            
            # Low price movement but decent volume = potential accumulation
            if market_cap > 0 and volume > 0:
                volume_ratio = volume / market_cap
                # Decent volume (>0.08) with small price change (<5%) = accumulation?
                if volume_ratio > 0.08 and abs(price_change) < 5:
                    return min(volume_ratio * 5, 0.8)
            return 0.2
        except:
            return 0.2
    
    def _calculate_ecosystem_beta(self, symbol: str, coin_data: Dict) -> float:
        """Calculate how much coin benefits from its ecosystem"""
        ecosystem_mapping = {
            # Ethereum ecosystem
            'UNI': 0.8, 'AAVE': 0.7, 'COMP': 0.6, 'MKR': 0.7, 'SNX': 0.6,
            'SUSHI': 0.6, 'CRV': 0.6, 'YFI': 0.7, 'INCH': 0.5, 'BAL': 0.5,
            
            # Binance Smart Chain ecosystem  
            'CAKE': 0.7, 'BNB': 0.9, 'AUTO': 0.5, 'BAKE': 0.4,
            
            # Solana ecosystem
            'RAY': 0.6, 'SRM': 0.5, 'FIDA': 0.4,
            
            # Polygon ecosystem
            'MATIC': 0.8, 'QUICK': 0.5, 'AAVEGOTCHI': 0.4,
            
            # Avalanche ecosystem  
            'AVAX': 0.8, 'JOE': 0.6, 'PNG': 0.4,
            
            # Layer 2 solutions
            'LRC': 0.6, 'IMX': 0.5, 'METIS': 0.4,
        }
        
        return ecosystem_mapping.get(symbol, 0.4)
    
    def _assess_cross_chain_potential(self, symbol: str, coin_data: Dict) -> float:
        """Assess potential to benefit from cross-chain trends"""
        # Bridge and interoperability tokens
        bridge_tokens = ['DOT', 'ATOM', 'RUNE', 'REN', 'KEEP', 'POLY']
        
        # Multi-chain protocols
        multichain_protocols = ['AAVE', 'UNI', 'SUSHI', 'CRV', 'COMP']
        
        if symbol in bridge_tokens:
            return 0.8
        elif symbol in multichain_protocols:
            return 0.6
        else:
            # General assessment based on rank and utility
            rank = coin_data.get('market_cap_rank', 999)
            if 50 < rank < 300:  # Mid-tier coins more likely to benefit from bridges
                return 0.5
            return 0.3
    
    def _calculate_symbiotic_relationships(self, symbol: str) -> float:
        """Calculate strength of symbiotic relationships with other tokens"""
        # DeFi tokens that benefit from each other
        defi_clusters = {
            'lending': ['AAVE', 'COMP', 'CREAM', 'ALPHA'],
            'dex': ['UNI', 'SUSHI', 'CAKE', 'QUICK'],
            'derivatives': ['SNX', 'PERP', 'DYDX', 'INJ'],
            'yield': ['YFI', 'HARVEST', 'AUTO', 'BEEFY'],
            'layer2': ['MATIC', 'LRC', 'IMX', 'METIS']
        }
        
        for cluster_name, tokens in defi_clusters.items():
            if symbol in tokens:
                return 0.7  # Strong symbiotic relationship
        
        return 0.4  # Default moderate relationship
    
    def _detect_whale_accumulation_pattern(self, coin_data: Dict) -> float:
        """Detect whale accumulation patterns"""
        try:
            volume = self._extract_numeric_value(coin_data.get('total_volume', '0'))
            price_change = coin_data.get('price_change_24h', 0)
            market_cap = self._extract_numeric_value(coin_data.get('market_cap', '0'))
            
            # High volume, low price impact = potential whale accumulation
            if market_cap > 0 and volume > 0:
                volume_ratio = volume / market_cap
                price_impact = abs(price_change) / 100  # Normalize
                
                # High volume (>0.15) with low price impact (<0.05) = whale accumulation?
                if volume_ratio > 0.15 and price_impact < 0.05:
                    return min(volume_ratio * 3, 0.9)
                elif volume_ratio > 0.1 and price_impact < 0.08:
                    return min(volume_ratio * 2, 0.6)
            return 0.3
        except:
            return 0.3
    
    def _detect_institutional_preparation(self, coin_data: Dict) -> float:
        """Detect signs of institutional preparation"""
        try:
            rank = coin_data.get('market_cap_rank', 999)
            volume = self._extract_numeric_value(coin_data.get('total_volume', '0'))
            
            # Well-ranked coins with growing volume = institutional interest?
            if rank < 100 and volume > 10_000_000:  # Top 100 with >$10M volume
                return 0.8
            elif rank < 200 and volume > 5_000_000:  # Top 200 with >$5M volume  
                return 0.6
            elif rank < 500 and volume > 1_000_000:  # Top 500 with >$1M volume
                return 0.4
            return 0.2
        except:
            return 0.2
    
    def _calculate_retail_exhaustion_score(self, coin_data: Dict) -> float:
        """Calculate retail exhaustion (when retail gives up, smart money enters)"""
        try:
            price_change = coin_data.get('price_change_24h', 0)
            volume = self._extract_numeric_value(coin_data.get('total_volume', '0'))
            rank = coin_data.get('market_cap_rank', 999)
            
            # Significant price drop with decreasing volume = retail exhaustion?
            if price_change < -10:
                exhaustion_score = min(abs(price_change) / 30, 0.8)
                
                # Better ranked coins have higher recovery probability
                if rank < 200:
                    return exhaustion_score * 1.2
                elif rank < 500:
                    return exhaustion_score
                else:
                    return exhaustion_score * 0.7
            return 0.2
        except:
            return 0.2
    
    def _calculate_limited_downside_score(self, coin_data: Dict) -> float:
        """Calculate limited downside potential"""
        try:
            price_change = coin_data.get('price_change_24h', 0)
            rank = coin_data.get('market_cap_rank', 999)
            
            # Already down significantly = limited further downside?
            if price_change < -20:
                # Better ranked coins have stronger support levels
                if rank < 100:
                    return 0.8
                elif rank < 300:
                    return 0.6
                elif rank < 500:
                    return 0.4
                return 0.2
            elif price_change < -10:
                return max(0.3, (300 - rank) / 1000) if rank < 300 else 0.2
            return 0.1
        except:
            return 0.1
    
    def _calculate_explosive_upside_potential(self, coin_data: Dict) -> float:
        """Calculate explosive upside potential"""
        try:
            rank = coin_data.get('market_cap_rank', 999)
            volume = self._extract_numeric_value(coin_data.get('total_volume', '0'))
            
            # Lower ranked coins with decent volume have more upside potential
            if 200 < rank < 800 and volume > 100_000:
                return min((rank / 1000) + (volume / 10_000_000), 0.8)
            elif 100 < rank < 200 and volume > 1_000_000:
                return 0.6
            return 0.3
        except:
            return 0.3
    
    def _assess_black_swan_beneficiary_potential(self, coin_data: Dict) -> float:
        """Assess potential to benefit from black swan events"""
        try:
            symbol = coin_data.get('symbol', 'UNKNOWN').upper()
            
            # Coins that could benefit from system stress/change
            safe_haven_coins = ['BTC', 'ETH', 'USDC', 'USDT']
            infrastructure_coins = ['LINK', 'DOT', 'ATOM', 'MATIC']
            defi_infrastructure = ['AAVE', 'UNI', 'COMP', 'MKR']
            
            if symbol in safe_haven_coins:
                return 0.9
            elif symbol in infrastructure_coins:
                return 0.7
            elif symbol in defi_infrastructure:
                return 0.6
            return 0.3
        except:
            return 0.3
    
    def _calculate_optionality_value(self, coin_data: Dict) -> float:
        """Calculate optionality value from future possibilities"""
        try:
            rank = coin_data.get('market_cap_rank', 999)
            symbol = coin_data.get('symbol', 'UNKNOWN').upper()
            
            # Platform coins have high optionality (could become next big thing)
            platform_coins = ['ETH', 'BNB', 'SOL', 'AVAX', 'MATIC', 'DOT', 'ATOM']
            
            # Infrastructure/utility coins have medium optionality
            infrastructure_coins = ['LINK', 'GRT', 'FIL', 'AR', 'OCEAN']
            
            if symbol in platform_coins:
                return 0.8
            elif symbol in infrastructure_coins:
                return 0.6
            elif 100 < rank < 500:  # Mid-tier coins have speculative optionality
                return 0.5
            return 0.3
        except:
            return 0.3