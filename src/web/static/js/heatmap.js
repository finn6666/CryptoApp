// Coin Heatmap — Finviz-style tile grid

// ─── Colour helpers ───────────────────────────────────────────

/**
 * Map a gem score (0–10) to a CSS background colour.
 * Low score → red, mid → amber, high → green.
 */
function _gemColour(score) {
    const s = Math.max(0, Math.min(10, score));
    // 0–3: red range, 3–6: amber, 6–10: green
    if (s < 3) {
        const t = s / 3;
        const r = Math.round(180 + (1 - t) * 40);
        const g = Math.round(40  + t * 40);
        return `rgb(${r},${g},40)`;
    } else if (s < 6) {
        const t = (s - 3) / 3;
        const r = Math.round(180 - t * 80);
        const g = Math.round(80  + t * 60);
        return `rgb(${r},${g},40)`;
    } else {
        const t = (s - 6) / 4;
        const r = Math.round(100 - t * 60);
        const g = Math.round(140 + t * 50);
        return `rgb(${r},${g},${40 + Math.round(t * 30)})`;
    }
}

/**
 * Map price_change_24h percentage to a text colour class.
 */
function _changeClass(pct) {
    if (pct > 0) return 'positive';
    if (pct < 0) return 'negative';
    return '';
}

// ─── Price formatter ──────────────────────────────────────────

function _fmtPrice(price) {
    if (price === null || price === undefined) return '—';
    if (price >= 1000) return `£${price.toLocaleString('en-GB', {maximumFractionDigits: 0})}`;
    if (price >= 1)    return `£${price.toFixed(2)}`;
    if (price >= 0.01) return `£${price.toFixed(4)}`;
    if (price >= 0.0001) return `£${price.toFixed(6)}`;
    return `£${price.toExponential(2)}`;
}

// ─── Tile size calculation ─────────────────────────────────────

/**
 * Compute flex-basis (px) for each tile proportional to its gem score.
 * Min floor prevents tiny unreadable tiles.
 */
function _tileSize(score, minScore, maxScore) {
    const MIN_PX = 72;
    const MAX_PX = 160;
    if (maxScore <= minScore) return MIN_PX;
    const t = (score - minScore) / (maxScore - minScore);
    return Math.round(MIN_PX + t * (MAX_PX - MIN_PX));
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

function _renderHeatmap(coins) {
    const grid = document.getElementById('heatmapGrid');
    if (!grid) return;

    if (!coins || coins.length === 0) {
        grid.innerHTML = '<div class="heatmap-loading">No coin data yet — trigger a scan to populate the heatmap.</div>';
        return;
    }

    const scores = coins.map(c => c.gem_score);
    const minScore = Math.min(...scores);
    const maxScore = Math.max(...scores);

    grid.innerHTML = '';
    coins.forEach(coin => {
        const size   = _tileSize(coin.gem_score, minScore, maxScore);
        const colour = _gemColour(coin.gem_score);
        const chg    = coin.price_change_24h;
        const chgStr = chg >= 0 ? `+${chg.toFixed(1)}%` : `${chg.toFixed(1)}%`;
        const chgCls = _changeClass(chg);

        const tile = document.createElement('div');
        tile.className = 'hm-tile';
        tile.style.cssText = `
            background: ${colour};
            flex-basis: ${size}px;
            flex-grow: ${size};
            height: ${Math.max(52, size * 0.6)}px;
        `;
        tile.title = `${coin.symbol} — ${coin.name}\nGem score: ${coin.gem_score}\nPrice: ${_fmtPrice(coin.price)}\n24h: ${chgStr}`;

        tile.innerHTML = `
            <div class="hm-tile__symbol">${escapeHtml(coin.symbol)}</div>
            <div class="hm-tile__price">${_fmtPrice(coin.price)}</div>
            <div class="hm-tile__change ${chgCls}">${chgStr}</div>
            <div class="hm-tile__score">${coin.gem_score}</div>
        `;

        tile.addEventListener('click', () => _showTileAnalysis(coin.symbol, coin.name, coin.price));
        grid.appendChild(tile);
    });
}

// ─── Public API ───────────────────────────────────────────────

async function loadHeatmap() {
    const grid = document.getElementById('heatmapGrid');
    if (!grid) return;

    grid.innerHTML = '<div class="heatmap-loading">Loading heatmap…</div>';

    try {
        const res = await fetch('/api/heatmap-data');
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        _renderHeatmap(data.coins || []);
    } catch (err) {
        if (grid) {
            grid.innerHTML = `<div class="heatmap-loading" style="color:var(--error);">Heatmap unavailable: ${escapeHtml(err.message)}</div>`;
        }
    }
}
