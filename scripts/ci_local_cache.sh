#!/usr/bin/env bash
# Locate the runner's PERSISTENT local cache, and (optionally) use it for apt.
#
# WHY THIS EXISTS
# ---------------
# CI moved to a self-hosted runner because GitHub-hosted minutes ran out. On
# that machine the bottleneck is not CPU, disk or Docker — it is a home
# internet connection. Measured on one App rail job:
#
#     installing runtime libraries (apt)   17m18s
#     downloading chrome-linux64.zip       26m35s, then
#     curl: (18) Transferred a partial file
#
# So the rule this file exists to serve is: ANYTHING THAT CROSSES THE NETWORK
# ONCE PER JOB IS NOT A FIX. The asset is the runner's local disk, which
# persists between jobs and between runs.
#
# Deliberately NOT actions/cache: its storage lives on GitHub, so a cache HIT
# still pulls the payload down the same slow link.
#
# WHERE THE CACHE LIVES
# ---------------------
# Beside the workspace, not inside it. The runner bind-mounts its whole `_work`
# root into every job container, so one directory is reachable from container
# jobs and host jobs alike WITHOUT touching any `container:` block:
#
#     host      /home/<user>/actions-runner/_work/_sapian_ci_cache
#     container /__w/_sapian_ci_cache
#
# Derived from $GITHUB_WORKSPACE rather than hard-coded, so it follows the
# runner wherever it is installed. Being OUTSIDE the workspace also means
# `actions/checkout`'s `git clean -ffdx` never deletes it.
#
# FRESH MACHINE MUST STILL WORK. Every function here degrades to "do the slow
# thing once" when the cache is absent or unwritable, and says so in the log.
# Nothing here may make CI depend on state only one laptop has.
set -euo pipefail

cache_log() { printf '[ci_local_cache] %s\n' "$*"; }

# ---------------------------------------------------------------------------
# cache_root -> prints a writable cache directory, or nothing if there is none.
#
# Prints the reason either way. "No output" must never be the same thing as
# "nothing needed doing".
# ---------------------------------------------------------------------------
cache_root() {
    local root="${SAPIAN_CI_CACHE:-}"
    if [ -z "${root}" ]; then
        if [ -z "${GITHUB_WORKSPACE:-}" ]; then
            cache_log "GITHUB_WORKSPACE is unset; no persistent cache (everything will be downloaded)." >&2
            return 0
        fi
        root="$(dirname "$(dirname "${GITHUB_WORKSPACE}")")/_sapian_ci_cache"
    fi
    if ! mkdir -p "${root}" 2>/dev/null || ! touch "${root}/.writable" 2>/dev/null; then
        cache_log "cache root ${root} is not writable; falling back to downloading (this run will be slow)." >&2
        return 0
    fi
    rm -f "${root}/.writable"
    printf '%s' "${root}"
}

# ---------------------------------------------------------------------------
# apt_from_cache <pkg>...  — install packages using cached lists and .debs.
#
# Two things are cached, because both are downloads:
#   apt-lists/     /var/lib/apt/lists — the package index. The odoo image ships
#                  it emptied, so without this every job runs `apt-get update`.
#   apt-archives/  the .deb files themselves, via Dir::Cache::archives.
#
# On a stale index the install can fail (the mirror has moved on). That is
# recoverable, not fatal: refresh the index and try once more, then re-save.
# ---------------------------------------------------------------------------
apt_from_cache() {
    local root; root="$(cache_root)"
    local lists archives
    export DEBIAN_FRONTEND=noninteractive

    if [ -z "${root}" ]; then
        cache_log "no cache: apt-get update + install over the network"
        apt-get update -qq
        apt-get install -y -qq --no-install-recommends "$@" >/dev/null
        return 0
    fi

    lists="${root}/apt-lists"
    archives="${root}/apt-archives"
    mkdir -p "${lists}" "${archives}/partial"

    if [ -n "$(ls -A "${lists}" 2>/dev/null || true)" ]; then
        cache_log "restoring apt index from ${lists} (no network)"
        cp -a "${lists}/." /var/lib/apt/lists/ 2>/dev/null || true
    else
        cache_log "apt index cache is empty — populating it once (this is the slow first run)"
        apt-get update -qq
        cp -a /var/lib/apt/lists/. "${lists}/" 2>/dev/null || true
    fi

    if apt-get install -y -qq --no-install-recommends \
            -o Dir::Cache::archives="${archives}" "$@" >/dev/null 2>&1; then
        cache_log "installed from cache: $*"
    else
        cache_log "install failed on the cached index — refreshing it and retrying once"
        apt-get update -qq
        apt-get install -y -qq --no-install-recommends \
            -o Dir::Cache::archives="${archives}" "$@" >/dev/null
        rm -rf "${lists:?}/"* 2>/dev/null || true
        cp -a /var/lib/apt/lists/. "${lists}/" 2>/dev/null || true
        cache_log "installed after refresh: $*"
    fi
}

# ---------------------------------------------------------------------------
# resilient_download <url> <destination>
#
# The link this runs on drops mid-transfer; we have watched it happen. So:
#   --continue-at -    resume a partial file rather than starting over
#   --retry            retry the transfer itself
#   --retry-all-errors retry on connection resets, not only on HTTP 5xx
# A partial file is left in place ON PURPOSE between attempts, so the next
# attempt resumes it. The CALLER must verify the finished file before trusting
# it — a truncated download that got cached would be worse than no cache.
# ---------------------------------------------------------------------------
resilient_download() {
    local url="$1" dest="$2"
    cache_log "downloading ${url}"
    curl -fL \
        --retry 5 --retry-delay 5 --retry-all-errors \
        --connect-timeout 30 --speed-time 120 --speed-limit 1024 \
        --continue-at - \
        -o "${dest}" "${url}"
}
