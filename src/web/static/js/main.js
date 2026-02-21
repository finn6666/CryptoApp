// CryptoApp Dashboard - Main Entry Point

// Global state
let refreshing = false;
let userFavorites = [];

// Initialize application
document.addEventListener('DOMContentLoaded', async () => {
    console.log('CryptoApp Dashboard initializing...');
    
    try {
        // Load overview cards, favorites and market conditions
        await Promise.all([
            loadOverviewCards(),
            loadFavorites(false),
            loadMarketConditions()
        ]);
        
        console.log('Dashboard loaded (basic data). Loading agent analyses in background...');
        
        // Load agent analyses in background (non-blocking)
        loadAgentAnalysesInBackground();
        
        // Start auto-refresh timer
        startRefreshTimer();
        
    } catch (error) {
        console.error('Error initializing dashboard:', error);
        showStatus('Error loading dashboard', 'error');
    }
});

// Expose refresh function globally for manual refresh
window.refreshDashboard = refreshData;
