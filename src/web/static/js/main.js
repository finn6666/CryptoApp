// CryptoApp Dashboard JavaScript
let refreshing = false;
let userFavorites = [];

// ===== STATUS & NOTIFICATIONS =====
function showStatus(message, type = 'info', duration = 4000) {
    const container = document.getElementById('statusContainer');
    const toast = document.getElementById('statusToast');
    const messageEl = document.getElementById('statusMessage');
    
    // Set message and type
    messageEl.textContent = message;
    toast.className = `status-toast ${type}`;
    
    // Show toast
    container.style.display = 'block';
    setTimeout(() => toast.classList.add('show'), 100);
    
    // Auto hide after duration
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            container.style.display = 'none';
        }, 300);
    }, duration);
}

// ===== DATA LOADING FUNCTIONS =====
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }

        document.getElementById('totalCoins').textContent = data.total_coins;
        document.getElementById('currentCoins').textContent = data.current_coins;
        document.getElementById('highPotential').textContent = data.high_potential;
        document.getElementById('trendingUp').textContent = data.trending_up;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadCoins() {
    try {
        // Try enhanced ML endpoint first, fallback to regular endpoint
        let response = await fetch('/api/coins/enhanced');
        let data = await response.json();
        
        if (data.error && !response.ok) {
            // Fallback to regular endpoint
            response = await fetch('/api/coins');
            data = await response.json();
        }
        
        if (data.error) {
            throw new Error(data.error);
        }

        const coinsHtml = generateCoinsTable(data.coins, data.ml_enhanced);
        document.getElementById('coinsContent').innerHTML = coinsHtml;
        
        // Update refresh status
        updateRefreshStatus(data.last_updated, data.cache_expires_in);
        
        // Update ML status if available
        if (data.ml_enhanced !== undefined) {
            updateMLStatus(data.ml_enhanced);
        }
        
    } catch (error) {
        document.getElementById('coinsContent').innerHTML = 
            `<div class="error">❌ Error loading data: ${error.message}</div>`;
    }
}

