// Coin Display and Rendering Functions

function generateCoinsTable(coins, mlEnabled = false) {
    if (!coins || coins.length === 0) {
        return '<div class="error">No coins available</div>';
    }
    
    let html = '<div class="coins-grid">';

    coins.forEach((coin, index) => {
        const priceChange = coin.price_change_24h || 0;
        const priceChangeClass = priceChange >= 0 ? 'positive' : 'negative';
        const priceChangeText = priceChange >= 0 ? `+${priceChange.toFixed(1)}%` : `${priceChange.toFixed(1)}%`;

        const { displayScore, scorePercentage, scoreClass, scoreLabel } = getScoreInfo(coin.enhanced_score || coin.score);
        const price = formatPrice(coin.price);
        const mlEnhancedBadge = mlEnabled && coin.enhanced_score ? '<span class="badge badge-ai">🧠 AI</span>' : '';
        
        const aiSentimentHtml = generateAISentimentHTML(coin, index);
        const mlReasoningHtml = generateMLReasoningHTML(coin, index, mlEnabled);
        
        html += `
            <div class="coin-card ${scoreClass}">
                <div class="coin-card-header">
                    <div class="coin-info">
                        <button class="favorite-btn-card ${userFavorites.includes(coin.symbol) ? 'active' : ''}" 
                                onclick="toggleFavorite('${coin.symbol}')" 
                                title="${userFavorites.includes(coin.symbol) ? 'Remove from favorites' : 'Add to favorites'}">
                            ${userFavorites.includes(coin.symbol) ? '⭐' : '☆'}
                        </button>
                        <div class="coin-identity">
                            <div class="coin-symbol-large">${coin.symbol}</div>
                            <div class="coin-name-small">${coin.name}</div>
                        </div>
                    </div>
                    <div class="badges">
                        ${mlEnhancedBadge}
                    </div>
                </div>
                
                <div class="coin-card-body">
                    <div class="price-section">
                        <div class="price-large">${price}</div>
                        <div class="price-change ${priceChangeClass}">${priceChangeText}</div>
                    </div>
                    
                    <div class="score-section">
                        <div class="score-header">
                            <span class="score-label">${scoreLabel}</span>
                            <span class="score-value">${displayScore.toFixed(1)}/10</span>
                        </div>
                        <div class="score-bar">
                            <div class="score-fill ${scoreClass}" style="width: ${scorePercentage}%"></div>
                        </div>
                    </div>
                    
                    ${aiSentimentHtml}
                    ${mlReasoningHtml}
                </div>
            </div>
        `;
    });

    html += '</div>';
    return html;
}

function generateFavoritesTable(favorites, mlEnabled = false) {
    if (!favorites || favorites.length === 0) {
        return '<div class="error">No favorites yet</div>';
    }
    
    let html = '<div class="coins-grid">';

    favorites.forEach((coin, index) => {
        const priceChange = coin.price_change_24h || 0;
        const priceChangeClass = priceChange >= 0 ? 'positive' : 'negative';
        const priceChangeText = priceChange >= 0 ? `+${priceChange.toFixed(1)}%` : `${priceChange.toFixed(1)}%`;

        const { displayScore, scorePercentage, scoreClass, scoreLabel } = getScoreInfo(coin.enhanced_score || coin.score);
        const price = formatPrice(coin.price);
        const mlEnhancedBadge = mlEnabled && coin.enhanced_score ? '<span class="badge badge-ai">🧠 AI</span>' : '';
        
        const aiSentimentHtml = generateAISentimentHTML(coin, `fav-${index}`);
        const mlReasoningHtml = generateMLReasoningHTML(coin, `fav-${index}`, mlEnabled);
        
        html += `
            <div class="coin-card ${scoreClass}">
                <div class="coin-card-header">
                    <div class="coin-info">
                        <button class="favorite-btn-card active" onclick="removeFavorite('${coin.symbol}')" title="Remove from favorites">❌</button>
                        <div class="coin-identity">
                            <div class="coin-symbol-large">${coin.symbol}</div>
                            <div class="coin-name-small">${coin.name}</div>
                        </div>
                    </div>
                    <div class="badges">
                        <span class="badge" style="background: gold; color: black;">⭐ FAVORITE</span>
                        ${mlEnhancedBadge}
                    </div>
                </div>
                
                <div class="coin-card-body">
                    <div class="price-section">
                        <div class="price-large">${price}</div>
                        <div class="price-change ${priceChangeClass}">${priceChangeText}</div>
                    </div>
                    
                    <div class="score-section">
                        <div class="score-header">
                            <span class="score-label">${scoreLabel}</span>
                            <span class="score-value">${displayScore.toFixed(1)}/10</span>
                        </div>
                        <div class="score-bar">
                            <div class="score-fill ${scoreClass}" style="width: ${scorePercentage}%"></div>
                        </div>
                    </div>
                    
                    ${aiSentimentHtml}
                    ${mlReasoningHtml}
                </div>
            </div>
        `;
    });

    html += '</div>';
    return html;
}
