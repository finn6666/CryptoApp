# 🚀 Crypto Investment Analyzer

A comprehensive cryptocurrency analysis tool with both **CLI** and **Web interfaces** that helps you identify attractive investment opportunities using live market data.

## 🌟 Features

- **🌐 Web Dashboard**: Dark theme web interface with real-time data refresh
- **💻 CLI Interface**: Rich, colorful terminal displays with interactive menus  
- **📊 Live Data Integration**: Real-time data from CoinGecko API
- **🔍 Smart Scoring System**: Ranks cryptocurrencies using attractiveness scores (1-10)
- **📈 Multi-Category Analysis**: Current coins, new entries, and upcoming opportunities
- **🎨 Beautiful UI**: Dark theme web interface + rich CLI formatting
- **🔄 Auto-Refresh**: Live market data updates every 5 minutes
- **📱 Responsive Design**: Works on desktop, tablet, and mobile

## 📊 What It Analyzes

### Current Coins
- Established cryptocurrencies currently trading
- Market cap rankings and price performance
- 24-hour price changes across multiple currencies

### New Coins
- Recently launched tokens with high growth potential
- Early entry opportunities with significant upside
- Risk assessment for emerging projects

### Upcoming Coins
- Pre-launch opportunities with presale access
- Discount percentages and expected ROI
- Revolutionary technologies and partnerships

## 🛠️ Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/CryptoApp.git
   cd CryptoApp
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**:
   ```bash
   # Web Interface (Recommended)
   python app.py
   # Then visit: http://localhost:5000
   
   # CLI Interface  
   python main.py
   ```

## 🚀 Usage

### 🌐 Web Interface (Recommended)
```bash
python app.py
```
**Visit: http://localhost:5000**

Features:
- **Dark theme UI** with modern design
- **Real-time data refresh** - Click "🔄 Refresh Now"  
- **Live market stats** - Total coins, trending up, high potential
- **Interactive tables** with hover effects
- **Responsive design** for all devices
- **Auto-refresh** every 5 minutes

### 💻 CLI Interface
```bash
python main.py                 # Full analysis report
python main.py --top 10        # Top 10 coins only
python main.py --live          # Fetch fresh data first
```

**CLI Features:**
- Rich colorful terminal displays
- Interactive menu system
- ASCII charts and visualizations
- Multiple filtering options

## � Screenshots

### 🌐 Web Interface
```
🚀 Investment Analyzer
├── � Live Stats Dashboard
│   ├── Total Coins: 100
│   ├── Active Coins: 85  
│   ├── High Potential: 15
│   └── Trending Up: 32
│
├── 📈 Real-Time Crypto Table
│   ├── Symbol | Name | Score | Price | 24h Change
│   ├── BTC    | Bitcoin | 8.5 | $43,250 | +2.1%
│   ├── ETH    | Ethereum | 8.8 | $2,554 | +1.8%
│   └── ... (sortable & interactive)
│
└── 🔄 Auto-refresh every 5min + manual refresh
```

### 💻 CLI Interface
```
🚀 CRYPTO INVESTMENT ANALYZER 🚀
📊 PORTFOLIO SUMMARY
• Total Coins: 100 | High Potential (8.0+): 15
• Trending Up: 32 | Current Trading: 85

🏆 TOP OPPORTUNITIES
Symbol │ Name     │ Score │ Price    │ 24h Change │ Rank
BTC    │ Bitcoin  │  8.5  │ $43,250  │ +2.1%      │ #1
ETH    │ Ethereum │  8.8  │ $2,554   │ +1.8%      │ #2
```

## 🔧 Project Structure

