"""
Multi-Exchange Manager
Manages multiple exchange connections (Coinbase + Kraken) with pair caching,
tradeable coin filtering, and priority-based order routing.
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from ml.error_handling import retry, alert_exchange_down, alert_trade_failure

logger = logging.getLogger(__name__)

# Cache file for exchange trading pairs
PAIRS_CACHE_FILE = Path("data/exchange_pairs_cache.json")
PAIRS_CACHE_TTL = 3600 * 6  # 6 hours


class ExchangeManager:
    """
    Manages multiple exchanges with priority-based routing.

    - Caches tradeable pairs per exchange on startup
    - Tags coins with which exchange(s) can trade them
    - Routes orders through exchanges in priority order
    - Falls back to secondary exchange when primary doesn't list a pair
    """

    def __init__(self):
        self._exchanges: Dict[str, Any] = {}
        self._pairs: Dict[str, set] = {}  # exchange_id → set of "BASE/QUOTE" pairs
        self._coin_exchange_map: Dict[str, List[str]] = {}  # symbol → [exchange_ids]

        # Exchange priority from env (comma-separated)
        priority_str = os.getenv("EXCHANGE_PRIORITY", "coinbase,kraken")
        self.exchange_priority: List[str] = [
            e.strip().lower() for e in priority_str.split(",") if e.strip()
        ]

        self._pairs_loaded = False
        logger.info(f"Exchange manager initialised — priority: {self.exchange_priority}")

    # ─── Exchange Connections ─────────────────────────────────

    def _init_exchange(self, exchange_id: str):
        """Lazy-initialise an exchange connection via ccxt."""
        if exchange_id in self._exchanges:
            return self._exchanges[exchange_id]

        try:
            import ccxt
        except ImportError:
            logger.error("ccxt not installed — run: pip install ccxt")
            return None

        config = self._get_exchange_config(exchange_id)
        if not config:
            logger.warning(f"No API keys configured for {exchange_id}")
            return None

        try:
            exchange_class = getattr(ccxt, exchange_id, None)
            if exchange_class is None:
                logger.error(f"Unknown exchange: {exchange_id}")
                return None

            exchange = exchange_class({
                **config,
                "enableRateLimit": True,
            })
            self._load_markets_with_retry(exchange, exchange_id)
            self._exchanges[exchange_id] = exchange
            logger.info(f"✅ {exchange_id} connected — {len(exchange.markets)} markets")
            return exchange
        except Exception as e:
            logger.error(f"Failed to connect {exchange_id}: {e}")
            alert_exchange_down(exchange_id, str(e))
            return None

    @staticmethod
    @retry(max_attempts=3, base_delay=2.0, backoff=2.0)
    def _load_markets_with_retry(exchange, exchange_id: str):
        """Load exchange markets with retry on network errors."""
        exchange.load_markets()

    def _get_exchange_config(self, exchange_id: str) -> Optional[Dict[str, str]]:
        """Get API credentials for an exchange from env vars."""
        if exchange_id == "coinbase":
            key = os.getenv("COINBASE_API_KEY", "")
            secret = os.getenv("COINBASE_API_SECRET", "")
            if key and secret:
                return {"apiKey": key, "secret": secret}
        elif exchange_id == "kraken":
            key = os.getenv("KRAKEN_API_KEY", "")
            secret = os.getenv("KRAKEN_PRIVATE_KEY", "")
            if key and secret:
                return {"apiKey": key, "secret": secret}
        else:
            # Generic fallback: EXCHANGE_API_KEY / EXCHANGE_API_SECRET
            prefix = exchange_id.upper()
            key = os.getenv(f"{prefix}_API_KEY", "")
            secret = os.getenv(f"{prefix}_API_SECRET", "")
            if key and secret:
                return {"apiKey": key, "secret": secret}
        return None

    # ─── Pair Caching ─────────────────────────────────────────

    def load_pairs(self, force_refresh: bool = False):
        """
        Load tradeable pairs for all configured exchanges.
        Uses disk cache if fresh enough, otherwise queries live.
        """
        if self._pairs_loaded and not force_refresh:
            return

        # Try loading from cache
        if not force_refresh and self._load_pairs_cache():
            self._pairs_loaded = True
            self._rebuild_coin_exchange_map()
            return

        # Query each exchange
        for exchange_id in self.exchange_priority:
            self._fetch_pairs(exchange_id)

        self._rebuild_coin_exchange_map()
        self._save_pairs_cache()
        self._pairs_loaded = True

    def _fetch_pairs(self, exchange_id: str):
        """Fetch all trading pairs from an exchange."""
        exchange = self._init_exchange(exchange_id)
        if not exchange:
            logger.warning(f"Skipping {exchange_id} — not connected")
            return

        try:
            pairs = set(exchange.markets.keys())
            self._pairs[exchange_id] = pairs
            logger.info(f"Cached {len(pairs)} pairs from {exchange_id}")
        except Exception as e:
            logger.error(f"Failed to fetch pairs from {exchange_id}: {e}")
            self._pairs[exchange_id] = set()

    def _rebuild_coin_exchange_map(self):
        """Build a symbol → [exchanges] map from cached pairs."""
        self._coin_exchange_map = {}
        for exchange_id, pairs in self._pairs.items():
            for pair in pairs:
                base = pair.split("/")[0] if "/" in pair else pair
                if base not in self._coin_exchange_map:
                    self._coin_exchange_map[base] = []
                if exchange_id not in self._coin_exchange_map[base]:
                    self._coin_exchange_map[base].append(exchange_id)

    def _load_pairs_cache(self) -> bool:
        """Load pairs from disk cache if still fresh."""
        if not PAIRS_CACHE_FILE.exists():
            return False
        try:
            with open(PAIRS_CACHE_FILE) as f:
                cache = json.load(f)
            cached_at = cache.get("cached_at", 0)
            if time.time() - cached_at > PAIRS_CACHE_TTL:
                logger.info("Exchange pairs cache expired — will refresh")
                return False

            for eid, pair_list in cache.get("pairs", {}).items():
                self._pairs[eid] = set(pair_list)

            total = sum(len(p) for p in self._pairs.values())
            logger.info(f"Loaded {total} pairs from cache ({len(self._pairs)} exchanges)")
            return True
        except Exception as e:
            logger.warning(f"Failed to load pairs cache: {e}")
            return False

    def _save_pairs_cache(self):
        """Save pairs to disk cache."""
        try:
            PAIRS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            cache = {
                "cached_at": time.time(),
                "cached_at_human": datetime.utcnow().isoformat(),
                "pairs": {eid: sorted(pairs) for eid, pairs in self._pairs.items()},
            }
            with open(PAIRS_CACHE_FILE, "w") as f:
                json.dump(cache, f)
            logger.info("Exchange pairs cache saved")
        except Exception as e:
            logger.error(f"Failed to save pairs cache: {e}")

    # ─── Tradeable Coin Filtering ─────────────────────────────

    def is_tradeable(self, symbol: str) -> bool:
        """Check if a coin is tradeable on any configured exchange."""
        self.load_pairs()
        return symbol.upper() in self._coin_exchange_map

    def get_exchanges_for_coin(self, symbol: str) -> List[str]:
        """Get list of exchanges that list this coin, in priority order."""
        self.load_pairs()
        available = self._coin_exchange_map.get(symbol.upper(), [])
        # Sort by priority
        return sorted(available, key=lambda e: (
            self.exchange_priority.index(e) if e in self.exchange_priority else 999
        ))

    def filter_tradeable_coins(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Filter a list of symbols to only those tradeable on configured exchanges.
        Returns list of dicts with symbol and exchange info.
        """
        self.load_pairs()
        tradeable = []
        for sym in symbols:
            exchanges = self.get_exchanges_for_coin(sym)
            if exchanges:
                tradeable.append({
                    "symbol": sym.upper(),
                    "exchanges": exchanges,
                    "primary_exchange": exchanges[0],
                })
        return tradeable

    def get_tradeable_summary(self) -> Dict[str, Any]:
        """Get a summary of tradeable pairs across exchanges."""
        self.load_pairs()
        return {
            "exchanges": {
                eid: len(pairs) for eid, pairs in self._pairs.items()
            },
            "total_tradeable_coins": len(self._coin_exchange_map),
            "priority": self.exchange_priority,
        }

    # ─── Order Routing ────────────────────────────────────────

    def find_best_pair(self, symbol: str) -> Optional[Tuple[str, str]]:
        """
        Find the best exchange and trading pair for a symbol.
        Tries exchanges in priority order.
        Returns (exchange_id, "SYMBOL/QUOTE") or None.
        """
        self.load_pairs()
        exchanges = self.get_exchanges_for_coin(symbol)

        for exchange_id in exchanges:
            pairs = self._pairs.get(exchange_id, set())
            # Try quote currencies in preference order
            for quote in ["GBP", "USD", "USDT", "USDC", "EUR", "BTC"]:
                pair = f"{symbol.upper()}/{quote}"
                if pair in pairs:
                    return exchange_id, pair

        return None

    def get_exchange(self, exchange_id: str):
        """Get a connected exchange instance."""
        if exchange_id in self._exchanges:
            return self._exchanges[exchange_id]
        return self._init_exchange(exchange_id)

    def execute_order(
        self,
        symbol: str,
        side: str,
        amount_gbp: float,
    ) -> Dict[str, Any]:
        """
        Execute an order on the best available exchange.
        Tries exchanges in priority order until one succeeds.
        """
        result = self.find_best_pair(symbol)
        if not result:
            return {
                "success": False,
                "error": f"No trading pair found for {symbol} on any exchange",
            }

        exchange_id, pair = result
        exchange = self.get_exchange(exchange_id)
        if not exchange:
            return {
                "success": False,
                "error": f"Failed to connect to {exchange_id}",
            }

        try:
            # Get current price (with retry)
            ticker = self._fetch_ticker_with_retry(exchange, pair)
            current_price = ticker["last"]
            quantity = amount_gbp / current_price

            # Place market order (with retry)
            order = self._place_order_with_retry(
                exchange, pair, side, quantity
            )

            return {
                "success": True,
                "exchange": exchange_id,
                "pair": pair,
                "order_id": order.get("id", "unknown"),
                "side": side,
                "quantity": order.get("filled", quantity),
                "price": order.get("average", current_price),
                "amount_gbp": amount_gbp,
            }
        except Exception as e:
            logger.error(f"Order failed on {exchange_id}: {e}")
            alert_trade_failure(symbol, str(e), {"exchange": exchange_id, "side": side})
            # Try next exchange
            exchanges = self.get_exchanges_for_coin(symbol)
            remaining = [eid for eid in exchanges if eid != exchange_id]
            for fallback_id in remaining:
                try:
                    fb_result = self._try_order_on_exchange(
                        fallback_id, symbol, side, amount_gbp
                    )
                    if fb_result.get("success"):
                        return fb_result
                except Exception as fb_e:
                    logger.error(f"Fallback order failed on {fallback_id}: {fb_e}")
                    continue

            return {"success": False, "error": str(e)}

    @staticmethod
    @retry(max_attempts=3, base_delay=1.0, backoff=2.0)
    def _fetch_ticker_with_retry(exchange, pair: str):
        """Fetch ticker with retry on transient network errors."""
        return exchange.fetch_ticker(pair)

    @staticmethod
    @retry(max_attempts=2, base_delay=1.5, backoff=2.0)
    def _place_order_with_retry(exchange, pair: str, side: str, quantity: float):
        """Place a market order with retry (fewer attempts — money is involved)."""
        if side == "buy":
            return exchange.create_market_buy_order(pair, quantity)
        else:
            return exchange.create_market_sell_order(pair, quantity)

    def _try_order_on_exchange(
        self, exchange_id: str, symbol: str, side: str, amount_gbp: float
    ) -> Dict[str, Any]:
        """Try to execute an order on a specific exchange."""
        exchange = self.get_exchange(exchange_id)
        if not exchange:
            return {"success": False, "error": f"Cannot connect to {exchange_id}"}

        pairs = self._pairs.get(exchange_id, set())
        for quote in ["GBP", "USD", "USDT", "USDC", "EUR", "BTC"]:
            pair = f"{symbol.upper()}/{quote}"
            if pair in pairs:
                ticker = self._fetch_ticker_with_retry(exchange, pair)
                current_price = ticker["last"]
                quantity = amount_gbp / current_price

                order = self._place_order_with_retry(
                    exchange, pair, side, quantity
                )

                return {
                    "success": True,
                    "exchange": exchange_id,
                    "pair": pair,
                    "order_id": order.get("id", "unknown"),
                    "side": side,
                    "quantity": order.get("filled", quantity),
                    "price": order.get("average", current_price),
                    "amount_gbp": amount_gbp,
                }

        return {"success": False, "error": f"No pair for {symbol} on {exchange_id}"}


# ─── Singleton ────────────────────────────────────────────────

_manager: Optional[ExchangeManager] = None


def get_exchange_manager() -> ExchangeManager:
    """Get or create the singleton exchange manager."""
    global _manager
    if _manager is None:
        _manager = ExchangeManager()
    return _manager
