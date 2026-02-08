// CryptoApp Dashboard - Main Entry Point
// Modularized for better maintainability

// Global state
let refreshing = false;
let userFavorites = [];

// Initialize application
document.addEventListener('DOMContentLoaded', async () => {
    console.log('CryptoApp Dashboard initializing...');
    
    try {
        // Phase 1: Load data WITHOUT agents (fast - shows UI immediately)
        await Promise.all([
            loadCoins(false),
            loadFavorites(false),
            loadMarketConditions()
        ]);
        
        console.log('Dashboard loaded (basic data). Loading agent analyses in background...');
        
        // Phase 2: Load agent analyses in background (non-blocking)
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
