// UI Components and HTML Generators

// Generate AI analysis HTML section
function generateAISentimentHTML(coin, coinId) {
    // Check for new ai_analysis format
    if (coin.ai_analysis) {
        const analysis = coin.ai_analysis;
        const recommendationClass = analysis.recommendation === 'BUY' ? 'positive' : 
                                   analysis.recommendation === 'SELL' || analysis.recommendation === 'AVOID' ? 'negative' : 'neutral';
        
        return `
            <div class="ai-sentiment-section">
                <button class="ml-reasoning-toggle" onclick="toggleAISentiment('${coinId}')">
                    <span>🤖 ${analysis.analysis_type || 'AI Analysis'}</span>
                    <span class="arrow">▼</span>
                </button>
                <div id="ai-sentiment-${coinId}" class="ml-reasoning-content" style="display: none;">
                    <div class="ml-prediction-detail">
                        <div class="prediction-row">
                            <span class="label">Recommendation:</span>
                            <span class="value ${recommendationClass}"><strong>${analysis.recommendation}</strong></span>
                        </div>
                        <div class="prediction-row">
                            <span class="label">Confidence:</span>
                            <span class="value">${analysis.confidence}</span>
                        </div>
                        ${analysis.summary ? `
                            <div class="sentiment-reasoning">
                                <strong>Analysis:</strong>
                                <p>${analysis.summary}</p>
                            </div>
                        ` : ''}
                        ${analysis.risk_level ? `
                            <div class="prediction-row">
                                <span class="label">Risk Level:</span>
                                <span class="value">${analysis.risk_level}</span>
                            </div>
                        ` : ''}
                        ${analysis.timing_score ? `
                            <div class="prediction-row">
                                <span class="label">Timing:</span>
                                <span class="value">${analysis.timing_score}</span>
                            </div>
                        ` : ''}
                        ${analysis.position_size ? `
                            <div class="prediction-row">
                                <span class="label">Position Size:</span>
                                <span class="value">${analysis.position_size}</span>
                            </div>
                        ` : ''}
                        ${analysis.gem_score ? `
                            <div class="prediction-row">
                                <span class="label">Gem Score:</span>
                                <span class="value">${analysis.gem_score}</span>
                            </div>
                        ` : ''}
                        ${analysis.prediction ? `
                            <div class="prediction-row">
                                <span class="label">Prediction:</span>
                                <span class="value">${analysis.prediction}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }
    
    // Fallback to old ai_sentiment format
    if (!coin.ai_sentiment || !coin.ai_sentiment.key_points || coin.ai_sentiment.key_points.length === 0) {
        return '';
    }

    const sentiment = coin.ai_sentiment;
    const sentimentLabel = sentiment.sentiment || 'Neutral';
    const sentimentClass = sentimentLabel.toLowerCase() === 'bullish' ? 'positive' : 
                           sentimentLabel.toLowerCase() === 'bearish' ? 'negative' : 'neutral';
    const scorePercent = sentiment.score ? (sentiment.score * 10).toFixed(0) : 'N/A';
    const confidencePercent = sentiment.confidence ? (sentiment.confidence * 100).toFixed(0) : 'N/A';
    
    return `
        <div class="ai-sentiment-section">
            <button class="ml-reasoning-toggle" onclick="toggleAISentiment('${coinId}')">
                <span>🧠 AI Sentiment (DeepSeek)</span>
                <span class="arrow">▼</span>
            </button>
            <div id="ai-sentiment-${coinId}" class="ml-reasoning-content" style="display: none;">
                <div class="ml-prediction-detail">
                    <div class="prediction-row">
                        <span class="label">Sentiment:</span>
                        <span class="value ${sentimentClass}">${sentimentLabel.toUpperCase()}</span>
                    </div>
                    <div class="prediction-row">
                        <span class="label">Score:</span>
                        <span class="value">${scorePercent}/10</span>
                    </div>
                    <div class="prediction-row">
                        <span class="label">Confidence:</span>
                        <span class="value">${confidencePercent}%</span>
                    </div>
                    ${sentiment.key_points && sentiment.key_points.length > 0 ? `
                        <div class="sentiment-points">
                            <strong>Key Points:</strong>
                            <ul>
                                ${sentiment.key_points.map(point => `<li>${point}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    ${sentiment.reasoning ? `
                        <div class="sentiment-reasoning">
                            <strong>Analysis:</strong>
                            <p>${sentiment.reasoning}</p>
                        </div>
                    ` : ''}
                </div>
            </div>
        </div>
    `;
}

// Generate ML reasoning HTML section
function generateMLReasoningHTML(coin, coinId, mlEnabled) {
    // Don't show this section anymore - we're using ai_analysis now in generateAISentimentHTML
    return '';
}

// Format price in GBP
function formatPrice(priceUSD) {
    if (!priceUSD) return 'N/A';
    
    const usdToGbp = 0.8;
    const priceInGbp = priceUSD * usdToGbp;
    
    if (priceInGbp < 0.01) {
        return `£${priceInGbp.toPrecision(2)}`;
    }
    return `£${priceInGbp.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 4})}`;
}

// Get score class and label
function getScoreInfo(score) {
    const displayScore = score || 0;
    const scorePercentage = (displayScore / 10) * 100;
    
    let scoreClass = 'score-low';
    let scoreLabel = 'Low Potential';
    
    if (displayScore >= 8) {
        scoreClass = 'score-high';
        scoreLabel = 'High Potential';
    } else if (displayScore >= 6) {
        scoreClass = 'score-medium';
        scoreLabel = 'Medium Potential';
    }
    
    return { displayScore, scorePercentage, scoreClass, scoreLabel };
}

// Toggle functions
function toggleAISentiment(coinId) {
    const content = document.getElementById(`ai-sentiment-${coinId}`);
    const button = content.previousElementSibling;
    const arrow = button.querySelector('.arrow');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        arrow.textContent = '▲';
    } else {
        content.style.display = 'none';
        arrow.textContent = '▼';
    }
}

function toggleMLReasoning(coinId) {
    const content = document.getElementById(`ml-reasoning-${coinId}`);
    const button = content.previousElementSibling;
    const arrow = button.querySelector('.arrow');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        arrow.textContent = '▲';
    } else {
        content.style.display = 'none';
        arrow.textContent = '▼';
    }
}

function toggleMLStatusDetails() {
    const detailsDiv = document.getElementById('mlStatusDetails');
    detailsDiv.style.display = detailsDiv.style.display === 'none' ? 'block' : 'none';
}

// Status notification
function showStatus(message, type = 'info', duration = 4000) {
    const container = document.getElementById('statusContainer');
    const toast = document.getElementById('statusToast');
    const messageEl = document.getElementById('statusMessage');
    
    messageEl.textContent = message;
    toast.className = `status-toast ${type}`;
    
    container.style.display = 'block';
    setTimeout(() => toast.classList.add('show'), 100);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            container.style.display = 'none';
        }, 300);
    }, duration);
}
