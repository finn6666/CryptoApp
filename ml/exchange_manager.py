"""
Exchange Manager
Manages the Kraken exchange connection with pair caching,
tradeable coin filtering, and order routing.
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
        self._fx_cache: Dict[str, float] = {}  # FX rate cache (per session)

        # Exchange priority from env (comma-separated)
        priority_str = os.getenv("EXCHANGE_PRIORITY", "kraken")
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
        if exchange_id == "kraken":
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
        Converts GBP to the pair's quote currency when needed.
        Verifies exchange balance before placing orders.
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
            current_price = ticker.get("last") or ticker.get("close")
            if not current_price:
                return {
                    "success": False,
                    "error": f"No current price available for {pair} on {exchange_id} (ticker returned None)",
                }

            # Convert GBP amount to quote currency if pair isn't GBP-quoted
            quote_currency = pair.split("/")[1] if "/" in pair else "GBP"
            fx_rate = 1.0
            if quote_currency != "GBP":
                fx_rate = self._get_fx_rate("GBP", quote_currency, exchange)
                if fx_rate is None:
                    return {
                        "success": False,
                        "error": f"Cannot convert GBP to {quote_currency} — no FX rate available",
                    }

            # amount in quote currency, then divide by price to get quantity
            amount_in_quote = amount_gbp * fx_rate
            quantity = amount_in_quote / current_price

            # Enforce exchange-specific minimum order sizes
            min_qty = self._get_min_order_quantity(exchange, pair)
            min_cost = self._get_min_order_cost(exchange, pair)

            # Bump quantity up to minimum if needed (and recalculate amount_gbp)
            if min_qty and quantity < min_qty:
                old_qty = quantity
                quantity = min_qty * 1.02  # 2% buffer above minimum
                new_amount_in_quote = quantity * current_price
                new_amount_gbp = new_amount_in_quote / fx_rate
                logger.info(
                    f"Bumped order from {old_qty:.8f} to {quantity:.8f} "
                    f"(min={min_qty:.8f}) — £{amount_gbp:.4f} → £{new_amount_gbp:.4f}"
                )
                amount_gbp = new_amount_gbp

            # Also check cost minimum (in quote currency)
            if min_cost and (quantity * current_price) < min_cost:
                quantity = (min_cost * 1.02) / current_price  # 2% buffer
                new_amount_gbp = (quantity * current_price) / fx_rate
                logger.info(
                    f"Bumped order to meet cost minimum {min_cost:.4f} {quote_currency} "
                    f"— £{amount_gbp:.4f} → £{new_amount_gbp:.4f}"
                )
                amount_gbp = new_amount_gbp

            # Recalculate amount_in_quote after any quantity bumps so the
            # balance check uses the *actual* order cost, not the original.
            amount_in_quote = quantity * current_price

            # Verify exchange balance before placing order
            balance_check = self._check_balance(exchange, exchange_id, side, pair, quantity, amount_in_quote)
            if not balance_check["ok"]:
                return {
                    "success": False,
                    "error": balance_check["error"],
                }

            # Place market order (with retry)
            order = self._place_order_with_retry(
                exchange, pair, side, quantity
            )

            # Log raw order response for debugging
            logger.info(
                f"Order response from {exchange_id}: id={order.get('id')}, "
                f"filled={order.get('filled')}, amount={order.get('amount')}, "
                f"average={order.get('average')}, cost={order.get('cost')}, "
                f"status={order.get('status')}"
            )

            # Extract fee from order response
            fee_gbp = self._extract_fee_gbp(order, fx_rate)

            # Use filled quantity from exchange, fall back to our calculated qty
            filled_qty = order.get("filled") or order.get("amount") or quantity

            return {
                "success": True,
                "exchange": exchange_id,
                "pair": pair,
                "order_id": order.get("id", "unknown"),
                "side": side,
                "quantity": filled_qty,
                "price": order.get("average") or current_price,
                "amount_gbp": amount_gbp,
                "fee_gbp": fee_gbp,
                "fx_rate": fx_rate,
                "quote_currency": quote_currency,
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
        """Try to execute an order on a specific exchange (with FX conversion)."""
        exchange = self.get_exchange(exchange_id)
        if not exchange:
            return {"success": False, "error": f"Cannot connect to {exchange_id}"}

        pairs = self._pairs.get(exchange_id, set())
        for quote in ["GBP", "USD", "USDT", "USDC", "EUR", "BTC"]:
            pair = f"{symbol.upper()}/{quote}"
            if pair in pairs:
                ticker = self._fetch_ticker_with_retry(exchange, pair)
                current_price = ticker.get("last") or ticker.get("close")
                if not current_price:
                    logger.warning(f"No price for {pair} on {exchange_id}, trying next quote")
                    continue

                # FX conversion
                fx_rate = 1.0
                if quote != "GBP":
                    fx_rate = self._get_fx_rate("GBP", quote, exchange)
                    if fx_rate is None:
                        continue  # Skip this quote, try next

                amount_in_quote = amount_gbp * fx_rate
                quantity = amount_in_quote / current_price

                # Enforce exchange minimums on fallback too
                min_qty = self._get_min_order_quantity(exchange, pair)
                min_cost = self._get_min_order_cost(exchange, pair)
                if min_qty and quantity < min_qty:
                    quantity = min_qty * 1.02
                    amount_gbp = (quantity * current_price) / fx_rate
                if min_cost and (quantity * current_price) < min_cost:
                    quantity = (min_cost * 1.02) / current_price
                    amount_gbp = (quantity * current_price) / fx_rate

                # Recalculate after any bumps
                amount_in_quote = quantity * current_price

                # Balance check
                balance_check = self._check_balance(exchange, exchange_id, side, pair, quantity, amount_in_quote)
                if not balance_check["ok"]:
                    continue

                order = self._place_order_with_retry(
                    exchange, pair, side, quantity
                )

                fee_gbp = self._extract_fee_gbp(order, fx_rate)

                filled_qty = order.get("filled") or order.get("amount") or quantity

                return {
                    "success": True,
                    "exchange": exchange_id,
                    "pair": pair,
                    "order_id": order.get("id", "unknown"),
                    "side": side,
                    "quantity": filled_qty,
                    "price": order.get("average") or current_price,
                    "amount_gbp": amount_gbp,
                    "fee_gbp": fee_gbp,
                    "fx_rate": fx_rate,
                    "quote_currency": quote,
                }

        return {"success": False, "error": f"No pair for {symbol} on {exchange_id}"}

    # ─── FX Conversion ───────────────────────────────────────

    def _get_fx_rate(self, from_currency: str, to_currency: str, exchange) -> Optional[float]:
        """
        Get exchange rate from one fiat/stable to another.
        Uses the exchange's own ticker data (e.g. GBP/USD pair).
        Falls back to hardcoded approximate rates if no direct pair exists.
        """
        if from_currency == to_currency:
            return 1.0

        cache_key = f"{from_currency}/{to_currency}"
        if cache_key in self._fx_cache:
            return self._fx_cache[cache_key]

        # Try direct pair on exchange (e.g. GBP/USD)
        for direct_pair in [f"{from_currency}/{to_currency}", f"{to_currency}/{from_currency}"]:
            try:
                if direct_pair in getattr(exchange, "markets", {}):
                    ticker = exchange.fetch_ticker(direct_pair)
                    rate = ticker.get("last", 0)
                    if rate and rate > 0:
                        if direct_pair.startswith(from_currency):
                            self._fx_cache[cache_key] = rate
                            return rate
                        else:
                            self._fx_cache[cache_key] = 1.0 / rate
                            return 1.0 / rate
            except Exception:
                continue

        # Fallback: approximate rates (GBP base)
        approx_rates = {
            "GBP/USD": 1.27, "GBP/USDT": 1.27, "GBP/USDC": 1.27,
            "GBP/EUR": 1.17, "GBP/BTC": 0.000012,
        }
        if cache_key in approx_rates:
            rate = approx_rates[cache_key]
            self._fx_cache[cache_key] = rate
            logger.warning(f"Using approximate FX rate: {cache_key} = {rate}")
            return rate

        # Try inverse
        inverse_key = f"{to_currency}/{from_currency}"
        if inverse_key in approx_rates:
            rate = 1.0 / approx_rates[inverse_key]
            self._fx_cache[cache_key] = rate
            logger.warning(f"Using approximate FX rate (inverse): {cache_key} = {rate:.6f}")
            return rate

        logger.error(f"No FX rate available for {cache_key}")
        return None

    # ─── Balance Verification ─────────────────────────────────

    def _check_balance(
        self, exchange, exchange_id: str, side: str, pair: str,
        quantity: float, amount_in_quote: float,
    ) -> Dict[str, Any]:
        """
        Verify the exchange account has sufficient balance for the order.
        If buying and the quote currency balance is too low but GBP is available,
        automatically converts GBP → quote currency on the exchange first.
        Returns {"ok": True} or {"ok": False, "error": "..."}.
        """
        try:
            # Timeout-safe balance fetch (Pi has limited bandwidth)
            balance = exchange.fetch_balance(params={"timeout": 10000})  # 10s
            base, quote = pair.split("/") if "/" in pair else (pair, "GBP")

            if side == "buy":
                # Need enough quote currency to cover the order
                available = balance.get(quote, {}).get("free", 0) or 0
                if available < amount_in_quote:
                    # Try auto-converting GBP → quote currency if possible
                    if quote != "GBP":
                        converted = self._auto_convert_gbp(
                            exchange, exchange_id, quote,
                            amount_in_quote - available, balance,
                        )
                        if converted:
                            return {"ok": True}

                    msg = (
                        f"Insufficient {quote} balance on {exchange_id}: "
                        f"have {available:.4f}, need {amount_in_quote:.4f}"
                    )
                    logger.warning(msg)
                    return {"ok": False, "error": msg}
            else:
                # Need enough base currency to sell
                available = balance.get(base, {}).get("free", 0) or 0
                if available < quantity:
                    msg = (
                        f"Insufficient {base} balance on {exchange_id}: "
                        f"have {available:.8f}, need {quantity:.8f}"
                    )
                    logger.warning(msg)
                    return {"ok": False, "error": msg}

            return {"ok": True}
        except Exception as e:
            # If balance check fails, log but allow the order to proceed
            # (the exchange will reject if funds are truly insufficient)
            logger.warning(f"Balance check failed on {exchange_id} (proceeding anyway): {e}")
            return {"ok": True}

    def _auto_convert_gbp(
        self, exchange, exchange_id: str, target_currency: str,
        amount_needed: float, balance: Dict,
    ) -> bool:
        """
        Auto-convert GBP → target_currency on the exchange when the target
        balance is insufficient but GBP is available.
        Returns True if conversion succeeded, False otherwise.
        """
        gbp_free = balance.get("GBP", {}).get("free", 0) or 0
        if gbp_free < 0.50:  # Need at least £0.50 to bother
            logger.info(f"Auto-convert skipped: only £{gbp_free:.2f} GBP available")
            return False

        # Check if GBP/<target> pair exists (e.g. GBP/USD)
        convert_pair = f"GBP/{target_currency}"
        if convert_pair not in getattr(exchange, "markets", {}):
            logger.info(f"Auto-convert skipped: {convert_pair} not available on {exchange_id}")
            return False

        try:
            ticker = exchange.fetch_ticker(convert_pair)
            rate = ticker["last"]
            if not rate or rate <= 0:
                return False

            # How much GBP do we need to sell to get amount_needed in target?
            # GBP/USD means selling GBP gives USD: gbp_amount * rate = usd_amount
            gbp_to_sell = (amount_needed / rate) * 1.03  # 3% buffer for slippage + fees

            # Don't convert more than we have (leave £1 cushion)
            max_gbp = gbp_free - 1.0
            if gbp_to_sell > max_gbp:
                gbp_to_sell = max_gbp
            if gbp_to_sell < 0.50:
                logger.info(f"Auto-convert: not enough GBP to convert (need £{gbp_to_sell:.2f})")
                return False

            # Check exchange minimum for this pair
            market = exchange.market(convert_pair)
            min_qty = (market.get("limits", {}).get("amount", {}).get("min", 0) or 0)
            min_cost = (market.get("limits", {}).get("cost", {}).get("min", 0) or 0)
            if min_qty and gbp_to_sell < min_qty:
                gbp_to_sell = min_qty * 1.02
            if min_cost and (gbp_to_sell * rate) < min_cost:
                gbp_to_sell = (min_cost * 1.02) / rate

            # Final check we can still afford it
            if gbp_to_sell > gbp_free:
                logger.info(f"Auto-convert: GBP needed (£{gbp_to_sell:.2f}) exceeds available (£{gbp_free:.2f})")
                return False

            logger.info(
                f"💱 Auto-converting £{gbp_to_sell:.2f} GBP → {target_currency} "
                f"on {exchange_id} (rate {rate:.4f}, need {amount_needed:.4f} {target_currency})"
            )

            order = exchange.create_market_sell_order(convert_pair, gbp_to_sell)
            filled = order.get("filled") or gbp_to_sell
            avg_price = order.get("average") or rate
            received = filled * avg_price

            logger.info(
                f"💱 Converted £{filled:.2f} → {received:.4f} {target_currency} "
                f"(avg rate {avg_price:.4f}, order {order.get('id', 'unknown')})"
            )
            return True

        except Exception as e:
            logger.error(f"Auto-convert GBP → {target_currency} failed: {e}")
            return False

    # ─── Fee Extraction ───────────────────────────────────────

    @staticmethod
    def _extract_fee_gbp(order: Dict[str, Any], fx_rate: float) -> float:
        """
        Extract trading fee from ccxt order response and convert to GBP.
        ccxt returns fee as {"cost": <float>, "currency": "<CODE>"}.
        """
        try:
            fee_info = order.get("fee") or {}
            fee_cost = fee_info.get("cost", 0) or 0
            if fee_cost <= 0:
                return 0.0
            # Convert fee to GBP (fee is in quote currency, fx_rate is GBP→quote)
            if fx_rate > 0:
                return round(fee_cost / fx_rate, 6)
            return round(fee_cost, 6)
        except Exception:
            return 0.0

    @staticmethod
    def _get_min_order_quantity(exchange, pair: str) -> float:
        """Get minimum order quantity for a pair on an exchange."""
        try:
            market = exchange.market(pair)
            limits = market.get("limits", {}).get("amount", {})
            return limits.get("min", 0) or 0
        except Exception:
            return 0

    @staticmethod
    def _get_min_order_cost(exchange, pair: str) -> float:
        """Get minimum order cost (in quote currency) for a pair on an exchange."""
        try:
            market = exchange.market(pair)
            cost_min = market.get("limits", {}).get("cost", {}).get("min", 0) or 0
            return float(cost_min)
        except Exception:
            return 0

    def get_min_order_gbp(self, symbol: str) -> float:
        """
        Get the minimum order size in GBP for a symbol.
        Checks both quantity-based and cost-based minimums.
        Returns the minimum GBP needed to place an order, or 0 if unknown.
        """
        result = self.find_best_pair(symbol)
        if not result:
            return 0

        exchange_id, pair = result
        exchange = self.get_exchange(exchange_id)
        if not exchange:
            return 0

        try:
            ticker = exchange.fetch_ticker(pair)
            current_price = ticker.get("last", 0)
            if not current_price:
                return 0

            quote_currency = pair.split("/")[1] if "/" in pair else "GBP"
            fx_rate = 1.0
            if quote_currency != "GBP":
                fx_rate = self._get_fx_rate("GBP", quote_currency, exchange)
                if fx_rate is None:
                    fx_rate = 1.27  # fallback approx GBP→USD

            # Minimum from quantity limit
            min_qty = self._get_min_order_quantity(exchange, pair)
            min_gbp_from_qty = (min_qty * current_price) / fx_rate if min_qty else 0

            # Minimum from cost limit (already in quote currency)
            min_cost = self._get_min_order_cost(exchange, pair)
            min_gbp_from_cost = min_cost / fx_rate if min_cost else 0

            # Take the larger of the two minimums, add 5% buffer for price movement
            min_gbp = max(min_gbp_from_qty, min_gbp_from_cost)
            if min_gbp > 0:
                min_gbp *= 1.05  # 5% buffer

            return round(min_gbp, 4)
        except Exception as e:
            logger.warning(f"Could not determine min order for {symbol}: {e}")
            return 0

    def get_status(self) -> Dict[str, Any]:
        """Get connectivity and configuration status for all exchanges."""
        status = {
            "priority": self.exchange_priority,
            "pairs_loaded": self._pairs_loaded,
            "total_coins": len(self._coin_exchange_map),
            "exchanges": {},
        }
        for eid in self.exchange_priority:
            has_keys = self._get_exchange_config(eid) is not None
            connected = eid in self._exchanges
            pair_count = len(self._pairs.get(eid, set()))
            status["exchanges"][eid] = {
                "configured": has_keys,
                "connected": connected,
                "pairs": pair_count,
            }
        return status


# ─── Singleton ────────────────────────────────────────────────

_manager: Optional[ExchangeManager] = None


def get_exchange_manager() -> ExchangeManager:
    """Get or create the singleton exchange manager."""
    global _manager
    if _manager is None:
        _manager = ExchangeManager()
    return _manager
