# CryptoApp - Complete Guide

## Quick Start

```bash
# Install and run
pip install -e .
python app.py
# Visit http://localhost:5001
```

## Features

- **Real-time Analysis**: Live crypto data with ML-powered insights
- **Hidden Gem Detection**: AI identifies undervalued coins
- **Weekly Email Reports**: Top 3 opportunities sent Monday 9 AM
- **On-Demand Learning**: ML only runs when you refresh (cost-effective)

## Email Setup (Weekly Reports)

```bash
# Set environment variables
export REPORT_EMAIL_FROM="your-email@gmail.com"
export REPORT_EMAIL_TO="your-email@gmail.com"
export SMTP_PASSWORD="your-gmail-app-password"
```

**Gmail App Password**: Google Account → Security → 2-Step Verification → App Passwords

## DeepSeek AI Integration (Optional)

Enhance gem detection with AI-powered sentiment analysis.

**Setup:**
1. Get API key from https://platform.deepseek.com/
2. Add to `.env`: `DEEPSEEK_API_KEY=your-key-here`
3. Restart application

**Features:**
- Market sentiment scoring (-1 to 1)
- Technology assessment
- Risk evaluation
- 24-hour caching (reduces API calls)

**Cost:** ~$0.60/month with caching

**Usage:**
- Automatically enhances gem scores when API key is configured
- Adds up to ±20 points to gem score based on sentiment
- Falls back gracefully if API unavailable

## Azure Deployment

### Resource Usage
- **ML Training**: 5-15 minutes, only runs on-demand
- **Weekly Report**: ~5 seconds once per week
- **Idle**: Minimal resources (<5% CPU)

**Break-even**: 1 successful trade/month covers costs

## Development

```bash
# Daily workflow
python app.py                              # Run web app
python -m pytest tests/ -v                 # Run tests

# Git workflow  
git pull && git add . && git commit -m "msg" && git push
```

## Key Files

- `app.py` - Main Flask application
- `src/core/crypto_analyzer.py` - Analysis engine
- `ml/enhanced_gem_detector.py` - Hidden gem AI
- `ml/weekly_report.py` - Email report system
- `ml/scheduler.py` - Weekly automation

## ML Models

Models saved in `models/` directory:
- `crypto_model.pkl` - Price predictor
- `gem_detector.pkl` - Hidden gem classifier
- `scaler.pkl` - Feature normalizer

**Training**: Sunday 2 AM (automatic) or click "Train Model" button

## Cost Optimization

✅ **Already Optimized**: On-demand model minimizes costs
- Only runs on manual refresh
- Weekly training (not continuous)
- Models persist (fast reload)

## FAQ

**Q: Will RL/ML work with infrequent use?**  
A: Yes! Weekly training is sufficient. Models learn from historical data.

**Q: Do I need the tests directory?**  
A: Optional for personal use, but recommended for safety before deployments.

**Q: Can I use other AI models (DeepSeek)?**  
A: Yes! DeepSeek is now integrated. Get API key from https://platform.deepseek.com/ (~$0.60/month). See "DeepSeek AI Integration" section above.

**Q: How do model files work?**  
A: `.pkl` files save trained models to disk. Load once, predict many times.

## Troubleshooting

**Email not sending**: Check environment variables are set  
**Model not found**: Click "Train Model" in web interface  
**High costs**: Downgrade to B1ms VM if underutilized

## Architecture

```
Data Collection → Feature Engineering → ML Training → Predictions → Dashboard
     ↓                    ↓                  ↓             ↓            ↓
  CoinGecko          RSI, MACD         RandomForest    Gem Scores   Web UI
```

## Disclaimer

**Not financial advice.** Educational purposes only. Crypto is highly volatile. Always do your own research. You may lose money.
