// CryptoApp Dashboard - Main Entry Point

// Global state
let refreshing = false;

// ─── API Key Modal ────────────────────────────────────────────
function openAuthModal() {
    const modal = document.getElementById('authModal');
    const input = document.getElementById('authKeyInput');
    if (!modal) return;
    input.value = '';
    modal.style.display = 'flex';
    setTimeout(() => input.focus(), 50);
}

function saveApiKey() {
    const input = document.getElementById('authKeyInput');
    const key = input ? input.value.trim() : '';
    if (!key) return;
    setApiKey(key);
    document.getElementById('authModal').style.display = 'none';
    // Reload auth-gated sections now that key is set
    loadOverviewCards();
    initTradingSections();
}

// ─── Initialize application ──────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    console.log('CryptoApp Dashboard initializing...');

    // Show key modal if no API key stored
    if (!getApiKey()) {
        openAuthModal();
    }

    try {
        // Live ticker across the top
        startTicker();

        // Single-call status strip + sidebar scanner stats
        await loadDashboardSummary();

        // Heatmap (independent — runs in parallel with init below)
        loadHeatmap();

        // Init trading/portfolio/scanning sidebar sections
        initTradingSections();

        console.log('Dashboard loaded.');

        // Fast retry: if market data isn't loaded yet, retry every 10s for up to 2 min
        startInitialRetry();

        // Start SSE stream (replaces setInterval polling for sidebar sections).
        // Falls back to startRefreshTimer() automatically on error.
        startDashboardSSE();

    } catch (error) {
        console.error('Error initializing dashboard:', error);
        showStatus('Error loading dashboard', 'error');
    }
});

// Expose refresh function globally for manual refresh
window.refreshDashboard = refreshData;
