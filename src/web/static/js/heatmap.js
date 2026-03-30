// Coin Heatmap — Finviz-style tile grid

// ─── Colour helpers ───────────────────────────────────────────

/**
 * Tile background colour based on price-change % performance.
 * Green = up, red = down. Intensity scales with magnitude (full at ±8%).
 * Gem score only affects tile SIZE, not colour.
 */
function _tileColour(pct) {
    if (!pct) return 'hsl(220, 15%, 18%)';          // neutral dark
    const intensity = Math.min(Math.abs(pct) / 5, 1); // full intensity at ±5%
    const sat = Math.round(50 + intensity * 35);      // 50–85%
    const lgt = Math.round(16 + intensity * 18);      // 16–34%
    return pct > 0 ? `hsl(120, ${sat}%, ${lgt}%)` : `hsl(0, ${sat}%, ${lgt}%)`;
}

/**
 * Map price_change_24h percentage to an inline colour string.
 * Avoids the global .positive/.negative class (which adds background + border).
 */
function _changeColour(pct) {
    if (pct > 0) return '#68d391';              // bright green — same as .positive
    if (pct < 0) return '#fc8181';              // bright red   — same as .negative
    return 'rgba(255,255,255,0.7)';
}

// ─── Price formatter ──────────────────────────────────────────

function _fmtPrice(price) {
    if (price === null || price === undefined) return '—';
    if (price >= 1000)    return `£${price.toLocaleString('en-GB', {maximumFractionDigits: 0})}`;
    if (price >= 1)       return `£${price.toFixed(2)}`;
    if (price >= 0.01)    return `£${price.toFixed(4)}`;
    if (price >= 0.0001)  return `£${price.toFixed(6)}`;
    if (price >= 0.000001) return `£${price.toFixed(8)}`;
    // For ultra-tiny prices: calculate exact decimal places needed (no scientific notation)
    const decimals = -Math.floor(Math.log10(price)) + 2;
    return `£${price.toFixed(Math.min(decimals, 12))}`;
}

// ─── Treemap row packing ──────────────────────────────────────

/**
 * Pack coins into rows for treemap layout.
 * Coins must be sorted descending by gem_score before calling.
 * Returns array of rows; within each row tile width = flex:gem_score,
 * so each row fills 100% of the container width exactly.
 */
function _packRows(coins, containerW, containerH) {
    const n = coins.length;
    if (n === 0) return [];
    // Estimate rows: target roughly square tiles
    const numRows = Math.max(1, Math.min(6, Math.round(Math.sqrt(n * containerH / (containerW || 1)))));
    const totalScore = coins.reduce((s, c) => s + c.gem_score, 0);
    const targetPerRow = totalScore / numRows;

    const rows = [[]];
    let rowSum = 0;
    coins.forEach(coin => {
        if (rowSum > 0 && rowSum >= targetPerRow && rows.length < numRows) {
            rows.push([]);
            rowSum = 0;
        }
        rows[rows.length - 1].push(coin);
        rowSum += coin.gem_score;
    });
    return rows;
}

// ─── Analysis panel ───────────────────────────────────────────

let _activeTileSymbol = null;
let _currentHoldingsMap = {};
let _currentCoins = [];
let _holdingsReady = false;

