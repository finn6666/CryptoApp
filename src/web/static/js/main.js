// CryptoApp Dashboard - Main Entry Point
// Modularized for better maintainability

// Global state
let refreshing = false;
let userFavorites = [];

// Initialize application
document.addEventListener('DOMContentLoaded', async () => {
    console.log('CryptoApp Dashboard initializing...');
    
    try {
        // Load all data in parallel
        await Promise.all([
            loadCoins(),
            loadFavorites()
        ]);
        
        console.log('Dashboard loaded successfully');
        
        // Start auto-refresh timer
        startRefreshTimer();
        
    } catch (error) {
        console.error('Error initializing dashboard:', error);
        showStatus('Error loading dashboard', 'error');
    }
});

// Expose refresh function globally for manual refresh
window.refreshDashboard = refreshData;
