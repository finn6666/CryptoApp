// UI Components and HTML Generators

// Generate combined AI analysis HTML section (ML + DeepSeek) - Always visible, compact design
function generateAISentimentHTML(coin, coinId) {
    // Only show if we have AI analysis or DeepSeek sentiment
    if (!coin.ai_analysis && !coin.ai_sentiment) {
        return '';
    }
    
    const analysis = coin.ai_analysis;
    const sentiment = coin.ai_sentiment;
    
    let content = '';
    
    // Build combined ML + DeepSeek analysis (use summary with individualized insights)
    if (analysis && sentiment) {
        const recommendationClass = analysis.recommendation === 'BUY' ? 'positive' : 
                                   analysis.recommendation === 'SELL' || analysis.recommendation === 'AVOID' ? 'negative' : 'neutral';
        
        let sentimentLabel = 'Neutral';
        if (sentiment.score >= 0.3) sentimentLabel = 'Bullish';
        else if (sentiment.score <= -0.3) sentimentLabel = 'Bearish';
        
        const scorePercent = sentiment.score ? ((sentiment.score + 1) * 5).toFixed(1) : 'N/A';
        
        // Use analysis.summary which now contains individualized DeepSeek key_points
        const displayText = analysis.summary || sentiment.reasoning || '';
        
        content += `
            <div class="deepseek-analysis-inline">
                <div class="deepseek-header">
                    <span>AI Analysis ${analysis.gem_score ? `(${analysis.gem_score})` : ''}</span>
                    <span class="sentiment-badge ${recommendationClass}">${analysis.recommendation} · ${sentimentLabel} ${scorePercent}/10</span>
                </div>
                <div class="key-points-compact">
                    <div class="key-point">${displayText}</div>
                </div>
            </div>
        `;
    }
    // Show ML only if no DeepSeek sentiment with reasoning
    else if (analysis) {
        const recommendationClass = analysis.recommendation === 'BUY' ? 'positive' : 
                                   analysis.recommendation === 'SELL' || analysis.recommendation === 'AVOID' ? 'negative' : 'neutral';
        
        // If we have sentiment without reasoning, show combined badge but use summary
        if (sentiment) {
            let sentimentLabel = 'Neutral';
            if (sentiment.score >= 0.3) sentimentLabel = 'Bullish';
            else if (sentiment.score <= -0.3) sentimentLabel = 'Bearish';
            const scorePercent = sentiment.score ? ((sentiment.score + 1) * 5).toFixed(1) : 'N/A';
            
            content += `
                <div class="deepseek-analysis-inline">
                    <div class="deepseek-header">
                        <span>AI Analysis</span>
                        <span class="sentiment-badge ${recommendationClass}">${analysis.recommendation} · ${sentimentLabel} ${scorePercent}/10</span>
                    </div>
                    ${(sentiment.key_points && sentiment.key_points[0]) ? `
                        <div class="key-points-compact">
                            <div class="key-point">${sentiment.key_points[0]}</div>
                        </div>
                    ` : ''}
                </div>
            `;
        } else {
            // No sentiment at all, just show ML prediction
            content += `
                <div class="deepseek-analysis-inline">
                    <div class="deepseek-header">
                        <span>ML Prediction</span>
                        <span class="sentiment-badge ${recommendationClass}">${analysis.recommendation}</span>
                    </div>
                    ${analysis.summary ? `
                        <div class="key-points-compact">
                            <div class="key-point">${analysis.summary}</div>
                        </div>
                    ` : ''}
                </div>
            `;
        }
    }
    // Show DeepSeek only if no ML analysis
    else if (sentiment && sentiment.key_points && sentiment.key_points.length > 0) {
        let sentimentLabel = 'Neutral';
        let sentimentClass = 'neutral';
        
        if (sentiment.score >= 0.3) {
            sentimentLabel = 'Bullish';
            sentimentClass = 'positive';
        } else if (sentiment.score <= -0.3) {
            sentimentLabel = 'Bearish';
            sentimentClass = 'negative';
        }
        
        const scorePercent = sentiment.score ? ((sentiment.score + 1) * 5).toFixed(1) : 'N/A';
        
        content += `
            <div class="deepseek-analysis-inline">
                <div class="deepseek-header">
                    <span>AI Sentiment</span>
                    <span class="sentiment-badge ${sentimentClass}">${sentimentLabel}</span>
                </div>
                <div class="deepseek-score">
                    <span class="score-text">${scorePercent}/10</span>
                </div>
                ${sentiment.key_points && sentiment.key_points.length > 0 ? `
                    <div class="key-points-compact">
                        ${sentiment.key_points.slice(0, 3).map(point => `
                            <div class="key-point">• ${point}</div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    return `
        <div class="ai-analysis-container">
            ${content}
        </div>
    `;
}

// Generate ML reasoning HTML section - Always visible inline
function generateMLReasoningHTML(coin, coinId, mlEnabled) {
    // Show investment highlights if available
    if (coin.investment_highlights && coin.investment_highlights.trim().length > 0) {
        return `
            <div class="ml-insights-inline">
                <div class="insights-label">ML Insights</div>
                <div class="insights-text">${coin.investment_highlights}</div>
            </div>
        `;
    }
    return '';
}

// Format price in GBP
function formatPrice(price) {
    if (!price || price === 0) return 'N/A';
    
    // Price is already in GBP from the API
    const priceInGbp = price;
    
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
