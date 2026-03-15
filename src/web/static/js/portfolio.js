// PHASE 5: Portfolio Analysis Functions

async function analyzePortfolio() {
    const container = document.getElementById('portfolioContainer');
    const content = document.getElementById('portfolioContent');
    const button = document.getElementById('portfolioBtn');
    
    // Show container
    container.style.display = 'block';
    container.scrollIntoView({ behavior: 'smooth' });
    
    // Disable button
    button.disabled = true;
    button.textContent = 'Analyzing...';
    
    content.innerHTML = '<div class="loading">🤖 AI agents analyzing portfolio opportunities...</div>';
    
    try {
        const response = await fetch('/api/portfolio/analyze?max_coins=15');
        
        if (!response.ok) {
            throw new Error(`API returned ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Render portfolio analysis
        content.innerHTML = generatePortfolioHTML(data);
        button.textContent = '📊 Portfolio Analysis';
        button.disabled = false;
        
        showStatus('Portfolio analysis complete!', 'success');
        
    } catch (error) {
        console.error('Portfolio analysis error:', error);
        content.innerHTML = `<div class="error">Analysis failed</div>`;
        button.textContent = '📊 Portfolio Analysis';
        button.disabled = false;
        showStatus('Portfolio analysis failed', 'error');
    }
}

function closePortfolioAnalysis() {
    const container = document.getElementById('portfolioContainer');
    container.style.display = 'none';
}

function generatePortfolioHTML(data) {
    const summary = data.summary;
    const recs = data.recommendations;
    
    const sentimentClass = summary.market_sentiment.includes('Bullish') ? 'positive' : 
                          summary.market_sentiment.includes('Bearish') ? 'negative' : 'neutral';
    
    // Invert risk into opportunity score (high risk = high opportunity)
    const opportunityScore = Math.max(0, Math.min(100, 100 - (summary.portfolio_risk || 50)));
    const oppClass = opportunityScore >= 60 ? 'positive' : 
                    opportunityScore < 40 ? 'neutral' : 'neutral';
    
    let html = `
        <div class="portfolio-analysis">
            <div class="portfolio-summary">
                <div class="summary-card">
                    <div class="summary-label">Market Sentiment</div>
                    <div class="summary-value ${sentimentClass}">${summary.market_sentiment}</div>
                </div>
                <div class="summary-card">
                    <div class="summary-label">Gems Found</div>
                    <div class="summary-value positive">${summary.gems_found}/${summary.total_analyzed}</div>
                </div>
                <div class="summary-card">
                    <div class="summary-label">Opportunity Level</div>
                    <div class="summary-value ${oppClass}">${opportunityScore}/100</div>
                </div>
                <div class="summary-card">
                    <div class="summary-label">Diversification</div>
                    <div class="summary-value">${summary.diversification}/100</div>
                </div>
            </div>
    `;
    
    // Top Opportunities
    if (data.top_opportunities && data.top_opportunities.length > 0) {
        html += `
            <div class="portfolio-section">
                <h3>🌟 Top Opportunities</h3>
                <div class="opportunities-grid">
                    ${data.top_opportunities.map(opp => `
                        <div class="opportunity-card">
                            <div class="opp-header">
                                <span class="opp-symbol">${escapeHtml(opp.symbol)}</span>
                                <span class="opp-score">${Number(opp.gem_score)}%</span>
                            </div>
                            <div class="opp-name">${escapeHtml(opp.name)}</div>
                            <div class="opp-reason">${escapeHtml(opp.reason)}</div>
                            <div class="opp-confidence">Confidence: ${Number(opp.confidence)}%</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    // Allocation Strategy
    if (data.allocation_strategy && Object.keys(data.allocation_strategy).length > 0) {
        html += `
            <div class="portfolio-section">
                <h3>💼 Suggested Allocation</h3>
                <div class="allocation-chart">
                    ${Object.entries(data.allocation_strategy).map(([symbol, pct]) => `
                        <div class="allocation-item">
                            <div class="allocation-bar-container">
                                <div class="allocation-bar" style="width: ${Number(pct)}%"></div>
                            </div>
                            <div class="allocation-label">
                                <span class="allocation-symbol">${escapeHtml(symbol)}</span>
                                <span class="allocation-pct">${Number(pct)}%</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    // Market Notes
    if (data.risk_warnings && data.risk_warnings.length > 0) {
        html += `
            <div class="portfolio-section">
                <h3>📋 Market Notes</h3>
                <div class="market-notes">
                    ${data.risk_warnings.map(warning => `
                        <div class="market-note">📌 ${escapeHtml(warning)}</div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    // BUY Recommendations
    if (recs.buy && recs.buy.length > 0) {
        html += `
            <div class="portfolio-section">
                <h3>✅ BUY Recommendations (${recs.buy.length})</h3>
                <div class="recs-list">
                    ${recs.buy.slice(0, 5).map(rec => `
                        <div class="rec-item buy">
                            <div class="rec-header">
                                <span class="rec-symbol">${escapeHtml(rec.symbol)}</span>
                                <span class="rec-score">${Number(rec.gem_score)}%</span>
                            </div>
                            <div class="rec-details">
                                <span class="rec-confidence">Confidence: ${Number(rec.confidence)}%</span>
                                <span class="rec-opportunity ${escapeHtml(rec.risk_level.toLowerCase())}">${rec.risk_level === 'High' || rec.risk_level === 'Very High' ? 'High Upside' : rec.risk_level === 'Low' ? 'Stable' : 'Balanced'}</span>
                            </div>
                            ${rec.key_strengths && rec.key_strengths.length > 0 ? `
                                <div class="rec-strengths">
                                    ${rec.key_strengths.map(s => `<div>✓ ${escapeHtml(s)}</div>`).join('')}
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    // HOLD Recommendations (collapsed by default)
    if (recs.hold && recs.hold.length > 0) {
        html += `
            <div class="portfolio-section">
                <h3 style="cursor: pointer;" onclick="togglePortfolioSection('hold')">
                    ⏸️ HOLD Recommendations (${recs.hold.length}) <span id="hold-arrow">▼</span>
                </h3>
                <div id="hold-section" class="recs-list" style="display: none;">
                    ${recs.hold.slice(0, 5).map(rec => `
                        <div class="rec-item hold">
                            <div class="rec-header">
                                <span class="rec-symbol">${escapeHtml(rec.symbol)}</span>
                                <span class="rec-score">${Number(rec.gem_score)}%</span>
                            </div>
                            <div class="rec-details">
                                <span class="rec-confidence">Confidence: ${Number(rec.confidence)}%</span>
                                <span class="rec-opportunity ${escapeHtml(rec.risk_level.toLowerCase())}">${rec.risk_level === 'High' || rec.risk_level === 'Very High' ? 'High Upside' : rec.risk_level === 'Low' ? 'Stable' : 'Balanced'}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    html += '</div>';
    return html;
}

function togglePortfolioSection(sectionId) {
    const section = document.getElementById(`${sectionId}-section`);
    const arrow = document.getElementById(`${sectionId}-arrow`);
    
    if (section.style.display === 'none') {
        section.style.display = 'block';
        arrow.textContent = '▲';
    } else {
        section.style.display = 'none';
        arrow.textContent = '▼';
    }
}
