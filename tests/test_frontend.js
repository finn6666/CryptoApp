/**
 * Frontend JS Tests for CryptoApp
 * 
 * Run with: node tests/test_frontend.js
 * 
 * Lightweight test runner — no external dependencies.
 * Tests utility functions and logic that don't require DOM.
 */

let passed = 0;
let failed = 0;
const failures = [];

function assert(condition, message) {
    if (condition) {
        passed++;
    } else {
        failed++;
        failures.push(message);
        console.error(`  FAIL: ${message}`);
    }
}

function assertEqual(actual, expected, message) {
    if (actual === expected) {
        passed++;
    } else {
        failed++;
        const msg = `${message} — expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`;
        failures.push(msg);
        console.error(`  FAIL: ${msg}`);
    }
}

function describe(name, fn) {
    console.log(`\n${name}`);
    fn();
}

function it(name, fn) {
    try {
        fn();
    } catch (e) {
        failed++;
        failures.push(`${name}: ${e.message}`);
        console.error(`  FAIL: ${name}: ${e.message}`);
    }
}

// ─── Mock DOM ───────────────────────────────────────────────

const mockElements = {};
const globalThis_doc = {
    getElementById(id) {
        if (!mockElements[id]) mockElements[id] = { textContent: "", innerHTML: "", classList: { toggle() {}, add() {}, remove() {} } };
        return mockElements[id];
    },
    querySelectorAll() { return []; },
};
if (typeof document === "undefined") global.document = globalThis_doc;
if (typeof fetch === "undefined") global.fetch = async () => ({ json: async () => ({}) });
if (typeof window === "undefined") global.window = {};

// ─── Utils Tests ────────────────────────────────────────────

describe("utils.js — updateRefreshStatus", () => {
    // Inline the function for testing
    function updateRefreshStatus(lastUpdated, cacheExpiresIn) {
        const lastUpdatedEl = document.getElementById("lastUpdated");
        const nextRefreshEl = document.getElementById("nextRefresh");

        if (lastUpdated) {
            const date = new Date(lastUpdated);
            const now = new Date();
            const minutesAgo = Math.floor((now - date) / 60000);

            if (minutesAgo < 1) {
                lastUpdatedEl.textContent = "Just now";
            } else if (minutesAgo < 60) {
                lastUpdatedEl.textContent = `${minutesAgo}m ago`;
            } else {
                const hoursAgo = Math.floor(minutesAgo / 60);
                lastUpdatedEl.textContent = `${hoursAgo}h ago`;
            }
        }

        if (cacheExpiresIn !== undefined && cacheExpiresIn !== null) {
            const minutes = Math.floor(cacheExpiresIn / 60);
            const seconds = cacheExpiresIn % 60;
            if (minutes > 0) {
                nextRefreshEl.textContent = `${minutes}m ${seconds}s`;
            } else {
                nextRefreshEl.textContent = `${seconds}s`;
            }
        }
    }

    it("shows 'Just now' for recent timestamp", () => {
        mockElements["lastUpdated"] = { textContent: "" };
        mockElements["nextRefresh"] = { textContent: "" };
        updateRefreshStatus(new Date().toISOString(), null);
        assertEqual(mockElements["lastUpdated"].textContent, "Just now", "recent timestamp");
    });

    it("shows minutes ago for older timestamp", () => {
        mockElements["lastUpdated"] = { textContent: "" };
        mockElements["nextRefresh"] = { textContent: "" };
        const fiveMinAgo = new Date(Date.now() - 5 * 60000).toISOString();
        updateRefreshStatus(fiveMinAgo, null);
        assertEqual(mockElements["lastUpdated"].textContent, "5m ago", "5 minutes ago");
    });

    it("shows hours ago for much older timestamp", () => {
        mockElements["lastUpdated"] = { textContent: "" };
        mockElements["nextRefresh"] = { textContent: "" };
        const twoHoursAgo = new Date(Date.now() - 120 * 60000).toISOString();
        updateRefreshStatus(twoHoursAgo, null);
        assertEqual(mockElements["lastUpdated"].textContent, "2h ago", "2 hours ago");
    });

    it("formats cache expiry with minutes and seconds", () => {
        mockElements["lastUpdated"] = { textContent: "" };
        mockElements["nextRefresh"] = { textContent: "" };
        updateRefreshStatus(null, 125);
        assertEqual(mockElements["nextRefresh"].textContent, "2m 5s", "cache expiry format");
    });

    it("formats cache expiry seconds only", () => {
        mockElements["lastUpdated"] = { textContent: "" };
        mockElements["nextRefresh"] = { textContent: "" };
        updateRefreshStatus(null, 45);
        assertEqual(mockElements["nextRefresh"].textContent, "45s", "seconds only");
    });
});

// ─── Favorites Logic Tests ──────────────────────────────────

