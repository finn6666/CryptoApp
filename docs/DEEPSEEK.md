# DeepSeek AI Integration

AI-powered sentiment analysis to enhance cryptocurrency gem detection.

## Overview

The DeepSeek integration provides intelligent sentiment analysis for cryptocurrencies, enhancing gem scores with AI-driven insights about market sentiment, technology assessment, and risk evaluation.

## Features

- **Sentiment Scoring**: AI analyzes market position and assigns sentiment (-1 to 1)
- **Confidence Levels**: Each analysis includes confidence metric (0 to 1)
- **Key Insights**: 3 key points about technology, adoption, and risks
- **Smart Caching**: 24-hour cache to minimize API calls and costs
- **Score Enhancement**: Adds up to ±20 points to gem scores
- **Graceful Fallback**: Works without API key (uses base scores only)

## Setup

### 1. Get API Key

1. Visit https://platform.deepseek.com/
2. Sign up for an account
3. Navigate to API Keys section
4. Create a new API key

### 2. Configure Environment

Add to your `.env` file:

```bash
DEEPSEEK_API_KEY=your-api-key-here
```

### 3. Restart Application

```bash
python app.py
```

## Usage

### Automatic Integration

Once configured, DeepSeek automatically enhances gem detection:

```python
from ml.deepseek_analyzer import deepseek_analyzer
from ml.enhanced_gem_detector import HiddenGemDetector

# Initialize gem detector (DeepSeek integration is automatic)
gem_detector = HiddenGemDetector()

# Scan for gems (now with AI sentiment enhancement)
results = gem_detector.scan_for_hidden_gems(limit=10)
```

### Manual Sentiment Analysis

```python
from ml.deepseek_analyzer import deepseek_analyzer

# Analyze a specific coin
coin_data = {
    'symbol': 'BTC',
    'name': 'Bitcoin',
    'price': 50000,
    'market_cap_rank': 1,
    'price_change_24h': 2.5
}

sentiment = deepseek_analyzer.analyze_coin_sentiment(coin_data)

if sentiment:
    print(f"Sentiment: {sentiment.score}")
    print(f"Confidence: {sentiment.confidence}")
    print(f"Key Points: {sentiment.key_points}")
    print(f"Reasoning: {sentiment.reasoning}")
```

### Enhance Gem Scores

```python
# Enhance an existing gem score with AI sentiment
base_score = 75.0
enhanced_data = deepseek_analyzer.enhance_gem_score(base_score, coin_data)

print(f"Base Score: {enhanced_data['base_score']}")
print(f"Enhanced Score: {enhanced_data['enhanced_score']}")
print(f"Sentiment Boost: {enhanced_data['sentiment_boost']}")
```

## Testing

Run the example script to test your integration:

```bash
python -m ml.deepseek_example
```

This will:
1. Check API configuration
2. Analyze a sample coin (Bitcoin)
3. Show sentiment results
4. Demonstrate score enhancement
5. Display cache statistics

## Cost Management

### Caching Strategy

- **Cache Duration**: 24 hours per symbol
- **Cache Location**: `data/deepseek_cache/`
- **Automatic Expiry**: Old cache files are ignored

### API Usage

- **Per Analysis**: ~500 tokens (~$0.01)
- **With Caching**: ~30-50 analyses/month
- **Estimated Cost**: $0.60/month

### Clear Cache

```python
# Clear cache for specific symbol
deepseek_analyzer.clear_cache('BTC')

# Clear all cache
deepseek_analyzer.clear_cache()
```

## How It Works

### 1. Sentiment Analysis

DeepSeek analyzes:
- Market position and competition
- Technology and use case
- Recent developments
- Risk factors for small-cap cryptos

### 2. Score Enhancement

```
Enhanced Score = Base Score + (Sentiment × 20 × Confidence)

Where:
- Base Score: 0-100 (from gem detector)
- Sentiment: -1 to 1 (AI sentiment)
- Confidence: 0-1 (AI confidence level)
- Maximum boost: ±20 points
```

### 3. Integration Flow

```
Coin Data
    ↓
Check Cache (24h)
    ↓
If Expired → DeepSeek API
    ↓
Sentiment Analysis
    ↓
Cache Result
    ↓
Enhance Gem Score
    ↓
Return Enhanced Data
```

## API Response Format

```json
{
    "sentiment_score": 0.65,
    "confidence": 0.80,
    "key_points": [
        "Strong institutional adoption",
        "Mature technology with proven security",
        "Regulatory clarity improving"
    ],
    "reasoning": "Bitcoin maintains strong market position with increasing institutional interest and regulatory acceptance, though volatility remains a consideration."
}
```

## Troubleshooting

### API Key Not Working

1. Check `.env` file has correct key
2. Verify no extra spaces in API key
3. Restart application after adding key
4. Check DeepSeek account is active

### High API Costs

1. Check cache is working: `deepseek_analyzer.get_usage_stats()`
2. Increase cache TTL if needed (default: 24 hours)
3. Clear old cache: `deepseek_analyzer.clear_cache()`

### Sentiment Analysis Failed

- Check internet connection
- Verify API key is valid
- Check DeepSeek API status
- Review logs for detailed errors

### No Sentiment Data

If API key not configured:
- Application continues to work normally
- Uses base gem scores without AI enhancement
- No errors thrown (graceful fallback)

## Configuration Options

Edit `ml/deepseek_analyzer.py` to customize:

```python
class DeepSeekAnalyzer:
    def __init__(self):
        self.model = "deepseek-chat"      # Model to use
        self.cache_ttl_hours = 24          # Cache duration
        # ... other settings
```

## Monitoring

Get usage statistics:

```python
stats = deepseek_analyzer.get_usage_stats()

print(f"Cached Symbols: {stats['cached_symbols']}")
print(f"Cache Size: {stats['cache_size_kb']} KB")
print(f"Monthly Cost: ${stats['estimated_monthly_cost_usd']}")
```

## Security

- ✅ API key stored in `.env` (not in code)
- ✅ `.env` file in `.gitignore` (not committed)
- ✅ Cache stored locally (not exposed)
- ✅ Rate limiting through caching

## Future Enhancements

Potential improvements:
- [ ] Multi-source sentiment (Twitter, Reddit, news)
- [ ] Historical sentiment tracking
- [ ] Sentiment trend analysis
- [ ] Custom sentiment weights per coin category

---

**Cost**: ~$0.60/month  
**Setup Time**: 2 minutes  
**Value**: Enhanced gem detection with AI insights
