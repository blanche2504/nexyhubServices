#!/bin/sh

log() {
    echo "[$(date +%H:%M:%S)] [ENTRYPOINT] $1"
}

log "=== Container avviato ==="
log "PID: $$"

INIT_DIR="/docker-entrypoint.d"

if [ -d "${INIT_DIR}" ]; then
    for f in "${INIT_DIR}"/*.sh; do
        [ -f "$f" ] || continue
        log "Esecuzione init script: $(basename "$f")"
        . "$f"
    done
else
    log "Nessuna directory ${INIT_DIR}, skip init scripts"
fi

if [ $# -gt 0 ]; then
    log "Avvio comando: $*"
    exec "$@"
else
    log "ERRORE: nessun CMD specificato nel Dockerfile o nella riga docker run"
    exit 1
fi
