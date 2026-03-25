// Coin Heatmap — Finviz-style tile grid

// ─── Colour helpers ───────────────────────────────────────────

/**
 * Tile background colour based on price-change % performance.
 * Green = up, red = down. Intensity scales with magnitude (full at ±8%).
 * Gem score only affects tile SIZE, not colour.
 */
function _tileColour(pct) {
    if (!pct) return 'hsl(220, 15%, 18%)';          // neutral dark
    const intensity = Math.min(Math.abs(pct) / 8, 1); // full intensity at ±8%
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

async function _showTileAnalysis(symbol, name, price) {
    const heatmapCol = document.getElementById('heatmapColumn');
    if (!heatmapCol) return;

    // Toggle off if clicking same tile
    if (_activeTileSymbol === symbol) {
        _closeTileAnalysis();
        return;
    }
    _activeTileSymbol = symbol;

    // Remove existing panel
    const existing = document.getElementById('hmAnalysisPanel');
    if (existing) existing.remove();

    const panel = document.createElement('div');
    panel.id = 'hmAnalysisPanel';
    panel.className = 'hm-analysis-panel';
    panel.innerHTML = `
        <div class="hm-analysis-header">
            <h3>${escapeHtml(symbol)} — ${escapeHtml(name)}</h3>
            <button class="hm-analysis-close" onclick="_closeTileAnalysis()">✕</button>
        </div>
        <div id="hmAnalysisBody" style="color: var(--text-secondary); font-size: 13px;">
            Running agent analysis...
        </div>
    `;
    heatmapCol.appendChild(panel);
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    try {
        const res = await fetch(`/api/agents/analyze/${encodeURIComponent(symbol)}`);
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        const body = document.getElementById('hmAnalysisBody');
        if (!body) return;

        // Reuse the unified AI analysis renderer from ui-components.js if available
        if (typeof generateUnifiedAIAnalysis === 'function') {
            body.innerHTML = generateUnifiedAIAnalysis(symbol, price, data);
        } else {
            const rec = data.recommendation || 'N/A';
            const conf = data.confidence || '—';
            const summary = data.summary || data.analysis || 'No summary available.';
            body.innerHTML = `
                <div style="display:flex;gap:12px;margin-bottom:10px;flex-wrap:wrap;">
                    <span style="font-weight:700;color:var(--text-primary);">${escapeHtml(rec)}</span>
                    <span style="color:var(--text-secondary);">Confidence: ${escapeHtml(String(conf))}</span>
                </div>
                <div style="font-size:12px;color:var(--text-secondary);line-height:1.6;">
                    ${escapeHtml(String(summary))}
                </div>
            `;
        }
    } catch (err) {
        const body = document.getElementById('hmAnalysisBody');
        if (body) {
            body.innerHTML = `<span style="color:var(--error);">Analysis unavailable: ${escapeHtml(err.message)}</span>`;
        }
    }
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
    // API returns coins sorted by gem_score desc — kept so largest tiles are top-left
    const allCoins = [...extraCoins, ...coins];

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
        rowEl.style.cssText = `display:flex; flex:${rowTotals[ri] / totalScore * rows.length}; gap:2px; min-height:55px;`;

        row.forEach(coin => {
            const held = holdingsMap[coin.symbol];

            // Colour by price performance — held coins use P&L, others use 24h change
            const pct = (held && held.unrealised_pnl_pct !== undefined && held.unrealised_pnl_pct !== null)
                ? held.unrealised_pnl_pct
                : (coin.price_change_24h || 0);
            const bgColour = _tileColour(pct);

            const displayStr  = pct >= 0 ? `+${pct.toFixed(1)}%` : `${pct.toFixed(1)}%`;
            const displayColor = _changeColour(pct);
            const scoreLabel  = String(coin.gem_score);
            const priceStr    = (held && held.current_price) ? _fmtPrice(held.current_price) : _fmtPrice(coin.price);
            const symbolText  = held ? `&#9679; ${escapeHtml(coin.symbol)}` : escapeHtml(coin.symbol);

            const tile = document.createElement('div');
            tile.className = 'hm-tile' + (coin.gem_score < 2 ? ' hm-tile--micro' : '');
            // flex: gem_score makes tile width proportional within the row
            tile.style.cssText = [
                `background:${bgColour}`,
                `flex:${coin.gem_score}`,
                held ? 'outline:2px solid rgba(255,255,255,0.5);outline-offset:-2px' : '',
            ].filter(Boolean).join(';');
            tile.title = `${coin.symbol} — ${coin.name}\n${held ? `P&L: ${displayStr}` : `24h: ${displayStr}`}\nPrice: ${priceStr}`;

            tile.innerHTML = `
                <div class="hm-tile__symbol">${symbolText}</div>
                <div class="hm-tile__price">${priceStr}</div>
                <div class="hm-tile__change" style="color:${displayColor}">${displayStr}</div>
                <div class="hm-tile__score">${scoreLabel}</div>
            `;

            tile.addEventListener('click', () => _showTileAnalysis(coin.symbol, coin.name, coin.price));
            rowEl.appendChild(tile);
        });

        grid.appendChild(rowEl);
    });
}

// ─── Public API ───────────────────────────────────────────────

async function loadHeatmap() {
    const grid = document.getElementById('heatmapGrid');
    if (!grid) return;

    grid.innerHTML = '<div class="heatmap-loading">Loading heatmap…</div>';

    try {
        const [heatmapRes, holdingsRes] = await Promise.all([
            fetch('/api/heatmap-data'),
            fetch('/api/portfolio/holdings', { headers: authHeaders() }),
        ]);
        const heatmapData  = await heatmapRes.json();
        const holdingsData = await holdingsRes.json().catch(() => ({}));

        if (heatmapData.error) throw new Error(heatmapData.error);

        // Build holdings map: symbol → holding (active positions only)
        const holdingsMap = {};
        for (const h of holdingsData.holdings || []) {
            if ((h.quantity || 0) > 0) holdingsMap[h.symbol] = h;
        }

        _renderHeatmap(heatmapData.coins || [], holdingsMap);
    } catch (err) {
        if (grid) {
            grid.innerHTML = `<div class="heatmap-loading" style="color:var(--error);">Heatmap unavailable: ${escapeHtml(err.message)}</div>`;
        }
    }
}

// Refresh every 60 s so P&L stays current
setInterval(loadHeatmap, 60000);
