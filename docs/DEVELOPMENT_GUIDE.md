# 🚀 CryptoApp Development Guide

## 📁 Project Structure
```
CryptoApp/
├── main.py                    # CLI entry point
├── app.py                     # Web app entry point
├── src/
│   ├── core/                  # Core business logic
│   │   ├── crypto_analyzer.py # Main analysis engine
│   │   ├── live_data_fetcher.py # API data fetching
│   │   └── config.py          # App configuration
│   └── web/templates/         # Web interface
├── ml/                        # Machine learning components
│   ├── data_pipeline.py       # Data processing
│   ├── training_pipeline.py   # ML model training
│   └── monitoring.py          # ML monitoring
├── services/                  # External services
│   └── ml_service.py          # ML prediction service
├── config/                    # Configuration files
│   └── ml_config.py           # ML-specific config
├── data/live_api.json         # Live crypto data
├── azure_functions/           # Azure deployment
├── requirements-ml.txt        # ML dependencies
└── tests/                     # Test files
```

## 🛠️ Daily Workflow
```bash
# Start session
git pull origin main

# Test & develop
python3 tests/test_basic_functionality.py
python3 main.py              # Data fetcher & simplified entry point
python3 app.py               # Full web application (localhost:5001)

# Commit changes
git add . && git commit -m "Description"
git pull origin main && git push origin main
```

## 🧪 Quick Commands
```bash
# Testing
python3 tests/test_basic_functionality.py
python3 main.py --live

# Git fixes
git pull origin main         # Fix "fetch first" errors
git status                   # Check current state
git log --oneline -3         # Recent commits

# Emergency
git stash && git pull origin main && git stash pop
git reset --hard HEAD~1      # Undo last commit
```

## 🚨 Deploy
```bash
git checkout main && git merge dev && git push origin main
```

**Always start with `git pull origin main` 🚀**