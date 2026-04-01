"""
Q-Learning Trade Selector

Learns from trade outcomes to adjust future buy/skip decisions.
Uses a discretised state space with epsilon-greedy exploration.

State features (discretised):
- gem_score_tier: low / medium / high  (attractiveness_score × 10)
- volume_mcap_ratio: low / medium / high  (24h_volume / market_cap)
- weekly_change: bearish / neutral / bullish  (price_change_7d)
- market_cap_tier: micro / small / mid / large
- screen_confidence_tier: low / medium / high  (quick-screen confidence %)

Actions: BUY, SKIP

Reward: actual P&L % from closed positions, with shaping for:
- Repeat losers (extra penalty for buying same pattern that lost before)
- Opportunity cost (small negative for long holds with no movement)
- Win streaks (small bonus for consecutive profitable trades)

Integration: provides a confidence_adjustment that modifies the agent's
raw confidence score before the scan loop's trade decision threshold.
"""

import json
import logging
import math
import os
import random
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

Q_TABLE_FILE = Path("data/q_table.json")
OUTCOME_LOG_FILE = Path("data/trade_outcomes.jsonl")

# ─── State Discretisation ─────────────────────────────────────

def _gem_tier(score: float) -> str:
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def _volume_mcap_tier(ratio: float) -> str:
    """ratio = 24h_volume / market_cap"""
    if ratio >= 0.3:
        return "high"
    if ratio >= 0.05:
        return "medium"
    return "low"


def _weekly_change_tier(pct: float) -> str:
    if pct > 5:
        return "bullish"
    if pct < -5:
        return "bearish"
    return "neutral"


def _confidence_tier(score: float) -> str:
    """Tier the agent/screen confidence score at scan time."""
    if score >= 70:
        return "high"
    if score >= 55:
        return "medium"
    return "low"


def _momentum_direction(pct_7d: float) -> str:
    """Classify 7-day price change direction at entry time."""
    if pct_7d > 5:
        return "uptrend"
    if pct_7d < -5:
        return "downtrend"
    return "flat"


def _btc_regime() -> str:
    """
    Classify the current BTC market regime (bull / neutral / bear) from
    BTC's 7-day price change in app state.  Falls back to 'neutral' if
    the data is unavailable so the state space stays consistent.
    """
    try:
        import services.app_state as state
        if state.analyzer and state.analyzer.coins:
            for coin in state.analyzer.coins:
                if getattr(coin, "symbol", "").upper() in ("BTC", "WBTC"):
                    pct = float(getattr(coin, "price_change_7d", 0) or 0)
                    if pct > 10:
                        return "bull"
                    if pct < -10:
                        return "bear"
                    return "neutral"
    except Exception:
        pass
    return "neutral"


def _mcap_tier(mcap_gbp: float) -> str:
    if mcap_gbp >= 500_000_000:
        return "large"
    if mcap_gbp >= 50_000_000:
        return "mid"
    if mcap_gbp >= 5_000_000:
        return "small"
    return "micro"


def discretise_state(coin_data: Dict[str, Any]) -> str:
    """
    Convert raw coin data into a hashable state string.
    Returns e.g. 'high|medium|bearish|micro|high'

    Supports multiple field name aliases to handle differences between
    scan-time coin dicts and portfolio holding dicts.  If a pre-computed
    'ql_state' key is present it is returned directly (used when the
    state was cached at buy time and passed through to close time).
    """
    # Pre-computed state takes full priority (buy-time cache passed through)
    if coin_data.get("ql_state"):
        return coin_data["ql_state"]

    # gem_score: quantitative market score (attractiveness_score = 0-10 scale
    # normalised to 0-100 by ×10; gem_score field is already 0-100)
    gem_raw = (
        coin_data.get("gem_score")
        or coin_data.get("attractiveness_score", 0) * 10
        or 0
    )
    try:
        gem_raw = float(gem_raw)
    except (TypeError, ValueError):
        gem_raw = 0.0
    gem = _gem_tier(gem_raw)

    try:
        mcap_val = float(coin_data.get("market_cap", 0) or 0)
    except (TypeError, ValueError):
        mcap_val = 0.0
    try:
        vol_val = float(coin_data.get("volume_24h", 0) or 0)
    except (TypeError, ValueError):
        vol_val = 0.0

    vol = _volume_mcap_tier(
        vol_val / max(mcap_val, 1)
    )

    # weekly change: coin_to_dict uses 'price_change_7d', not 'percent_change_7d'
    weekly_pct = (
        coin_data.get("price_change_7d")
        or coin_data.get("percent_change_7d")
        or 0
    )
    try:
        weekly_pct = float(weekly_pct)
    except (TypeError, ValueError):
        weekly_pct = 0.0
    wk = _weekly_change_tier(weekly_pct)

    mc = _mcap_tier(mcap_val)

    # agent/screen confidence at scan time (differentiates high vs low conviction buys)
    conf_raw = (
        coin_data.get("screen_confidence")
        or coin_data.get("confidence")
        or 0
    )
    try:
        conf_raw = float(conf_raw)
    except (TypeError, ValueError):
        conf_raw = 0.0
    conf = _confidence_tier(conf_raw)

    momentum = _momentum_direction(weekly_pct)
    btc = _btc_regime()
    return f"{gem}|{vol}|{wk}|{mc}|{conf}|{momentum}|{btc}"


