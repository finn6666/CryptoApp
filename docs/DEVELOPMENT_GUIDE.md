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
git reset --hard HEAD~1 # Go back 1 commit and delete all changes after it
```

**Happy coding! 🚀**

---

## Git Workflow & Sync Issues

### The Problem
If you're getting "fetch first" errors when pushing, it means the remote repository has changes that your local repository doesn't have. This commonly happens when working across multiple environments.

### Root Causes
- **Multiple development environments** (local machine + GitHub Codespaces)
- **Direct edits on GitHub.com**
- **Collaborators pushing changes**
- **IDE auto-commits** in different environments

### Prevention Strategy

#### Always Start Coding Sessions With:
```bash
git pull origin main
```

#### Before Making Changes:
```bash
git status
git log --oneline -5  # Check recent commits
```

### Recommended Git Workflow

#### 1. Start Session
```bash
git pull origin main
```

#### 2. Make Changes
```bash
# ... make your code changes ...
```

#### 3. Commit Frequently
```bash
git add .
git commit -m "Descriptive commit message"
```

#### 4. Before Pushing
```bash
# Pull again in case of new remote changes
git pull origin main

# Then push
git push origin main
```

### Fixing Sync Issues

#### When Push is Rejected:
```bash
# Pull remote changes
git pull origin main

# If merge conflicts appear:
# 1. Resolve them in VS Code
# 2. Save the files
# 3. Then:
git add .
git commit -m "Resolve merge conflicts"

# Push your changes
git push origin main
```

#### Emergency Force Push (Use Carefully):
```bash
# WARNING: This overwrites remote changes
git push --force-with-lease origin main
```

### Best Practices
- **Pull before coding** - Always start with `git pull origin main`
- **Commit frequently** - Don't let changes build up
- **Pull before pushing** - Check for remote changes before pushing
- **Use descriptive commit messages** - Help future you understand changes
- **One environment at a time** - Avoid coding simultaneously in multiple places

### Commit Message Guidelines
```bash
# Good examples:
git commit -m "Fix table alignment and price display formatting"
git commit -m "Add USD to GBP conversion with 2 decimal places"
git commit -m "Update price parsing to handle different API formats"

# Avoid:
git commit -m "fix"
git commit -m "updates"
git commit -m "changes"
```

### Multiple Environment Sync
If working across environments:
1. **Finish work in Environment A**
2. **Commit and push all changes**
3. **Switch to Environment B**
4. **Pull latest changes before starting**