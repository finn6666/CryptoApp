# JavaScript Module Structure

The JavaScript codebase has been refactored from a single 1000+ line file into focused, maintainable modules.

## File Structure

```
js/
├── main.js                  # Entry point & initialization (25 lines)
├── ui-components.js         # UI helpers & HTML generators (200 lines)
├── coin-display.js          # Coin card rendering (140 lines)
├── api-service.js           # API calls & data loading (220 lines)
├── favorites.js             # Favorites management (50 lines)
├── symbol-search.js         # Symbol search functionality (110 lines)
├── utils.js                 # Utility functions (40 lines)
└── main-old-backup.js       # Original monolithic file (backup)
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

## Benefits

✅ **Better Organization** - Each file has a clear purpose
✅ **Easier Maintenance** - Find and fix code faster
✅ **Better Testing** - Test modules independently
✅ **Reduced Complexity** - Smaller, focused files
✅ **Team Collaboration** - Less merge conflicts
✅ **Code Reuse** - Share functions across files

## Loading Order

Scripts are loaded in dependency order in `index.html`:
1. ui-components.js (base UI functions)
2. coin-display.js (uses UI components)
3. api-service.js (uses coin display)
4. favorites.js (uses API service)
5. symbol-search.js (uses API service)
6. utils.js (standalone utilities)
7. main.js (initializes everything)

## Migration Notes

- Old `main.js` backed up as `main-old-backup.js`
- All functionality preserved
- No breaking changes to API
- Same global functions exposed
