# � CryptoApp Development Guide

Complete development workflow for the Cryptocurrency Investment Analyzer.

---

## 📁 Project Structure

```
CryptoApp/
├── main.py                    # CLI entry point
├── app.py                     # Web app entry point
├── pyproject.toml             # Project configuration
├── requirements.txt           # Dependencies
│
├── src/                       # Source code
│   ├── __init__.py           # Package metadata
│   ├── core/                 # Core business logic
│   │   ├── __init__.py       # Core module exports
│   │   ├── crypto_analyzer.py # Analysis engine
│   │   ├── crypto_visualizer.py # Data visualization
│   │   └── live_data_fetcher.py # API data fetching
│   │
│   └── cli/                  # Command line interface
│       ├── __init__.py       # CLI module exports
│       └── crypto_display.py # Rich CLI display
│
├── src/web/                  # Web interface
│   ├── web_app.py           # Flask routes
│   └── templates/
│       └── index.html       # Dark theme UI
│
├── data/                     # Data files
│   └── live_api.json        # Live crypto data
│
├── tests/                    # Test files
│   ├── test_basic_functionality.py
│   └── test_favorites.py
│
├── docs/                     # Documentation
│   ├── README.md
│   ├── DEPLOYMENT.md
│   └── DEVELOPMENT_GUIDE.md  # This file
│
└── scripts/                  # Utility scripts
    └── (empty - cleaned up)
```

---

## 🛠️ Development Workflow

### 1. **Before Making Changes**
```bash
# Switch to dev branch
git checkout dev

# Make sure you're up to date
git pull origin dev

# Check current status
git status
```

### 2. **Testing Strategy** 🧪
After each change, run:
```bash
# Test core functionality
python3 tests/test_basic_functionality.py

# Test CLI interface
python3 main.py --help

# Test web interface
python3 app.py
# Then visit: http://localhost:5000
```

### 3. **Running the Applications**

**CLI Version:**
```bash
python3 main.py                    # Full analysis
python3 main.py --top 10          # Top 10 coins
python3 main.py --live            # Fetch live data first
```

**Web Version:**
```bash
python3 app.py
# Visit: http://localhost:5000
# Click "� Refresh Now" for live data
```

### 4. **Data Management**

**Live Data Source:**
- App uses `data/live_api.json` (fetched from CoinGecko API)
- Refreshes automatically via web interface
- No more static `api.json` file

**Fetch Fresh Data:**
```bash
# Via CLI
python3 main.py --live

# Via Web UI
# Click "Refresh Now" button at http://localhost:5000
```

---

## 🔄 Git Workflow

### Branch Structure
- **`main`** - Stable production code
- **`dev`** - Development branch

### Making Changes
```bash
# 1. Create feature branch from dev
git checkout dev
git checkout -b feature/your-feature-name

# 2. Make your changes
# ... edit files ...

# 3. Test changes
python3 tests/test_basic_functionality.py

# 4. Commit changes
git add .
git commit -m "Add your feature description"

# 5. Merge back to dev
git checkout dev
git merge feature/your-feature-name

# 6. Clean up feature branch
git branch -d feature/your-feature-name

# 7. When ready for release, merge dev to main
git checkout main
git merge dev
git push origin main
```

---

## 🧪 Testing & Debugging

### Running Tests
```bash
# Basic functionality test
cd /Users/finnbryant/Dev/CryptoApp
python3 tests/test_basic_functionality.py

# Test with live data
python3 tests/test_favorites.py
```

### Debug Common Issues

**Import Errors:**
```bash
# Make sure you're in the right directory
pwd  # Should show: /Users/finnbryant/Dev/CryptoApp

# Check Python path
python3 -c "import sys; print(sys.path)"
```

**Data File Issues:**
```bash
# Check if live data exists
ls -la data/live_api.json

# Fetch fresh data if needed
python3 main.py --live
```

**Flask App Issues:**
```bash
# Check if port 5000 is free
lsof -i :5000

# Run with debug info
FLASK_DEBUG=1 python3 app.py
```

---

## 🚨 Emergency Procedures

### Quick Rollback
If something breaks:
```bash
# Discard all changes
git checkout -- .
git clean -fd

# Or restore from main
git checkout main
git reset --hard HEAD
```

### Restore Previous Version
```bash
# See recent commits
git log --oneline -5

# Reset to specific commit
git reset --hard <commit-hash>

# Or create new branch from old commit
git checkout -b hotfix/restore main~1
```

### Data Recovery
```bash
# If live_api.json gets corrupted
rm data/live_api.json
python3 main.py --live  # Fetches fresh data
```

---

## 📦 Dependencies & Environment

### Required Packages
```bash
# Install all dependencies
pip install -r requirements.txt

# Key packages:
# - flask (web interface)
# - rich (CLI formatting)  
# - requests (API calls)
```

### Environment Setup
```bash
# Create virtual environment (optional)
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

---

## 🌐 Deployment

### Local Development
```bash
# CLI version
python3 main.py

# Web version  
python3 app.py
# Visit: http://localhost:5000
```

### Production Deployment
See [`DEPLOYMENT.md`](DEPLOYMENT.md) for Azure VM deployment instructions.

---

## 🔧 Code Style & Standards

### File Organization
- **`src/core/`** - Business logic, no UI dependencies
- **`src/cli/`** - Command line interface code  
- **`src/web/`** - Web interface code
- **`tests/`** - All test files
- **`data/`** - Data files only

### Import Standards
```python
# Core modules use relative imports
from .crypto_analyzer import CryptoAnalyzer

# App-level files use absolute imports  
from src.core.crypto_analyzer import CryptoAnalyzer
```

### Testing Standards
- Test after every change
- Use `test_basic_functionality.py` for core features
- Test both CLI and web interfaces

---

## 📝 Quick Reference

### Most Common Commands
```bash
# Test everything
python3 tests/test_basic_functionality.py

# Run CLI
python3 main.py

# Run web app
python3 app.py

# Fetch live data
python3 main.py --live

# Git workflow
git checkout dev
git add . && git commit -m "Your changes"
git checkout main && git merge dev
```

### File Locations
- **Main CLI**: `main.py`
- **Web App**: `app.py`  
- **Core Logic**: `src/core/crypto_analyzer.py`
- **Live Data**: `data/live_api.json`
- **Web UI**: `src/web/templates/index.html`
- **Tests**: `tests/test_basic_functionality.py`

---

**Happy coding! 🚀** Your crypto analyzer is ready for development and deployment.