# 📦 JavaScript Module Structure

Modular JavaScript architecture for maintainability and clarity.

> **Refactored:** Previously a single 1000+ line file, now organized into focused modules.

## 📁 File Structure

```
js/
├── main.js                  # Entry point & initialization (~25 lines)
├── ui-components.js         # UI helpers & HTML generators (~200 lines)
├── coin-display.js          # Coin card rendering (~140 lines)
├── api-service.js           # API calls & data loading (~220 lines)
├── favorites.js             # Favorites management (~50 lines)
├── symbol-search.js         # Symbol search functionality (~110 lines)
├── utils.js                 # Utility functions (~40 lines)
└── main-old-backup.js       # Original file (backup only)
```

## Module Descriptions

### `main.js` (Entry Point)
- Application initialization
- Global state management
- Auto-refresh timer setup

### `ui-components.js`
- `generateAISentimentHTML()` - AI sentiment section
- `generateMLReasoningHTML()` - ML prediction section
- `formatPrice()` - Price formatting
- `getScoreInfo()` - Score calculations
- `toggleAISentiment()` - AI section toggle
- `toggleMLReasoning()` - ML section toggle
- `showStatus()` - Toast notifications

### `coin-display.js`
- `generateCoinsTable()` - Main coins grid
- `generateFavoritesTable()` - Favorites grid
- Handles all coin card HTML generation

### `api-service.js`
- `loadStats()` - Load dashboard stats
- `loadCoins()` - Load coin data
- `loadFavorites()` - Load favorites
- `loadMLStatus()` - Load ML status
- `trainMLModel()` - Train ML model
- `forceRefresh()` - Manual refresh
- `refreshData()` - Reload all data

### `favorites.js`
- `toggleFavorite()` - Add/remove favorite
- `removeFavorite()` - Remove favorite
- `updateFavoriteButtons()` - Update UI state

### `symbol-search.js`
- `toggleSymbolSearch()` - Show/hide search
- `searchSymbols()` - Search for coins
- `addSymbol()` - Add new symbol
- Enter key handler

### `utils.js`
- `updateRefreshStatus()` - Update timestamps
- `startRefreshTimer()` - Auto-refresh setup
- `updateMLStatus()` - Update ML badges

## ✨ Benefits

- ✅ **Better Organization** - Each file has a clear, single purpose
- ✅ **Easier Maintenance** - Find and fix code faster
- ✅ **Better Testing** - Test modules independently
- ✅ **Reduced Complexity** - Smaller, focused files (~40-220 lines each)
- ✅ **Team Collaboration** - Fewer merge conflicts
- ✅ **Code Reuse** - Share functions across modules

## 📋 Loading Order

Scripts load in dependency order in [index.html](../../templates/index.html):

1. **ui-components.js** - Base UI functions (no dependencies)
2. **coin-display.js** - Uses UI components
3. **api-service.js** - Uses coin display
4. **favorites.js** - Uses API service
5. **symbol-search.js** - Uses API service
6. **utils.js** - Standalone utilities
7. **main.js** - Initializes everything (entry point)

## Migration Notes

- Old `main.js` backed up as `main-old-backup.js`
- All functionality preserved
- No breaking changes to API
- Same global functions exposed
