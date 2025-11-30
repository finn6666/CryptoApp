// Favorites Management

async function toggleFavorite(symbol) {
    try {
        const isFavorited = userFavorites.includes(symbol);
        const endpoint = isFavorited ? '/api/favorites/remove' : '/api/favorites/add';
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: symbol })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error);
        }
        
        if (isFavorited) {
            userFavorites = userFavorites.filter(s => s !== symbol);
            showStatus(`Removed ${symbol} from favorites`, 'info');
        } else {
            userFavorites.push(symbol);
            showStatus(`Added ${symbol} to favorites`, 'success');
        }
        
        await loadFavorites();
        updateFavoriteButtons();
        
    } catch (error) {
        console.error('Error toggling favorite:', error);
        showStatus(`Error: ${error.message}`, 'error');
    }
}

async function removeFavorite(symbol) {
    await toggleFavorite(symbol);
}

function updateFavoriteButtons() {
    document.querySelectorAll('.favorite-btn-card').forEach(btn => {
        const symbol = btn.getAttribute('onclick').match(/'([^']+)'/)[1];
        const isFavorited = userFavorites.includes(symbol);
        
        btn.classList.toggle('active', isFavorited);
        btn.textContent = isFavorited ? '⭐' : '☆';
        btn.title = isFavorited ? 'Remove from favorites' : 'Add to favorites';
    });
}
