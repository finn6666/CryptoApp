// Dashboard Overview Cards — fetches summary data for the main page

async function loadOverviewCards() {
    await Promise.all([
        loadPortfolioCard(),
        loadTradingCard(),
        loadScanCard(),
        loadMonitorCard(),
        loadExchangeCard(),
    ]);
}

// ─── Portfolio Summary ───────────────────────────────────────
async function loadPortfolioCard() {
    const valEl  = document.getElementById('sidebarPortfolioValue');
    const pnlEl  = document.getElementById('sidebarPortfolioPnl');
    const subEl  = document.getElementById('sidebarPortfolioSub');
    const listEl = document.getElementById('sidebarHoldingsList');
    if (!valEl) return;

    try {
        const res = await fetch('/api/portfolio/holdings', { headers: authHeaders() });

        if (res.status === 401) {
            valEl.textContent = '—';
            if (pnlEl) { pnlEl.textContent = 'Tap to set API key'; pnlEl.className = 'portfolio-card__pnl'; pnlEl.style.cursor = 'pointer'; pnlEl.onclick = () => openAuthModal(); }
            return;
        }

        const data = await res.json();
        if (data.error) throw new Error(data.error);

        const summary  = data.summary  || {};
        const holdings = data.holdings || [];

        const totalValue = summary.total_value_gbp ?? 0;
        const totalPnL   = summary.unrealised_pnl_gbp ?? 0;
        const totalCost  = summary.total_cost_gbp ?? 0;
        const pnlPct     = totalCost > 0 ? (totalPnL / totalCost) * 100 : null;

        if (holdings.length === 0) {
            valEl.textContent = '£0.00';
            if (pnlEl) { pnlEl.textContent = 'No open positions'; pnlEl.className = 'portfolio-card__pnl'; pnlEl.onclick = null; }
            if (subEl) subEl.textContent = '';
            if (listEl) listEl.style.display = 'none';
            return;
        }

        valEl.textContent = `£${Number(totalValue).toFixed(2)}`;

        if (pnlEl) {
            const sign = totalPnL >= 0 ? '+' : '';
            let txt = `${sign}£${Math.abs(Number(totalPnL)).toFixed(2)}`;
            if (pnlPct !== null) txt += ` (${sign}${Math.abs(Number(pnlPct)).toFixed(1)}%)`;
            pnlEl.textContent = txt;
            pnlEl.className = 'portfolio-card__pnl ' + (totalPnL >= 0 ? 'positive' : 'negative');
            pnlEl.onclick = null;
            pnlEl.style.cursor = '';
        }

        if (subEl) subEl.textContent = `${holdings.length} position${holdings.length !== 1 ? 's' : ''}`;

        if (listEl) {
            listEl.style.display = '';
            const sortedHoldings = [...holdings].sort((a, b) => (b.unrealised_pnl_pct ?? 0) - (a.unrealised_pnl_pct ?? 0));
            listEl.innerHTML = sortedHoldings.map(h => {
                const pct = h.unrealised_pnl_pct ?? 0;
                const val = h.current_value_gbp ?? 0;
                const cls = pct >= 0 ? 'positive' : 'negative';
                const sign = pct >= 0 ? '+' : '';
                return `<div class="holding-row">
                    <span class="holding-row__symbol">${escapeHtml(h.symbol)}</span>
                    <span class="holding-row__value">£${Number(val).toFixed(2)}</span>
                    <span class="holding-row__pnl ${cls}">${sign}${Number(pct).toFixed(1)}%</span>
                </div>`;
            }).join('');
        }
    } catch (e) {
        console.warn('Portfolio card:', e.message);
        valEl.textContent = '—';
        if (pnlEl) { pnlEl.textContent = 'Could not load'; pnlEl.className = 'portfolio-card__pnl'; }
    }
}

// ─── Trading Engine ──────────────────────────────────────────
async function loadTradingCard() {
    try {
        const res = await fetch('/api/trades/status', { headers: authHeaders() });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        const budget = data.remaining_today_gbp ?? data.remaining_budget ?? data.budget_remaining ?? data.daily_budget ?? null;
        const active = data.active_trades ?? data.open_trades ?? 0;
        const killSwitch = data.kill_switch ?? data.kill_switch_active ?? false;

        const valEl = document.getElementById('tradingBudget');
        const subEl = document.getElementById('tradingSub');

        if (killSwitch) {
            valEl.textContent = 'STOPPED';
            valEl.style.color = 'var(--error)';
            subEl.textContent = 'Kill switch active';
            subEl.className = 'overview-card-sub negative';
            return;
        }

        if (budget !== null) {
            valEl.textContent = `£${Number(budget).toFixed(2)}`;
        } else {
            valEl.textContent = 'Active';
        }
        valEl.style.color = '';

        let subParts = [];
        subParts.push(`${active} active trade${active !== 1 ? 's' : ''}`);
        if (data.trades_today !== undefined) {
            subParts.push(`${data.trades_today} today`);
        }
        subEl.textContent = subParts.join(' · ');
        subEl.className = 'overview-card-sub neutral';
    } catch (e) {
        console.warn('Trading card:', e.message);
        document.getElementById('tradingBudget').textContent = '—';
        document.getElementById('tradingSub').textContent = 'Unavailable';
        document.getElementById('tradingSub').className = 'overview-card-sub neutral';
    }
}

