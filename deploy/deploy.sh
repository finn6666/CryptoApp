#!/usr/bin/env bash
# Run from your Mac: bash deploy/deploy.sh [branch]
# Defaults to main. Example: bash deploy/deploy.sh dev

set -euo pipefail

BRANCH="${1:-main}"
PI="pi"   # matches your ~/.ssh/config Host entry

echo "Deploying branch '$BRANCH' to Pi..."

ssh "$PI" "
  set -e
  cd ~/CryptoApp
  git fetch origin
  git checkout '${BRANCH}'
  git pull origin '${BRANCH}'
  uv sync --quiet
  sudo systemctl restart cryptoapp
  sleep 3
  sudo systemctl is-active cryptoapp
"

echo "Done. Service is running."
