# Data Model

Key data structures, state globals, and file formats.

## Coin Object (CoinMarketCap data)

Coins flowing through the pipeline have these key fields:

| Field | Type | Source |
|-------|------|--------|
| `symbol` | str | CoinMarketCap |
| `name` | str | CoinMarketCap |
| `price` | float | CoinMarketCap |
| `volume_24h` | float | CoinMarketCap |
| `percent_change_24h` | float | CoinMarketCap |
| `percent_change_7d` | float | CoinMarketCap |
| `market_cap` | float | CoinMarketCap |
| `cmc_rank` | int | CoinMarketCap |
| `attractiveness_score` | float | Computed (0–10 scale) |

## TradeProposal (dataclass)

```python
@dataclass
class TradeProposal:
    id: str
    symbol: str
    side: str                  # 'buy' | 'sell'
    amount_gbp: float
    price_at_proposal: float
    reason: str
    confidence: float          # 0–100
    agent_recommendation: str
    status: str                # pending → approved/rejected/executed/expired
    executed_at: Optional[str]
    execution_price: Optional[float]
    quantity: Optional[float]
    order_id: Optional[str]
    error: Optional[str]
```

## DailyBudget (dataclass)

```python
@dataclass
class DailyBudget:
    date: str
    spent_gbp: float
    trades_executed: int
    trades_proposed: int
    sell_proceeds_gbp: float
    sells_executed: int
    fees_gbp: float
```

## App State Globals (`services/app_state.py`)

Key globals initialised by `init_all()` on startup:

| Global | Type | Purpose |
|--------|------|---------|
| `trading_engine` | `TradingEngine` | Singleton trading engine |
| `scan_loop` | `ScanLoop` | Singleton scan loop |
| `market_monitor` | `MarketMonitor` | Singleton monitor |
| `official_adk_available` | bool | Whether ADK agents loaded |
| `analyze_crypto_adk` | callable | ADK analysis entry point |
| `CACHE_EXPIRY_SECONDS` | int | 43200 (12h) |
| `analysis_cache` | dict | In-memory analysis results |
| `exchange_manager` | `ExchangeManager` | Singleton exchange manager |

Imports within Flask request context: always use `import services.app_state as state` inside functions, never at module level.

## JSON State Files

| File | Schema | Notes |
|------|--------|-------|
| `data/portfolio.json` | `{holdings: [], trade_history: [], closed_positions: []}` | Updated on every trade |
| `data/trades/trading_state.json` | `{proposals: [], daily_budgets: []}` | Proposals + budget tracking |
| `data/trades/sell_automation_state.json` | `{peak_prices: {}, last_recheck: {}}` | Sell automation state |
| `data/agent_analysis_cache.json` | `{symbol: {result, timestamp}}` | Disk backup of analysis cache |
| `data/exchange_pairs_cache.json` | `{pairs: [], fetched_at: ""}` | Exchange pair list (6h TTL) |
| `data/trades/audit_log.jsonl` | JSONL — one event per line | Full audit trail |

## Scan Log Format

`data/scan_logs/scan_YYYY-MM-DD.json` — JSON array of per-coin results:

```json
[
  {
    "symbol": "BTC",
    "analyzed": true,
    "trade_decision": {"should_trade": false, "side": "hold", "conviction": 42},
    "proposal_id": null,
    "error": null,
    "timestamp": "2026-03-14T12:00:00"
  }
]
```

## Gem Score Data

`data/gem_score_history.jsonl` — historical attractiveness scores per coin per scan, used by `/api/gems/history` endpoints. Written by `GemScoreTracker` even after gem detector removal (now uses `attractiveness_score` as the score value).
