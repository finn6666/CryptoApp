# 🚀 Crypto Investment Analyzer

A comprehensive cryptocurrency analysis tool that helps you identify attractive investment opportunities across current, new, and upcoming coins.

## 🌟 Features

- **Smart Scoring System**: Ranks cryptocurrencies using attractiveness scores (1-10)
- **Multi-Category Analysis**: Covers current trading coins, new market entries, and upcoming presales
- **Beautiful CLI Interface**: Rich, colorful terminal displays with tables and charts
- **Investment Insights**: Highlights key features and investment opportunities for each coin
- **Risk Assessment**: Categorizes coins by risk level and market maturity
- **Visual Analytics**: ASCII charts showing price changes, rankings, and distribution
- **Interactive Mode**: Menu-driven interface for exploring different coin categories

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

## 🛠️ Installation

1. **Clone or download** the project
2. **Set up virtual environment**:
   ```bash
   cd CryptoApp
   python -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # or
   .venv\Scripts\activate     # On Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install rich tabulate colorama requests
   ```

## 🚀 Usage

### Full Analysis Report
```bash
python main.py
```
Shows complete analysis with:
- Top investment opportunities
- Upcoming presale opportunities  
- Trending coins (24h gainers)
- Established lower-risk options
- Visual charts and statistics

### Interactive Mode
```bash
python main.py --mode interactive
```
Provides menu-driven interface to:
- Filter coins by status (current/new/upcoming)
- View coins by attractiveness score
- Explore specific categories
- Refresh data

### Command Options
```bash
python main.py --help
```

## 📈 Sample Output

```
🚀 CRYPTO INVESTMENT ANALYZER 🚀
Find the most attractive cryptocurrency opportunities

📊 PORTFOLIO SUMMARY
• Total Coins Analyzed: 8
• Current Trading: 5
• Upcoming Launches: 2
• High Potential (8.0+ Score): 2

🏆 HIGHEST RATED COINS
Symbol │ Name        │ Score │ Price      │ 24h Change │ Highlights
AIPR   │ AI Protocol │  9.3  │ $0.08      │ N/A        │ AI trend leader, 50% presale bonus
ETH    │ Ethereum    │  8.8  │ $2,554.32  │ +1.8%      │ DeFi ecosystem, Smart contracts
```

## 🔧 Project Structure

```
CryptoApp/
├── main.py              # Entry point and CLI interface
├── crypto_analyzer.py   # Core data processing and filtering
├── crypto_display.py    # Rich terminal UI and formatting
├── crypto_visualizer.py # ASCII charts and data visualization
├── api.json            # Cryptocurrency data (your dataset)
├── pyproject.toml      # Project configuration and dependencies
└── README.md           # This file
```

## 💎 Key Components

### CryptoAnalyzer
- Loads and parses cryptocurrency data
- Implements filtering by score, status, and risk level
- Provides methods for trending, upcoming, and high-potential coins

### CryptoDisplay  
- Beautiful Rich-based terminal interface
- Color-coded tables and panels
- Interactive menu system
- Multiple display modes

### CryptoVisualizer
- ASCII-based charts for data visualization
- Score comparisons and price change charts
- Status distribution and market cap rankings

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

Currently uses curated dataset in `api.json`. Future versions may integrate:
- Live CoinGecko API feeds
- Real-time price updates
- Social sentiment analysis
- On-chain metrics

## 🚀 Future Enhancements

- [ ] Live API integration
- [ ] Portfolio tracking
- [ ] Price alerts
- [ ] Web dashboard
- [ ] Mobile app
- [ ] Advanced charting
- [ ] Social sentiment analysis

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