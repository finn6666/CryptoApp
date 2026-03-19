#!/usr/bin/env bash
# CryptoApp security check script
# Run manually: bash deploy/security-check.sh
# Or via systemd timer: see deploy/cryptoapp-security.timer
#
# Setup on Pi:
#   sudo cp deploy/cryptoapp-security.service /etc/systemd/system/
#   sudo cp deploy/cryptoapp-security.timer   /etc/systemd/system/
#   sudo systemctl daemon-reload
#   sudo systemctl enable --now cryptoapp-security.timer

set -euo pipefail

APP_DIR="${APP_DIR:-/home/pi/CryptoApp}"
LOG_FILE="$APP_DIR/data/security_audit.log"
FAIL=0

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

log "========================================"
log "CryptoApp security check starting"
log "========================================"

# ── 1. CVE scan via pip-audit ────────────────────────────────────────────────
log "→ Scanning dependencies for known CVEs..."
if ! command -v pip-audit &>/dev/null; then
    log "  Installing pip-audit..."
    uv pip install pip-audit --quiet
fi

if uv run pip-audit --format=columns 2>&1 | tee -a "$LOG_FILE"; then
    log "  ✅ No known CVEs found"
else
    log "  ❌ CVEs detected — review output above"
    FAIL=1
fi

# ── 2. Outdated packages ─────────────────────────────────────────────────────
log "→ Checking for outdated packages..."
uv pip list --outdated 2>&1 | tee -a "$LOG_FILE" || true

# ── 3. .env file permissions ─────────────────────────────────────────────────
log "→ Checking .env permissions..."
ENV_FILE="$APP_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
    PERMS=$(stat -c "%a" "$ENV_FILE" 2>/dev/null || stat -f "%OLp" "$ENV_FILE")
    if [[ "$PERMS" == "600" ]]; then
        log "  ✅ .env permissions OK (600)"
    else
        log "  ❌ .env permissions are $PERMS — should be 600"
        chmod 600 "$ENV_FILE"
        log "  🔧 Fixed: chmod 600 applied"
    fi
else
    log "  ⚠️  .env not found at $ENV_FILE"
fi

# ── 4. Open ports audit ──────────────────────────────────────────────────────
log "→ Checking open listening ports..."
ss -tlnp 2>&1 | tee -a "$LOG_FILE" || true

# ── 5. OS security updates available ────────────────────────────────────────
log "→ Checking for OS security updates..."
if command -v apt-get &>/dev/null; then
    apt-get -s upgrade 2>&1 | grep -i "security" | tee -a "$LOG_FILE" || log "  ✅ No pending security updates"
fi

# ── 6. Secret patterns in git history (last 10 commits) ─────────────────────
log "→ Scanning recent git commits for accidental secrets..."
cd "$APP_DIR"
SECRET_PATTERN='(API_KEY|SECRET|PASSWORD|TOKEN|PRIVATE_KEY)\s*=\s*["\047][^"\047]{8,}'
if git log --oneline -10 -p 2>/dev/null | grep -iE "$SECRET_PATTERN" | grep -v "^---" | grep -v "\.env" | tee -a "$LOG_FILE"; then
    log "  ❌ Possible secrets found in recent commits — review above"
    FAIL=1
else
    log "  ✅ No obvious secrets in recent commits"
fi

# ── 7. nginx security headers ────────────────────────────────────────────────
log "→ Verifying nginx security headers..."
NGINX_CONF="/etc/nginx/sites-available/cryptoapp"
REQUIRED_HEADERS=("X-Content-Type-Options" "X-Frame-Options" "Strict-Transport-Security" "Content-Security-Policy")
if [[ -f "$NGINX_CONF" ]]; then
    for header in "${REQUIRED_HEADERS[@]}"; do
        if grep -q "$header" "$NGINX_CONF"; then
            log "  ✅ $header present"
        else
            log "  ❌ $header MISSING from nginx config"
            FAIL=1
        fi
    done
else
    log "  ⚠️  nginx config not found at $NGINX_CONF (skip if running locally)"
fi

# ── 8. Update changelog ──────────────────────────────────────────────────────
log "→ Updating docs/CHANGELOG.md from git log..."
cd "$APP_DIR"
uv run python -m ml.doc_updater 2>&1 | tee -a "$LOG_FILE" || log "  ⚠️  changelog update failed (non-fatal)"

# ── Summary ──────────────────────────────────────────────────────────────────
log "========================================"
if [[ "$FAIL" -eq 0 ]]; then
    log "✅ All security checks passed"
else
    log "❌ One or more checks FAILED — review log: $LOG_FILE"
fi
log "========================================"

exit $FAIL
