# 🚀 CryptoApp

AI-powered cryptocurrency analysis platform with hidden gem detection and weekly email reports.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## 📚 **[→ Full Documentation](docs/README.md)**

### Quick Links

| Need to... | Go to |
|------------|-------|
| **Update code on Azure VM** ⭐ | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#updates-most-common) |
| **First time setup & deployment** | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| **Setup Raspberry Pi SIEM** | [raspberry_pi/README.md](raspberry_pi/README.md) |
| **Understand the architecture** | [docs/README.md](docs/README.md#-architecture) |

---

## ⚡ Quick Start

```bash
# Install and run locally
pip install -e .
python app.py
# Visit http://localhost:5001
```

## ✨ Features

- 📊 **Real-time Analysis** - CoinMarketCap API with 16+ alpha signals
- 💎 **Hidden Gem Detection** - ML-powered ranking (1-10 score)
- 🧠 **Inline ML Analysis** - Detailed predictions and reasoning displayed directly on each coin card
- 🤖 **DeepSeek AI Sentiment** - Optional AI-powered sentiment scores with concise, formatted insights
- 📈 **Simple RL Learning** - Learns from your trades via Trade Journal
- 📧 **Weekly Reports** - Top 3 opportunities via email (Monday 9 AM)
- ⭐ **Favorites** - Save and track your picks
- 🎨 **Modern UI** - Clean, responsive cards with inline analysis and auto-refresh

## 🚀 Update Azure VM

```bash
ssh your-username@your-vm-ip
cd ~/CryptoApp
git pull origin main
sudo systemctl restart cryptoapp
sudo systemctl status cryptoapp
```

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete guide.

## 💰 Cost

- **Azure VM B2s**: ~$40/month (recommended)
- **Azure VM B1ms**: ~$15/month (budget)
- **Break-even**: 1 good trade per month

## ⚠️ Disclaimer

**NOT FINANCIAL ADVICE.** Educational purposes only. Cryptocurrency investments are highly risky. Always do your own research and never invest more than you can afford to lose.

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/finn6666/CryptoApp/issues)
- **Service problems**: `sudo journalctl -u cryptoapp -n 100`

---

**MIT License** • [Full Documentation](docs/README.md)