function _showTileAnalysis(coin, holding) {
    const { symbol, name, price, price_change_24h, gem_score, market_cap_rank } = coin;
    const container = document.querySelector('.heatmap-container');
    if (!container) return;

    // Toggle off if clicking same tile
    if (_activeTileSymbol === symbol) {
        _closeTileAnalysis();
        return;
    }
    _activeTileSymbol = symbol;

    const existing = document.getElementById('hmAnalysisPanel');
    if (existing) existing.remove();

    const pct24h = price_change_24h || 0;
    const changeStr = pct24h >= 0 ? `+${pct24h.toFixed(1)}%` : `${pct24h.toFixed(1)}%`;
    const changeColour = _changeColour(pct24h);

    const scoreColour = gem_score >= 7 ? 'var(--success)' : gem_score >= 4 ? 'var(--accent-gold)' : 'var(--error)';
    const scoreLabel  = gem_score >= 7 ? 'Strong' : gem_score >= 4 ? 'Moderate' : 'Weak';
    const rankStr     = market_cap_rank && market_cap_rank < 999 ? `#${market_cap_rank}` : '—';

    let holdingHtml = '';
    if (holding) {
        const pnlPct = holding.unrealised_pnl_pct || 0;
        const pnlGbp = holding.unrealised_pnl_gbp || 0;
        const pnlColour = pnlPct >= 0 ? 'var(--success)' : 'var(--error)';
        const pnlSign   = pnlPct >= 0 ? '+' : '';
        holdingHtml = `
            <div class="hm-stat-row">
                <span class="hm-stat-label">Your position</span>
                <span style="color:${pnlColour};font-weight:700;">${pnlSign}${pnlPct.toFixed(1)}% (${pnlSign}£${Math.abs(pnlGbp).toFixed(2)})</span>
            </div>`;
    } else if (!_holdingsReady) {
        holdingHtml = `
            <div class="hm-stat-row">
                <span class="hm-stat-label">Your position</span>
                <span style="color:var(--text-secondary)">Loading...</span>
            </div>`;
    }

    const panel = document.createElement('div');
    panel.id = 'hmAnalysisPanel';
    panel.className = 'hm-analysis-panel';
    panel.innerHTML = `
        <div class="hm-analysis-header">
            <h3>${escapeHtml(symbol)} — ${escapeHtml(name)}</h3>
            <button class="hm-analysis-close" onclick="_closeTileAnalysis()">x</button>
        </div>
        <div class="hm-stat-grid">
            <div class="hm-stat-row">
                <span class="hm-stat-label">Price</span>
                <span>${_fmtPrice(price)}</span>
            </div>
            <div class="hm-stat-row">
                <span class="hm-stat-label">24h</span>
                <span style="color:${changeColour}">${changeStr}</span>
            </div>
            <div class="hm-stat-row">
                <span class="hm-stat-label">Gem score</span>
                <span style="color:${scoreColour}">${gem_score.toFixed(1)} — ${scoreLabel}</span>
            </div>
            <div class="hm-stat-row">
                <span class="hm-stat-label">Market cap rank</span>
                <span>${rankStr}</span>
            </div>
            ${holdingHtml}
        </div>
    `;
    container.appendChild(panel);
}

function _closeTileAnalysis() {
    _activeTileSymbol = null;
    const panel = document.getElementById('hmAnalysisPanel');
    if (panel) panel.remove();
}

// ─── Render ───────────────────────────────────────────────────

/**
 * Render heatmap tiles.
 * holdingsMap = { SYMBOL: holdingObject } for currently held coins.
 * Held coins are highlighted with a white border and display P&L instead of 24h change.
 * Held coins missing from the analyzer data are prepended as extra tiles.
 */
