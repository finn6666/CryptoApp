// Utility Functions

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
        // Check if portfolio card has loaded real data (no longer shows default text)
        const valEl = document.getElementById('portfolioValue');
        const tradingEl = document.getElementById('tradingBudget');
        const hasData = (valEl && valEl.textContent !== '£0.00' && valEl.textContent !== '$0.00' && valEl.textContent !== '—') ||
                        (tradingEl && tradingEl.textContent !== '—' && tradingEl.textContent !== 'Connecting...');
        if (hasData || _initialRetryCount >= maxRetries) {
            clearInterval(timer);
            if (hasData) console.log('Initial data loaded after', _initialRetryCount * 10, 'seconds');
            return;
        }
        console.log(`Retry ${_initialRetryCount}/${maxRetries}: refreshing dashboard...`);
        await refreshData();
    }, 10000); // every 10 seconds
}
