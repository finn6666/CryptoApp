// Live market ticker — scrolling headlines left, pinned stats right

let _tickerInterval = null;

// ─── Colour for Fear & Greed value ───────────────────────────

function _fngColor(val) {
    if (val <= 20) return '#fc8181';
    if (val <= 35) return '#f6ad55';
    if (val <= 55) return '#ecc94b';
    if (val <= 75) return '#68d391';
    return '#48bb78';
}

// ─── Load and render ─────────────────────────────────────────

async function loadTicker() {
    const track = document.getElementById('tickerTrack');
    const right  = document.getElementById('tickerRight');
    if (!track || !right) return;

    try {
        const res  = await fetch('/api/market/state');
        const data = await res.json();
        if (data.error || data.current_value === null) return;

        // ── Left: scrolling headlines ──────────────────────────
        const headlines = data.headlines || [];
        if (headlines.length > 0) {
            const items = headlines.map(h =>
                `<span class="ticker-item">
                    <span class="ticker-headline">${escapeHtml(h.title || '')}</span>
                    ${h.source ? `<span class="ticker-source">${escapeHtml(h.source)}</span>` : ''}
                </span>`
            ).join('');
            // Duplicate for seamless loop
            track.innerHTML = items + items;

            const duration = Math.max(40, headlines.length * 8);
            track.style.animationDuration = `${duration}s`;
        }

        // ── Right: pinned Fear & Greed + global stats ──────────
        const val  = data.current_value;
        const cls  = data.classification || '';
        const trend = data.trend || '';
        const color = _fngColor(val);

        const trendArrow = trend === 'IMPROVING' ? '↗' : trend === 'DETERIORATING' ? '↘' : '→';

        const gs = data.global_stats || {};
        const btcDom   = gs.btc_dominance   ? `<span class="ticker-stat"><span class="ticker-stat__label">BTC DOM</span><span class="ticker-stat__value">${escapeHtml(String(gs.btc_dominance))}%</span></span>` : '';
        const mcapChg  = gs.market_cap_change_24h !== undefined
            ? (() => {
                const chg = gs.market_cap_change_24h;
                const col = chg >= 0 ? 'var(--success)' : 'var(--error)';
                const arrow = chg >= 0 ? '▲' : '▼';
                return `<span class="ticker-stat"><span class="ticker-stat__label">MCAP 24H</span><span class="ticker-stat__value" style="color:${col}">${arrow}${Math.abs(chg).toFixed(1)}%</span></span>`;
            })()
            : '';

        right.innerHTML = `
            ${btcDom}
            ${mcapChg}
            <span class="ticker-fng" style="border-left: 1px solid rgba(255,255,255,0.08); margin-left:4px; padding-left:10px;">
                <span class="ticker-fng__label">F&G</span>
                <span class="ticker-fng__value" style="color:${color};">${val}</span>
                <span class="ticker-fng__cls" style="color:${color};">${escapeHtml(cls)} ${trendArrow}</span>
            </span>
        `;

    } catch (e) {
        console.warn('Ticker load failed:', e.message);
    }
}

function startTicker() {
    loadTicker();
    _tickerInterval = setInterval(loadTicker, 600000); // refresh every 10 min
}
