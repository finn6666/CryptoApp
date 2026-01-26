# 🧠 ML Engine - Hidden Gem Detection System

**Goal:** Identify high-potential low-cap cryptocurrencies before they moon using multi-layered AI analysis.

---

## 🎯 The ML Pipeline Flow

```
Raw Coin Data → Feature Engineering → Gem Detection → AI Sentiment → Final Score
     ↓              ↓                    ↓               ↓              ↓
data_pipeline → advanced_alpha → enhanced_gem_detector ← deepseek → USER
                                         ↑
                                    simple_rl (reward learning)
                                         ↑
                                  training_pipeline
```

---

## 📁 File Roles & Optimization Points

### 🔹 **data_pipeline.py** - Data Collector
**What it does:** Fetches live market data from CoinMarketCap API  
**Key function:** `collect_training_data()` - gathers price, volume, market cap  
**Optimize:**
- Add more data sources (Coingecko, on-chain metrics)
- Increase historical lookback period
- Add social sentiment data (Twitter, Reddit volume)

---

### 🔹 **advanced_alpha_features.py** - Feature Engineer
**What it does:** Transforms raw data into 100+ predictive features  
**Key features:**
- Technical indicators (RSI, MACD, Bollinger Bands)
- Volume patterns (accumulation/distribution)
- Market structure (support/resistance)
- Social signals (mentions, sentiment scores)

**Optimize:**
- Tune indicator windows (RSI default: 14 periods)
- Add whale wallet tracking
- Include DEX liquidity metrics
- Weight features by importance (feature_importances_)

---

### 🔹 **enhanced_gem_detector.py** - Core ML Model
**What it does:** Multi-model ensemble that predicts "gem probability"  
**Models used:**
1. Random Forest (pattern recognition)
2. Gradient Boosting (trend prediction)
3. Simple RL agent (learns from outcomes)

**Key metric:** `gem_probability` (0-1 score)

**Optimize:**
- Tune hyperparameters: `n_estimators`, `max_depth`, `learning_rate`
- Adjust gem threshold (currently 0.6 = 60%)
- Retrain more frequently on recent winners
- Add XGBoost or LightGBM for speed

**Where to tweak:**
```python
# Line ~45: Model initialization
self.models = {
    'rf': RandomForestClassifier(n_estimators=200),  # ← Increase trees
    'gb': GradientBoostingClassifier(learning_rate=0.05)  # ← Lower = slower but better
}
```

---

### 🔹 **simple_rl.py** - Reinforcement Learning Agent
**What it does:** Learns optimal buy/hold decisions from past trades  
**Method:** Q-learning (reward-based learning)  
**Integrated into:** `enhanced_gem_detector.py` as 3rd model

**Optimize:**
- Increase exploration rate for volatile markets
- Adjust reward function (currently: price_change * confidence)
- Add penalty for false positives

**Key params:**
```python
learning_rate = 0.1      # How fast it learns (0.1 = moderate)
discount_factor = 0.95   # Values future rewards (0.95 = patient investor)
epsilon = 0.1            # Exploration rate (10% random actions)
```

---

### 🔹 **deepseek_analyzer.py** - AI Sentiment Layer
**What it does:** Analyzes coin fundamentals using DeepSeek AI  
**Output:** Unique insights per coin (catalyst, edge, risk)  
**Cached:** Saves results to avoid API spam

**Optimize:**
- Improve prompt engineering for better insights
- Add competitor comparison in prompts
- Include recent news/events in context
- Tune cache TTL (currently saves forever)

**Where to tweak:**
```python
# Line ~80: The prompt sent to DeepSeek
prompt = f"""Analyze {coin['symbol']}: 
Market Cap: ${coin['market_cap']}
Volume: ${coin['volume_24h']}
Price Change: {coin['price_change_24h']}%

Provide:
1. Unique catalyst (why it could moon)
2. Competitive edge (vs similar coins)
3. Key risk (biggest threat)
"""
```

---

### 🔹 **training_pipeline.py** - Model Trainer
**What it does:** Trains/retrains all models on historical data  
**Triggered by:** Manual training or scheduled updates

**Optimize:**
- Increase training data size (more coins/timeframes)
- Add cross-validation for robustness
- Implement incremental learning (don't retrain from scratch)
- Track model drift over time

---

### 🔹 **monitoring.py** - Performance Tracker (Future Use)
**Planned:** Track prediction accuracy, false positive rate, ROI  
**Use case:** Detect when model degrades and needs retraining

---

### 🔹 **scheduler.py** - Auto-Trainer (Future Use)
**Planned:** Automatically retrain models weekly  
**Use case:** Keep models fresh with latest market patterns

---

### 🔹 **weekly_report.py** - Results Reporter (Future Use)
**Planned:** Generate performance summaries  
**Metrics:** Top picks, hit rate, missed gems

---

## 🚀 Quick Optimization Wins

### 1. **Improve Gem Detection Accuracy**
Edit `enhanced_gem_detector.py` line ~120:
```python
# Current threshold
gem_probability_threshold = 0.6  # 60% confidence

# More aggressive (more gems, more false positives)
gem_probability_threshold = 0.5

# More conservative (fewer gems, higher quality)
gem_probability_threshold = 0.7
```

### 2. **Add More Features**
Edit `advanced_alpha_features.py`, add to `calculate_features()`:
```python
# New feature: Whale activity
features['whale_score'] = detect_large_holders(coin_data)

# New feature: DEX liquidity depth
features['liquidity_score'] = check_uniswap_depth(coin_data)
```

### 3. **Faster Retraining**
Edit `training_pipeline.py` line ~50:
```python
# Use only recent data for speed
training_data = load_last_n_days(days=30)  # Instead of all history
```

### 4. **Better DeepSeek Prompts**
Edit `deepseek_analyzer.py` line ~80:
```python
# Add context about recent winners
prompt = f"""You're a crypto gem hunter. Analyze {coin['symbol']}.
Recent 100x coins had: novel tech, low initial cap, viral narrative.
Does this coin have similar traits?
"""
```

---

## 🎓 Understanding the Scoring

**Final gem_score (0-100) combines:**
- 40% ML model predictions (Random Forest + Gradient Boost)
- 30% RL agent recommendation
- 20% DeepSeek sentiment score
- 10% Technical indicators

**To adjust weights:** Edit `enhanced_gem_detector.py` line ~200

---

## 📊 Model Performance Metrics

Check these to know if your optimizations work:

- **Precision:** % of predicted gems that actually mooned
- **Recall:** % of actual gems we caught
- **F1 Score:** Balance of precision/recall
- **ROI:** If you bought all BUY recommendations, what's the return?

Track in `monitoring.py` (future implementation)

---

## 🔧 Development Workflow

1. **Make changes** to feature engineering or model params
2. **Retrain model:** Call `/api/ml/train` endpoint or run `training_pipeline.py`
3. **Test on live data:** Check `/api/coins` for new predictions
4. **Monitor results:** Track which predictions mooned (future: weekly_report.py)
5. **Iterate:** Adjust based on what worked

---

**Remember:** ML models learn from data. If market conditions change (bear→bull, meme season), retrain with recent data!
