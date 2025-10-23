# 🚀 CryptoApp Development Guide

Quick development workflow for the Cryptocurrency Investment Analyzer.

---

## 📁 Project Structure

```
CryptoApp/
├── main.py                    # CLI entry point
├── app.py                     # Web app entry point
├── requirements.txt           # Dependencies
├── src/core/                  # Core business logic
├── src/cli/                   # Command line interface
├── src/web/templates/         # Web interface
├── data/live_api.json         # Live crypto data
└── tests/                     # Test files
```

---

## 🛠️ Development Workflow

### Daily Development
```bash
# Switch to dev branch and test
git checkout dev
python3 tests/test_basic_functionality.py

# Make changes, then test
python3 main.py              # CLI version
python3 app.py               # Web version (http://localhost:5000)

# Commit changes
git add . && git commit -m "Your changes"
```

### Deploy to Production
```bash
git checkout main && git merge dev && git push origin main
```

---

## 🧪 Quick Testing

```bash
# Test core functionality
python3 tests/test_basic_functionality.py

# Test with live data
python3 main.py --live

# Test web interface
python3 app.py  # Visit: http://localhost:5000
```

---

## 🚨 Emergency Commands

```bash
# Rollback changes
git checkout -- . && git clean -fd

# Restore live data
rm data/live_api.json && python3 main.py --live

# Fix dependencies
pip install -r requirements.txt
```

---

## 📝 Quick Reference

### Most Used Commands
```bash
python3 tests/test_basic_functionality.py  # Test everything
python3 main.py                            # Run CLI
python3 app.py                             # Run web app
git checkout dev                           # Development
git checkout main && git merge dev         # Deploy
```

**Happy coding! 🚀**