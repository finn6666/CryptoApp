# 📚 CryptoApp Documentation# CryptoApp Documentation



**Complete documentation for the AI-powered cryptocurrency analysis platform.**AI-powered cryptocurrency analysis platform with hidden gem detection and weekly email reports.



------



## 🎯 Start Here## 📚 Documentation Index



### **What do you need to do?**### **🚀 [DEPLOYMENT.md](DEPLOYMENT.md)** - Azure VM Setup & Updates

Complete guide for:

| Task | Documentation |- Initial Azure VM setup

|------|---------------|- **Updating code on your server** (most common)

| **🚀 Update code on Azure VM** | **[DEPLOYMENT.md](DEPLOYMENT.md#-quick-update-most-common)** ⭐ Most common |- Service management (start/stop/restart)

| **🏗️ First time Azure setup** | [DEPLOYMENT.md](DEPLOYMENT.md) - Ubuntu or RHEL |- Troubleshooting common issues

| **📖 Learn how to use the app** | [GUIDE.md](GUIDE.md) - Features & setup |- Daily maintenance workflow

| **🧠 Understand ML system** | [ML_SYSTEM_COMPLETE.md](ML_SYSTEM_COMPLETE.md) - Technical details |

| **🤖 Setup DeepSeek AI** | [DEEPSEEK.md](DEEPSEEK.md) - AI integration |### **📖 [GUIDE.md](GUIDE.md)** - User Guide & Features

| **💾 Understand models** | [MODELS.md](MODELS.md) - ML models explained |- Quick start & installation

- Email setup for weekly reports

---- DeepSeek AI integration

- Development workflow

## 📋 Documentation Files- FAQ



### **🚀 [DEPLOYMENT.md](DEPLOYMENT.md)** - Server Deployment Guide### **🧠 [ML_SYSTEM_COMPLETE.md](ML_SYSTEM_COMPLETE.md)** - ML Architecture

**GO HERE TO UPDATE YOUR AZURE VM!**Technical documentation:

- Machine learning system architecture

Complete deployment guide including:- Feature engineering details

- ⚡ **Quick Update** - Update code in 5 commands- Model training process

- 🐧 Ubuntu/Debian setup (B2s VM)- Hidden gem detection algorithm

- 🎩 RHEL setup (with uv)

- 🎛️ Service management (start/stop/restart/logs)---

- 🔧 Troubleshooting (service issues, permissions, networking)

- 📊 Testing & verification## ⚡ Quick Commands

- 🔐 Security best practices

- 💡 Pro tips & aliases### Update Code on Azure VM

```bash

**Quick command:**ssh your-username@your-vm-ip

```bashcd ~/CryptoApp

cd ~/CryptoApp && git pull && sudo systemctl restart cryptoappgit pull origin main

```sudo systemctl restart cryptoapp

sudo systemctl status cryptoapp

---```



### **📖 [GUIDE.md](GUIDE.md)** - User Guide & Features### Local Development

Everything about using CryptoApp:```bash

- Quick start & installationpip install -e .

- Features overviewpython app.py

- Email setup for weekly reports# Visit http://localhost:5001

- DeepSeek AI integration```

- Development workflow

- Key files & structure### Check Service Logs

- ML models```bash

- FAQsudo journalctl -u cryptoapp -f

```

**Start local development:**

```bash---

pip install -e .

python app.py## 🎯 Common Tasks

```

| Task | Documentation |

---|------|---------------|

| **Update code on Azure VM** | [DEPLOYMENT.md](DEPLOYMENT.md#updating-code) |

### **🧠 [ML_SYSTEM_COMPLETE.md](ML_SYSTEM_COMPLETE.md)** - ML Architecture| **Initial Azure setup** | [DEPLOYMENT.md](DEPLOYMENT.md#initial-setup) |

Technical deep-dive into the machine learning system:| **Setup email reports** | [GUIDE.md](GUIDE.md#email-setup-weekly-reports) |

- System architecture| **Add DeepSeek AI** | [GUIDE.md](GUIDE.md#deepseek-ai-integration-optional) |

- Feature engineering (35+ features)| **Troubleshoot service** | [DEPLOYMENT.md](DEPLOYMENT.md#troubleshooting) |

- Model training process| **Train ML model** | [GUIDE.md](GUIDE.md#ml-models) |

- Hidden gem detection algorithm| **Understand ML system** | [ML_SYSTEM_COMPLETE.md](ML_SYSTEM_COMPLETE.md) |

- Reinforcement learning engine

- Data pipeline---

- Performance metrics

## 💡 Features

**For developers and ML enthusiasts**

- ✅ Real-time crypto analysis with ML predictions

---- ✅ Hidden gem detection AI (DeepSeek powered)

- ✅ Weekly email reports (Monday 9 AM)

### **🤖 [DEEPSEEK.md](DEEPSEEK.md)** - DeepSeek AI Integration- ✅ On-demand learning (cost-effective)

How to add AI-powered sentiment analysis:- ✅ Interactive web dashboard

- Overview & features- ✅ Favorites tracking

- Setup instructions

- API configuration## 💰 Azure VM Recommendations

- Usage examples

- Cost optimization (24hr caching)| VM Type | vCPU | RAM | Cost/Month | Use Case |

- Integration with gem detection|---------|------|-----|------------|----------|

- Troubleshooting| **B2s** | 2 | 4GB | $40 | Recommended (smooth ML training) |

| **B1ms** | 1 | 2GB | $15 | Budget (slower but works) |

**Adds ±20 points to gem scores based on AI sentiment**

**Break-even**: 1 good trade per month covers costs

---

## ⚠️ Disclaimer

### **💾 [MODELS.md](MODELS.md)** - ML Models Explained

Understanding the models directory:**Not financial advice.** Educational purposes only. Cryptocurrency investments are highly risky. Always do your own research and never invest more than you can afford to lose.

- File types (.pkl, .joblib, .onnx)

- What each model does---

- Data flow diagram

- Model persistence**MIT License** • [GitHub](https://github.com/finn6666/CryptoApp)

- When models are retrained---
- File sizes & formats

**Technical reference for model files**

---

## ⚡ Quick Commands

### Most Common: Update Code on Azure VM
```bash
ssh your-username@your-vm-ip
cd ~/CryptoApp
git pull origin main
sudo systemctl restart cryptoapp
sudo systemctl status cryptoapp
```

### Check Service Status
```bash
sudo systemctl status cryptoapp
```

### View Logs
```bash
sudo journalctl -u cryptoapp -f
```

### Local Development
```bash
pip install -e .
python app.py
# Visit http://localhost:5001
```

### Train ML Model
```bash
# Via web UI: Click "Train ML Model" button
# OR via command line:
python -c "from ml.training_pipeline import CryptoMLPipeline; CryptoMLPipeline().train_and_evaluate()"
```

---

## 📁 Project Structure

```
CryptoApp/
├── docs/              ← YOU ARE HERE
│   ├── README.md      ← Documentation index (this file)
│   ├── DEPLOYMENT.md  ← Azure VM deployment & updates ⭐
│   ├── GUIDE.md       ← User guide & features
│   ├── ML_SYSTEM_COMPLETE.md  ← ML architecture
│   ├── DEEPSEEK.md    ← DeepSeek AI integration
│   └── MODELS.md      ← ML models explained
│
├── app.py             ← Main Flask application
├── ml/                ← Machine learning code
│   ├── enhanced_gem_detector.py  ← Hidden gem AI
│   ├── deepseek_analyzer.py      ← AI sentiment
│   ├── training_pipeline.py      ← Model training
│   └── weekly_report.py          ← Email reports
│
├── models/            ← Trained ML models (*.pkl)
├── src/               ← Core application code
│   ├── core/          ← Analysis engine
│   └── web/           ← Frontend (HTML/CSS/JS)
│
├── deploy/            ← Deployment configs
│   ├── cryptoapp.service       ← Systemd service
│   └── nginx-cryptoapp.conf    ← Nginx config
│
└── tests/             ← Unit tests
```

---

## 💡 Features Overview

✅ **Real-time Analysis** - Live crypto data with ML predictions  
✅ **Hidden Gem Detection** - AI identifies undervalued coins  
✅ **DeepSeek AI** - Sentiment analysis & reasoning  
✅ **Weekly Reports** - Top 3 opportunities via email (Monday 9 AM)  
✅ **Favorites Tracking** - Save & monitor your picks  
✅ **Interactive Dashboard** - Clean, modern web interface  
✅ **On-Demand Learning** - ML trains when you click (cost-effective)  

---

## 💰 Azure VM Costs

| VM Type | vCPU | RAM | Cost/Month | Recommended For |
|---------|------|-----|------------|-----------------|
| **B2s** | 2 | 4GB | ~$40 | Smooth ML training, production use |
| **B1ms** | 1 | 2GB | ~$15 | Budget option, slower but works |

**Break-even:** 1 good crypto trade per month covers costs 📈

---

## 🔍 Common Questions

**Q: How do I update my Azure VM with new code?**  
A: See [DEPLOYMENT.md - Quick Update](DEPLOYMENT.md#-quick-update-most-common)

**Q: Service won't start?**  
A: Check logs: `sudo journalctl -u cryptoapp -n 50` - See [Troubleshooting](DEPLOYMENT.md#-troubleshooting)

**Q: Browser can't connect?**  
A: Check Azure NSG has ports 80/443 open - See [DEPLOYMENT.md](DEPLOYMENT.md#8-azure-network-security-group-critical)

**Q: How do I add DeepSeek AI?**  
A: See [DEEPSEEK.md](DEEPSEEK.md#setup)

**Q: Where are my ML models stored?**  
A: `models/` directory - See [MODELS.md](MODELS.md)

**Q: How do I setup email reports?**  
A: See [GUIDE.md - Email Setup](GUIDE.md#email-setup-weekly-reports)

---

## 🛠️ For Developers

### Run Tests
```bash
pytest tests/ -v
```

### Code Structure
- **Frontend**: `src/web/static/js/` - Modular JavaScript
- **Backend**: `src/core/` - Analysis engine
- **ML**: `ml/` - Training & prediction
- **API**: `app.py` - Flask routes

### JavaScript Modules
See [src/web/static/js/README.md](../src/web/static/js/README.md) for frontend architecture.

---

## ⚠️ Disclaimer

**NOT FINANCIAL ADVICE.** This is an educational project for learning ML and cryptocurrency analysis. 

- Cryptocurrency investments are highly risky
- Past performance doesn't guarantee future results
- Always do your own research (DYOR)
- Never invest more than you can afford to lose

---

## 📞 Support

- **Documentation Issues?** Check [DEPLOYMENT.md](DEPLOYMENT.md#-troubleshooting)
- **Service Problems?** Run: `sudo journalctl -u cryptoapp -n 100`
- **GitHub:** [finn6666/CryptoApp](https://github.com/finn6666/CryptoApp)

---

**MIT License** • Last Updated: December 2025