// ===== TABLE GENERATION =====
function generateCoinsTable(coins, mlEnabled = false) {
    if (!coins || coins.length === 0) {
        return '<div class="error">No cryptocurrency data available</div>';
    }

    const showMLColumn = true;
    
    let html = `
        <table class="coins-table">
            <thead>
                <tr>
                    <th>⭐</th>
                    <th>Symbol</th>
                    <th>Name</th>
                    <th>Score${mlEnabled ? ' 🧠' : ''}</th>
                    <th>Price</th>
                    <th>24h Change</th>
                    ${showMLColumn ? '<th>🤖 ML Prediction</th>' : ''}
                </tr>
            </thead>
            <tbody>
    `;

    coins.forEach(coin => {
        const priceChangeClass = coin.price_change_24h >= 0 ? 'positive' : 'negative';
        const priceChangeText = coin.price_change_24h >= 0 ? 
            `+${coin.price_change_24h.toFixed(1)}%` : 
            `${coin.price_change_24h.toFixed(1)}%`;

        const displayScore = coin.enhanced_score || coin.score;
        let scoreClass = 'score-low';
        if (displayScore >= 8) scoreClass = 'score-high';
        else if (displayScore >= 6) scoreClass = 'score-medium';

        const usdToGbp = 0.8;
        const priceInGbp = coin.price ? coin.price * usdToGbp : null;
        const price = priceInGbp ? `£${priceInGbp.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 4})}` : 'N/A';

        let mlPredictionHtml = '';
        if (showMLColumn) {
            if (mlEnabled && coin.ml_prediction) {
                const pred = coin.ml_prediction;
                const predClass = pred.direction === 'bullish' ? 'positive' : pred.direction === 'bearish' ? 'negative' : 'neutral';
                const confidenceEmoji = pred.confidence > 0.7 ? '🟢' : pred.confidence > 0.4 ? '🟡' : '🔴';
                mlPredictionHtml = `<td class="ml-prediction">
                    <span class="prediction ${predClass}">${pred.prediction_percentage > 0 ? '+' : ''}${pred.prediction_percentage}%</span><br>
                    <small>${confidenceEmoji} ${(pred.confidence * 100).toFixed(0)}%</small>
                </td>`;
            } else {
                mlPredictionHtml = `<td class="ml-prediction">
                    <small style="color: #a0aec0;">🤖 ${mlEnabled ? 'Training Needed' : 'ML Unavailable'}</small>
                </td>`;
            }
        }

        const recentlyAddedIndicator = coin.recently_added ? ' 🆕' : '';
        
        html += `
            <tr>
                <td><button class="favorite-btn" onclick="toggleFavorite('${coin.symbol}')" id="fav-${coin.symbol}">⭐</button></td>
                <td class="coin-symbol">${coin.symbol}${recentlyAddedIndicator}</td>
                <td class="coin-name">${coin.name}</td>
                <td><span class="score ${scoreClass}">${displayScore.toFixed(1)}</span></td>
                <td class="price">${price}</td>
                <td><span class="price-change ${priceChangeClass}">${priceChangeText}</span></td>
                ${mlPredictionHtml}
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    return html;
}

// ===== FAVORITES SYSTEM =====
async function loadFavorites() {
    try {
        const response = await fetch('/api/favorites');
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }

        const favorites = data.favorites;
        userFavorites = favorites.map(fav => fav.symbol);
        
        if (favorites.length > 0) {
            const favoritesHtml = generateFavoritesTable(favorites, data.ml_enhanced);
            document.getElementById('favoritesContent').innerHTML = favoritesHtml;
            document.getElementById('favoritesContainer').style.display = 'block';
        } else {
            document.getElementById('favoritesContainer').style.display = 'none';
        }
        
        updateFavoriteButtons();
        
    } catch (error) {
        console.error('Error loading favorites:', error);
        document.getElementById('favoritesContent').innerHTML = 
            `<div class="error">❌ Error loading favorites: ${error.message}</div>`;
    }
}

function generateFavoritesTable(favorites, mlEnabled = false) {
    const showMLColumn = true;
    
    let html = `
        <table class="coins-table">
            <thead>
                <tr>
                    <th>❌</th>
                    <th>Symbol</th>
                    <th>Name</th>
                    <th>Score${mlEnabled ? ' 🧠' : ''}</th>
                    <th>Price</th>
                    <th>24h Change</th>
                    ${showMLColumn ? '<th>🤖 ML Prediction</th>' : ''}
                </tr>
            </thead>
            <tbody>
    `;

    favorites.forEach(coin => {
        const priceChangeClass = coin.price_change_24h >= 0 ? 'positive' : 'negative';
        const priceChangeText = coin.price_change_24h >= 0 ? 
            `+${coin.price_change_24h.toFixed(1)}%` : 
            `${coin.price_change_24h.toFixed(1)}%`;

        const displayScore = coin.enhanced_score || coin.score;
        let scoreClass = 'score-low';
        if (displayScore >= 8) scoreClass = 'score-high';
        else if (displayScore >= 6) scoreClass = 'score-medium';

        const usdToGbp = 0.8;
        const priceInGbp = coin.price ? coin.price * usdToGbp : null;
        const price = priceInGbp ? `£${priceInGbp.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 4})}` : 'N/A';

        let mlPredictionHtml = '';
        if (showMLColumn) {
            if (mlEnabled && coin.ml_prediction) {
                const pred = coin.ml_prediction;
                const predClass = pred.direction === 'bullish' ? 'positive' : pred.direction === 'bearish' ? 'negative' : 'neutral';
                const confidenceEmoji = pred.confidence > 0.7 ? '🟢' : pred.confidence > 0.4 ? '🟡' : '🔴';
                mlPredictionHtml = `<td class="ml-prediction">
                    <span class="prediction ${predClass}">${pred.prediction_percentage > 0 ? '+' : ''}${pred.prediction_percentage}%</span><br>
                    <small>${confidenceEmoji} ${(pred.confidence * 100).toFixed(0)}%</small>
                </td>`;
            } else {
                mlPredictionHtml = `<td class="ml-prediction">
                    <small style="color: #a0aec0;">🤖 ${mlEnabled ? 'Training Needed' : 'ML Unavailable'}</small>
                </td>`;
            }
        }

        html += `
            <tr>
                <td><button class="favorite-btn" onclick="removeFavorite('${coin.symbol}')" style="color: #fc8181;">❌</button></td>
                <td class="coin-symbol">${coin.symbol}</td>
                <td class="coin-name">${coin.name}</td>
                <td><span class="score ${scoreClass}">${displayScore.toFixed(1)}</span></td>
                <td class="price">${price}</td>
                <td><span class="price-change ${priceChangeClass}">${priceChangeText}</span></td>
                ${mlPredictionHtml}
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    return html;
}