```
CryptoApp/
├── main.py                    # CLI entry point
├── app.py                     # Web app entry point  
├── pyproject.toml             # Project configuration
├── requirements.txt           # Dependencies
│
├── src/                       # Source code
│   ├── core/                 # Business logic
│   │   ├── crypto_analyzer.py # Analysis engine
│   │   ├── crypto_visualizer.py # Data visualization
│   │   └── live_data_fetcher.py # API integration
│   │
│   ├── cli/                  # Command line interface
│   │   └── crypto_display.py # Rich CLI formatting
│   │
│   └── web/                  # Web interface
│       ├── web_app.py       # Flask routes
│       └── templates/
│           └── index.html    # Dark theme UI
│
├── data/
│   └── live_api.json        # Live market data
│
├── tests/                    # Test files
├── docs/                     # Documentation
└── scripts/                  # Utility scripts
```

## 💎 Key Components

### 🌐 Web Interface (`app.py`)
- **Flask-based** web application 
- **Dark theme** with gradient backgrounds
- **Real-time refresh** with live API integration
- **Responsive design** for all screen sizes
- **Interactive elements** with hover effects

### 💻 CLI Interface (`src/cli/crypto_display.py`)
- **Rich terminal UI** with colors and formatting
- **Interactive menus** and command options
- **ASCII charts** and data visualization
- **Multiple display modes** and filtering

### 🔧 Core Engine (`src/core/crypto_analyzer.py`)
- **Smart filtering** by score, status, and risk
- **Live data processing** from CoinGecko API
- **Investment opportunity detection**
- **Multi-category analysis**

### 📡 Live Data (`src/core/live_data_fetcher.py`)
- **CoinGecko API integration**
- **Real-time price updates** 
- **Low-cap coin focus**
- **Automatic data refresh**

## 🎯 Investment Categories

### 🏆 Top Opportunities (Score 8.5+)
High-quality projects with strong fundamentals and growth potential

### 💎 Upcoming Presales (Score 9.0+)
Early access opportunities with significant discounts and high expected returns

### 🚀 Trending Coins
Currently gaining momentum with positive 24-hour price performance

### 🛡️ Lower Risk Options
Established cryptocurrencies with proven track records (Top 20 market cap)

## 📊 Scoring Methodology

Attractiveness scores (1-10) based on:
- **Technology Strength** (2.5 pts)
- **Market Position** (2.5 pts)  
- **Growth Potential** (2.5 pts)
- **Risk/Reward Ratio** (2.5 pts)

## 🔮 Data Sources

Uses live cryptocurrency data in `data/live_api.json` fetched from:
- **CoinGecko API** - Real-time prices and market data
- **Live market updates** - Fresh data on each refresh
- **Low-cap focus** - Specialized filtering for emerging coins

Future integrations may include:
- Social sentiment analysis
- On-chain metrics
- Advanced technical indicators

## 🚀 Live Demo

### Web Interface
1. **Run**: `python app.py`
2. **Visit**: http://localhost:5000
3. **Click**: "🔄 Refresh Now" for live data
4. **Enjoy**: Dark theme crypto dashboard!

### CLI Interface  
1. **Run**: `python main.py`
2. **Explore**: Interactive menus and rich displays
3. **Filter**: By score, status, and categories

## 🔄 Live Data Features

- **Real-time prices** from CoinGecko API
- **Auto-refresh** every 5 minutes in web UI
- **Manual refresh** via CLI or web button
- **Low-cap focus** for emerging opportunities
- **Cache management** for optimal performance

## 🚀 Future Enhancements

- [x] ~~Live API integration~~ ✅ **DONE**
- [x] ~~Web dashboard~~ ✅ **DONE**  
- [x] ~~Dark theme UI~~ ✅ **DONE**
- [ ] Portfolio tracking & watchlists
- [ ] Price alerts & notifications  
- [ ] Advanced charting with candlesticks
- [ ] Social sentiment analysis
- [ ] Mobile PWA version
- [ ] User authentication & saved preferences

## 📝 License

Open source - feel free to modify and enhance!

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional data sources
- Enhanced visualization
- Web interface
- Mobile compatibility
- Advanced analytics

---

**⚠️ Disclaimer**: This tool is for educational and research purposes only. Always do your own research before making investment decisions. Cryptocurrency investments carry significant risk.