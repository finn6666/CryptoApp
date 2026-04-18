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
log "-> Scanning dependencies for known CVEs..."
if uv run pip-audit --format=columns 2>&1 | tee -a "$LOG_FILE"; then
    log "   PASS: No known CVEs found"
else
    log "   FAIL: CVEs detected — review output above"
    FAIL=1
fi

# ── 2. Outdated packages ─────────────────────────────────────────────────────
log "-> Checking for outdated packages..."
uv run pip list --outdated 2>&1 | tee -a "$LOG_FILE" || true

# ── 3. .env file permissions ─────────────────────────────────────────────────
log "-> Checking .env permissions..."
ENV_FILE="$APP_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
    PERMS=$(stat -c "%a" "$ENV_FILE" 2>/dev/null || stat -f "%OLp" "$ENV_FILE")
    if [[ "$PERMS" == "600" ]]; then
        log "   PASS: .env permissions OK (600)"
    else
        log "   WARN: .env permissions are $PERMS — should be 600, fixing..."
        chmod 600 "$ENV_FILE"
        log "   FIXED: chmod 600 applied"
    fi
else
    log "   WARN: .env not found at $ENV_FILE"
fi

# ── 4. Open ports audit ──────────────────────────────────────────────────────
log "-> Checking open listening ports..."
ss -tlnp 2>&1 | tee -a "$LOG_FILE" || true

# ── 5. SSH password auth disabled ────────────────────────────────────────────
log "-> Checking SSH password authentication..."
if grep -qE "^PasswordAuthentication\s+no" /etc/ssh/sshd_config 2>/dev/null; then
    log "   PASS: SSH password auth disabled"
else
    log "   WARN: SSH password auth may be enabled — run: sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && sudo systemctl restart ssh"
fi

# ── 6. Firewall SSH rule check ────────────────────────────────────────────────
log "-> Checking firewall SSH rules..."
if sudo ufw status 2>/dev/null | grep -q "22.*ALLOW.*192\.168\|22.*ALLOW.*100\.64"; then
    log "   PASS: SSH restricted to local/Tailscale ranges"
elif sudo ufw status 2>/dev/null | grep -qE "^22\s+ALLOW\s+Anywhere"; then
    log "   FAIL: SSH port 22 is open to the internet — restrict with ufw rules in docs/DEPLOYMENT.md"
    FAIL=1
else
    log "   INFO: Could not determine SSH firewall rule state"
fi

# ── 7. OS security updates available ─────────────────────────────────────────
log "-> Checking for OS security updates..."
if command -v apt-get &>/dev/null; then
    UPDATES=$(apt-get -s upgrade 2>&1 | grep -i "security" || true)
    if [[ -z "$UPDATES" ]]; then
        log "   PASS: No pending security updates"
    else
        echo "$UPDATES" | tee -a "$LOG_FILE"
    fi
fi

# ── 8. Secret patterns in git history (last 10 commits) ──────────────────────
log "-> Scanning recent git commits for accidental secrets..."
cd "$APP_DIR"
SECRET_PATTERN='(API_KEY|SECRET|PASSWORD|TOKEN|PRIVATE_KEY)\s*=\s*["\047][^"\047]{8,}'
SECRETS=$(git log --oneline -10 -p 2>/dev/null | grep -iE "$SECRET_PATTERN" | grep -v "^---" | grep -v "\.env" || true)
if [[ -n "$SECRETS" ]]; then
    echo "$SECRETS" | tee -a "$LOG_FILE"
    log "   FAIL: Possible secrets found in recent commits — review above"
    FAIL=1
else
    log "   PASS: No obvious secrets in recent commits"
fi

# ── 9. nginx security headers ─────────────────────────────────────────────────
log "-> Verifying nginx security headers..."
NGINX_CONF="/etc/nginx/sites-available/cryptoapp"
REQUIRED_HEADERS=("X-Content-Type-Options" "X-Frame-Options" "Strict-Transport-Security" "Content-Security-Policy")
if [[ -f "$NGINX_CONF" ]]; then
    for header in "${REQUIRED_HEADERS[@]}"; do
        if grep -q "$header" "$NGINX_CONF"; then
            log "   PASS: $header present"
        else
            log "   FAIL: $header MISSING from nginx config"
            FAIL=1
        fi
    done
else
    log "   INFO: nginx config not found at $NGINX_CONF (skip if running locally)"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
log "========================================"
if [[ "$FAIL" -eq 0 ]]; then
    log "PASS: All security checks passed"
else
    log "FAIL: One or more checks failed — review log: $LOG_FILE"
fi
log "========================================"

exit $FAIL
