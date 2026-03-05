# Skill: Testing

## Overview

pytest with shared fixtures in `conftest.py`. All exchange/API calls are mocked — no integration tests that hit real services.

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `tests/conftest.py` | ~100 | Shared fixtures + env var setup |
| `tests/test_trading_engine.py` | ~165 | TradingEngine unit tests (15 tests) |
| `tests/test_scan_loop.py` | ~55 | ScanLoop basic tests (3 tests) |
| `tests/test_backtesting.py` | ~118 | Backtesting engine tests |
| `tests/test_exchange_manager.py` | ~122 | Exchange manager tests |
| `tests/test_portfolio_tracker.py` | ~218 | Portfolio tracker tests |
| `tests/test_training_pipeline.py` | ~147 | ML training pipeline tests |
| `tests/test_agent_memory.py` | ~51 | Agent memory tests |
| `tests/test_frontend.js` | ~295 | Frontend JS tests (manually run) |

## Running Tests

```bash
uv run pytest                    # all tests
uv run pytest tests/test_trading_engine.py  # specific file
uv run pytest -v                 # verbose
uv run pytest -x                 # stop on first failure
```

## Fixtures (`conftest.py`)

**Environment setup** (runs before all imports):
```python
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["GOOGLE_API_KEY"] = "test-google-key"
os.environ["TRADING_API_KEY"] = "test-api-key"
```

| Fixture | Scope | Provides |
|---------|-------|----------|
| `tmp_data_dir(tmp_path)` | function | Temp directory with `data/trades/`, `data/agent_memory/`, `data/scan_logs/` |
| `sample_coin_data()` | function | Dict: TestCoin at £0.05, 500K mcap, 120K volume |
| `sample_trade_proposal()` | function | Dict: TEST buy £0.02 at £0.05, confidence 80 |
| `mock_exchange()` | function | MagicMock ccxt exchange with `TEST/GBP`, `TEST/USD`, `BTC/GBP` markets; mocked ticker + orders |
| `mock_ccxt(mock_exchange)` | function | Patches `sys.modules["ccxt"]` to return mock exchange |
| `live_prices()` | function | Dict: `{TEST: 0.06, BTC: 45000, ETH: 3000, DOGE: 0.08}` |

## Test Patterns

**TradingEngine tests** (most comprehensive — 15 tests):
- `test_initial_state` — budget matches env, kill switch off
- `test_can_afford_trade` — within/over budget
- `test_kill_switch_blocks_trades` — proposals blocked when active
- `test_propose_trade_success` — creates proposal with ID
- `test_propose_trade_budget_cap` — amount capped at `max_trade_pct`
- `test_propose_trade_cooldown` — second proposal blocked within cooldown
- `test_reject_trade` / `test_reject_nonexistent`
- `test_approve_expired_proposal` — manually sets `created_at` 2h ago
- `test_activate/deactivate_kill_switch`
- `test_token_sign_verify` — HMAC round-trip
- `test_persistence` — save state, create new engine, verify proposal count
- `test_get_pending_proposals` / `test_get_trade_history_empty`

**ScanLoop tests** (basic — 3 tests):
- `test_init_config` — verifies env vars applied
- `test_get_status` — status dict has required keys
- `test_run_scan_no_coins` — mocked pipeline, no tradeable coins

## Writing New Tests

1. Use existing fixtures from `conftest.py`
2. Mock external services (exchanges, APIs) — never hit real endpoints
3. Use `tmp_data_dir` for any file I/O to avoid polluting `data/`
4. Tests use `DAILY_TRADE_BUDGET_GBP` from env (defaults £3.00)
5. Follow existing patterns: class-based grouping, descriptive method names

Example:
```python
class TestNewFeature:
    def test_basic_behavior(self, tmp_data_dir, sample_coin_data, mock_ccxt):
        engine = TradingEngine(data_dir=tmp_data_dir / "data")
        result = engine.some_method(sample_coin_data)
        assert result["success"] is True
```

## Gotchas

- `mock_ccxt` patches at `sys.modules` level — affects all imports in that test
- `test_scan_loop.py` sets `SCAN_ENABLED=false` and patches file paths to tmp dir
- No integration tests that call real exchanges or ADK
- Frontend tests (`test_frontend.js`) are separate — not run by pytest
- Budget defaults come from env vars, not hardcoded — `DAILY_TRADE_BUDGET_GBP=3.00`
