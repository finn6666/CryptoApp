# 🔄 Safe Code Change Workflow

**Testing Strategy** 🧪
After each change:
- Run: `python3 test_basic_functionality.py`

## Emergency Rollback 🚨
If something breaks:
```bash
# Quick rollback
git checkout -- .          # Discard file changes
git clean -fd              # Remove untracked files

# Or restore from backup branch
git checkout main          # Go to main branch
git reset --hard HEAD      # Reset to last commit
```