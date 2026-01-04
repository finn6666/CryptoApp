# Models Directory

## Purpose

This directory stores trained machine learning models for the crypto analysis system. Models are persisted to disk so they don't need to be retrained every time the application starts.

## Model Files Explained

### File Types

#### `.pkl` Files (Pickle Format)
- **What**: Python's serialization format for saving objects
- **Contains**: Complete model objects with all learned parameters
- **Size**: Typically 1-50 MB depending on model complexity
- **Speed**: Fast to load and save
- **Used For**: Scikit-learn models (Random Forest, classifiers, scalers)

**Example Files**:
- `crypto_model.pkl` - Main prediction model (Random Forest)
- `scaler.pkl` - Feature scaling parameters (StandardScaler)
- `hidden_gem_detector.pkl` - Hidden gem classification model
- `rl_agent.pkl` - Reinforcement learning agent metadata
- `rl_agent_network.pth` - RL neural network (PyTorch format)

#### `.joblib` Files (Joblib Format)  
- **What**: Optimized format for NumPy arrays (used by scikit-learn)
- **Contains**: Same as .pkl but more efficient for large numpy arrays
- **Size**: Often smaller than .pkl for same model
- **Speed**: Faster than pickle for large arrays
- **Used For**: Large scikit-learn models, especially with many features

**Why Both Formats?**
- `.pkl` is standard Python, works everywhere
- `.joblib` is faster for ML models with large matrices
- Code uses whichever is available

#### `.onnx` Files (ONNX Format)
- **What**: Open Neural Network Exchange format
- **Contains**: Model in platform-independent format
- **Used For**: Deploying to production, Azure Functions, other languages
- **Benefit**: Can run model without Python/scikit-learn

---

## High-Level Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     CRYPTO ANALYSIS SYSTEM                       │
└─────────────────────────────────────────────────────────────────┘

STEP 1: DATA COLLECTION
┌──────────────┐
│ CoinGecko    │──┐
│ API          │  │
└──────────────┘  │
                  ├──→ ┌────────────────┐
┌──────────────┐  │    │ Live Data      │
│ CryptoCompare│──┘    │ Fetcher        │
│ API          │       └────────┬───────┘
└──────────────┘                │
                                ↓
                     ┌─────────────────────┐
                     │ Raw Crypto Data     │
                     │ (Price, Volume,     │
                     │  Market Cap, etc.)  │
                     └──────────┬──────────┘
                                │

STEP 2: FEATURE ENGINEERING
                                ↓
                     ┌─────────────────────┐
                     │ Data Pipeline       │
                     │ • Calculate RSI     │
                     │ • Calculate MACD    │
                     │ • Moving Averages   │
                     │ • Price Changes     │
                     │ • Volume Trends     │
                     └──────────┬──────────┘
                                │
                                ↓
                     ┌─────────────────────┐
                     │ Engineered Features │
                     │ (40+ indicators     │
                     │  per coin)          │
                     └──────────┬──────────┘
                                │

STEP 3: MODEL TRAINING (Weekly/On-Demand)
                                ↓
                     ┌─────────────────────┐
                     │ Training Pipeline   │
                     │ • Split data        │
                     │ • Train models      │
                     │ • Validate          │
                     │ • Tune parameters   │
                     └──────────┬──────────┘
                                │
                                ↓
                     ┌─────────────────────┐
                     │ TRAINED MODELS      │
                     │ (Saved to disk)     │
                     │                     │
                     │ 📁 models/          │
                     │  ├─ crypto_model.pkl│
                     │  ├─ hidden_gem_     │
                     │  │  detector.pkl    │
                     │  ├─ rl_agent.pkl    │
                     │  ├─ rl_agent_       │
                     │  │  network.pth     │
                     │  └─ scaler.pkl      │
                     └──────────┬──────────┘
                                │

STEP 4: PREDICTION & ANALYSIS (When User Refreshes)
                                ↓
                     ┌─────────────────────┐
                     │ Load Models         │
                     │ from Disk           │
                     └──────────┬──────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ↓                     ↓                     ↓
   ┌─────────────┐    ┌─────────────────┐   ┌──────────────┐
   │ ML Pipeline │    │ Gem Detector    │   │ RL Agent     │
   │ (Random     │    │ (Enhanced       │   │ (Deep Q      │
   │  Forest)    │    │  Classifier)    │   │  Network)    │
   └──────┬──────┘    └────────┬────────┘   └──────┬───────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               ↓
                    ┌─────────────────────┐
                    │ Crypto Analyzer     │
                    │ • Calculates scores │
                    │ • Ranks coins       │
                    │ • Finds gems        │
                    │ • RL decisions      │
                    │ • DeepSeek insights │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ↓                    ↓                    ↓
   ┌─────────────┐    ┌─────────────────┐  ┌──────────────┐
   │ Low-Cap     │    │ Favorites       │  │ On-Demand    │
   │ Coins       │    │ (Any coin)      │  │ API Fetch    │
   │ (<£1 price) │    │ ETH, SOL, etc.  │  │ (Rate limit  │
   │             │    │                 │  │  handling)   │
   └─────────────┘    └─────────────────┘  └──────────────┘
                              │

STEP 5: PRESENTATION
                              ↓
                   ┌─────────────────────┐
                   │ Web Interface       │
                   │ • Dashboard         │
                   │ • Coin Tables       │
                   │ • ML Predictions    │
                   │ • Gem Scores        │
                   └─────────────────────┘
                              │
                              ↓
                         👤 YOU!
```

---

## Summary

**Models directory = Your app's "memory"**

Just like you don't forget what you learned after sleeping, the app doesn't forget its trained patterns after restarting. Models are the persistent storage of learned cryptocurrency patterns and behaviors.

**Key Points**:
- `.pkl`/`.joblib` = Saved models (scikit-learn, metadata)
- `.pth` = PyTorch neural networks (RL agent)
- Models trained once, used many times
- Updated weekly with new data via scheduler
- Load quickly on startup
- Enable fast predictions without retraining
