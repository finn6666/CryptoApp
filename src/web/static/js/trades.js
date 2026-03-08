// Trade Journal & Live Trading Functions
// Extracted from trades.html inline script for merged dashboard

// ─── Auth Helper ────────────────────────────────────

function getApiKey() {
    let key = sessionStorage.getItem('tradingApiKey');
    if (!key) {
        key = prompt('Enter first 6 characters of your API key:');
        if (key) sessionStorage.setItem('tradingApiKey', key);
    }
    return key;
}

function authHeaders() {
    const key = getApiKey();
    if (!key) return null;
    return { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` };
}

// ─── Live Trading Functions ──────────────────────────

async function loadTradingStatus() {
    try {
        const response = await fetch('/api/trades/status');
        const data = await response.json();

        document.getElementById('budgetRemaining').textContent = `£${data.remaining_today_gbp.toFixed(2)}`;
        document.getElementById('tradesToday').textContent = data.trades_today || 0;

        const statusEl = document.getElementById('tradingStatus');
        if (!data.active) {
            statusEl.textContent = '⛔ HALTED';
            statusEl.style.background = 'rgba(245,101,101,0.2)';
            statusEl.style.color = '#fc8181';
            document.getElementById('killSwitchBtn').textContent = '▶️ Resume';
        } else {
            statusEl.textContent = '🟢 ACTIVE';
            statusEl.style.background = 'rgba(72,187,120,0.2)';
            statusEl.style.color = '#48bb78';
            document.getElementById('killSwitchBtn').textContent = '🛑 Kill Switch';
        }

        const configWarning = document.getElementById('configWarning');
        if (!data.exchange_configured || !data.email_configured) {
            configWarning.style.display = 'block';
            let warnings = [];
            if (!data.exchange_configured) warnings.push('Kraken API keys');
            if (!data.email_configured) warnings.push('Gmail SMTP credentials');
            configWarning.innerHTML = `⚠️ <strong>Setup required:</strong> Add ${warnings.join(' and ')} to <code>.env</code> — see <code>.env.example</code>`;
        } else {
            configWarning.style.display = 'none';
        }
    } catch (e) {
        console.error('Error loading trading status:', e);
    }
}

async function loadPendingProposals() {
    try {
        const response = await fetch('/api/trades/pending');
        const data = await response.json();
        const section = document.getElementById('pendingSection');
        const container = document.getElementById('pendingProposals');

        if (data.proposals && data.proposals.length > 0) {
            section.style.display = 'block';
            container.innerHTML = data.proposals.map(p => {
                const sideColor = p.side === 'buy' ? '#48bb78' : '#fc8181';
                const sideIcon = p.side === 'buy' ? '🟢' : '🔴';
                const created = new Date(p.created_at).toLocaleString();
                return `
                    <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-left: 3px solid ${sideColor}; border-radius: 8px; padding: 14px; margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div>
                                <span style="font-weight: 700; font-size: 15px;">${sideIcon} ${p.side.toUpperCase()} ${p.symbol}</span>
                                <span style="color: var(--text-secondary); font-size: 12px; margin-left: 8px;">£${p.amount_gbp.toFixed(2)}</span>
                            </div>
                            <div style="display: flex; gap: 6px;">
                                <button onclick="approveTrade('${p.id}')" style="padding: 6px 14px; background: linear-gradient(135deg, #38a169, #48bb78); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px;">✅ Approve</button>
                                <button onclick="rejectTrade('${p.id}')" style="padding: 6px 14px; background: linear-gradient(135deg, #e53e3e, #fc8181); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px;">❌ Reject</button>
                            </div>
                        </div>
                        <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.5;">
                            <div style="margin-bottom: 4px;">${p.reason}</div>
                            <div>Confidence: ${p.confidence}% • Price: £${p.price_at_proposal.toFixed(6)} • ${created}</div>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            section.style.display = 'none';
        }
    } catch (e) {
        console.error('Error loading proposals:', e);
    }
}

function formatPrice(price) {
    if (price === null || price === undefined || price === 0) return '—';
    return `£${Number(price).toFixed(6)}`;
}

