# CryptoApp Documentation

AI-powered crypto gem detection using CoinMarketCap API, ML analysis, and Simple RL learning.

---

## ⚡ Quick Start

**Run locally:**
```bash
python3 app.py  # http://localhost:5001
```

**Update Azure VM:**
```bash
cd ~/CryptoApp && git pull && sudo systemctl restart cryptoapp
```

**Check status:**
```bash
sudo systemctl status cryptoapp
sudo journalctl -u cryptoapp -f  # View logs
```

---

## 🔑 Setup

### 1. API Keys (.env file)

```bash
COINMARKETCAP_API_KEY=your-cmc-key-here
DEEPSEEK_API_KEY=your-deepseek-key-here  # Optional
```

- **CoinMarketCap**: Get from https://coinmarketcap.com/api/ (REQUIRED)
- **DeepSeek AI**: Get from https://platform.deepseek.com/ (Optional - adds AI sentiment analysis)

### 2. Email Reports (Optional)

```bash
REPORT_EMAIL_FROM=your-email@gmail.com
REPORT_EMAIL_TO=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
```

Gmail App Password: Google Account → Security → 2-Step Verification → App Passwords

---

## 💡 Features

- **CoinMarketCap Integration** - Professional crypto data API
- **16+ Alpha Signals** - Whale accumulation, quiet accumulation, early mover advantage
- **DeepSeek AI** - Optional sentiment analysis (24hr cache, ~$0.60/month)
- **Simple RL** - Learns from your trades via Trade Journal page
- **Trade Journal** - Report trades at /trades to teach RL system
- **Favorites** - Track specific coins
- **Auto-refresh** - Updates every 5 minutes

---

## 📊 Trade Journal & RL

Visit `/trades` page to report your trading outcomes:

1. Enter symbol (BTC, ETH, etc. - any symbol works)
2. Entry price, exit price, days held
3. Optional notes about why you made the trade
4. RL system learns profit patterns (doesn't validate symbols)

**How RL learns:** Tracks feature patterns that led to profitable vs unprofitable trades, adjusts future recommendations.

---

## 🏗️ Architecture

```
┌─────────────────┐
│ CoinMarketCap   │ ← API calls (your paid key)
│     API         │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────┐
│  LiveDataFetcher                    │
│  • Top coins by market cap          │
│  • Trending/gainers                 │
│  • New listings                     │
└────────┬────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────┐
│  AdvancedAlphaFeatures              │
│  • 16 signals (whale, quiet, etc.)  │
│  • Early mover advantage            │
│  • Smart money detection            │
└────────┬────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────┐
│  ML Models (RandomForest/GBM)       │
│  • Predict gem potential            │
│  • Score: 1-10                      │
└────────┬────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────┐
│  DeepSeek AI (Optional)             │
│  • Sentiment: -1 to +1              │
│  • Confidence score                 │
│  • Adjusts ±20 points               │
└────────┬────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────┐
│  Simple RL (Q-Learning)             │
│  • Boost based on past trades       │
│  • JSON persistence                 │
│  • No PyTorch dependency            │
└────────┬────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────┐
│  Final Score → Dashboard            │
└─────────────────────────────────────┘
```

---

## 🚀 Azure Deployment

### First-Time Setup

**1. Create VM**
```bash
# Azure Portal: Ubuntu 22.04 LTS, B2s (2 vCPU, 4GB RAM)
# Open ports: 22 (SSH), 80 (HTTP), 443 (HTTPS)
```

**2. SSH & Install**
```bash
ssh azureuser@your-vm-ip

# Install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv nginx git -y

# Clone repo
cd ~
git clone https://github.com/yourusername/CryptoApp.git
cd CryptoApp

# Setup Python
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

**3. Configure .env**
```bash
nano .env
# Add your API keys (see Setup section above)
```

**4. Setup systemd service**
```bash
sudo cp deploy/cryptoapp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cryptoapp
sudo systemctl start cryptoapp
```

**5. Setup Nginx**
```bash
sudo cp deploy/nginx-cryptoapp.conf /etc/nginx/sites-available/cryptoapp
sudo ln -s /etc/nginx/sites-available/cryptoapp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**6. SSL (Optional)**
```bash
sudo bash deploy/setup-ssl-rhel.sh your-domain.com
```

### Updates (Most Common)

```bash
cd ~/CryptoApp
git pull
sudo systemctl restart cryptoapp
```

---

## 💰 Costs

| Item | Monthly Cost |
|------|-------------|
| Azure B2s VM (2 vCPU, 4GB) | ~$40 |
| CoinMarketCap Basic Plan | Free tier available |
| DeepSeek AI (optional, cached) | ~$0.60 |
| **Total** | **~$40-45** |

**Note:** B1ms (1 vCPU, 2GB) works for ~$15/month but ML may be slower.

---

## 📁 Project Structure

```
CryptoApp/
├── app.py                 Main Flask application
├── ml/
│   ├── enhanced_gem_detector.py    Gem detection + RL
│   ├── advanced_alpha_features.py  16+ signals
│   ├── simple_rl.py               Q-learning (240 lines)
│   ├── deepseek_analyzer.py       AI sentiment
│   └── data_pipeline.py           Training data
├── src/
│   ├── core/
│   │   ├── config.py              CMC API config
│   │   └── live_data_fetcher.py   CMC data fetching
│   └── web/
│       ├── static/                CSS/JS
│       └── templates/             HTML (index, trades)
├── models/                        Saved .pkl models
├── data/                          API cache + favorites
├── deploy/                        systemd, nginx configs
└── docs/                          This file
```

---

## 🔧 Troubleshooting

**App not starting:**
```bash
sudo journalctl -u cryptoapp -n 50  # Check logs
```

**No data showing:**
- Check CoinMarketCap API key in .env
- Check logs for API errors
- Verify internet connection

**RL not learning:**
- Visit /trades page to report trades
- Check models/rl_simple_learner.json exists
- Verify write permissions in models/ directory

**DeepSeek not working:**
- API key correct in .env?
- Check data/deepseek_cache/ for cached responses
- DeepSeek is optional - app works without it

---

## 📝 Model Files

`models/` directory contains:

- **crypto_model.pkl** - RandomForest classifier
- **scaler.pkl** - Feature normalization
- **hidden_gem_detector.pkl** - Gem detection model
- **rl_simple_learner.json** - RL learned weights + trade history

Models auto-retrain when missing. First run may take 2-3 minutes.

---

## ⚠️ Disclaimer

This is educational software. Not financial advice. Trade at your own risk.
