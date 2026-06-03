#!/bin/sh

if [ -z "${CAN_INTERFACE}" ]; then
    log "WARN: CAN_INTERFACE non impostata, skip setup CAN"
    return 0 2>/dev/null || exit 0
fi

CAN_BITRATE="${CAN_BITRATE:-500000}"
CAN_RESTART_MS="${CAN_RESTART_MS:-100}"

if echo "${CAN_INTERFACE}" | grep -q "^vcan"; then
    log "CAN: setup virtuale ${CAN_INTERFACE}"
    if ip link add dev "${CAN_INTERFACE}" type vcan 2>/dev/null; then
        ip link set "${CAN_INTERFACE}" up
        log "CAN: ${CAN_INTERFACE} virtuale up"
    else
        log "WARN: impossibile creare ${CAN_INTERFACE} virtuale — sarà attesa dall'app"
    fi
else
    log "CAN: setup ${CAN_INTERFACE} a ${CAN_BITRATE} bit/s (restart-ms=${CAN_RESTART_MS})"
    if ip link set "${CAN_INTERFACE}" up type can bitrate "${CAN_BITRATE}" restart-ms "${CAN_RESTART_MS}" 2>/dev/null; then
        log "CAN: ${CAN_INTERFACE} up (bitrate=${CAN_BITRATE})"
    else
        log "WARN: impossibile portare su ${CAN_INTERFACE} — sarà attesa dall'app"
    fi
fi