async function loadExecutedTrades() {
    try {
        const [execRes, histRes] = await Promise.all([
            fetch('/api/trades/history'),
            fetch('/api/portfolio/history?limit=100')
        ]);
        const execData = await execRes.json();
        const histData = await histRes.json();
        const container = document.getElementById('tradeLogUnified');

        const allTrades = [];

        if (execData.trades) {
            execData.trades.forEach(t => {
                allTrades.push({
                    symbol: t.symbol,
                    side: t.side,
                    quantity: t.quantity,
                    price: t.price,
                    amount_gbp: t.amount_gbp,
                    fee_gbp: t.fee_gbp || 0,
                    exchange: t.exchange || '—',
                    timestamp: t.timestamp,
                    reasoning: t.reason || t.reasoning || '',
                    realised_pnl_gbp: t.realised_pnl_gbp,
                    source: 'engine',
                });
            });
        }

        if (histData.trades) {
            histData.trades.forEach(t => {
                const isDupe = allTrades.some(
                    e => e.symbol === t.symbol && e.timestamp === t.timestamp && e.side === t.side
                );
                if (!isDupe) {
                    allTrades.push({
                        symbol: t.symbol,
                        side: t.side,
                        quantity: t.quantity || 0,
                        price: t.price || 0,
                        amount_gbp: t.amount_gbp || 0,
                        fee_gbp: t.fee_gbp || 0,
                        exchange: t.exchange || '—',
                        timestamp: t.timestamp,
                        reasoning: t.reasoning || '',
                        realised_pnl_gbp: t.realised_pnl_gbp,
                        source: 'portfolio',
                    });
                }
            });
        }

        allTrades.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        if (allTrades.length > 0) {
            container.innerHTML = allTrades.map(t => {
                const isBuy = t.side === 'buy';
                const sideColor = isBuy ? '#48bb78' : '#fc8181';
                const sideIcon = isBuy ? '🟢' : '🔴';
                const time = new Date(t.timestamp).toLocaleString();
                const priceDisplay = (t.price && t.price > 0) ? `£${Number(t.price).toFixed(6)}` : '—';
                const pnlStr = t.realised_pnl_gbp !== undefined && t.realised_pnl_gbp !== null
                    ? ` • P&L: ${t.realised_pnl_gbp >= 0 ? '+' : ''}£${t.realised_pnl_gbp.toFixed(2)}`
                    : '';
                return `
                    <div style="display: flex; gap: 10px; align-items: flex-start; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.03); font-size: 13px;">
                        <span>${sideIcon}</span>
                        <div style="flex: 1;">
                            <span style="font-weight: 700;">${t.symbol}</span>
                            <span style="color: ${sideColor}; font-weight: 600; margin-left: 6px;">${t.side.toUpperCase()}</span>
                            <span style="color: var(--text-secondary);"> ${(t.quantity || 0).toFixed(6)} @ ${priceDisplay}</span>
                            <div style="color: var(--text-secondary); font-size: 11px; margin-top: 3px;">
                                £${(t.amount_gbp || 0).toFixed(2)} • ${t.exchange} • Fee: £${(t.fee_gbp || 0).toFixed(2)}${pnlStr}
                            </div>
                            ${t.reasoning ? `<div style="color: var(--text-secondary); font-size: 11px; margin-top: 2px; font-style: italic;">"${t.reasoning.substring(0, 120)}${t.reasoning.length > 120 ? '…' : ''}"</div>` : ''}
                        </div>
                        <span style="color: var(--text-secondary); font-size: 11px; white-space: nowrap;">${time}</span>
                    </div>
                `;
            }).join('');
        } else {
            container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 20px; font-size: 13px;">No trades yet. Agents will propose trades when they find high-conviction opportunities.</p>';
        }
    } catch (e) {
        console.error('Error loading trade log:', e);
    }
}

async function approveTrade(proposalId) {
    if (!confirm('Approve and execute this trade?')) return;
    try {
        const response = await fetch(`/api/trades/approve/${proposalId}`, {
            method: 'POST'
        });
        const data = await response.json();
        if (data.success) {
            showTradeAlert(`✅ Trade approved — ${data.side?.toUpperCase()} ${data.symbol}`, 'success');
        } else {
            showTradeAlert(`⚠️ ${data.error || 'Could not approve'}`, 'error');
        }
        setTimeout(() => {
            loadPendingProposals();
            loadExecutedTrades();
            loadTradingStatus();
            loadTradesPortfolio();
        }, 1000);
    } catch (e) {
        showTradeAlert('Error approving trade: ' + e.message, 'error');
    }
}