function _renderHeatmap(coins, holdingsMap) {
    holdingsMap = holdingsMap || {};
    const grid = document.getElementById('heatmapGrid');
    if (!grid) return;

    if (!coins || coins.length === 0) {
        grid.innerHTML = '<div class="heatmap-loading">No coin data yet — trigger a scan to populate the heatmap.</div>';
        return;
    }

    // Prepend held coins that aren't already in the analyzer list
    const inHeatmap = new Set(coins.map(c => c.symbol));
    const extraCoins = [];
    for (const [sym, h] of Object.entries(holdingsMap)) {
        if (!inHeatmap.has(sym)) {
            extraCoins.push({
                symbol: sym,
                name: h.coin_name || sym,
                price: h.current_price || h.avg_entry_price || 0,
                price_change_24h: h.price_change_24h || 0,
                gem_score: 5,
                market_cap_rank: 999,
            });
        }
    }
    // Sort all tiles by their display % descending (held coins use P&L%, others use 24h change)
    const allCoins = [...extraCoins, ...coins];
    allCoins.sort((a, b) => {
        const heldA = holdingsMap[a.symbol];
        const heldB = holdingsMap[b.symbol];
        const pctA = heldA ? (heldA.unrealised_pnl_pct ?? 0) : (a.price_change_24h || 0);
        const pctB = heldB ? (heldB.unrealised_pnl_pct ?? 0) : (b.price_change_24h || 0);
        return pctB - pctA;
    });

    // Pack into treemap rows: each row fills 100% width, tile widths proportional within row
    const containerW = grid.parentElement ? grid.parentElement.offsetWidth  || 800 : 800;
    const containerH = grid.parentElement ? grid.parentElement.offsetHeight || 500 : 500;
    const rows = _packRows(allCoins, containerW, containerH);
    const rowTotals = rows.map(r => r.reduce((s, c) => s + c.gem_score, 0));
    const totalScore = rowTotals.reduce((a, b) => a + b, 0) || 1;

    // Switch grid to column layout so rows stack and fill the height
    grid.style.cssText = 'display:flex; flex-direction:column; height:100%; gap:2px; overflow:hidden;';
    grid.innerHTML = '';

    rows.forEach((row, ri) => {
        const rowEl = document.createElement('div');
        // flex value proportional to row's total score so taller rows get more height
        rowEl.style.cssText = `display:flex; flex:${rowTotals[ri] / totalScore * rows.length}; gap:2px; min-height:64px;`;

        row.forEach(coin => {
            const held = holdingsMap[coin.symbol];

            // Colour by price performance — held coins use P&L, others use 24h change
            const pct = (held && held.unrealised_pnl_pct !== undefined && held.unrealised_pnl_pct !== null)
                ? held.unrealised_pnl_pct
                : (coin.price_change_24h || 0);
            const bgColour = _tileColour(pct);

            const displayStr  = pct >= 0 ? `+${pct.toFixed(1)}%` : `${pct.toFixed(1)}%`;
            const displayColor = _changeColour(pct);
            const scoreLabel  = coin.gem_score.toFixed(1);
            const priceStr    = (held && held.current_price) ? _fmtPrice(held.current_price) : _fmtPrice(coin.price);
            const symbolText  = held ? `&#9679; ${escapeHtml(coin.symbol)}` : escapeHtml(coin.symbol);

            // For held coins: show GBP P&L amount below the percentage
            let pnlHtml = '';
            if (held) {
                const pnlGbp  = held.unrealised_pnl_gbp ?? 0;
                const pnlSign = pnlGbp >= 0 ? '+' : '-';
                pnlHtml = `<div class="hm-tile__pnl" style="color:${displayColor}">${pnlSign}£${Math.abs(pnlGbp).toFixed(2)}</div>`;
            }

            const tile = document.createElement('div');
            tile.className = 'hm-tile' + (coin.gem_score < 3 ? ' hm-tile--micro' : '');
            // flex: gem_score makes tile width proportional within the row
            tile.style.cssText = [
                `background:${bgColour}`,
                `flex:${coin.gem_score}`,
                held ? 'outline:2px solid rgba(255,255,255,0.55);outline-offset:-2px' : '',
            ].filter(Boolean).join(';');
            tile.title = `${coin.symbol} — ${coin.name}\n${held ? `P&L: ${displayStr}` : `24h: ${displayStr}`}\nPrice: ${priceStr}`;

            tile.innerHTML = `
                <div class="hm-tile__symbol">${symbolText}</div>
                <div class="hm-tile__change" style="color:${displayColor}">${displayStr}</div>
                ${pnlHtml}
                <div class="hm-tile__price">${priceStr}</div>
                <div class="hm-tile__score">${scoreLabel}</div>
            `;

            // Look up holding at click time (not capture time) so the panel
            // always reflects the latest loaded holdings regardless of which
            // render pass the tile was created in.
            tile.addEventListener('click', () => _showTileAnalysis(coin, _currentHoldingsMap[coin.symbol] || null));
            rowEl.appendChild(tile);
        });

        grid.appendChild(rowEl);
    });
}

// ─── Public API ───────────────────────────────────────────────

let _heatmapLoaded = false;

async function loadHeatmap() {
    const grid = document.getElementById('heatmapGrid');
    if (!grid) return;

    // Show loading placeholder on first load only
    if (!_heatmapLoaded) {
        grid.innerHTML = '<div class="heatmap-loading">Loading heatmap&hellip;</div>';
    }

    try {
        // Fetch coin data and holdings in parallel — render once when both are ready
        const [heatmapRes, holdingsRes] = await Promise.all([
            fetch('/api/heatmap-data'),
            fetch('/api/portfolio/holdings', { headers: authHeaders() }).catch(() => null),
        ]);

        const heatmapData = await heatmapRes.json();
        if (heatmapData.error) throw new Error(heatmapData.error);

        const holdingsData = holdingsRes ? await holdingsRes.json().catch(() => ({})) : {};
        const holdingsMap = {};
        for (const h of holdingsData.holdings || []) {
            if ((h.quantity || 0) > 0) holdingsMap[h.symbol] = h;
        }

        // Store globals and render once — no layout shift from a second pass
        _currentHoldingsMap = holdingsMap;
        _currentCoins = heatmapData.coins || [];
        _holdingsReady = true;

        _renderHeatmap(_currentCoins, _currentHoldingsMap);
        _heatmapLoaded = true;

        // If the analysis panel is open, refresh it with current data
        if (_activeTileSymbol) {
            const openCoin = _currentCoins.find(c => c.symbol === _activeTileSymbol);
            if (openCoin) _showTileAnalysis(openCoin, _currentHoldingsMap[_activeTileSymbol] || null);
        }
    } catch (err) {
        if (grid) {
            grid.innerHTML = `<div class="heatmap-loading" style="color:var(--error);">Heatmap unavailable: ${escapeHtml(err.message)}</div>`;
        }
    }
}

// Refresh every 60 s so P&L stays current
setInterval(loadHeatmap, 60000);
