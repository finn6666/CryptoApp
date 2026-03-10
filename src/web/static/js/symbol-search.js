// Symbol Search Functionality

function toggleSymbolSearch() {
    const container = document.getElementById('symbolSearchContainer');
    const btn = document.getElementById('symbolToggleBtn');
    
    if (container.style.display === 'none' || !container.style.display) {
        container.style.display = 'block';
        btn.textContent = '❌ Close Search';
        document.getElementById('symbolSearchInput').focus();
    } else {
        container.style.display = 'none';
        btn.textContent = '⭐ Add Favorite';
        document.getElementById('searchResults').innerHTML = '';
        document.getElementById('symbolSearchInput').value = '';
    }
}

async function searchSymbols() {
    const input = document.getElementById('symbolSearchInput');
    const query = input.value.trim().toUpperCase();
    const resultsDiv = document.getElementById('searchResults');
    const searchBtn = document.getElementById('searchBtn');
    
    if (!query) {
        resultsDiv.innerHTML = '<div class="error">⚠️ Please enter a symbol</div>';
        return;
    }
    
    searchBtn.textContent = '🔍 Searching...';
    searchBtn.disabled = true;
    resultsDiv.innerHTML = '<div class="loading">🔄 Searching...</div>';
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Search failed');
        }
        
        if (data.results && data.results.length > 0) {
            let html = '<div class="search-results-grid">';
            data.results.forEach(coin => {
                const safeSym = coin.symbol.replace(/[^A-Z0-9]/gi, '');
                const safeName = coin.name.replace(/[<>&"']/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c]));
                html += `
                    <div class="search-result-card">
                        <div class="search-result-info">
                            <div class="search-result-symbol">${safeSym}</div>
                            <div class="search-result-name">${safeName}</div>
                        </div>
                        <button class="btn-small" onclick="addSymbol('${safeSym}', '${safeName}')">
                            ➕ Add
                        </button>
                    </div>
                `;
            });
            html += '</div>';
            resultsDiv.innerHTML = html;
        } else {
            resultsDiv.innerHTML = '<div class="error">❌ No results found</div>';
        }
        
    } catch (error) {
        console.error('Search error:', error);
        resultsDiv.innerHTML = `<div class="error">❌ Search failed</div>`;
    } finally {
        searchBtn.textContent = '🔍 Search';
        searchBtn.disabled = false;
    }
}

async function addSymbol(symbol, name) {
    try {
        showStatus(`Adding ${symbol} to favorites...`, 'info');
        
        // Step 1: Add symbol to supported symbols (if not already tracked)
        const addResponse = await fetch('/api/symbols/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: symbol })
        });
        
        const addData = await addResponse.json();
        
        if (!addData.success) {
            throw new Error(addData.error || 'Failed to add symbol');
        }
        
        // Step 2: Add to favorites
        const favResponse = await fetch('/api/favorites/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: symbol })
        });
        
        const favData = await favResponse.json();
        
        if (!favData.success) {
            throw new Error(favData.error || 'Failed to add to favorites');
        }
        
        showStatus(`✅ Added ${symbol} to favorites!`, 'success');
        
        toggleSymbolSearch();
        await refreshData();
        
    } catch (error) {
        console.error('Add symbol error:', error);
        showStatus(`❌ Error: ${error.message}`, 'error');
    }
}

// Enter key handler
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('symbolSearchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchSymbols();
            }
        });
    }
});
