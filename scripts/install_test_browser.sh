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

# The runner's persistent local disk. On the self-hosted runner the bottleneck
# is a home internet connection, and this script used to spend 17m18s on apt
# and 26m35s on Chrome — per job — before one of those transfers died with
# `curl: (18) Transferred a partial file`. Everything below resolves from local
# disk first and only reaches the network when the cache genuinely has nothing.
# shellcheck source=scripts/ci_local_cache.sh
. "$(dirname "${BASH_SOURCE[0]}")/ci_local_cache.sh"

# ---------------------------------------------------------------------------
# 1. Runtime libraries + the websocket client Odoo's CDP driver needs.
#    python3-websocket comes from the archive rather than pip so this works on
#    an image with an externally-managed Python.
# ---------------------------------------------------------------------------
log "installing runtime libraries"
apt_from_cache \
    ca-certificates curl unzip fonts-liberation python3-websocket \
    libnss3 libnspr4 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2t64 libatspi2.0-0t64

python3 -c 'import websocket' \
    || die "python3-websocket did not install; browser_js would skip on it"

# ---------------------------------------------------------------------------
# 2. Chrome. Odoo looks for google-chrome / chromium / chromium-browser /
#    google-chrome-stable on PATH (odoo/tests/common.py:2127).
# ---------------------------------------------------------------------------
#
#    CACHE FIRST, AND NOTE WHAT IS NOT ASKED. On a cache hit this does NOT
#    resolve "the current stable build" — that resolution is itself a network
#    call, and asking what is newest only to then use the copy on disk would
#    put the slow link back in the path for no benefit. The version actually
#    used is logged every run, so the browser is never anonymous.
CACHE_ROOT="$(cache_root)"
CHROME_CACHE="${CACHE_ROOT:+${CACHE_ROOT}/chrome}"

cached_zip() {   # -> path of the highest-versioned verified zip, or nothing
    # NOT `ls ... | sort | tail`: this script runs under `set -o pipefail`, so
    # a glob that matches nothing makes ls fail, makes the pipeline fail, and
    # `set -e` then kills the script on the EMPTY-CACHE path — the one case a
    # fresh machine is guaranteed to hit.
    [ -n "${CHROME_CACHE}" ] || return 0
    local found
    found="$(ls -1 "${CHROME_CACHE}"/*/chrome-linux64.zip 2>/dev/null || true)"
    [ -n "${found}" ] || return 0
    printf '%s\n' "${found}" | sort -V | tail -1
}

if command -v google-chrome >/dev/null 2>&1 || command -v chromium >/dev/null 2>&1; then
    log "a browser is already on PATH, leaving it alone"
else
    ZIP="$(cached_zip)"
    if [ -n "${ZIP}" ]; then
        log "using cached Chrome from ${ZIP} (no network)"
    else
        if [ -n "${CHROME_CACHE}" ]; then
            log "Chrome cache is empty — downloading once (the slow first run)"
        fi
        log "resolving the current Chrome-for-Testing stable build"
        VERSIONS_URL="https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
        CHROME_JSON="$(curl -sSfL --retry 5 --retry-all-errors "$VERSIONS_URL")" \
            || die "could not reach the Chrome-for-Testing version index"
        CHROME_URL="$(printf '%s' "${CHROME_JSON}" | python3 -c '
import json, sys
data = json.load(sys.stdin)
downloads = data["channels"]["Stable"]["downloads"]["chrome"]
print(next(d["url"] for d in downloads if d["platform"] == "linux64"))
')"
        [ -n "${CHROME_URL}" ] || die "could not resolve a Chrome download URL"
        CHROME_VERSION="$(printf '%s' "${CHROME_URL}" | sed -E 's#.*/([0-9][0-9.]*)/linux64/.*#\1#')"
        [ -n "${CHROME_VERSION}" ] || die "could not read a version out of ${CHROME_URL}"

        STAGE="${CHROME_CACHE:+${CHROME_CACHE}/${CHROME_VERSION}}"
        STAGE="${STAGE:-/tmp/chrome-dl}"
        mkdir -p "${STAGE}"
        # Downloaded to .part and only renamed after `unzip -t` passes. A
        # truncated transfer that got promoted into the cache would be worse
        # than no cache at all: every later run would fail on it, fast, and
        # look like a code problem.
        resilient_download "${CHROME_URL}" "${STAGE}/chrome-linux64.zip.part"
        unzip -tqq "${STAGE}/chrome-linux64.zip.part" \
            || { rm -f "${STAGE}/chrome-linux64.zip.part"
                 die "the downloaded Chrome archive is corrupt; nothing was cached"; }
        mv -f "${STAGE}/chrome-linux64.zip.part" "${STAGE}/chrome-linux64.zip"
        ZIP="${STAGE}/chrome-linux64.zip"
        log "cached Chrome ${CHROME_VERSION} at ${ZIP}"
    fi

    unzip -q -o "${ZIP}" -d /opt
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
