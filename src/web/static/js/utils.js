// Utility Functions

// ─── HTML Escaping ─────────────────────────────────────────

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(String(str)));
    return div.innerHTML;
}

// ─── Auth ──────────────────────────────────────────────────

/** Return stored API key from sessionStorage (cleared on tab close). */
function getApiKey() {
    return sessionStorage.getItem('tradingApiKey');
}

/** Persist API key to sessionStorage. */
function setApiKey(key) {
    if (key) {
        sessionStorage.setItem('tradingApiKey', key.trim());
    } else {
        sessionStorage.removeItem('tradingApiKey');
    }
}

/** Headers for authenticated GET requests. Returns {} if no key stored. */
function authHeaders() {
    const key = getApiKey();
    if (!key) return {};
    return { 'Authorization': `Bearer ${key}` };
}

/** Headers for authenticated POST requests (includes Content-Type). Returns {} if no key stored. */
function authHeadersJson() {
    const key = getApiKey();
    if (!key) return {};
    return { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` };
}


function updateRefreshStatus(lastUpdated, cacheExpiresIn) {
    const lastUpdatedEl = document.getElementById('lastUpdated');
    const nextRefreshEl = document.getElementById('nextRefresh');

    if (lastUpdated && lastUpdatedEl) {
        const date = new Date(lastUpdated);
        const now = new Date();
        const minutesAgo = Math.floor((now - date) / 60000);

        if (minutesAgo < 1) {
            lastUpdatedEl.textContent = 'Just now';
        } else if (minutesAgo < 60) {
            lastUpdatedEl.textContent = `${minutesAgo}m ago`;
        } else {
            const hoursAgo = Math.floor(minutesAgo / 60);
            lastUpdatedEl.textContent = `${hoursAgo}h ago`;
        }
    }

    if (cacheExpiresIn !== undefined && cacheExpiresIn !== null && nextRefreshEl) {
        const minutes = Math.floor(cacheExpiresIn / 60);
        const seconds = cacheExpiresIn % 60;

        if (minutes > 0) {
            nextRefreshEl.textContent = `${minutes}m ${seconds}s`;
        } else {
            nextRefreshEl.textContent = `${seconds}s`;
        }
    }
}

function startRefreshTimer() {
    setInterval(() => {
        refreshData();
    }, 300000); // 5 minutes — fallback when SSE is unavailable
}

// ─── Portfolio Holdings Cache ───────────────────────────────
// Deduplicates concurrent calls to /api/portfolio/holdings.
// loadPortfolioCard (SSE-driven, ~30s) and loadHeatmap (60s interval)
// both need this data — the cache prevents double-fetching when they fire close together.

let _holdingsCache = { data: null, expiry: 0, promise: null };

async function fetchPortfolioHoldings() {
    const now = Date.now();
    if (_holdingsCache.data && now < _holdingsCache.expiry) return _holdingsCache.data;
    if (_holdingsCache.promise) return _holdingsCache.promise;

    _holdingsCache.promise = fetch('/api/portfolio/holdings', { headers: authHeaders() })
        .then(r => {
            if (!r.ok) { const err = new Error('HTTP ' + r.status); err.status = r.status; throw err; }
            return r.json();
        })
        .then(data => {
            _holdingsCache.data = data;
            _holdingsCache.expiry = Date.now() + 30000; // 30s TTL
            _holdingsCache.promise = null;
            return data;
        })
        .catch(e => {
            _holdingsCache.promise = null;
            throw e;
        });
    return _holdingsCache.promise;
}

// ─── SSE Dashboard Stream ───────────────────────────────────
// Replaces the setInterval soup in initTradingSections().
// The server sends one event with all sidebar data then closes;
// the browser auto-reconnects after 30s (set via SSE retry field).
// Thread on the Pi is only held during the actual data fetch, not idle.

let _sseSource = null;

function startDashboardSSE() {
    if (_sseSource) { _sseSource.close(); _sseSource = null; }

    const key = getApiKey();
    const url = key
        ? `/api/stream/dashboard?key=${encodeURIComponent(key)}`
        : '/api/stream/dashboard';

    _sseSource = new EventSource(url);

    _sseSource.onmessage = (evt) => {
        try {
            const d = JSON.parse(evt.data);
            if (typeof loadDashboardSummary  === 'function') loadDashboardSummary(d);
            if (typeof loadTradingStatus     === 'function') loadTradingStatus(d.trading || null);
            if (typeof loadPendingProposals  === 'function') loadPendingProposals(d.pending_proposals ?? null);
            if (typeof loadScanStatusDetail  === 'function') loadScanStatusDetail(d.scan_detail ?? null);
            if (typeof loadActivityLog       === 'function') loadActivityLog(d.activity ?? null);
            if (typeof loadPortfolioCard     === 'function') loadPortfolioCard();
        } catch (e) {
            console.warn('SSE parse error:', e);
        }
    };

    _sseSource.onerror = () => {
        _sseSource.close();
        _sseSource = null;
        console.warn('SSE stream unavailable — falling back to 5-min poll');
        startRefreshTimer();
    };
}

// Fast retry loop: polls every 10s until data appears (max 2 min)
let _initialRetryCount = 0;
function startInitialRetry() {
    const maxRetries = 12; // 12 × 10s = 2 minutes
    const timer = setInterval(async () => {
        _initialRetryCount++;
        // Check if any status pill has loaded real data (not still showing default/empty text)
        const budgetEl = document.getElementById('pillBudget');
        const heatmapEl = document.getElementById('heatmapGrid');
        const hasData = (budgetEl && budgetEl.textContent && budgetEl.textContent !== '—') ||
                        (heatmapEl && heatmapEl.children.length > 0 && !heatmapEl.querySelector('.heatmap-loading'));
        if (hasData || _initialRetryCount >= maxRetries) {
            clearInterval(timer);
            if (hasData) console.log('Initial data loaded after', _initialRetryCount * 10, 'seconds');
            return;
        }
        console.log(`Retry ${_initialRetryCount}/${maxRetries}: refreshing dashboard...`);
        await refreshData();
    }, 10000); // every 10 seconds
}
