// API and Data Loading Functions

async function loadMarketConditions() {
    try {
        const response = await fetch('/api/market/conditions');
        const data = await response.json();

        if (data.error) {
            console.warn('Market conditions unavailable:', data.error);
            return;
        }

        // If data isn't loaded yet, auto-trigger a refresh
        if (data.opportunity_level === 'UNKNOWN') {
            try {
                const refreshRes = await fetch('/api/refresh', { method: 'POST' });
                const refreshData = await refreshRes.json();
                if (refreshData.success) {
                    setTimeout(() => refreshData_afterAutoLoad(), 2000);
                }
            } catch (e) {
                console.warn('Auto-refresh failed:', e);
            }
        }
        
    } catch (error) {
        console.error('Error loading market conditions:', error);
    }
}

async function loadMLStatus() {
    try {
        const response = await fetch('/api/ml/status');
        const data = await response.json();

        if (data.error) {
            console.error('ML Status Error:', data.error);
            document.getElementById('mlStatusContent').innerHTML = 
                `<div class="error">❌ ML status unavailable</div>`;
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
        
        statusHtml += '</div>';
        document.getElementById('mlStatusContent').innerHTML = statusHtml;
        
    } catch (error) {
        console.error('Error loading ML status:', error);
        document.getElementById('mlStatusContent').innerHTML = 
            `<div class="error">❌ Error loading ML status</div>`;
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
    
    showStatus('🎯 Starting ML model training (this may take 30-60 seconds)...', 'info', 60000);
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minute timeout
        
        const response = await fetch('/api/ml/train', { 
            method: 'POST',
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Training failed');
        }
        
        showStatus(`${data.message} (Trained on ${data.rows_trained || 'multiple'} data points)`, 'success', 8000);
        console.log('Training result:', data.training_result);
        
        
    } catch (error) {
        if (error.name === 'AbortError') {
            showStatus('⏱️ Training timed out. The model may still be training in the background.', 'warning', 8000);
        } else {
            showStatus(`❌ Training failed: ${error.message}`, 'error', 8000);
        }
        console.error('Training error:', error);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function refreshData() {
    await Promise.all([
        loadOverviewCards(),
        loadMarketConditions()
    ]);
}

// Called after auto-refresh succeeds — reloads entire dashboard
async function refreshData_afterAutoLoad() {
    console.log('Data became available — reloading entire dashboard...');
    await Promise.all([
        loadOverviewCards(),
        loadMarketConditions()
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

// ─── Live Trading Functions ──────────────────────────

async function proposeTrade(symbol, price, analysis) {
    try {
        const response = await fetch('/api/trades/auto-evaluate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                symbol: symbol,
                current_price: price,
                analysis: analysis,
                recommendation: analysis.recommendation || 'BUY',
            })
        });
        const result = await response.json();
        
        if (result.success && result.proposal_id) {
            showStatus(`📧 Trade proposal sent for ${symbol} — check your email!`, 'success', 6000);
        } else if (result.should_trade === false) {
            showStatus(`🤔 Agent decided not to trade ${symbol}: ${result.reason}`, 'info', 5000);
        } else {
            showStatus(`⚠️ ${result.error || 'Could not propose trade'}`, 'error');
        }
        return result;
    } catch (error) {
        console.error('Error proposing trade:', error);
        showStatus(`❌ Trade proposal failed: ${error.message}`, 'error');
        return {success: false, error: error.message};
    }
}
