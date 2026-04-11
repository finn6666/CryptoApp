#!/usr/bin/env bash
# Installs the pre-commit hook into the local git repo
# Run once after cloning: bash deploy/install-hooks.sh

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

cp "$REPO_ROOT/deploy/pre-commit" "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit"

echo "OK: pre-commit hook installed at $HOOKS_DIR/pre-commit"
