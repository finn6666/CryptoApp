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

function updateMLStatus(mlEnabled) {
    const mlBadges = document.querySelectorAll('.badge-ai');
    mlBadges.forEach(badge => {
        badge.style.display = mlEnabled ? 'inline-block' : 'none';
    });
}
