// CryptoApp Dashboard - Main Entry Point

// Global state
let refreshing = false;

// Initialize application
document.addEventListener('DOMContentLoaded', async () => {
    console.log('CryptoApp Dashboard initializing...');

    // Prompt for API key once per session so authenticated endpoints work.
    if (!sessionStorage.getItem('tradingApiKey')) {
        const key = prompt('Enter your API key to access the dashboard:');
        if (key) sessionStorage.setItem('tradingApiKey', key.trim());
    }

    
    try {
        // Load overview cards, market conditions, and trading sections
        await Promise.all([
            loadOverviewCards(),
            loadMarketConditions()
        ]);

        // Init trading/portfolio/scanning sections
        initTradingSections();
        
        console.log('Dashboard loaded (basic data).');
        
        // Fast retry: if market data isn't loaded yet, retry every 10s for up to 2 min
        startInitialRetry();
        
        // Start auto-refresh timer (5 min interval)
        startRefreshTimer();
        
    } catch (error) {
        console.error('Error initializing dashboard:', error);
        showStatus('Error loading dashboard', 'error');
    }
});

// Expose refresh function globally for manual refresh
window.refreshDashboard = refreshData;
