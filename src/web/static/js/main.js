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
    
    let html = '<div class="coins-grid">';

    coins.forEach((coin, index) => {
        const priceChangeClass = coin.price_change_24h >= 0 ? 'positive' : 'negative';
        const priceChangeText = coin.price_change_24h >= 0 ? 
            `+${coin.price_change_24h.toFixed(1)}%` : 
            `${coin.price_change_24h.toFixed(1)}%`;

        const displayScore = coin.enhanced_score || coin.score;
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

        const usdToGbp = 0.8;
        const priceInGbp = coin.price ? coin.price * usdToGbp : null;
        let price = 'N/A';
        if (priceInGbp) {
            // For very small prices, show 2 significant digits
            if (priceInGbp < 0.01) {
                price = `£${priceInGbp.toPrecision(2)}`;
            } else {
                price = `£${priceInGbp.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 4})}`;
            }
        }

        const recentlyAddedBadge = coin.recently_added ? '<span class="badge badge-new">🆕 NEW</span>' : '';
        const mlEnhancedBadge = mlEnabled && coin.enhanced_score ? '<span class="badge badge-ai">🧠 AI</span>' : '';
        
        let mlReasoningHtml = '';
        if (mlEnabled && coin.ml_prediction) {
            const pred = coin.ml_prediction;
            const predClass = pred.direction === 'bullish' ? 'positive' : pred.direction === 'bearish' ? 'negative' : 'neutral';
            const confidencePercent = (pred.confidence * 100).toFixed(0);
            const confidenceClass = pred.confidence > 0.7 ? 'high' : pred.confidence > 0.4 ? 'medium' : 'low';
            
            mlReasoningHtml = `
                <div class="ml-reasoning-section">
                    <button class="ml-reasoning-toggle" onclick="toggleMLReasoning('coin-${index}')">
                        <span>🤖 ML Analysis</span>
                        <span class="arrow">▼</span>
                    </button>
                    <div id="ml-reasoning-coin-${index}" class="ml-reasoning-content" style="display: none;">
                        <div class="ml-prediction-detail">
                            <div class="prediction-row">
                                <span class="label">Prediction:</span>
                                <span class="value ${predClass}">${pred.prediction_percentage > 0 ? '+' : ''}${pred.prediction_percentage}% (${pred.direction.toUpperCase()})</span>
                            </div>
                            <div class="prediction-row">
                                <span class="label">Confidence:</span>
                                <div class="confidence-bar">
                                    <div class="confidence-fill ${confidenceClass}" style="width: ${confidencePercent}%"></div>
                                    <span class="confidence-text">${confidencePercent}%</span>
                                </div>
                            </div>
                            <div class="prediction-row">
                                <span class="label">Direction:</span>
                                <span class="direction-indicator ${predClass}">
                                    ${pred.direction === 'bullish' ? '📈 Bullish' : pred.direction === 'bearish' ? '📉 Bearish' : '➡️ Neutral'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else if (mlEnabled) {
            mlReasoningHtml = `
                <div class="ml-reasoning-section">
                    <div class="ml-unavailable">
                        <span>🤖 ML prediction not available</span>
                        <small>Model needs training data</small>
                    </div>
                </div>
            `;
        }
        
        html += `
            <div class="coin-card ${scoreClass}">
                <div class="coin-card-header">
                    <div class="coin-info">
                        <button class="favorite-btn-card" onclick="toggleFavorite('${coin.symbol}')" id="fav-${coin.symbol}">⭐</button>
                        <div class="coin-identity">
                            <div class="coin-symbol-large">${coin.symbol}</div>
                            <div class="coin-name-small">${coin.name}</div>
                        </div>
                    </div>
                    <div class="badges">
                        ${recentlyAddedBadge}
                        ${mlEnhancedBadge}
                    </div>
                </div>
                
                <div class="coin-card-body">
                    <div class="price-section">
                        <div class="price-large">${price}</div>
                        <div class="price-change ${priceChangeClass}">${priceChangeText}</div>
                    </div>
                    
                    <div class="score-section">
                        <div class="score-header">
                            <span class="score-label">${scoreLabel}</span>
                            <span class="score-value">${displayScore.toFixed(1)}/10</span>
                        </div>
                        <div class="score-bar">
                            <div class="score-fill ${scoreClass}" style="width: ${scorePercentage}%"></div>
                        </div>
                    </div>
                    
                    ${mlReasoningHtml}
                </div>
            </div>
        `;
    });

    html += '</div>';
    return html;
}

// Toggle ML reasoning visibility
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
    if (!favorites || favorites.length === 0) {
        return '<div class="error">No favorites yet</div>';
    }
    
    let html = '<div class="coins-grid">';

    favorites.forEach((coin, index) => {
        const priceChange = coin.price_change_24h || 0;
        const priceChangeClass = priceChange >= 0 ? 'positive' : 'negative';
        const priceChangeText = priceChange >= 0 ? 
            `+${priceChange.toFixed(1)}%` : 
            `${priceChange.toFixed(1)}%`;

        const displayScore = coin.enhanced_score || coin.score || 0;
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

        const usdToGbp = 0.8;
        const priceInGbp = coin.price ? coin.price * usdToGbp : null;
        let price = 'N/A';
        if (priceInGbp) {
            // For very small prices, show 2 significant digits
            if (priceInGbp < 0.01) {
                price = `£${priceInGbp.toPrecision(2)}`;
            } else {
                price = `£${priceInGbp.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 4})}`;
            }
        }

        const mlEnhancedBadge = mlEnabled && coin.enhanced_score ? '<span class="badge badge-ai">🧠 AI</span>' : '';
        
        let mlReasoningHtml = '';
        if (mlEnabled && coin.ml_prediction) {
            const pred = coin.ml_prediction;
            const predClass = pred.direction === 'bullish' ? 'positive' : pred.direction === 'bearish' ? 'negative' : 'neutral';
            const confidencePercent = (pred.confidence * 100).toFixed(0);
            const confidenceClass = pred.confidence > 0.7 ? 'high' : pred.confidence > 0.4 ? 'medium' : 'low';
            
            mlReasoningHtml = `
                <div class="ml-reasoning-section">
                    <button class="ml-reasoning-toggle" onclick="toggleMLReasoning('fav-${index}')">
                        <span>🤖 ML Analysis</span>
                        <span class="arrow">▼</span>
                    </button>
                    <div id="ml-reasoning-fav-${index}" class="ml-reasoning-content" style="display: none;">
                        <div class="ml-prediction-detail">
                            <div class="prediction-row">
                                <span class="label">Prediction:</span>
                                <span class="value ${predClass}">${pred.prediction_percentage > 0 ? '+' : ''}${pred.prediction_percentage}% (${pred.direction.toUpperCase()})</span>
                            </div>
                            <div class="prediction-row">
                                <span class="label">Confidence:</span>
                                <div class="confidence-bar">
                                    <div class="confidence-fill ${confidenceClass}" style="width: ${confidencePercent}%"></div>
                                    <span class="confidence-text">${confidencePercent}%</span>
                                </div>
                            </div>
                            <div class="prediction-row">
                                <span class="label">Direction:</span>
                                <span class="direction-indicator ${predClass}">
                                    ${pred.direction === 'bullish' ? '📈 Bullish' : pred.direction === 'bearish' ? '📉 Bearish' : '➡️ Neutral'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else if (mlEnabled) {
            mlReasoningHtml = `
                <div class="ml-reasoning-section">
                    <div class="ml-unavailable">
                        <span>🤖 ML prediction not available</span>
                        <small>Model needs training data</small>
                    </div>
                </div>
            `;
        }
        
        html += `
            <div class="coin-card ${scoreClass}">
                <div class="coin-card-header">
                    <div class="coin-info">
                        <button class="favorite-btn-card active" onclick="removeFavorite('${coin.symbol}')" title="Remove from favorites">❌</button>
                        <div class="coin-identity">
                            <div class="coin-symbol-large">${coin.symbol}</div>
                            <div class="coin-name-small">${coin.name}</div>
                        </div>
                    </div>
                    <div class="badges">
                        <span class="badge" style="background: gold; color: black;">⭐ FAVORITE</span>
                        ${mlEnhancedBadge}
                    </div>
                </div>
                
                <div class="coin-card-body">
                    <div class="price-section">
                        <div class="price-large">${price}</div>
                        <div class="price-change ${priceChangeClass}">${priceChangeText}</div>
                    </div>
                    
                    <div class="score-section">
                        <div class="score-header">
                            <span class="score-label">${scoreLabel}</span>
                            <span class="score-value">${displayScore.toFixed(1)}/10</span>
                        </div>
                        <div class="score-bar">
                            <div class="score-fill ${scoreClass}" style="width: ${scorePercentage}%"></div>
                        </div>
                    </div>
                    
                    ${mlReasoningHtml}
                </div>
            </div>
        `;
    });

    html += '</div>';
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
    console.log('🔄 loadMLStatus() called');
    try {
        console.log('📡 Fetching /api/ml/status...');
        const response = await fetch('/api/ml/status');
        console.log('📊 Response received:', response.status, response.ok);
        const data = await response.json();
        console.log('📦 Data:', data);
        
        let statusHtml = '';
        let showPanel = false;

        if (data.service_available) {
            const status = data.ml_status;
            const loadedChipClass = status.model_loaded ? 'ml-chip good' : 'ml-chip bad';
            const loadedText = status.model_loaded ? 'Loaded' : 'Not Loaded';
            const featureCount = status.feature_columns ? status.feature_columns.length : 0;
            const trainingStatus = status.training_status || 'Idle';
            const lastTrainShort = status.last_training_time ? new Date(status.last_training_time).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : 'Never';

            statusHtml = `
                <div class="ml-status-summary-row">
                    <span class="ml-chip ${loadedChipClass}">🧠 ${loadedText}</span>
                    <span class="ml-chip">⚙️ ${status.model_type ? status.model_type.replace(/Regressor|Classifier/i,'') : 'RF'}</span>
                    <span class="ml-chip">📊 ${featureCount} feats</span>
                    <span class="ml-chip warn">⏱ ${lastTrainShort}</span>
                    <span class="ml-chip">🔄 ${trainingStatus}</span>
                    <button class="ml-expand-toggle" onclick="toggleMLStatusDetails()" id="mlExpandBtn">Details ▼</button>
                </div>
                <div class="ml-status-details" id="mlStatusDetails">
                    <div class="ml-status-grid">
                        <div class="ml-status-item">
                            <strong>Model Status</strong>
                            ${loadedText}
                        </div>
                        <div class="ml-status-item">
                            <strong>Last Training</strong>
                            ${status.last_training_time ? new Date(status.last_training_time).toLocaleString() : 'Never'}
                        </div>
                        <div class="ml-status-item">
                            <strong>Model Type</strong>
                            ${status.model_type || 'RandomForestRegressor (Not Trained)'}
                        </div>
                        <div class="ml-status-item">
                            <strong>Features</strong>
                            ${featureCount} indicators
                        </div>
                        <div class="ml-status-item">
                            <strong>Training Status</strong>
                            ${trainingStatus}
                        </div>
                    </div>
                </div>
            `;
            showPanel = true;
        } else {
            const reason = data.ml_status ? (data.ml_status.error || 'Service offline') : 'Service offline';
            statusHtml = `
                <div class="ml-status-summary-row">
                    <span class="ml-chip bad">🧠 ML Offline</span>
                    <span class="ml-chip">Reason: ${reason}</span>
                </div>
            `;
            showPanel = true;
        }

        const container = document.getElementById('mlStatusContent');
        if (!container) {
            console.error('❌ mlStatusContent element not found!');
            return;
        }
        container.innerHTML = statusHtml;
        document.getElementById('mlStatusContainer').style.display = showPanel ? 'block' : 'none';
        console.log('✅ ML Status updated successfully');
        
    } catch (error) {
        console.error('❌ Error loading ML status:', error);
        console.error('Error details:', error.stack);
        const errorHtml = `
            <div class="ml-status-summary-row">
                <span class="ml-chip bad">🔴 ML Error</span>
                <span class="ml-chip">${error.message}</span>
            </div>
        `;
        const container = document.getElementById('mlStatusContent');
        if (container) {
            container.innerHTML = errorHtml;
        }
        document.getElementById('mlStatusContainer').style.display = 'block';
        
        // Show user-friendly notification
        showStatus(`Failed to refresh ML status: ${error.message}`, 'error');
    }
}

async function refreshMLStatus() {
    console.log('🔄 refreshMLStatus() wrapper called');
    const btn = document.getElementById('refreshMLBtn');
    if (!btn) {
        console.error('❌ refreshMLBtn button not found!');
        return;
    }
    
    // Disable button and show loading state
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '🔄 Refreshing...';
    
    try {
        await loadMLStatus();
        btn.innerHTML = '✅ Refreshed!';
        showStatus('ML status refreshed successfully', 'success');
        
        // Reset button after 2 seconds
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }, 2000);
    } catch (error) {
        console.error('Error in refreshMLStatus wrapper:', error);
        btn.innerHTML = '❌ Failed';
        showStatus('Failed to refresh ML status', 'error');
        
        // Reset button after 2 seconds
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }, 2000);
    }
}

function toggleMLStatusDetails() {
    const details = document.getElementById('mlStatusDetails');
    const btn = document.getElementById('mlExpandBtn');
    if (!details || !btn) return;
    const open = details.classList.toggle('open');
    btn.textContent = open ? 'Details ▲' : 'Details ▼';
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