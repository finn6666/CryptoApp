"""
Claude Agent Runner — Lightweight between-scan portfolio manager.

Runs every 1-2h via systemd timer. Fetches a context snapshot from the app,
calls Gemini for portfolio reasoning, and optionally proposes trades via the
/api/claude/propose endpoint.

Conservative by default: only flags concerns unless conviction >= 70% for buys.
Sells are proposed and require standard email approval.

Usage:
    uv run python -m ml.claude_agent_runner
    # or via systemd timer: cryptoapp-claude-agent.timer
"""

import os
import sys
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ─── Logging ───────────────────────────────────────────────────────────────────

LOG_DIR = Path("data/agent_runner_logs")
LOG_DIR.mkdir(exist_ok=True)

_log_file = LOG_DIR / f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_log_file),
    ],
)
logger = logging.getLogger(__name__)

# ─── Config from environment ────────────────────────────────────────────────────

APP_URL = os.getenv("TRADE_SERVER_URL", "http://localhost:5001").rstrip("/")
API_KEY = os.getenv("TRADING_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
AGENT_MODEL = os.getenv("CLAUDE_AGENT_MODEL", "gemini-2.0-flash")

MIN_BUY_CONFIDENCE = 70   # Only propose buys at this confidence or above
MIN_SELL_CONFIDENCE = 60  # Only propose sells at this confidence or above


# ─── HTTP helpers ──────────────────────────────────────────────────────────────

def _auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }


def _get(path: str) -> dict:
    url = f"{APP_URL}{path}"
    req = urllib.request.Request(url, headers=_auth_headers())
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _post(path: str, body: dict) -> dict:
    url = f"{APP_URL}{path}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=_auth_headers(), method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


# ─── Context fetching ──────────────────────────────────────────────────────────

def fetch_context() -> dict:
    """Fetch the compact portfolio context snapshot from the app."""
    logger.info("Fetching context snapshot from %s/api/claude/context", APP_URL)
    ctx = _get("/api/claude/context")
    holdings_count = len(ctx.get("holdings", []))
    pending_count = len(ctx.get("pending_proposals", []))
    remaining = ctx.get("budget", {}).get("remaining_gbp", "?")
    logger.info(
        "Context: %d holdings, %d pending proposals, GBP %.2f remaining",
        holdings_count,
        pending_count,
        float(remaining) if isinstance(remaining, (int, float)) else 0,
    )
    return ctx


# ─── Gemini analysis ───────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a conservative cryptocurrency portfolio manager agent.
Your role is to review the current portfolio every 1-2 hours and flag issues or
opportunities. You have access to current holdings, pending proposals, and market
conditions.

Your priorities (in order):
1. Capital preservation — protect against significant losses
2. Exit management — ensure held positions have appropriate exits
3. Opportunity seizing — only propose new buys at very high conviction (>=70%)

Output a JSON object with this exact structure:
{
  "summary": "<1-2 sentence assessment of portfolio health>",
  "concerns": ["<concern 1>", "<concern 2>"],
  "proposed_actions": [
    {
      "action": "buy" | "sell" | "flag",
      "symbol": "<SYMBOL>",
      "confidence": <integer 0-100>,
      "reasoning": "<concise rationale, max 300 chars>",
      "sell_quantity": <float or null>
    }
  ],
  "overall_risk": "low" | "medium" | "high"
}

