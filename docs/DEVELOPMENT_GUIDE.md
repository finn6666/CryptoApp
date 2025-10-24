# 🚀 CryptoApp Development Guide

## 📁 Project Structure
```
CryptoApp/
├── main.py                    # CLI entry point
├── app.py                     # Web app entry point
├── src/core/                  # Core business logic
├── src/cli/                   # Command line interface
├── src/web/templates/         # Web interface
├── data/live_api.json         # Live crypto data
└── tests/                     # Test files
```

## 🛠️ Daily Workflow
```bash
# Start session
git pull origin main

# Test & develop
python3 tests/test_basic_functionality.py
python3 main.py              # CLI version
python3 app.py               # Web version (localhost:5000)

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