# ─── Q-Learning Engine ────────────────────────────────────────

ACTIONS = ("buy", "skip")


class QLearningTrader:
    """
    Tabular Q-learning agent for buy/skip decisions.

    - Persists Q-table to disk so learning survives restarts
    - Logs every outcome for auditing
    - Provides confidence_adjustment() for the scan loop
    """

    def __init__(
        self,
        alpha: float = None,
        gamma: float = None,
        epsilon: float = None,
        epsilon_min: float = None,
        epsilon_decay: float = None,
    ):
        # Learning rate — how much new info overrides old
        self.alpha = alpha if alpha is not None else float(
            os.environ.get("QL_ALPHA", "0.15")
        )
        # Discount factor — importance of future rewards
        self.gamma = gamma if gamma is not None else float(
            os.environ.get("QL_GAMMA", "0.9")
        )
        # Exploration rate — probability of random action
        # Lower default (0.10 vs legacy 0.3) to reduce random noise in live trading
        self.epsilon = epsilon if epsilon is not None else float(
            os.environ.get("QL_EPSILON", "0.10")
        )
        self.epsilon_min = epsilon_min if epsilon_min is not None else float(
            os.environ.get("QL_EPSILON_MIN", "0.02")
        )
        # Decay per episode (each completed trade outcome)
        self.epsilon_decay = epsilon_decay if epsilon_decay is not None else float(
            os.environ.get("QL_EPSILON_DECAY", "0.995")
        )
        # Minimum visits a state needs before Q-learning can block/adjust trades.
        # Prevents one bad trade from poisoning an entire state class.
        self.min_visits_to_act = int(os.environ.get("QL_MIN_VISITS", "3"))

        # Q-table: state → {action → value}
        self.q_table: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {a: 0.0 for a in ACTIONS}
        )
        # Visit counts for diagnostics
        self.visit_counts: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {a: 0 for a in ACTIONS}
        )
        # Track symbols that have lost money: stores Unix timestamps of losses.
        # Time-decayed: only losses within the last 90 days count toward penalties.
        self.loss_memory: Dict[str, List[float]] = {}
        # State recorded at scan/buy time, keyed by symbol; used at close time
        # so record_outcome uses the real market-context state, not stale holding data
        self._symbol_state_cache: Dict[str, str] = {}
        # Total update steps (increments twice per closed trade: buy + skip update)
        self.episodes = 0
        # Actual completed trade count — what the UI should display
        self.closed_trades = 0

        self._load()

    # ─── Core Q-Learning ──────────────────────────────────────

    def get_action(self, state: str) -> str:
        """Epsilon-greedy action selection."""
        if random.random() < self.epsilon:
            return random.choice(ACTIONS)
        q_values = self.q_table[state]
        return max(q_values, key=q_values.get)

    def update(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: Optional[str] = None,
    ):
        """
        Q-value update using Bellman equation.
        next_state is None for terminal states (position closed).
        """
        current_q = self.q_table[state][action]

        if next_state is not None:
            max_next_q = max(self.q_table[next_state].values())
            target = reward + self.gamma * max_next_q
        else:
            target = reward

        # Q-learning update rule
        self.q_table[state][action] = current_q + self.alpha * (target - current_q)
        self.visit_counts[state][action] += 1

        # Decay epsilon after each learning step
        self.episodes += 1
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        self._save()

    # ─── Reward Shaping ───────────────────────────────────────

    def calculate_reward(
        self,
        pnl_pct: float,
        symbol: str,
        hold_hours: float = 0,
    ) -> float:
        """
        Shaped reward signal from trade outcome.

        Components:
        1. Base reward: scaled P&L percentage
        2. Repeat-loser penalty: extra cost for buying patterns that keep losing
        3. Opportunity cost: small drag for very long holds with minimal movement
        4. Asymmetric scaling: losses hurt more than equivalent gains help
           (reflects real psychology + the math of recovering from losses)
        """
        # 1. Base reward — scale P&L into [-1, 1] range using tanh
        #    tanh(pnl/30) maps ±30% P&L to roughly ±0.8
        base = math.tanh(pnl_pct / 30.0)

        # 2. Asymmetric loss penalty — losses are 1.5× as impactful
        if base < 0:
            base *= 1.5

        # 3. Repeat-loser penalty — count only losses within the last 90 days
        loss_window = time.time() - 90 * 86400
        if pnl_pct < -5:
            timestamps = self.loss_memory.get(symbol, [])
            # Prune losses older than 90 days, then record this one
            timestamps = [t for t in timestamps if t > loss_window]
            timestamps.append(time.time())
            self.loss_memory[symbol] = timestamps
            times_lost = len(timestamps)
            # Progressive penalty: -0.1 first loss, -0.2 second, capped at -0.5
            repeat_penalty = -0.1 * min(times_lost, 5)
            base += max(repeat_penalty, -0.5)
        elif pnl_pct > 5:
            # Winning resets the loss counter
            self.loss_memory.pop(symbol, None)

        # 4. Opportunity cost for long stagnant holds (>168h = 1 week)
        if hold_hours > 168 and abs(pnl_pct) < 5:
            base -= 0.05  # Small penalty for capital tied up with no movement

        return round(base, 4)

    # ─── Integration: Confidence Adjustment ───────────────────

    def confidence_adjustment(self, coin_data: Dict[str, Any]) -> int:
        """
        Returns an adjustment (-20 to +15) to apply to the agent's
        raw confidence score before the buy threshold check.

        Positive = Q-learning thinks this state pattern tends to win.
        Negative = Q-learning thinks this state pattern tends to lose.
        """
        state = discretise_state(coin_data)
        # Cache state so record_outcome can use it at close time
        symbol = coin_data.get("symbol")
        if symbol:
            self._symbol_state_cache[symbol] = state
        q_buy = self.q_table[state]["buy"]
        q_skip = self.q_table[state]["skip"]
        visits = self.visit_counts[state]["buy"]

        # Not enough data — don't adjust until we have min_visits_to_act observations
        if visits < self.min_visits_to_act:
            return 0

        # Difference between buy and skip Q-values
        advantage = q_buy - q_skip

        # Scale to [-20, +15] range (asymmetric: easier to penalise than boost)
        # Clamp advantage to [-1, 1] first
        clamped = max(-1.0, min(1.0, advantage))
        if clamped >= 0:
            adjustment = int(clamped * 15)
        else:
            adjustment = int(clamped * 20)

        return adjustment

    def should_skip(self, coin_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Consult Q-table for a direct BUY/SKIP recommendation.
        Returns (should_skip, reason).

        Only recommends SKIP if the state has been visited at least once —
        avoids blocking trades based on random epsilon-greedy exploration
        on unseen states (which caused spurious SKIPs in the activity log).
        """
        state = discretise_state(coin_data)
        # Also cache state here in case confidence_adjustment wasn't called
        symbol = coin_data.get("symbol")
        if symbol:
            self._symbol_state_cache[symbol] = state

        visits = sum(self.visit_counts[state].values())
        # Need at least min_visits_to_act observations before blocking trades.
        # Prevents a single bad trade from locking out an entire state class.
        if visits < self.min_visits_to_act * 2:  # *2 because buy+skip are both updated
            return False, ""

        action = self.get_action(state)

        if action == "skip":
            q_vals = self.q_table[state]
            reason = (
                f"Q-learning recommends SKIP for state {state} "
                f"(Q_buy={q_vals['buy']:.3f}, Q_skip={q_vals['skip']:.3f}, "
                f"visits={visits}, ε={self.epsilon:.3f})"
            )
            return True, reason

        return False, ""

    # ─── Outcome Recording ────────────────────────────────────

    def record_outcome(
        self,
        symbol: str,
        coin_data: Dict[str, Any],
        action: str,
        pnl_pct: float,
        hold_hours: float = 0,
        exit_trigger: str = "",
    ):
        """
        Record a trade outcome and update Q-values.
        Called by sell automation when a position closes, or periodically
        for unrealised P&L checkpoints.
        """
        # Prefer the state cached at buy/scan time over recalculating from the
        # portfolio holding dict (which lacks live market data fields)
        state = (
            self._symbol_state_cache.get(symbol)
            or coin_data.get("ql_state")
            or discretise_state(coin_data)
        )
        reward = self.calculate_reward(pnl_pct, symbol, hold_hours)

        # Terminal update (position closed)
        self.update(state, action, reward, next_state=None)

        # Also update the skip action inversely — if buying lost money,
        # skipping would have been correct (and vice versa)
        skip_reward = -reward * 0.3  # Weaker inverse signal
        self.update(state, "skip", skip_reward, next_state=None)

        # Count this as one completed trade (episodes incremented twice above,
        # once per update call, so closed_trades is the accurate UI metric)
        self.closed_trades += 1

        # Log outcome
        outcome = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "state": state,
            "action": action,
            "pnl_pct": round(pnl_pct, 2),
            "hold_hours": round(hold_hours, 1),
            "reward": reward,
            "exit_trigger": exit_trigger,
            "epsilon": round(self.epsilon, 4),
            "q_buy": round(self.q_table[state]["buy"], 4),
            "q_skip": round(self.q_table[state]["skip"], 4),
        }
        self._log_outcome(outcome)

        logger.info(
            f"Q-learning outcome: {symbol} {action} → "
            f"P&L {pnl_pct:+.1f}%, reward={reward:+.3f}, "
            f"Q_buy={self.q_table[state]['buy']:.3f}, "
            f"Q_skip={self.q_table[state]['skip']:.3f}, "
            f"ε={self.epsilon:.3f}"
        )

    def record_unrealised_checkpoint(
        self,
        symbol: str,
        coin_data: Dict[str, Any],
        pnl_pct: float,
        hold_hours: float,
    ):
        """
        Periodic checkpoint for open positions.
        Uses a much smaller learning rate to avoid overreacting to
        unrealised swings, but still nudges Q-values in the right direction.
        """
        state = (
            self._symbol_state_cache.get(symbol)
            or coin_data.get("ql_state")
            or discretise_state(coin_data)
        )
        # Pure base reward — does NOT call calculate_reward() to avoid
        # mutating loss_memory on every market-monitor tick (which would
        # inflate loss counts by hundreds per position)
        base = math.tanh(pnl_pct / 30.0)
        if base < 0:
            base *= 1.5
        reward = round(base, 4) * 0.2
        current_q = self.q_table[state]["buy"]
        self.q_table[state]["buy"] = current_q + self.alpha * 0.3 * (reward - current_q)
        self._save()

    # ─── Diagnostics ──────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return Q-learning diagnostics for the dashboard."""
        total_states = len(self.q_table)
        visited_states = sum(
            1 for s in self.visit_counts
            if sum(self.visit_counts[s].values()) > 0
        )
        total_visits = sum(
            sum(v.values()) for v in self.visit_counts.values()
        )

        # Best and worst states
        best_state = max(
            self.q_table, key=lambda s: self.q_table[s]["buy"], default=None
        )
        worst_state = max(
            self.q_table, key=lambda s: -self.q_table[s]["buy"], default=None
        )

        # State diversity: how many distinct states have been visited
        # Ideal: visited_states > 2 (means coins are being differentiated)
        state_diversity = visited_states / max(total_states, 1)

        return {
            "epsilon": round(self.epsilon, 4),
            "alpha": self.alpha,
            "gamma": self.gamma,
            "episodes": self.episodes,
            "closed_trades": self.closed_trades,
            "total_states": total_states,
            "visited_states": visited_states,
            "state_diversity": round(state_diversity, 2),
            "state_cache_size": len(self._symbol_state_cache),
            "total_visits": total_visits,
            "loss_memory": {
                k: len([t for t in v if t > time.time() - 90 * 86400])
                for k, v in self.loss_memory.items()
            },
            "best_state": {
                "state": best_state,
                "q_buy": round(self.q_table[best_state]["buy"], 4) if best_state else 0,
            } if best_state else None,
            "worst_state": {
                "state": worst_state,
                "q_buy": round(self.q_table[worst_state]["buy"], 4) if worst_state else 0,
            } if worst_state else None,
        }

    def get_outcome_history(self, limit: int = 50) -> List[Dict]:
        """Read recent outcomes from the log."""
        if not OUTCOME_LOG_FILE.exists():
            return []
        entries = []
        try:
            with open(OUTCOME_LOG_FILE) as f:
                for line in f:
                    try:
                        entries.append(json.loads(line.strip()))
                    except (json.JSONDecodeError, ValueError):
                        pass
            return list(reversed(entries[-limit:]))
        except Exception as e:
            logger.warning(f"Failed to read outcome history: {e}")
            return []

    # ─── Persistence ──────────────────────────────────────────

    def _save(self):
        try:
            Q_TABLE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "q_table": dict(self.q_table),
                "visit_counts": dict(self.visit_counts),
                "loss_memory": self.loss_memory,
                "symbol_state_cache": self._symbol_state_cache,
                "epsilon": self.epsilon,
                "episodes": self.episodes,
                "closed_trades": self.closed_trades,
            }
            with open(Q_TABLE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save Q-table: {e}")

    def _load(self):
        if not Q_TABLE_FILE.exists():
            logger.info("No existing Q-table — starting fresh")
            return
        try:
            with open(Q_TABLE_FILE) as f:
                data = json.load(f)

            skipped_legacy = 0
            for state, actions in data.get("q_table", {}).items():
                if state.count("|") != 6:
                    skipped_legacy += 1
                    continue
                self.q_table[state] = actions
            for state, counts in data.get("visit_counts", {}).items():
                if state.count("|") != 6:
                    continue
                self.visit_counts[state] = counts
            if skipped_legacy:
                logger.info(
                    f"Q-table loaded: skipped {skipped_legacy} legacy state entries (dimension mismatch)"
                )

            # loss_memory is stored as lists of Unix timestamps.
            # Migrate from legacy int format (counts) to timestamp list format.
            raw_loss = data.get("loss_memory", {})
            migrated = {}
            for k, v in raw_loss.items():
                if isinstance(v, list):
                    migrated[k] = v
                elif isinstance(v, (int, float)) and v > 0:
                    # Legacy: count → synthesize timestamps spaced 1 day apart
                    now_ts = time.time()
                    migrated[k] = [now_ts - i * 86400 for i in range(min(int(v), 5))]
            self.loss_memory = migrated

            self._symbol_state_cache = data.get("symbol_state_cache", {})
            loaded_eps = data.get("epsilon", self.epsilon)
            # QL_EPSILON_FLOOR: minimum exploration rate to restore on load.
            # Set this env var (e.g. 0.2) to re-open exploration after a losing streak.
            eps_floor = float(os.environ.get("QL_EPSILON_FLOOR", "0.0"))
            self.epsilon = max(loaded_eps, eps_floor)
            self.episodes = data.get("episodes", 0)
            self.closed_trades = data.get("closed_trades", self.episodes // 2)

            logger.info(
                f"Loaded Q-table: {len(self.q_table)} states, "
                f"{self.closed_trades} closed trades, ε={self.epsilon:.3f}, "
                f"state_cache={len(self._symbol_state_cache)} symbols"
            )
        except Exception as e:
            logger.error(f"Failed to load Q-table: {e}")

    def _log_outcome(self, outcome: Dict):
        try:
            OUTCOME_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(OUTCOME_LOG_FILE, "a") as f:
                f.write(json.dumps(outcome) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log outcome: {e}")


# ─── Singleton ────────────────────────────────────────────────

_instance: Optional[QLearningTrader] = None


def get_q_learner() -> QLearningTrader:
    global _instance
    if _instance is None:
        _instance = QLearningTrader()
    return _instance