Rules:
- Only include buy actions if confidence >= 70
- Only include sell actions if confidence >= 60
- Use "flag" for concerns that don't warrant immediate action
- Keep reasoning concise and factual
- Never propose a buy if kill_switch is true
- Never propose a buy if remaining budget < 1.00 GBP
"""


def analyse_with_gemini(ctx: dict) -> dict:
    """Send context to Gemini and get structured portfolio analysis."""
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore

    client = genai.Client(api_key=GOOGLE_API_KEY)

    context_str = json.dumps(ctx, indent=2, default=str)
    prompt = (
        "Here is the current portfolio context:\n\n"
        f"```json\n{context_str}\n```\n\n"
        "Analyse this and respond with the JSON structure described. "
        "Output only valid JSON — no markdown fences, no explanation outside the JSON."
    )

    from services.gemini_budget import get_gemini_budget, BudgetExceededError
    try:
        get_gemini_budget().check_and_record("claude_runner")
    except BudgetExceededError as _be:
        raise RuntimeError(f"Gemini daily budget exceeded: {_be}") from _be

    logger.info("Calling Gemini model %s for portfolio analysis", AGENT_MODEL)
    response = client.models.generate_content(
        model=AGENT_MODEL,
        contents=_SYSTEM_PROMPT + "\n\n" + prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )

    text = response.text.strip()
    # Strip any accidental markdown fences
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            l for l in lines if not l.startswith("```")
        ).strip()

    analysis = json.loads(text)
    logger.info("Analysis summary: %s | risk: %s", analysis.get("summary", ""), analysis.get("overall_risk", "?"))
    return analysis


# ─── Action execution ──────────────────────────────────────────────────────────

def execute_actions(analysis: dict, ctx: dict) -> None:
    """Execute proposed_actions from the Gemini analysis."""
    kill_switch = ctx.get("kill_switch", False)
    remaining = float(ctx.get("budget", {}).get("remaining_gbp", 0) or 0)

    concerns = analysis.get("concerns", [])
    if concerns:
        logger.info("Concerns flagged: %s", "; ".join(concerns))

    for action in analysis.get("proposed_actions", []):
        act = action.get("action", "").lower()
        symbol = str(action.get("symbol", "")).upper().strip()
        confidence = int(action.get("confidence", 0))
        reasoning = str(action.get("reasoning", "")).strip()

        if act == "flag":
            logger.info("FLAG [%s]: %s", symbol, reasoning)
            continue

        if not symbol or not reasoning:
            logger.warning("Skipping action with missing symbol or reasoning: %s", action)
            continue

        if act == "buy":
            if kill_switch:
                logger.info("Skipping buy [%s] — kill switch active", symbol)
                continue
            if remaining < 1.0:
                logger.info("Skipping buy [%s] — insufficient budget (GBP %.2f)", symbol, remaining)
                continue
            if confidence < MIN_BUY_CONFIDENCE:
                logger.info(
                    "Skipping buy [%s] — confidence %d%% below threshold %d%%",
                    symbol, confidence, MIN_BUY_CONFIDENCE,
                )
                continue
            logger.info("Proposing buy [%s] confidence=%d%%: %s", symbol, confidence, reasoning)
            try:
                result = _post("/api/claude/propose", {
                    "symbol": symbol,
                    "side": "buy",
                    "reasoning": reasoning,
                    "confidence": confidence,
                })
                logger.info("Buy proposal result: %s", result)
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="replace")
                logger.warning("Buy proposal failed [%s] HTTP %d: %s", symbol, e.code, body)
            except Exception as e:
                logger.warning("Buy proposal error [%s]: %s", symbol, e)

        elif act == "sell":
            if confidence < MIN_SELL_CONFIDENCE:
                logger.info(
                    "Skipping sell [%s] — confidence %d%% below threshold %d%%",
                    symbol, confidence, MIN_SELL_CONFIDENCE,
                )
                continue
            sell_qty = action.get("sell_quantity")
            payload = {
                "symbol": symbol,
                "side": "sell",
                "reasoning": reasoning,
                "confidence": confidence,
            }
            if sell_qty is not None:
                payload["sell_quantity"] = sell_qty
            logger.info("Proposing sell [%s] confidence=%d%%: %s", symbol, confidence, reasoning)
            try:
                result = _post("/api/claude/propose", payload)
                logger.info("Sell proposal result: %s", result)
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="replace")
                logger.warning("Sell proposal failed [%s] HTTP %d: %s", symbol, e.code, body)
            except Exception as e:
                logger.warning("Sell proposal error [%s]: %s", symbol, e)

        else:
            logger.warning("Unknown action type '%s' for symbol %s — skipping", act, symbol)


# ─── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    start = datetime.now(timezone.utc)
    logger.info("=== Claude agent runner starting ===")

    if not API_KEY:
        logger.error("TRADING_API_KEY is not set — cannot call the app API")
        return 1

    if not GOOGLE_API_KEY:
        logger.error("GOOGLE_API_KEY is not set — cannot call Gemini")
        return 1

    try:
        ctx = fetch_context()
    except urllib.error.HTTPError as e:
        logger.error("Failed to fetch context HTTP %d: %s", e.code, e.read().decode(errors="replace"))
        return 1
    except Exception as e:
        logger.error("Failed to fetch context: %s", e)
        return 1

    try:
        analysis = analyse_with_gemini(ctx)
    except Exception as e:
        logger.error("Gemini analysis failed: %s", e)
        return 1

    # Persist the analysis for debugging
    run_log = {
        "timestamp": start.isoformat(),
        "context_summary": {
            "holdings": len(ctx.get("holdings", [])),
            "pending_proposals": len(ctx.get("pending_proposals", [])),
            "remaining_gbp": ctx.get("budget", {}).get("remaining_gbp"),
            "kill_switch": ctx.get("kill_switch"),
        },
        "analysis": analysis,
    }
    log_path = LOG_DIR / f"analysis_{start.strftime('%Y%m%d_%H%M%S')}.json"
    log_path.write_text(json.dumps(run_log, indent=2, default=str))
    logger.info("Analysis saved to %s", log_path)

    execute_actions(analysis, ctx)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info("=== Claude agent runner done in %.1fs ===", elapsed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
