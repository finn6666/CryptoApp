// API and Data Loading Functions

// ─── Dashboard Summary (single-call status) ───────────────────

/**
 * Fetch /api/dashboard-summary once and populate the compact status strip
 * and sidebar panel stats. Reduces 5 parallel card fetches to 1 call.
 */
async function loadDashboardSummary(prefetchedData = null) {
    try {
        const data = prefetchedData || await fetch('/api/dashboard-summary', { headers: authHeaders() }).then(r => r.json());

        // Budget pill
        _updatePill('pillBudget', () => {
            const t = data.trading || {};
            if (t.kill_switch) return { value: 'HALTED', cls: 'warning' };
            const b = t.remaining_today_gbp ?? t.remaining_budget ?? t.budget_remaining ?? t.daily_budget ?? null;
            return { value: b !== null ? `£${Number(b).toFixed(2)}` : 'Active' };
        });

        // Scanner pill
        _updatePill('pillScanner', () => {
            const s = data.scanner || {};
            const running   = s.scan_running ?? s.running ?? s.is_running ?? false;
            const scheduled = s.scheduler_running ?? s.scheduler_active ?? false;
            if (running)   return { value: '● Scanning', cls: 'warning' };
            if (scheduled) return { value: '● Scheduled', cls: 'positive' };
            return { value: '○ Idle' };
        });

        // Monitor pill
        _updatePill('pillMonitor', () => {
            const m = data.monitor || {};
            const running = m.running ?? false;
            return { value: running ? '● Active' : '○ Off', cls: running ? 'positive' : '' };
        });

        // Populate sidebar scanner stats
        const s = data.scanner || {};
        _setText('sbScanNext',     s.next_scan  ? timeAgo(s.next_scan, true) : '—');
        _setText('sbScanLast',     s.last_scan  ? timeAgo(s.last_scan)       : 'Never');
        _setText('sbScanCoins',    s.coins_scanned ?? 0);
        _setText('sbScanProposals',s.total_proposals ?? s.proposals_made ?? 0);

        // Populate sidebar scan-status badge
        const scanBadge = document.getElementById('scanStatusDetail');
        if (scanBadge) {
            const running   = s.scan_running ?? s.running ?? false;
            const scheduled = s.scheduler_running ?? s.scheduler_active ?? false;
            scanBadge.textContent = running ? '● Scanning' : scheduled ? '● Scheduled' : '○ Idle';
            scanBadge.style.color = running ? 'var(--warning)' : scheduled ? 'var(--success)' : 'var(--text-secondary)';
        }

    } catch (e) {
        console.warn('Dashboard summary error:', e.message);
    }
}

function _updatePill(id, fn) {
    const pill = document.getElementById(id);
    if (!pill) return;
    try {
        const { value, cls } = fn();
        pill.textContent = value;
        pill.className = 'st-val' + (cls ? ' ' + cls : '');
    } catch (e) {
        pill.textContent = '—';
    }
}

function _setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

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
                const refreshRes = await fetch('/api/refresh', { method: 'POST', headers: authHeadersJson() });
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
                `<div class="error">ML status unavailable</div>`;
            return;
        }

        const status = data.ml_status;
        const isEnabled = status.model_trained && status.model_loaded;
        
        let statusHtml = '<div class="ml-status-summary-row">';
        
        statusHtml += `
            <div class="ml-status-item ${isEnabled ? 'success' : 'warning'}">
                <span class="ml-status-label">Status</span>
                <span class="ml-status-value">${isEnabled ? 'Active' : 'Inactive'}</span>
            </div>
        `;

        if (status.model_trained) {
            statusHtml += `
                <div class="ml-status-item">
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
            `<div class="error">Error loading ML status</div>`;
    }
}

async function refreshMLStatus() {
    const btn = document.getElementById('refreshMLBtn');
    if (!btn) return;
    
    const originalText = btn.textContent;
    btn.textContent = 'Refreshing...';
    btn.disabled = true;

    try {
        await loadMLStatus();
        btn.textContent = 'Refreshed!';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 2000);
    } catch (error) {
        btn.textContent = 'Error';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 2000);
    }
}

async function trainMLModel() {
    const btn = document.getElementById('trainBtn');
    const originalText = btn.textContent;
    
    btn.textContent = 'Training...';
    btn.disabled = true;

    showStatus('Starting ML model training (this may take 30-60 seconds)...', 'info', 60000);
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minute timeout
        
        const response = await fetch('/api/ml/train', { 
            method: 'POST',
            headers: authHeadersJson(),
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
            showStatus('Training timed out. The model may still be training in the background.', 'warning', 8000);
        } else {
            showStatus(`Training failed: ${error.message}`, 'error', 8000);
        }
        console.error('Training error:', error);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function refreshData() {
    await Promise.all([
        loadDashboardSummary(),
        loadMarketConditions(),
        loadHeatmap(),
    ]);
}

// Called after auto-refresh succeeds — reloads entire dashboard
async function refreshData_afterAutoLoad() {
    console.log('Data became available — reloading entire dashboard...');
    await Promise.all([
        loadDashboardSummary(),
        loadMarketConditions(),
        loadHeatmap(),
    ]);
}

async function forceRefresh() {
    if (refreshing) return;

    const btn = document.getElementById('refreshBtn');
    refreshing = true;
    if (btn) { btn.textContent = 'Refreshing...'; btn.disabled = true; }

    try {
        const response = await fetch('/api/refresh', { method: 'POST', headers: authHeadersJson() });
        const data = await response.json();

        if (data.success) {
            showStatus('Data refreshed successfully', 'success');
            await refreshData();
        } else {
            throw new Error(data.error || 'Refresh failed');
        }
    } catch (error) {
        console.error('Error refreshing data:', error);
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        refreshing = false;
        if (btn) { btn.textContent = 'Refresh'; btn.disabled = false; }
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
            showStatus(`Trade proposal sent for ${symbol} — check your email`, 'success', 6000);
        } else if (result.should_trade === false) {
            showStatus(`Agent decided not to trade ${symbol}: ${result.reason}`, 'info', 5000);
        } else {
            showStatus(result.error || 'Could not propose trade', 'error');
        }
        return result;
    } catch (error) {
        console.error('Error proposing trade:', error);
        showStatus(`Trade proposal failed: ${error.message}`, 'error');
        return {success: false, error: error.message};
    }
}
