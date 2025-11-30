// API and Data Loading Functions

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
        let response = await fetch('/api/coins/enhanced');
        
        if (!response.ok) {
            response = await fetch('/api/coins');
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }

        const coins = data.coins || [];
        const mlEnabled = data.ml_enhanced || false;
        
        const coinsHtml = generateCoinsTable(coins, mlEnabled);
        document.getElementById('coinsContent').innerHTML = coinsHtml;
        
        updateRefreshStatus(data.last_updated, data.cache_expires_in);
        
    } catch (error) {
        console.error('Error loading coins:', error);
        document.getElementById('coinsContent').innerHTML = 
            `<div class="error">❌ Error loading coins: ${error.message}</div>`;
    }
}

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

async function loadMLStatus() {
    try {
        const response = await fetch('/api/ml/status');
        const data = await response.json();

        if (data.error) {
            console.error('ML Status Error:', data.error);
            document.getElementById('mlStatusContent').innerHTML = 
                `<div class="error">❌ ${data.error}</div>`;
            return;
        }

        const status = data.ml_status;
        const isEnabled = status.model_trained && status.model_loaded;
        
        let statusHtml = '<div class="ml-status-summary-row">';
        
        statusHtml += `
            <div class="ml-status-item ${isEnabled ? 'success' : 'warning'}">
                <span class="ml-status-icon">${isEnabled ? '✅' : '⚠️'}</span>
                <span class="ml-status-label">Status</span>
                <span class="ml-status-value">${isEnabled ? 'Active' : 'Inactive'}</span>
            </div>
        `;
        
        if (status.model_trained) {
            statusHtml += `
                <div class="ml-status-item">
                    <span class="ml-status-icon">📊</span>
                    <span class="ml-status-label">Training Samples</span>
                    <span class="ml-status-value">${status.training_samples || 0}</span>
                </div>
            `;
        }
        
        if (status.last_trained) {
            const trainedDate = new Date(status.last_trained);
            const now = new Date();
            const hoursSince = Math.floor((now - trainedDate) / (1000 * 60 * 60));
            
            statusHtml += `
                <div class="ml-status-item">
                    <span class="ml-status-icon">⏰</span>
                    <span class="ml-status-label">Last Trained</span>
                    <span class="ml-status-value">${hoursSince}h ago</span>
                </div>
            `;
        }
        
        if (data.deepseek_enabled !== undefined) {
            statusHtml += `
                <div class="ml-status-item ${data.deepseek_enabled ? 'success' : 'warning'}">
                    <span class="ml-status-icon">${data.deepseek_enabled ? '🧠' : '💤'}</span>
                    <span class="ml-status-label">AI Analysis</span>
                    <span class="ml-status-value">${data.deepseek_enabled ? 'Active' : 'Inactive'}</span>
                </div>
            `;
        }
        
        statusHtml += '</div>';
        document.getElementById('mlStatusContent').innerHTML = statusHtml;
        
    } catch (error) {
        console.error('Error loading ML status:', error);
        document.getElementById('mlStatusContent').innerHTML = 
            `<div class="error">❌ Error: ${error.message}</div>`;
    }
}

async function refreshMLStatus() {
    const btn = document.getElementById('refreshMLBtn');
    if (!btn) return;
    
    const originalText = btn.textContent;
    btn.textContent = '🔄 Refreshing...';
    btn.disabled = true;
    
    try {
        await loadMLStatus();
        btn.textContent = '✅ Refreshed!';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 2000);
    } catch (error) {
        btn.textContent = '❌ Error';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 2000);
    }
}

async function trainMLModel() {
    const btn = document.getElementById('trainBtn');
    const originalText = btn.textContent;
    
    btn.textContent = '🎯 Training...';
    btn.disabled = true;
    
    showStatus('🎯 Starting ML model training...', 'info', 6000);
    
    try {
        const response = await fetch('/api/ml/train', { method: 'POST' });
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Training failed');
        }
        
        showStatus(`✅ ${data.message}`, 'success', 5000);
        
        await loadMLStatus();
        await loadCoins();
        await loadFavorites();
        
    } catch (error) {
        showStatus(`❌ Training failed: ${error.message}`, 'error', 6000);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function refreshData() {
    await Promise.all([
        loadCoins(),
        loadFavorites(),
        loadMLStatus()
    ]);
}

async function forceRefresh() {
    if (refreshing) return;
    
    const btn = document.getElementById('refreshBtn');
    const originalText = btn.textContent;
    
    refreshing = true;
    btn.textContent = '🔄 Refreshing...';
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/refresh', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            showStatus('✅ Data refreshed successfully!', 'success');
            await refreshData();
        } else {
            throw new Error(data.error || 'Refresh failed');
        }
    } catch (error) {
        console.error('Error refreshing data:', error);
        showStatus(`❌ Error: ${error.message}`, 'error');
    } finally {
        refreshing = false;
        btn.textContent = originalText;
        btn.disabled = false;
    }
}