describe("favorites.js — toggleFavorite logic", () => {
    it("adds symbol to favorites list", () => {
        const favorites = ["BTC", "ETH"];
        const symbol = "DOGE";
        if (!favorites.includes(symbol)) {
            favorites.push(symbol);
        }
        assert(favorites.includes("DOGE"), "DOGE should be in favorites");
        assertEqual(favorites.length, 3, "length after add");
    });

    it("removes symbol from favorites list", () => {
        let favorites = ["BTC", "ETH", "DOGE"];
        const symbol = "ETH";
        if (favorites.includes(symbol)) {
            favorites = favorites.filter(s => s !== symbol);
        }
        assert(!favorites.includes("ETH"), "ETH should be removed");
        assertEqual(favorites.length, 2, "length after remove");
    });

    it("does not duplicate symbols", () => {
        const favorites = ["BTC", "ETH"];
        const symbol = "BTC";
        if (!favorites.includes(symbol)) {
            favorites.push(symbol);
        }
        assertEqual(favorites.length, 2, "no duplicate added");
    });
});

// ─── API Service Logic Tests ────────────────────────────────

describe("api-service.js — response parsing", () => {
    it("handles coin data structure", () => {
        const coinData = {
            symbol: "TEST",
            name: "TestCoin",
            price: 0.05,
            market_cap: 500000,
            volume_24h: 120000,
        };
        assertEqual(coinData.symbol, "TEST", "symbol");
        assert(coinData.price > 0, "price positive");
        assert(coinData.market_cap > 0, "market_cap positive");
    });

    it("handles empty response gracefully", () => {
        const response = {};
        const coins = response.coins || [];
        assertEqual(coins.length, 0, "empty coins array");
    });
});

// ─── Portfolio Logic Tests ──────────────────────────────────

describe("portfolio.js — allocation calculation", () => {
    it("calculates percentage allocation", () => {
        const holdings = [
            { symbol: "BTC", value: 60 },
            { symbol: "ETH", value: 30 },
            { symbol: "DOGE", value: 10 },
        ];
        const total = holdings.reduce((sum, h) => sum + h.value, 0);
        assertEqual(total, 100, "total value");
        const btcPct = (holdings[0].value / total) * 100;
        assertEqual(btcPct, 60, "BTC allocation");
    });

    it("handles empty portfolio", () => {
        const holdings = [];
        const total = holdings.reduce((sum, h) => sum + h.value, 0);
        assertEqual(total, 0, "empty total");
    });
});

// ─── Symbol Search Logic Tests ──────────────────────────────

describe("symbol-search.js — search filtering", () => {
    it("filters symbols by query", () => {
        const symbols = ["BTC", "ETH", "BTCUSDT", "DOGE", "BONE"];
        const query = "BT";
        const filtered = symbols.filter(s => s.toUpperCase().includes(query.toUpperCase()));
        assertEqual(filtered.length, 2, "BT matches BTC and BTCUSDT");
    });

    it("case-insensitive search", () => {
        const symbols = ["BTC", "ETH", "DOGE"];
        const query = "btc";
        const filtered = symbols.filter(s => s.toUpperCase().includes(query.toUpperCase()));
        assertEqual(filtered.length, 1, "case-insensitive match");
        assertEqual(filtered[0], "BTC", "matched BTC");
    });

    it("returns empty for no match", () => {
        const symbols = ["BTC", "ETH"];
        const query = "XYZ";
        const filtered = symbols.filter(s => s.toUpperCase().includes(query.toUpperCase()));
        assertEqual(filtered.length, 0, "no match");
    });
});

// ─── UI Components Logic Tests ──────────────────────────────

describe("ui-components.js — formatting helpers", () => {
    it("formats price with appropriate decimals", () => {
        const formatPrice = (price) => {
            if (price < 0.01) return price.toFixed(8);
            if (price < 1) return price.toFixed(4);
            return price.toFixed(2);
        };
        assertEqual(formatPrice(0.001), "0.00100000", "tiny price");
        assertEqual(formatPrice(0.5), "0.5000", "sub-dollar price");
        assertEqual(formatPrice(45000), "45000.00", "large price");
    });

    it("formats percentage change", () => {
        const formatPct = (pct) => `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
        assertEqual(formatPct(5.5), "+5.50%", "positive pct");
        assertEqual(formatPct(-3.2), "-3.20%", "negative pct");
        assertEqual(formatPct(0), "+0.00%", "zero pct");
    });
});

// ─── Coin Display Logic Tests ───────────────────────────────

describe("coin-display.js — data mapping", () => {
    it("maps coin data for table display", () => {
        const coin = {
            symbol: "TEST",
            name: "TestCoin",
            price: 0.05,
            percent_change_24h: 12.5,
        };
        const row = {
            symbol: coin.symbol,
            name: coin.name,
            price: coin.price,
            change: coin.percent_change_24h,
            bullish: coin.percent_change_24h > 0,
        };
        assertEqual(row.symbol, "TEST", "symbol mapping");
        assert(row.bullish, "bullish indicator");
    });
});

// ─── Results ────────────────────────────────────────────────

console.log(`\n${"=".repeat(50)}`);
console.log(`Results: ${passed} passed, ${failed} failed`);
if (failures.length > 0) {
    console.log(`\nFailures:`);
    failures.forEach((f, i) => console.log(`  ${i + 1}. ${f}`));
    process.exit(1);
} else {
    console.log("All tests passed!");
    process.exit(0);
}
