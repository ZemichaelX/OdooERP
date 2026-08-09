#!/usr/bin/env bash
# Shared preconditions for the ops scripts. Source it; do not execute it.
#
# Why this exists: backup.sh produced seven 0-byte "backups" over two weeks
# because Docker Desktop was not running. The dump command failed, but the
# shell's `>` redirect had already created the destination file, and nothing
# reached the operator. Checking that the stack is actually reachable BEFORE
# touching the filesystem removes the whole class: no daemon, no file, no
# silence.

# Timestamped log lines. The original backup log had none, so diagnosing a
# fortnight of failures meant guessing against file mtimes.
log_line() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

log_error() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2
}

# require_docker_stack <compose-command> [service ...]
#
# Fails (returns 1) unless the Docker daemon answers AND every named compose
# service is running. Callers must check the return value and exit non-zero
# WITHOUT creating any output file.
require_docker_stack() {
  local compose="$1"
  shift

  if ! docker info >/dev/null 2>&1; then
    log_error "!! Docker daemon is not reachable — is Docker Desktop running?"
    return 1
  fi

  local service
  for service in "$@"; do
    # `compose ps --status running` prints the service name only when it is up.
    if ! ${compose} ps --status running --services 2>/dev/null | grep -qx "${service}"; then
      log_error "!! Compose service '${service}' is not running — start the stack first."
      return 1
    fi
  done
  return 0
}