// ─── Scan Loop ───────────────────────────────────────────────
async function loadScanCard() {
    try {
        const res = await fetch('/api/trades/scan-status', { headers: authHeaders() });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        const status = data.status || {};
        const valEl = document.getElementById('scanStatus');
        const subEl = document.getElementById('scanSub');

        const running = status.scan_running ?? status.running ?? status.is_running ?? false;
        const scheduled = status.scheduler_running ?? status.scheduler_active ?? false;
        if (running) {
            valEl.textContent = '● Scanning';
            valEl.style.color = 'var(--warning)';
        } else if (scheduled) {
            valEl.textContent = '● Scheduled';
            valEl.style.color = 'var(--success)';
        } else {
            valEl.textContent = '○ Idle';
            valEl.style.color = 'var(--text-secondary)';
        }

        let subParts = [];
        if (status.last_scan) {
            const ago = timeAgo(status.last_scan);
            subParts.push(`Last: ${ago}`);
        }
        if (status.next_scan) {
            const next = timeAgo(status.next_scan, true);
            subParts.push(`Next: ${next}`);
        }
        if (status.coins_scanned) {
            subParts.push(`${status.coins_scanned} coins`);
        }
        if (status.total_scans) {
            subParts.push(`${status.total_scans} scans`);
        }
        subEl.textContent = subParts.length > 0 ? subParts.join(' · ') : 'No scan data yet';
        subEl.className = 'overview-card-sub neutral';
    } catch (e) {
        console.warn('Scan card:', e.message);
        document.getElementById('scanStatus').textContent = '—';
        document.getElementById('scanSub').textContent = 'Unavailable';
        document.getElementById('scanSub').className = 'overview-card-sub neutral';
    }
}

// ─── Market Monitor ──────────────────────────────────────────
async function loadMonitorCard() {
    try {
        const res = await fetch('/api/monitor/status', { headers: authHeaders() });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        const valEl = document.getElementById('monitorStatus');
        const subEl = document.getElementById('monitorSub');

        const running = data.running ?? false;
        const stats = data.stats || {};

        if (running) {
            valEl.textContent = '● Active';
            valEl.style.color = 'var(--success)';
        } else {
            valEl.textContent = '○ Off';
            valEl.style.color = 'var(--text-secondary)';
        }

        let subParts = [];
        if (stats.buy_proposals > 0) {
            subParts.push(`${stats.buy_proposals} buys`);
        }
        if (stats.alerts_fired > 0) {
            subParts.push(`${stats.alerts_fired} alerts`);
        }
        if (stats.price_checks > 0) {
            subParts.push(`${stats.price_checks} checks`);
        }
        if (stats.sell_proposals > 0) {
            subParts.push(`${stats.sell_proposals} sells`);
        }
        if (stats.quick_scans > 0) {
            subParts.push(`${stats.quick_scans} quick scans`);
        }
        if (subParts.length === 0 && running) {
            subParts.push('Warming up...');
        }
        const intervals = data.intervals || {};
        if (intervals.price_check_min) {
            subParts.push(`every ${intervals.price_check_min}m`);
        }
        subEl.textContent = subParts.length > 0 ? subParts.join(' · ') : 'Not running';
        subEl.className = 'overview-card-sub neutral';
    } catch (e) {
        console.warn('Monitor card:', e.message);
        document.getElementById('monitorStatus').textContent = '—';
        document.getElementById('monitorSub').textContent = 'Unavailable';
        document.getElementById('monitorSub').className = 'overview-card-sub neutral';
    }
}

// ─── Exchange Status ─────────────────────────────────────────
async function loadExchangeCard() {
    try {
        const res = await fetch('/api/exchanges/status');
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        const valEl = document.getElementById('exchangeStatus');
        const subEl = document.getElementById('exchangeSub');

        const exchanges = data.exchanges || {};
        const names = Object.keys(exchanges);
        const connected = names.filter(n => exchanges[n]?.connected || exchanges[n]?.status === 'connected');

        valEl.textContent = `${connected.length}/${names.length} Online`;
        valEl.style.color = connected.length === names.length ? 'var(--success)' : 'var(--warning)';

        let subParts = [];
        if (data.total_tradeable_coins) {
            subParts.push(`${data.total_tradeable_coins} pairs`);
        }
        if (connected.length > 0) {
            subParts.push(connected.map(n => n.charAt(0).toUpperCase() + n.slice(1)).join(', '));
        }
        subEl.textContent = subParts.length > 0 ? subParts.join(' · ') : 'No exchange data';
        subEl.className = 'overview-card-sub neutral';
    } catch (e) {
        console.warn('Exchange card:', e.message);
        document.getElementById('exchangeStatus').textContent = '—';
        document.getElementById('exchangeSub').textContent = 'Unavailable';
        document.getElementById('exchangeSub').className = 'overview-card-sub neutral';
    }
}

// ─── Helpers ─────────────────────────────────────────────────
function timeAgo(dateStr, future = false) {
    try {
        const d = new Date(dateStr);
        const now = new Date();
        const diffMs = future ? d - now : now - d;
        if (isNaN(diffMs)) return dateStr;

        const mins = Math.abs(Math.floor(diffMs / 60000));
        if (mins < 1) return future ? 'soon' : 'just now';
        if (mins < 60) return `${mins}m ${future ? '' : 'ago'}`.trim();

        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}h ${future ? '' : 'ago'}`.trim();

        const days = Math.floor(hrs / 24);
        return `${days}d ${future ? '' : 'ago'}`.trim();
    } catch {
        return dateStr;
    }
}
