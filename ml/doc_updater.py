"""
Lightweight weekly documentation updater.

Reads Python files changed in the last 7 days (via git), sends them to a
single Gemini Flash call, and updates docs/CHANGELOG.md + docs/ARCHITECTURE.md.

No ADK, no heavy deps — just google.genai directly.
Run via: systemd cryptoapp-docs.timer  (Sundays 02:00)
Or manually: uv run python -m ml.doc_updater
"""

import os
import logging
import subprocess
import textwrap
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────
MODEL = "gemini-2.0-flash"
MAX_SOURCE_BYTES = 40_000   # ~40 KB of Python source sent to Gemini
APP_DIR = Path(__file__).parent.parent
CHANGELOG_PATH = APP_DIR / "docs" / "CHANGELOG.md"
ARCHITECTURE_PATH = APP_DIR / "docs" / "ARCHITECTURE.md"
STATE_FILE = APP_DIR / "data" / "doc_updater_state.json"

# Python files that are architecturally significant
CORE_FILES = [
    "app.py",
    "ml/scan_loop.py",
    "ml/market_monitor.py",
    "ml/trading_engine.py",
    "ml/exchange_manager.py",
    "ml/sell_automation.py",
    "ml/orchestrator_wrapper.py",
    "services/app_state.py",
    "routes/trading.py",
    "routes/ml_routes.py",
]


# ── Git helpers ─────────────────────────────────────────────────────────────

def _git(*args) -> str:
    result = subprocess.run(
        ["git", *args], cwd=APP_DIR, capture_output=True, text=True, timeout=15
    )
    return result.stdout.strip()


def get_changed_py_files(since_days: int = 7) -> list[str]:
    """Return .py files changed in the last N days (relative paths)."""
    out = _git("log", f"--since={since_days} days ago", "--name-only",
               "--pretty=format:", "--diff-filter=AM")
    files = [f for f in out.splitlines() if f.endswith(".py") and f]
    # Deduplicate, prioritise core files first
    seen = set()
    ordered = []
    for f in CORE_FILES:
        if f in files and f not in seen:
            ordered.append(f)
            seen.add(f)
    for f in files:
        if f not in seen:
            ordered.append(f)
            seen.add(f)
    return ordered


def get_recent_commits(days: int = 7) -> str:
    """Return one-line git log for the last N days."""
    return _git("log", f"--since={days} days ago", "--oneline")


def read_file_capped(path: Path, budget: list[int]) -> str:
    """Read a file, contributing at most `budget[0]` bytes. Mutates budget."""
    if budget[0] <= 0 or not path.exists():
        return ""
    try:
        text = path.read_text(errors="replace")
        chunk = text[: budget[0]]
        budget[0] -= len(chunk)
        if len(chunk) < len(text):
            chunk += "\n# ... (truncated)"
        return chunk
    except Exception:
        return ""


def build_source_context(changed_files: list[str]) -> str:
    """Collect source from changed files up to MAX_SOURCE_BYTES."""
    budget = [MAX_SOURCE_BYTES]
    parts = []
    for rel in changed_files:
        path = APP_DIR / rel
        content = read_file_capped(path, budget)
        if content:
            parts.append(f"### {rel}\n```python\n{content}\n```")
        if budget[0] <= 0:
            parts.append("_Additional changed files omitted (budget exhausted)._")
            break
    return "\n\n".join(parts)


# ── Existing docs helpers ───────────────────────────────────────────────────

def read_existing_doc(path: Path, max_chars: int = 6000) -> str:
    if not path.exists():
        return "(file does not exist yet)"
    text = path.read_text(errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + "\n... (truncated for context)"
    return text


# ── Gemini call ─────────────────────────────────────────────────────────────

def call_gemini(prompt: str) -> str:
    """Single synchronous Gemini Flash call. Returns model text."""
    import google.genai as genai  # lazy import — not needed at module load

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )
    return response.text


# ── Prompt building ─────────────────────────────────────────────────────────

