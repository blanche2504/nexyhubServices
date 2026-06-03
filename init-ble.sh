#!/bin/sh

if [ -z "${BLE_ADAPTER}" ]; then
    log "WARN: BLE_ADAPTER non impostata, skip BLE init"
    return 0 2>/dev/null || exit 0
fi

ADAPTER_PATH="/sys/class/bluetooth/${BLE_ADAPTER}"

if [ -d "${ADAPTER_PATH}" ]; then
    log "BLE: ${BLE_ADAPTER} trovato"
    hciconfig "${BLE_ADAPTER}" up 2>/dev/null && log "BLE: ${BLE_ADAPTER} up" || log "WARN: hciconfig fallito"
else
    log "WARN: ${ADAPTER_PATH} non trovato — sarà atteso dall'app"
fi