async function toggleFavorite(symbol) {
    try {
        const isFavorited = userFavorites.includes(symbol);
        const endpoint = isFavorited ? '/api/favorites/remove' : '/api/favorites/add';
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ symbol: symbol })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error);
        }
        
        await loadFavorites();
        
    } catch (error) {
        console.error('Error toggling favorite:', error);
        alert(`Error: ${error.message}`);
    }
}

async function removeFavorite(symbol) {
    await toggleFavorite(symbol);
}

function updateFavoriteButtons() {
    userFavorites.forEach(symbol => {
        const btn = document.getElementById(`fav-${symbol}`);
        if (btn) {
            btn.classList.add('favorited');
        }
    });
}

// ===== REFRESH & DATA MANAGEMENT =====
async function forceRefresh() {
    if (refreshing) return;
    
    refreshing = true;
    const refreshBtn = document.getElementById('refreshBtn');
    refreshBtn.disabled = true;
    refreshBtn.innerHTML = '🔄 Refreshing...';

    try {
        const response = await fetch('/api/refresh', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error);
        }

        await loadStats();
        await loadCoins();
        
        refreshBtn.innerHTML = '✅ Refreshed!';
        setTimeout(() => {
            refreshBtn.innerHTML = '🔄 Refresh Now';
        }, 2000);
        
    } catch (error) {
        console.error('Force refresh failed:', error);
        refreshBtn.innerHTML = '❌ Failed';
        setTimeout(() => {
            refreshBtn.innerHTML = '🔄 Refresh Now';
        }, 3000);
    } finally {
        refreshing = false;
        refreshBtn.disabled = false;
    }
}

async function refreshData() {
    if (refreshing) return;
    
    refreshing = true;

    try {
        await loadStats();
        await loadCoins();
        
    } catch (error) {
        console.error('Error refreshing data:', error);
    } finally {
        refreshing = false;
    }
}

function updateRefreshStatus(lastUpdated, cacheExpiresIn) {
    const lastUpdatedEl = document.getElementById('lastUpdated');
    const nextRefreshEl = document.getElementById('nextRefresh');
    
    if (lastUpdated && lastUpdated !== 'Never') {
        const date = new Date(lastUpdated);
        lastUpdatedEl.textContent = date.toLocaleTimeString();
    } else {
        lastUpdatedEl.textContent = 'Never';
    }
    
    if (cacheExpiresIn > 0) {
        const minutes = Math.floor(cacheExpiresIn / 60);
        const seconds = cacheExpiresIn % 60;
        nextRefreshEl.textContent = `${minutes}m ${seconds}s`;
    } else {
        nextRefreshEl.textContent = 'Available now';
    }
}

