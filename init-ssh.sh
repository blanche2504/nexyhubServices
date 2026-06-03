#!/bin/sh

if [ "${SSH_ENABLED}" != "true" ]; then
    log "SSH disabilitato (SSH_ENABLED=${SSH_ENABLED})"
    return 0 2>/dev/null || exit 0
fi

if [ -z "${SSH_ROOT_PASSWORD}" ]; then
    log "WARN: SSH_ROOT_PASSWORD non impostata — SSH non verrà avviato"
    log "WARN: Usa: docker run -e SSH_ROOT_PASSWORD=..."
    return 0 2>/dev/null || exit 0
fi

log "SSH abilitato sulla porta ${SSH_PORT:-22}"

if echo "root:${SSH_ROOT_PASSWORD}" | chpasswd 2>/dev/null; then
    log "Password root impostata"
else
    log "WARN: chpasswd fallito, SSH potrebbe non funzionare"
fi

if [ -n "${SSH_PORT}" ] && [ "${SSH_PORT}" != "22" ]; then
    sed -i "s/^Port .*/Port ${SSH_PORT}/" /etc/ssh/sshd_config
    log "Porta SSH impostata a ${SSH_PORT}"
fi

rm -f /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub 2>/dev/null
ssh-keygen -A 2>/dev/null
log "Host keys generate"

/usr/sbin/sshd -D -e &
SSHD_PID=$!

sleep 0.5
if kill -0 "$SSHD_PID" 2>/dev/null; then
    log "SSH server avviato (PID: ${SSHD_PID})"
else
    log "WARN: sshd non è partito, continuo senza SSH"
fi