async function rejectTrade(proposalId) {
    if (!confirm('Reject this trade proposal?')) return;
    try {
        const response = await fetch(`/api/trades/reject/${proposalId}`, {
            method: 'POST'
        });
        const data = await response.json();
        if (data.success) {
            showTradeAlert('Trade rejected', 'success');
        } else {
            showTradeAlert(`⚠️ ${data.error || 'Could not reject'}`, 'error');
        }
        loadPendingProposals();
    } catch (e) {
        showTradeAlert('Error rejecting trade: ' + e.message, 'error');
    }
}

async function toggleKillSwitch() {
    const btn = document.getElementById('killSwitchBtn');
    const isHalted = btn.textContent.includes('Resume');
    const action = isHalted ? 'deactivate' : 'activate';

    if (!isHalted && !confirm('⛔ This will HALT all trading and reject pending proposals. Continue?')) return;

    const hdrs = authHeaders();
    if (!hdrs) return;
    try {
        await fetch('/api/trades/kill-switch', {
            method: 'POST',
            headers: hdrs,
            body: JSON.stringify({action})
        });
        showTradeAlert(isHalted ? 'Trading resumed' : 'Trading HALTED — all pending proposals rejected', isHalted ? 'success' : 'error');
        loadTradingStatus();
        loadPendingProposals();
    } catch (e) {
        showTradeAlert('Error toggling kill switch: ' + e.message, 'error');
    }
}

// ─── Scan Functions ───────────────────────────────────

async function loadScanStatusDetail() {
    try {
        const response = await fetch('/api/trades/scan-status');
        const data = await response.json();
        const status = data.status || {};

        const statusEl = document.getElementById('scanStatusDetail');
        if (status.scan_running) {
            statusEl.textContent = '⏳ Running';
            statusEl.style.background = 'rgba(237,137,54,0.2)';
            statusEl.style.color = '#ed8936';
        } else if (status.scheduler_active) {
            statusEl.textContent = '🟢 Scheduled';
            statusEl.style.background = 'rgba(72,187,120,0.2)';
            statusEl.style.color = '#48bb78';
        } else {
            statusEl.textContent = '⚪ Off';
            statusEl.style.background = 'rgba(255,255,255,0.05)';
            statusEl.style.color = 'var(--text-secondary)';
        }

        if (status.next_scan) {
            const next = new Date(status.next_scan);
            const now = new Date();
            const diffMs = next - now;
            if (diffMs > 0) {
                const diffH = Math.floor(diffMs / 3600000);
                const diffM = Math.floor((diffMs % 3600000) / 60000);
                document.getElementById('scanNextTime').textContent = diffH > 0 ? `${diffH}h ${diffM}m` : `${diffM}m`;
            } else {
                document.getElementById('scanNextTime').textContent = 'Soon';
            }
        } else if (status.scan_interval_hours && status.scan_interval_hours > 0) {
            document.getElementById('scanNextTime').textContent = `Every ${status.scan_interval_hours}h`;
        } else {
            document.getElementById('scanNextTime').textContent = status.scan_time || '—';
        }
        document.getElementById('scanLastRun').textContent = status.last_scan
            ? new Date(status.last_scan).toLocaleString()
            : 'Never';

        const logs = data.recent_logs || [];
        if (logs.length > 0) {
            const latest = logs[logs.length - 1];
            document.getElementById('scanCoinsAnalysed').textContent = latest.coins_analysed || 0;
            document.getElementById('scanProposals').textContent = latest.proposals_made || 0;
        }
    } catch (e) {
        console.error('Error loading scan status:', e);
    }
}

