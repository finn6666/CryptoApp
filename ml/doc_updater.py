"""
Minimal changelog updater — writes git log for the last 7 days to docs/CHANGELOG.md.
No external API calls. Called by deploy/security-check.sh on its weekly run.

Run manually: uv run python -m ml.doc_updater
"""

import subprocess
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).parent.parent
CHANGELOG_PATH = APP_DIR / "docs" / "CHANGELOG.md"


def run():
    run_date = datetime.now().strftime("%Y-%m-%d")

    log = subprocess.run(
        ["git", "log", "--since=7 days ago", "--oneline", "--no-merges"],
        cwd=APP_DIR, capture_output=True, text=True, timeout=10
    ).stdout.strip()

    entry = f"## [{run_date}]\n\n"
    entry += (f"```\n{log}\n```\n" if log else "_No commits in the last 7 days._\n")

    existing = CHANGELOG_PATH.read_text() if CHANGELOG_PATH.exists() else "# Changelog\n\n"
    # Insert new entry after the first heading line
    lines = existing.splitlines(keepends=True)
    insert_at = next((i + 1 for i, l in enumerate(lines) if l.startswith("# ")), 0)
    lines.insert(insert_at, "\n" + entry)
    CHANGELOG_PATH.write_text("".join(lines))
    print(f"[doc_updater] wrote {CHANGELOG_PATH.name} ({len(log.splitlines())} commits)")


if __name__ == "__main__":
    run()
