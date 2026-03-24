// UI Components and HTML Generators

// PHASE 4: Generate unified AI analysis HTML (multi-agent integrated)
function generateUnifiedAIAnalysis(coin, coinId) {
    // Check if we have multi-agent analysis
    const agentAnalysis = coin.agent_analysis;
    
    if (agentAnalysis) {
        // Full multi-agent analysis available
        const gemScore = agentAnalysis.gem_score || 0;
        const scoreClass = gemScore >= 70 ? 'score-high' : 
                          gemScore >= 50 ? 'score-medium' : 'score-low';
        
        const riskLevel = agentAnalysis.risk_level || 'Moderate';
        // Map risk levels to opportunity framing
        const opportunityLabel = riskLevel.toLowerCase().includes('extreme') ? 'High Upside' :
                                riskLevel.toLowerCase().includes('high') ? 'Growth Play' :
                                riskLevel.toLowerCase().includes('conservative') ? 'Stable' :
                                riskLevel.toLowerCase().includes('low') ? 'Stable' : 'Balanced';
        const oppClass = riskLevel.toLowerCase().includes('extreme') || riskLevel.toLowerCase().includes('high') ? 'positive' : 
                         riskLevel.toLowerCase().includes('conservative') || riskLevel.toLowerCase().includes('low') ? 'neutral' : 'neutral';
        
        const recommendation = agentAnalysis.recommendation || 'HOLD';
        const recClass = recommendation === 'BUY' || recommendation === 'STRONG BUY' ? 'positive' :
                        recommendation === 'SELL' || recommendation === 'AVOID' ? 'negative' : 'neutral';
        
        const confidence = agentAnalysis.confidence || 0;
        
        // Summary text — personalized from agents (sanitize JSON leaks)
        let summary = agentAnalysis.summary || '';
        if (typeof summary === 'object') summary = '';
        if (summary.includes('{"') || summary.includes('": "')) {
            summary = summary.replace(/\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}/g, '').replace(/\s{2,}/g, ' ').trim();
        }
        
        // Get strengths and weaknesses 
        const strengths = agentAnalysis.key_strengths || [];
        const weaknesses = agentAnalysis.key_weaknesses || [];
        
        return `
            <div class="unified-ai-analysis compact">
                <div class="ai-header-compact">
                    <div class="ai-score-badge ${scoreClass}">
                        <div class="score-number">${Math.round(gemScore)}%</div>
                        <div class="score-action ${recClass}">${recommendation}</div>
                    </div>
                    <div class="ai-confidence-risk">
                        <div class="confidence-indicator">${confidence}% confident</div>
                        <div class="opportunity-badge ${oppClass}">${opportunityLabel}</div>
                    </div>
                </div>
                
                ${summary ? `
                <div class="ai-summary-text">
                    ${summary.length > 200 ? summary.substring(0, 200) + '...' : summary}
                </div>
                ` : ''}
                
                ${strengths.length > 0 || weaknesses.length > 0 ? `
                <div class="ai-summary-compact">
                    ${strengths.length > 0 ? `
                    <div class="summary-item positive">
                        <span class="summary-icon">✓</span>
                        <span class="summary-text">${strengths[0].length > 100 ? strengths[0].substring(0, 100) + '...' : strengths[0]}</span>
                    </div>
                    ` : ''}
                    ${weaknesses.length > 0 ? `
                    <div class="summary-item negative">
                        <span class="summary-icon">!</span>
                        <span class="summary-text">${weaknesses[0].length > 100 ? weaknesses[0].substring(0, 100) + '...' : weaknesses[0]}</span>
                    </div>
                    ` : ''}
                </div>
                ` : ''}
                
                <div style="display: flex; gap: 6px; margin-top: 6px;">
                    ${recommendation === 'BUY' || recommendation === 'STRONG BUY' ? `
                    <button class="ai-expand-btn" onclick="proposeTrade('${coin.symbol}', ${coin.price || 0}, ${JSON.stringify({gem_score: gemScore, recommendation, confidence, risk_level: riskLevel, summary: (summary || '').substring(0,150), key_strengths: strengths.slice(0,2), key_weaknesses: weaknesses.slice(0,2)}).replace(/'/g, "\\'")})" style="flex: 1; background: linear-gradient(135deg, #38a169, #48bb78); color: white; border: none; font-weight: 700;">
                        ⚡ Trade
                    </button>
                    ` : ''}
                    ${strengths.length > 1 || weaknesses.length > 1 ? `
                    <button class="ai-expand-btn" onclick="toggleAgentDetails('${coinId}')" style="flex: 1;">
                        <span>More</span> <span class="arrow">▼</span>
                    </button>
                    ` : ''}
                </div>
                    <div id="agent-details-${coinId}" class="agent-details-compact" style="display: none;">
                        ${strengths.length > 1 ? `
                            <div class="detail-section">
                                <div class="detail-header positive">Key Insights</div>
                                ${strengths.slice(1, 4).map(s => `
                                    <div class="detail-item">• ${s.length > 120 ? s.substring(0, 120) + '...' : s}</div>
                                `).join('')}
                            </div>
                        ` : ''}
                        ${weaknesses.length > 1 ? `
                            <div class="detail-section">
                                <div class="detail-header negative">Watch For</div>
                                ${weaknesses.slice(1, 3).map(w => `
                                    <div class="detail-item">• ${w.length > 120 ? w.substring(0, 120) + '...' : w}</div>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    // Fallback to legacy AI analysis if no multi-agent data
    const analysis = coin.ai_analysis;
    const sentiment = coin.ai_sentiment;
    
    if (!analysis && !sentiment) {
        return `
            <div class="unified-ai-analysis loading-analysis">
                <div class="ai-loading">
                    <span class="loading-icon">🔄</span>
                    <span>AI analysis loading in background...</span>
                </div>
            </div>
        `;
    }
    
    // Show AI analysis (with or without sentiment)
    if (analysis) {
        const recommendationClass = analysis.recommendation === 'BUY' || analysis.recommendation === 'STRONG BUY' ? 'positive' : 
                                   analysis.recommendation === 'SELL' || analysis.recommendation === 'AVOID' ? 'negative' : 'neutral';
        
        let sentimentText = '';
        if (sentiment && sentiment.score != null) {
            let sentimentLabel = 'Neutral';
            if (sentiment.score >= 0.3) sentimentLabel = 'Bullish';
            else if (sentiment.score <= -0.3) sentimentLabel = 'Bearish';
            const scorePercent = ((sentiment.score + 1) * 50).toFixed(0);
            sentimentText = ` • ${sentimentLabel} ${scorePercent}%`;
        }
        
        const gemScore = analysis.gem_score || '';
        const riskLevel = analysis.risk_level || '';
        const confidence = analysis.confidence || '';
        
        // Sanitize summary - strip any raw JSON that leaked through
        let summaryText = analysis.summary || (sentiment && sentiment.reasoning) || 'Analysis in progress...';
        if (typeof summaryText === 'object') {
            summaryText = 'Analysis in progress...';
        } else if (summaryText.includes('{"') || summaryText.includes('": "')) {
            // Strip JSON objects from the text
            summaryText = summaryText.replace(/\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}/g, '').replace(/\s{2,}/g, ' ').trim();
            if (!summaryText || summaryText.length < 10) summaryText = 'Analysis complete';
        }
        
        return `
            <div class="unified-ai-analysis">
                <div class="ai-header">
                    <div class="ai-title">
                        <span class="ai-icon">🤖</span>
                        <span>Analysis</span>
                    </div>
                    <div class="ai-sentiment ${recommendationClass}">
                        ${analysis.recommendation}${sentimentText}${confidence ? ' • ' + confidence : ''}
                    </div>
                </div>
                ${gemScore ? `
                <div class="ai-meta">
                    ${gemScore ? `<span class="gem-score">Score: ${gemScore}</span>` : ''}
                </div>
                ` : ''}
                <div class="ai-summary">
                    ${summaryText}
                </div>
            </div>
        `;
    }
    
    return '';
}


// Format price in GBP
function formatPrice(price) {
    if (!price || price === 0) return 'N/A';
    const n = Number(price);
    if (n >= 0.01)         return `£${n.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 4})}`;
    if (n >= 0.000001)     return `£${n.toFixed(6)}`;
    const decimals = -Math.floor(Math.log10(n)) + 2;
    return `£${n.toFixed(Math.min(decimals, 12))}`;
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



function toggleMLStatusDetails() {
    const detailsDiv = document.getElementById('mlStatusDetails');
    detailsDiv.style.display = detailsDiv.style.display === 'none' ? 'block' : 'none';
}

// PHASE 4: Toggle agent details
function toggleAgentDetails(coinId) {
    const content = document.getElementById(`agent-details-${coinId}`);
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