// ===== ML FUNCTIONS =====
async function loadMLStatus() {
    try {
        const response = await fetch('/api/ml/status');
        const data = await response.json();
        
        let statusHtml = '';
        let showPanel = false;
        
        if (data.service_available) {
            const status = data.ml_status;
            statusHtml = `
                <div class="ml-status-grid">
                    <div class="ml-status-item">
                        <strong>Model Status:</strong><br>
                        ${status.model_loaded ? '🟢 Loaded' : '🔴 Not Loaded'}
                    </div>
                    <div class="ml-status-item">
                        <strong>Last Training:</strong><br>
                        ${status.last_training_time ? new Date(status.last_training_time).toLocaleString() : 'Never'}
                    </div>
                    <div class="ml-status-item">
                        <strong>Model Type:</strong><br>
                        ${status.model_type || 'RandomForestRegressor (Not Trained)'}
                    </div>
                    <div class="ml-status-item">
                        <strong>Features:</strong><br>
                        ${status.feature_columns ? status.feature_columns.length : 0} indicators
                    </div>
                </div>
                <div style="text-align: center; margin-top: 15px;">
                    <small><strong>Status:</strong> ${status.training_status}</small>
                </div>
            `;
            showPanel = true;
        } else {
            statusHtml = `
                <div class="ml-status-grid">
                    <div class="ml-status-item">
                        <strong>ML Service:</strong><br>
                        🔴 Not Available
                    </div>
                    <div class="ml-status-item">
                        <strong>Reason:</strong><br>
                        ${data.ml_status ? data.ml_status.error : 'Service offline'}
                    </div>
                </div>
            `;
            showPanel = true;
        }
        
        document.getElementById('mlStatusContent').innerHTML = statusHtml;
        document.getElementById('mlStatusContainer').style.display = showPanel ? 'block' : 'none';
        
    } catch (error) {
        console.error('Error loading ML status:', error);
        const errorHtml = `
            <div class="ml-status-grid">
                <div class="ml-status-item">
                    <strong>ML Service:</strong><br>
                    🔴 Connection Error
                </div>
                <div class="ml-status-item">
                    <strong>Error:</strong><br>
                    ${error.message}
                </div>
            </div>
        `;
        document.getElementById('mlStatusContent').innerHTML = errorHtml;
        document.getElementById('mlStatusContainer').style.display = 'block';
    }
}

