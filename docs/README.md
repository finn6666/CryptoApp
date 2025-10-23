# 🚀 Crypto Investment Analyzer

A cryptocurrency analysis tool with **CLI** and **Web interfaces** that identifies investment opportunities using live market data.

## 🌟 Features

- **🌐 Web Dashboard**: Dark theme with real-time data refresh
- **💻 CLI Interface**: Rich terminal displays  
- **📊 Live Data**: Real-time CoinGecko API integration
- **🔍 Smart Scoring**: Ranks cryptocurrencies (1-10 attractiveness score)
- **📱 Responsive**: Works on desktop, tablet, mobile

## 🛠️ Quick Start

```bash
git clone https://github.com/your-username/CryptoApp.git
cd CryptoApp
pip install -r requirements.txt

# Web Interface (Recommended)
python app.py
# Visit: http://localhost:5000

# CLI Interface  
python main.py
```

## 🎯 What It Does

- **Analyzes 100+ cryptocurrencies** with live market data
- **Scores investment potential** (1-10 scale)
- **Focuses on low-cap gems** (under $1B market cap)
- **Provides risk assessment** and investment highlights
- **Auto-refreshes** every 5 minutes

## 📊 Screenshots

### Web Interface
Dark theme dashboard with live crypto tables, price changes, and refresh button.

### CLI Interface
```
🚀 CRYPTO INVESTMENT ANALYZER 🚀
Symbol │ Name     │ Score │ Price    │ 24h Change
BTC    │ Bitcoin  │  8.5  │ $43,250  │ +2.1%
ETH    │ Ethereum │  8.8  │ $2,554   │ +1.8%
```

## 🔧 Project Structure

```
CryptoApp/
├── main.py                    # CLI entry point
├── app.py                     # Web app entry point
├── src/core/                  # Analysis engine
├── src/web/templates/         # Dark theme UI
├── data/live_api.json         # Live market data
└── tests/                     # Test files
```

## 🚀 Usage

```bash
python app.py                  # Web interface
python main.py                 # CLI interface
python main.py --live          # Fetch fresh data
```

**⚠️ Disclaimer**: For educational purposes only. Always research before investing.