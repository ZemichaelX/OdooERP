#!/usr/bin/env bash
# Shared preconditions and Windows path handling for the ops scripts.
# Source it; do not execute it.
#
# Why this exists: backup.sh produced seven 0-byte "backups" over two weeks
# because Docker Desktop was not running. The dump failed, but the shell's `>`
# redirect had already created the destination file, and nothing reached the
# operator. Checking that the stack is actually reachable BEFORE touching the
# filesystem removes the whole class: no daemon, no file, no silence.

# Timestamped log lines. The original backup log had none, so diagnosing a
# fortnight of failures meant guessing against file mtimes.
log_line() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

log_error() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2
}

# compose_cmd <path-to-compose-file>
#
# Echo the compose invocation with a HOST path docker can actually open.
#
# On Git Bash, ${REPO_ROOT} is a POSIX path (/c/Users/...). docker.exe is a
# native Windows binary and resolves that against the current drive as
# C:\c\Users\... — "The system cannot find the path specified". MSYS normally
# converts such arguments on the way out, but these scripts used to disable
# conversion wholesale (MSYS2_ARG_CONV_EXCL='*') to protect CONTAINER paths
# like /var/lib/odoo/filestore, and the blanket took the -f host path with it.
# The exclusion is now scoped to the container paths that need it (see the
# callers), and the host path is converted explicitly here so it does not
# depend on MSYS heuristics, which differ between Git-for-Windows releases.
# cygpath -m yields C:/Users/... (forward slashes), which docker accepts and
# which survives word-splitting unlike a backslash form. No-op off Windows.
compose_cmd() {
  local compose_file="$1"
  if command -v cygpath >/dev/null 2>&1; then
    compose_file="$(cygpath -m "${compose_file}")"
  fi
  printf 'docker compose -f %s' "${compose_file}"
}

# require_docker_stack <compose-command> [service ...]
#
# Fails (returns 1) unless the Docker daemon answers AND every named compose
# service is running. Callers must check the return value and exit non-zero
# WITHOUT creating any backup artefact.
#
# NOTE: stderr from the probes is REPORTED, never discarded. An earlier version
# sent it to /dev/null and a broken -f path surfaced only as "service 'db' is
# not running" — the true error ("open C:\c\Users\...: The system cannot find
# the path specified") was swallowed. Suppressing the stream that carries the
# reason is the same silent-failure disease these scripts exist to remove.
require_docker_stack() {
  local compose="$1"
  shift

  local probe
  # `2>&1 >/dev/null` captures STDERR only: `docker info` prints pages of client
  # information to stdout even when the daemon is unreachable, and burying the
  # one useful line under it is its own small act of hiding the reason.
  # --format keeps it to a single server field, so success is quiet.
  if ! probe="$(docker info --format '{{.ServerVersion}}' 2>&1 >/dev/null)"; then
    log_error "!! Docker daemon is not reachable — is Docker Desktop running?"
    printf '%s\n' "${probe}" | head -3 | sed 's/^/     /' >&2
    return 1
  fi

  local running
  # `compose ps --status running --services` prints the service names that are
  # up. A non-zero exit here means compose itself failed (bad -f path, bad
  # file, no project) — a different fault from "the service is down", and the
  # operator needs to see which.
  if ! running="$(${compose} ps --status running --services 2>&1)"; then
    log_error "!! 'docker compose ps' FAILED — compose could not read the project:"
    printf '%s\n' "${running}" | sed 's/^/     /' >&2
    log_error "!! (command was: ${compose} ps --status running --services)"
    return 1
  fi

  local service
  for service in "$@"; do
    if ! printf '%s\n' "${running}" | grep -qx "${service}"; then
      log_error "!! Compose service '${service}' is not running — start the stack first."
      log_error "!! Services currently running: ${running:-<none>}"
      return 1
    fi
  done
  return 0
}