async function triggerScan() {
    const btn = document.getElementById('scanNowBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Scanning...';
    const resultEl = document.getElementById('scanResultMsg');

    try {
        const hdrs = authHeaders();
        if (!hdrs) { btn.disabled = false; btn.textContent = '🔍 Scan Now'; return; }

        const response = await fetch('/api/trades/scan-now', {
            method: 'POST',
            headers: hdrs
        });
        const data = await response.json();

        resultEl.style.display = 'block';
        if (data.success) {
            resultEl.style.borderColor = 'var(--success)';
            resultEl.style.background = 'rgba(72,187,120,0.1)';
            resultEl.innerHTML = `✅ Scan complete — <strong>${data.coins_analysed}</strong> coins analysed, <strong>${data.proposals_made}</strong> proposals made, <strong>${data.errors?.length || 0}</strong> errors`;
        } else {
            resultEl.style.borderColor = 'var(--error)';
            resultEl.style.background = 'rgba(245,101,101,0.1)';
            resultEl.innerHTML = `⚠️ ${data.error || 'Scan failed'}`;
        }

        loadScanStatusDetail();
        loadPendingProposals();
    } catch (e) {
        resultEl.style.display = 'block';
        resultEl.innerHTML = `❌ Network error: ${e.message}`;
    } finally {
        btn.disabled = false;
        btn.textContent = '🔍 Scan Now';
    }
}

// ─── Portfolio Functions ──────────────────────────────

async function refreshTradesPortfolio() {
    const btn = document.getElementById('portfolioRefreshBtn');
    const origText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '⏳ Refreshing...';
    try {
        await loadTradesPortfolio();
        btn.textContent = '✅ Updated';
        setTimeout(() => { btn.textContent = origText; btn.disabled = false; }, 1500);
    } catch (e) {
        btn.textContent = '❌ Error';
        setTimeout(() => { btn.textContent = origText; btn.disabled = false; }, 2000);
    }
}

async function loadTradesPortfolio() {
    try {
        const response = await fetch('/api/portfolio/holdings');
        const data = await response.json();
        const holdings = data.holdings || [];
        const summary = data.summary || {};

        document.getElementById('tpValue').textContent = `£${(summary.total_value_gbp || 0).toFixed(2)}`;
        document.getElementById('tpCount').textContent = summary.active_holdings || 0;
        document.getElementById('tpTotalTrades').textContent = summary.total_trades || 0;
        document.getElementById('tpFees').textContent = `£${(summary.total_fees_gbp || 0).toFixed(2)}`;

        const now = new Date();
        document.getElementById('portfolioUpdated').textContent = `Updated ${now.toLocaleTimeString()}`;

        const pnlEl = document.getElementById('tpPnl');
        const unrealisedPnl = summary.unrealised_pnl_gbp || 0;
        pnlEl.textContent = `${unrealisedPnl >= 0 ? '+' : ''}£${unrealisedPnl.toFixed(2)}`;
        pnlEl.style.color = unrealisedPnl >= 0 ? 'var(--success)' : 'var(--error)';

        const realisedEl = document.getElementById('tpRealisedPnl');
        const realisedPnl = summary.realised_pnl_gbp || 0;
        realisedEl.textContent = `${realisedPnl >= 0 ? '+' : ''}£${realisedPnl.toFixed(2)}`;
        realisedEl.style.color = realisedPnl >= 0 ? 'var(--success)' : 'var(--error)';

        const container = document.getElementById('holdingsList');

        if (holdings.length > 0) {
            container.innerHTML = `<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px;">` + holdings.map(h => {
                const pnlPct = h.unrealised_pnl_pct || 0;
                const pnlGbp = h.unrealised_pnl_gbp || 0;
                const isUp = pnlGbp >= 0;
                const pnlColor = isUp ? '#48bb78' : '#fc8181';
                const pnlBg = isUp ? 'rgba(72,187,120,0.1)' : 'rgba(252,129,129,0.1)';
                const borderAccent = isUp ? 'rgba(72,187,120,0.3)' : 'rgba(252,129,129,0.3)';
                const arrow = isUp ? '▲' : '▼';
                return `
                <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-top: 3px solid ${borderAccent}; border-radius: 10px; padding: 16px; display: flex; flex-direction: column; gap: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 18px; font-weight: 700; color: var(--text-primary);">${h.symbol}</span>
                        <span style="font-size: 12px; font-weight: 600; color: ${pnlColor}; background: ${pnlBg}; padding: 3px 10px; border-radius: 6px;">${arrow} ${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%</span>
                    </div>
                    <div style="font-size: 20px; font-weight: 700; color: var(--text-primary);">£${(h.current_value_gbp || 0).toFixed(2)}</div>
                    <div style="display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-secondary);">
                        <div style="display: flex; justify-content: space-between;"><span>Cost</span><span>£${(h.total_cost_gbp || 0).toFixed(2)}</span></div>
                        <div style="display: flex; justify-content: space-between;"><span>P&L</span><span style="color: ${pnlColor}; font-weight: 600;">${pnlGbp >= 0 ? '+' : ''}£${pnlGbp.toFixed(2)}</span></div>
                        <div style="display: flex; justify-content: space-between;"><span>Qty</span><span>${h.quantity?.toFixed(4) || 0}</span></div>
                        <div style="display: flex; justify-content: space-between;"><span>Exchange</span><span>${h.exchange || '—'}</span></div>
                    </div>
                </div>`;
            }).join('') + `</div>`;
        } else {
            container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 20px; font-size: 13px;">No holdings yet. The portfolio tracker records every executed trade automatically.</p>';
        }
    } catch (e) {
        console.error('Error loading portfolio:', e);
    }
}

// ─── Market State ────────────────────────────────────

async function loadMarketState() {
    const el = document.getElementById('fngDisplay');
    const headlinesEl = document.getElementById('marketHeadlines');
    const statsEl = document.getElementById('globalStats');
    try {
        const response = await fetch('/api/market/state');
        const data = await response.json();

        if (data.error || data.current_value === null) {
            el.innerHTML = '<span style="color: var(--text-secondary); font-size: 13px;">Unavailable</span>';
            headlinesEl.innerHTML = '';
            return;
        }

        const val = data.current_value;
        const cls = data.classification;
        const trend = data.trend || '';

        let color, bg;
        if (val <= 20) { color = '#fc8181'; bg = 'rgba(252,129,129,0.12)'; }
        else if (val <= 35) { color = '#f6ad55'; bg = 'rgba(246,173,85,0.12)'; }
        else if (val <= 55) { color = '#ecc94b'; bg = 'rgba(236,201,75,0.12)'; }
        else if (val <= 75) { color = '#68d391'; bg = 'rgba(104,211,145,0.12)'; }
        else { color = '#48bb78'; bg = 'rgba(72,187,120,0.12)'; }

        let trendIcon = '';
        if (trend === 'IMPROVING') trendIcon = ' ↗';
        else if (trend === 'DETERIORATING') trendIcon = ' ↘';
        else if (trend === 'STABLE') trendIcon = ' →';

        let sparkline = '';
        if (data.history_7d && data.history_7d.length > 1) {
            const vals = data.history_7d.map(h => h.value).reverse();
            const max = Math.max(...vals, 1);
            sparkline = `<div style="display: flex; align-items: flex-end; gap: 2px; height: 20px; margin-left: 4px;">` +
                vals.map(v => {
                    const h = Math.max(3, (v / max) * 20);
                    let barColor;
                    if (v <= 20) barColor = '#fc8181';
                    else if (v <= 35) barColor = '#f6ad55';
                    else if (v <= 55) barColor = '#ecc94b';
                    else if (v <= 75) barColor = '#68d391';
                    else barColor = '#48bb78';
                    return `<div style="width: 4px; height: ${h}px; background: ${barColor}; border-radius: 1px; opacity: 0.7;"></div>`;
                }).join('') + `</div>`;
        }

        el.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px; background: ${bg}; border: 1px solid ${color}33; border-radius: 8px; padding: 6px 12px;">
                <span style="font-size: 22px; font-weight: 700; color: ${color};">${val}</span>
                <div>
                    <div style="font-size: 13px; font-weight: 600; color: ${color};">${cls}${trendIcon}</div>
                </div>
                ${sparkline}
            </div>
            <span style="font-size: 12px; color: var(--text-secondary); font-style: italic;">${data.trading_signal || ''}</span>
        `;

        const gs = data.global_stats || {};
        if (gs.btc_dominance) {
            const mcapChange = gs.market_cap_change_24h || 0;
            const mcapColor = mcapChange >= 0 ? '#68d391' : '#fc8181';
            const mcapArrow = mcapChange >= 0 ? '▲' : '▼';
            statsEl.innerHTML = `
                <span style="font-size: 12px; color: var(--text-secondary);">BTC ${gs.btc_dominance}%</span>
                <span style="font-size: 11px; color: rgba(255,255,255,0.15);">|</span>
                <span style="font-size: 12px; color: ${mcapColor};">${mcapArrow} ${Math.abs(mcapChange).toFixed(1)}% 24h</span>
            `;
        }

        const headlines = data.headlines || [];
        if (headlines.length > 0) {
            headlinesEl.innerHTML = `
                <div style="display: flex; flex-direction: column; gap: 6px;">
                    ${headlines.map(h => `
                        <div style="display: flex; align-items: flex-start; gap: 8px; line-height: 1.4;">
                            <span style="color: rgba(255,255,255,0.15); font-size: 11px; flex-shrink: 0; margin-top: 2px;">●</span>
                            <div>
                                <a href="${h.link}" target="_blank" rel="noopener noreferrer"
                                   style="font-size: 12px; color: var(--text-secondary); text-decoration: none; transition: color 0.15s;"
                                   onmouseover="this.style.color='var(--text-primary)'"
                                   onmouseout="this.style.color='var(--text-secondary)'">
                                    ${h.title}
                                </a>
                                <span style="font-size: 10px; color: rgba(255,255,255,0.2); margin-left: 6px;">${h.source}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } else {
            headlinesEl.innerHTML = '<div style="color: var(--text-secondary); font-size: 12px;">No headlines available</div>';
        }
    } catch (e) {
        el.innerHTML = '<span style="color: var(--text-secondary); font-size: 13px;">Unavailable</span>';
        headlinesEl.innerHTML = '';
        console.error('Error loading market state:', e);
    }
}

// ─── RL Insights ─────────────────────────────────────

async function loadRlInsights() {
    try {
        const response = await fetch('/api/rl/insights');
        const data = await response.json();
        const insights = data.insights || [];
        const container = document.getElementById('rlInsights');

        if (insights.length > 0) {
            container.innerHTML = `<ul style="list-style: none; padding: 0; margin: 0;">${insights.map(text =>
                `<li style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04); font-size: 13px; color: var(--text-secondary); line-height: 1.5;"><span style="color: var(--text-secondary); margin-right: 8px;">&#8226;</span>${text}</li>`
            ).join('')}</ul>`;
        } else {
            container.innerHTML = '<p style="color: var(--text-secondary); font-size: 13px; padding: 12px 0;">Nothing to report yet.</p>';
        }
    } catch (e) {
        console.error('Error loading RL insights:', e);
    }
}

// ─── Closed Positions ────────────────────────────────

async function loadClosedPositions() {
    try {
        const response = await fetch('/api/portfolio/closed');
        const data = await response.json();
        const positions = data.positions || [];
        const container = document.getElementById('closedPositions');

        if (positions.length > 0) {
            container.innerHTML = positions.map(p => {
                const won = p.won;
                const pnlColor = won ? '#48bb78' : '#fc8181';
                const icon = won ? '✅' : '❌';
                const closedDate = p.closed_at ? new Date(p.closed_at).toLocaleDateString() : '—';
                return `
                    <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-left: 3px solid ${pnlColor}; border-radius: 8px; padding: 14px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="font-weight: 700; font-size: 15px;">${icon} ${p.symbol}</span>
                                <span style="color: var(--text-secondary); font-size: 12px; margin-left: 8px;">${p.trades} trades</span>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-weight: 700; color: ${pnlColor}; font-size: 14px;">${p.realised_pnl_gbp >= 0 ? '+' : ''}£${p.realised_pnl_gbp.toFixed(2)}</div>
                                <div style="font-size: 11px; color: var(--text-secondary);">Cost: £${p.total_cost_gbp.toFixed(2)} • Fees: £${p.total_fees_gbp.toFixed(2)}</div>
                            </div>
                        </div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 6px;">
                            Exchange: ${p.exchange || '—'} • Closed: ${closedDate}
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 20px; font-size: 13px;">No closed positions yet.</p>';
        }
    } catch (e) {
        console.error('Error loading closed positions:', e);
    }
}

// ─── Trade Log ───────────────────────────────────────

async function loadTradeLog() {
    await loadExecutedTrades();
}

// ─── Activity Log ────────────────────────────────────

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function truncate(str, max) {
    if (!str || str.length <= max) return str;
    return str.slice(0, max) + '…';
}

async function loadActivityLog() {
    try {
        const response = await fetch('/api/trades/audit-trail?limit=50');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        const entries = data.entries || [];
        const container = document.getElementById('activityLog');

        if (entries.length > 0) {
            container.innerHTML = entries.map(e => {
                const time = new Date(e.timestamp).toLocaleString();
                let icon = '📋', color = 'var(--text-secondary)';
                if (e.event === 'proposal') { icon = '📨'; color = '#667eea'; }
                else if (e.event === 'sell_proposal') { icon = '📤'; color = '#ed8936'; }
                else if (e.event === 'skip') { icon = '⏭️'; color = 'var(--text-secondary)'; }
                else if (e.event === 'scan_start') { icon = '🔍'; color = '#ed8936'; }
                else if (e.event === 'scan_complete') { icon = '✅'; color = '#48bb78'; }
                else if (e.event === 'trade_executed') { icon = '💰'; color = '#48bb78'; }
                else if (e.event === 'trade_failed') { icon = '⚠️'; color = '#fc8181'; }
                else if (e.event === 'error') { icon = '❌'; color = '#fc8181'; }
                else if (e.event === 'scan_no_coins') { icon = '⚠️'; color = '#ecc94b'; }
                else if (e.event === 'budget_exhausted') { icon = '💸'; color = '#ecc94b'; }

                let detail = '';
                if (e.symbol) detail += `<strong>${escapeHtml(e.symbol)}</strong> `;
                if (e.side) detail += `${escapeHtml(e.side.toUpperCase())} `;
                if (e.amount_gbp) detail += `£${Number(e.amount_gbp).toFixed(2)} `;
                if (e.price && Number(e.price) > 0) detail += `@ £${Number(e.price).toFixed(6)} `;
                if (e.exchange) detail += `on ${escapeHtml(e.exchange)} `;
                if (e.reason) detail += `— ${escapeHtml(truncate(e.reason, 120))} `;
                if (e.confidence) detail += `(${Number(e.confidence)}% conf) `;
                if (e.proposals !== undefined) detail += `${Number(e.proposals)} proposals `;
                if (e.error) detail += `— ${escapeHtml(truncate(e.error, 120))} `;

                return `<div style="display: flex; gap: 10px; align-items: flex-start; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.03); font-size: 13px;">
                    <span>${icon}</span>
                    <div style="flex: 1;">
                        <span style="color: ${color}; font-weight: 600;">${escapeHtml(e.event)}</span>
                        <span style="color: var(--text-secondary);"> ${detail}</span>
                    </div>
                    <span style="color: var(--text-secondary); font-size: 11px; white-space: nowrap;">${time}</span>
                </div>`;
            }).join('');
        } else {
            container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 20px; font-size: 13px;">No activity yet. Activity will appear here when scans run and trades are proposed.</p>';
        }
    } catch (e) {
        console.error('Error loading activity log:', e);
        const container = document.getElementById('activityLog');
        if (container && container.textContent.includes('Loading')) {
            container.innerHTML = '<p style="color: #fc8181; text-align: center; padding: 20px; font-size: 13px;">Failed to load activity log.</p>';
        }
    }
}

// ─── Stats ───────────────────────────────────────────

async function loadTradeStats() {
    try {
        const response = await fetch('/api/portfolio/performance');
        const data = await response.json();

        document.getElementById('totalTrades').textContent = data.total_trades || 0;
        document.getElementById('winRate').textContent = (data.win_rate_pct || 0).toFixed(1) + '%';
        document.getElementById('winningTrades').textContent = data.winning_trades || 0;
        document.getElementById('losingTrades').textContent = data.losing_trades || 0;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// ─── Alert ───────────────────────────────────────────

function showTradeAlert(message, type = 'success') {
    const alertEl = document.getElementById('tradeAlert');
    const messageEl = document.getElementById('tradeAlertMessage');
    if (!alertEl || !messageEl) return;
    
    messageEl.textContent = message;
    alertEl.className = `alert ${type} show`;
    
    setTimeout(() => {
        alertEl.classList.remove('show');
    }, 5000);
}

// ─── Init Trading Sections ───────────────────────────

function initTradingSections() {
    loadTradeStats();
    loadTradingStatus();
    loadPendingProposals();
    loadExecutedTrades();
    loadScanStatusDetail();
    loadTradesPortfolio();
    loadMarketState();
    loadClosedPositions();
    loadRlInsights();
    loadActivityLog();

    // Periodic refresh
    setInterval(loadPendingProposals, 30000);
    setInterval(loadTradingStatus, 30000);
    setInterval(loadScanStatusDetail, 60000);
    setInterval(loadTradesPortfolio, 60000);
    setInterval(loadMarketState, 600000);
    setInterval(loadActivityLog, 30000);
}