def build_prompt(
    changed_files: list[str],
    source_context: str,
    recent_commits: str,
    existing_changelog: str,
    existing_architecture: str,
    run_date: str,
) -> str:
    changed_list = "\n".join(f"- {f}" for f in changed_files) or "- (no Python files changed)"
    return textwrap.dedent(f"""
        You are a technical documentation writer for a Python cryptocurrency trading app
        running on a Raspberry Pi. The app uses Flask, Google ADK agents, and Kraken via ccxt.

        Today is {run_date}. Your task is to update two documentation files based on
        recent code changes. Respond with EXACTLY this structure — no other text:

        ---CHANGELOG---
        <full updated CHANGELOG.md content>
        ---ARCHITECTURE---
        <full updated ARCHITECTURE.md content>

        ## Recent git commits (last 7 days)
        {recent_commits or "(none)"}

        ## Changed Python files
        {changed_list}

        ## Source code of changed files
        {source_context or "(no changed source to review)"}

        ## Existing CHANGELOG.md (update this)
        {existing_changelog}

        ## Existing ARCHITECTURE.md (update this)
        {existing_architecture}

        ### Instructions

        For CHANGELOG.md:
        - Add a new `## [{run_date}]` section at the top listing what changed
        - Be specific: mention function names, files, behaviour changes
        - Keep previous entries intact below the new one
        - If nothing changed, add a brief "No significant changes" entry

        For ARCHITECTURE.md:
        - Update any sections that no longer match the code (file names, class names, flow)
        - Add brief notes for any new modules or patterns introduced
        - Do NOT rewrite sections that are still accurate — preserve existing prose
        - Keep the document concise (under 600 lines)
    """).strip()


# ── Writer helpers ──────────────────────────────────────────────────────────

def parse_response(text: str) -> tuple[str, str]:
    """Split Gemini response into (changelog, architecture) content."""
    changelog = ""
    architecture = ""
    if "---CHANGELOG---" in text and "---ARCHITECTURE---" in text:
        after_cl = text.split("---CHANGELOG---", 1)[1]
        changelog_raw, after_arch = after_cl.split("---ARCHITECTURE---", 1)
        changelog = changelog_raw.strip()
        architecture = after_arch.strip()
    else:
        # Fallback: put everything in changelog, leave architecture untouched
        changelog = text.strip()
        logger.warning("doc_updater: response did not contain expected delimiters")
    return changelog, architecture


def write_if_nonempty(path: Path, content: str):
    if content:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info("doc_updater: wrote %s (%d chars)", path.name, len(content))


# ── Main entry ──────────────────────────────────────────────────────────────

def run():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [doc_updater] %(message)s")
    run_date = datetime.now().strftime("%Y-%m-%d")
    logger.info("Starting documentation update for %s", run_date)

    changed_files = get_changed_py_files(since_days=7)
    logger.info("Changed files (%d): %s", len(changed_files), changed_files)

    recent_commits = get_recent_commits(days=7)
    source_context = build_source_context(changed_files)
    existing_changelog = read_existing_doc(CHANGELOG_PATH)
    existing_architecture = read_existing_doc(ARCHITECTURE_PATH)

    prompt = build_prompt(
        changed_files=changed_files,
        source_context=source_context,
        recent_commits=recent_commits,
        existing_changelog=existing_changelog,
        existing_architecture=existing_architecture,
        run_date=run_date,
    )

    logger.info("Calling Gemini Flash (%d prompt chars)...", len(prompt))
    response_text = call_gemini(prompt)
    logger.info("Response received (%d chars)", len(response_text))

    changelog_content, architecture_content = parse_response(response_text)
    write_if_nonempty(CHANGELOG_PATH, changelog_content)
    if architecture_content:
        write_if_nonempty(ARCHITECTURE_PATH, architecture_content)
    else:
        logger.info("No architecture update in response — leaving file unchanged")

    logger.info("Documentation update complete")


if __name__ == "__main__":
    run()
