# CryptoApp Documentation

AI-powered cryptocurrency gem detection with advanced ML and real-time insights.

---

## 📖 Quick Navigation

| Need to... | Go to |
|-----------|-------|
| **Update code on Azure VM** | [DEPLOYMENT.md - Quick Update](DEPLOYMENT.md#-quick-update-most-common) ⭐ Most common |
| **First-time Azure setup** | [DEPLOYMENT.md](DEPLOYMENT.md) |
| **Learn how to use the app** | [GUIDE.md](GUIDE.md) |
| **Understand ML architecture** | [ML_SYSTEM_COMPLETE.md](ML_SYSTEM_COMPLETE.md) |
| **Setup DeepSeek AI** | [DEEPSEEK.md](DEEPSEEK.md) |
| **Understand model files** | [MODELS.md](MODELS.md) |

---

## ⚡ Quick Commands

**Update Azure VM:**
```bash
cd ~/CryptoApp && git pull && sudo systemctl restart cryptoapp
```

**Check status:**
```bash
sudo systemctl status cryptoapp
```

**View logs:**
```bash
sudo journalctl -u cryptoapp -f
```

**Run locally:**
```bash
python app.py  # Visit http://localhost:5001
```

---

## 📋 Documentation Files

### [DEPLOYMENT.md](DEPLOYMENT.md)
Complete Azure VM deployment guide with quick updates, service management, and troubleshooting.

### [GUIDE.md](GUIDE.md)
User guide covering features, email setup, DeepSeek integration, and daily workflows.

### [ML_SYSTEM_COMPLETE.md](ML_SYSTEM_COMPLETE.md)
Technical deep-dive: ML architecture, feature engineering, training pipeline, and gem detection.

### [DEEPSEEK.md](DEEPSEEK.md)
DeepSeek AI integration for sentiment analysis with cost optimization and caching.

### [MODELS.md](MODELS.md)
Model file formats, data flow diagrams, and persistence explained.

---

## 💡 Key Features

- **Advanced Gem Detection** - 16+ alpha signals others miss
- **AI Sentiment Analysis** - DeepSeek-powered insights (optional)
- **Reinforcement Learning** - Learns from trading outcomes
- **Real-time Data** - Live crypto analysis
- **Interactive Dashboard** - Modern web interface
- **Favorites Tracking** - Monitor your picks

---

## 💰 Costs

| Component | Cost/Month | Notes |
|-----------|-----------|-------|
| Azure VM B2s (2 vCPU, 4GB) | ~$40 | Recommended for smooth ML |
| Azure VM B1ms (1 vCPU, 2GB) | ~$15 | Budget option |
| DeepSeek AI (optional) | ~$0.60 | With 24hr caching |

**ROI**: One good trade covers monthly costs.

---

## 📁 Project Structure

```
CryptoApp/
├── docs/           Documentation (you are here)
├── ml/             ML models & training
├── src/            Core analysis & web UI
├── models/         Saved ML models (.pkl)
├── data/           API data & cache
└── deploy/         Service configs
```

---

## ⚠️ Disclaimer

**NOT FINANCIAL ADVICE.** Educational project only. Crypto is highly risky. DYOR. Never invest more than you can afford to lose.

---

**MIT License** • [GitHub](https://github.com/finn6666/CryptoApp) • Last Updated: January 2026
