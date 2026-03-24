// Utility Functions

// ─── HTML Escaping ─────────────────────────────────────────

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(String(str)));
    return div.innerHTML;
}

// ─── Auth ──────────────────────────────────────────────────

/** Return stored API key (no prompt — key only needed for agent trade proposals). */
function getApiKey() {
    return sessionStorage.getItem('tradingApiKey');
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
    
    if (lastUpdated) {
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
    
    if (cacheExpiresIn !== undefined && cacheExpiresIn !== null) {
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
    }, 300000); // 5 minutes
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
