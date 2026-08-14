#!/usr/bin/env bash
# Install a headless Chrome and websocket-client into an Odoo test container,
# so `HttpCase.browser_js` runs instead of skipping.
#
# WHY THIS EXISTS
# ---------------
# The app rail is an OWL component. The only assertion that proves it renders
# is one made in a real browser (addons/sapian_theme/tests/test_app_rail.py).
# `HttpCase.browser_js` raises unittest.SkipTest when it cannot find Chrome
# (odoo/tests/common.py:2153) and when the `websocket` module is missing
# (:1259) — and a skipped test is a success signal produced by doing nothing.
# The odoo:19.0 image ships neither.
#
# The image is Ubuntu 24.04, which has NO chromium deb at all: `chromium` is
# not in the archive and `chromium-browser` is a 2:1snap1 stub that installs a
# snap, which does not work in a container. So Chrome comes from Google's
# Chrome-for-Testing bucket.
#
# Run as root inside the Odoo container. Idempotent. Fails loudly — a browser
# that did not install must not look like a browser that did.
set -euo pipefail

log() { printf '[install_test_browser] %s\n' "$*"; }
die() { printf '[install_test_browser] ERROR: %s\n' "$*" >&2; exit 1; }

export DEBIAN_FRONTEND=noninteractive

# ---------------------------------------------------------------------------
# 1. Runtime libraries + the websocket client Odoo's CDP driver needs.
#    python3-websocket comes from the archive rather than pip so this works on
#    an image with an externally-managed Python.
# ---------------------------------------------------------------------------
log "installing runtime libraries"
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
    ca-certificates curl unzip fonts-liberation python3-websocket \
    libnss3 libnspr4 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2t64 libatspi2.0-0t64 >/dev/null

python3 -c 'import websocket' \
    || die "python3-websocket did not install; browser_js would skip on it"

# ---------------------------------------------------------------------------
# 2. Chrome. Odoo looks for google-chrome / chromium / chromium-browser /
#    google-chrome-stable on PATH (odoo/tests/common.py:2127).
# ---------------------------------------------------------------------------
if command -v google-chrome >/dev/null 2>&1 || command -v chromium >/dev/null 2>&1; then
    log "a browser is already on PATH, leaving it alone"
else
    log "resolving the current Chrome-for-Testing stable build"
    VERSIONS_URL="https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
    CHROME_URL="$(curl -sSfL "$VERSIONS_URL" | python3 -c '
import json, sys
data = json.load(sys.stdin)
downloads = data["channels"]["Stable"]["downloads"]["chrome"]
print(next(d["url"] for d in downloads if d["platform"] == "linux64"))
')"
    [ -n "${CHROME_URL}" ] || die "could not resolve a Chrome download URL"
    log "downloading ${CHROME_URL}"
    curl -sSfL -o /tmp/chrome-linux64.zip "${CHROME_URL}"
    unzip -q -o /tmp/chrome-linux64.zip -d /opt
    rm -f /tmp/chrome-linux64.zip
    [ -x /opt/chrome-linux64/chrome ] || die "the archive did not contain /opt/chrome-linux64/chrome"
    ln -sf /opt/chrome-linux64/chrome /usr/bin/chromium
    chmod -R a+rX /opt/chrome-linux64
fi

# ---------------------------------------------------------------------------
# 3. Prove it. `--version` exercises the shared-library load, which is the part
#    that actually fails on a slim image, and it is the only evidence that the
#    two steps above did something.
# ---------------------------------------------------------------------------
VERSION="$(chromium --version 2>&1 || google-chrome --version 2>&1 || true)"
case "${VERSION}" in
    *Chrom*) log "browser ready: ${VERSION}" ;;
    *) die "no working browser after install (got: ${VERSION:-nothing})" ;;
esac