async function trainMLModel() {
    const trainBtn = document.getElementById('trainBtn');
    trainBtn.disabled = true;
    trainBtn.innerHTML = '🎯 Training...';
    
    try {
        const response = await fetch('/api/ml/train', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            alert('Model trained successfully! 🎉');
            await loadMLStatus();
            await loadCoins();
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('Error training model:', error);
        alert(`Training failed: ${error.message}`);
    } finally {
        trainBtn.disabled = false;
        trainBtn.innerHTML = '🎯 Train Model (Demo)';
    }
}

function updateMLStatus(mlEnabled) {
    if (mlEnabled) {
        loadMLStatus();
    }
}

// ===== HIDDEN GEM DETECTION =====
async function scanForHiddenGems() {
    try {
        const container = document.getElementById('hiddenGemsContainer');
        const content = document.getElementById('hiddenGemsContent');
        
        container.style.display = 'block';
        content.innerHTML = '<div class="loading">🔍 Scanning for hidden gems...</div>';
        
        showStatus('🔍 Scanning for hidden gems...', 'info');
        
        const response = await fetch('/api/gems/scan?limit=15&min_probability=0.6');
        const data = await response.json();
        
        if (data.error) {
            content.innerHTML = `<div class="error">❌ ${data.error}</div>`;
            showStatus(`❌ ${data.error}`, 'error');
            return;
        }
        
        displayHiddenGems(data);
        showStatus(`💎 Found ${data.gems_found} potential hidden gems!`, 'success');
        
    } catch (error) {
        console.error('Error scanning for hidden gems:', error);
        const content = document.getElementById('hiddenGemsContent');
        content.innerHTML = '<div class="error">❌ Failed to scan for hidden gems</div>';
        showStatus('❌ Failed to scan for hidden gems', 'error');
    }
}

function displayHiddenGems(data) {
    const content = document.getElementById('hiddenGemsContent');
    
    if (data.hidden_gems.length === 0) {
        content.innerHTML = '<div class="no-results">No hidden gems found with current criteria. Try lowering the probability threshold.</div>';
        return;
    }
    
    let html = `
        <div class="scan-summary" style="background: rgba(255, 215, 0, 0.1); padding: 15px; border-radius: 10px; margin-bottom: 20px;">
            <h3>📊 Scan Results</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-top: 10px;">
                <div><strong>Total Scanned:</strong> ${data.total_scanned}</div>
                <div><strong>Gems Found:</strong> ${data.gems_found}</div>
                <div><strong>Ultra High (80%+):</strong> ${data.scan_summary?.ultra_high_potential || 0}</div>
                <div><strong>High (70-80%):</strong> ${data.scan_summary?.high_potential || 0}</div>
                <div><strong>Moderate (60-70%):</strong> ${data.scan_summary?.moderate_potential || 0}</div>
            </div>
        </div>
    `;
    
    data.hidden_gems.forEach(gem => {
        const gemScore = Math.round(gem.gem_score);
        const probabilityPercent = (gem.gem_probability * 100).toFixed(1);
        
        html += `
            <div class="gem-card">
                <div class="gem-header">
                    <div>
                        <span class="gem-title">${gem.symbol}</span>
                        <span style="color: #a0aec0; margin-left: 10px; font-size: 0.9em;">${gem.name}</span>
                    </div>
                    <div class="gem-score">💎 ${gemScore}%</div>
                </div>
                
                <div class="gem-details">
                    <div class="gem-metric">
                        <div style="color: #a0aec0; font-size: 0.9em;">Current Price</div>
                        <div style="font-weight: bold;">$${gem.price?.toFixed(8) || 'N/A'}</div>
                    </div>
                    <div class="gem-metric">
                        <div style="color: #a0aec0; font-size: 0.9em;">Market Cap Rank</div>
                        <div style="font-weight: bold;">#${gem.market_cap_rank || 'N/A'}</div>
                    </div>
                    <div class="gem-metric">
                        <div style="color: #a0aec0; font-size: 0.9em;">Gem Probability</div>
                        <div style="font-weight: bold; color: #ffd700;">${probabilityPercent}%</div>
                    </div>
                    <div class="gem-metric">
                        <div style="color: #a0aec0; font-size: 0.9em;">Risk Level</div>
                        <div><span class="risk-level risk-${gem.risk_level?.toLowerCase().replace(' ', '-')}">${gem.risk_level}</span></div>
                    </div>
                </div>
                
                <div class="gem-recommendation">
                    ${gem.recommendation}
                </div>
                
                ${gem.key_strengths?.length > 0 ? `
                    <div class="gem-strengths">
                        <div style="font-weight: bold; color: #48bb78; margin-bottom: 8px;">🔹 Key Strengths:</div>
                        ${gem.key_strengths.slice(0, 3).map(strength => `<div style="margin: 4px 0; font-size: 0.9em;">• ${strength}</div>`).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    });
    
    content.innerHTML = html;
}

async function trainGemDetector() {
    try {
        showStatus('🏋️ Training Hidden Gem Detector...', 'info');
        
        const response = await fetch('/api/gems/train', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            const result = data.training_result;
            showStatus(`✅ Model trained! Accuracy: ${(result.accuracy * 100).toFixed(1)}%, AUC: ${(result.auc_score * 100).toFixed(1)}%`, 'success');
            
            const content = document.getElementById('hiddenGemsContent');
            content.innerHTML = `
                <div class="training-results" style="background: rgba(72, 187, 120, 0.1); padding: 20px; border-radius: 10px;">
                    <h3>🎯 Training Complete!</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
                        <div><strong>Accuracy:</strong> ${(result.accuracy * 100).toFixed(1)}%</div>
                        <div><strong>AUC Score:</strong> ${(result.auc_score * 100).toFixed(1)}%</div>
                        <div><strong>CV Score:</strong> ${(result.cv_mean * 100).toFixed(1)}%</div>
                        <div><strong>Total Coins:</strong> ${result.total_coins_trained}</div>
                        <div><strong>Hidden Gems:</strong> ${result.hidden_gems_identified}</div>
                        <div><strong>Model Type:</strong> ${result.model_type}</div>
                    </div>
                    
                    <div style="margin-top: 20px;">
                        <h4>🔝 Top Features:</h4>
                        <div style="margin-top: 10px;">
                            ${result.top_features.slice(0, 5).map(([feature, importance]) => 
                                `<div style="background: rgba(0,0,0,0.2); padding: 8px; margin: 4px 0; border-radius: 6px;">
                                    <strong>${feature.replace('_', ' ')}:</strong> ${(importance * 100).toFixed(1)}%
                                </div>`
                            ).join('')}
                        </div>
                    </div>
                </div>
            `;
        } else {
            showStatus(`❌ Training failed: ${data.error}`, 'error');
        }
        
    } catch (error) {
        console.error('Error training gem detector:', error);
        showStatus('❌ Failed to train gem detector', 'error');
    }
}

async function getTopHiddenGems(count) {
    try {
        const container = document.getElementById('hiddenGemsContainer');
        const content = document.getElementById('hiddenGemsContent');
        
        container.style.display = 'block';
        content.innerHTML = `<div class="loading">🔍 Analyzing top ${count} hidden gems...</div>`;
        
        showStatus(`🔍 Finding top ${count} hidden gems...`, 'info');
        
        const response = await fetch(`/api/gems/top/${count}`);
        const data = await response.json();
        
        if (data.error) {
            content.innerHTML = `<div class="error">❌ ${data.error}</div>`;
            showStatus(`❌ ${data.error}`, 'error');
            return;
        }
        
        displayTopGems(data);
        showStatus(`💎 Found ${data.found_count} top hidden gems!`, 'success');
        
    } catch (error) {
        console.error('Error getting top gems:', error);
        showStatus('❌ Failed to get top hidden gems', 'error');
    }
}

function displayTopGems(data) {
    const content = document.getElementById('hiddenGemsContent');
    
    if (data.top_hidden_gems.length === 0) {
        content.innerHTML = '<div class="no-results">No hidden gems found. Try training the model first.</div>';
        return;
    }
    
    let html = `
        <div class="analysis-summary" style="background: rgba(255, 215, 0, 0.1); padding: 15px; border-radius: 10px; margin-bottom: 20px;">
            <h3>🏆 Top Hidden Gems Analysis</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-top: 10px;">
                <div><strong>Average Score:</strong> ${data.analysis_summary?.average_gem_score?.toFixed(1) || 'N/A'}%</div>
                <div><strong>Low Risk:</strong> ${data.analysis_summary?.risk_distribution?.Low || 0}</div>
                <div><strong>Medium Risk:</strong> ${data.analysis_summary?.risk_distribution?.Medium || 0}</div>
                <div><strong>High Risk:</strong> ${data.analysis_summary?.risk_distribution?.High || 0}</div>
            </div>
        </div>
    `;
    
    data.top_hidden_gems.forEach((gem, index) => {
        const gemScore = Math.round(gem.gem_score);
        
        html += `
            <div class="gem-card">
                <div class="gem-header">
                    <div>
                        <span style="background: #ffd700; color: #333; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; margin-right: 10px;">#${index + 1}</span>
                        <span class="gem-title">${gem.symbol}</span>
                        <span style="color: #a0aec0; margin-left: 10px; font-size: 0.9em;">${gem.name}</span>
                    </div>
                    <div class="gem-score">💎 ${gemScore}%</div>
                </div>
                
                <div class="gem-recommendation">
                    ${gem.recommendation}
                </div>
            </div>
        `;
    });
    
    content.innerHTML = html;
}

// ===== INITIALIZATION =====
window.addEventListener('load', async () => {
    await loadStats();
    await loadCoins();
    await loadFavorites();
    await loadMLStatus();
});

// Update refresh timer every second
setInterval(() => {
    const nextRefreshEl = document.getElementById('nextRefresh');
    if (nextRefreshEl && nextRefreshEl.textContent !== 'Available now') {
        // This will be updated when loadCoins() is called
    }
}, 1000);