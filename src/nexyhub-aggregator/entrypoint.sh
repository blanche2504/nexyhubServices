#!/bin/sh

log() {
    echo "[$(date +%H:%M:%S)] [ENTRYPOINT] $1"
}

log "=== Container started ==="
log "PID: $$"

INIT_DIR="/docker-entrypoint.d"

if [ -d "${INIT_DIR}" ]; then
    for f in "${INIT_DIR}"/*.sh; do
        [ -f "$f" ] || continue
        log "Running init script: $(basename "$f")"
        . "$f"
    done
else
    log "No ${INIT_DIR} directory, skipping init scripts"
fi

if [ $# -gt 0 ]; then
    log "Starting command: $*"
    exec "$@"
else
    log "ERROR: no CMD specified in Dockerfile or docker run command"
    exit 1
fi
