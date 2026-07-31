FROM python:3.11-slim

LABEL maintainer="developer"
LABEL description="NexyHub Aggregator (slot 4) — IPC Consumer + UI Dashboard"
LABEL version="1.0"

RUN touch /etc/ssh/ssh_host_rsa_key /etc/ssh/ssh_host_ecdsa_key /etc/ssh/ssh_host_ed25519_key 2>/dev/null; \
    apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/run/sshd /docker-entrypoint.d \
    && rm -f /etc/ssh/ssh_host_*

COPY src/nexyhub-aggregator/sshd_config /etc/ssh/sshd_config
COPY src/nexyhub-aggregator/init-ssh.sh /docker-entrypoint.d/00-ssh.sh
COPY src/nexyhub-aggregator/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh /docker-entrypoint.d/00-ssh.sh

ENV SSH_ENABLED=true
ENV SSH_PORT=22
EXPOSE 22

RUN pip install --no-cache-dir flask pyyaml

WORKDIR /app
COPY src/nexyhub-aggregator/nexyhub_ipc/ /app/nexyhub_ipc/
COPY src/nexyhub-aggregator/nexyhub_ui/ /app/nexyhub_ui/
COPY src/shared/nexyhub_config/ /app/nexyhub_config/
COPY src/shared/nexyhub_db/ /app/nexyhub_db/
COPY src/shared/nexyhub_alarms/ /app/nexyhub_alarms/
COPY src/shared/nexyhub_logs/ /app/nexyhub_logs/
COPY src/shared/nexyhub_utils/ /app/nexyhub_utils/

ENV FLASK_PORT=5000
ENV SSH_ROOT_PASSWORD=
ENV NEXYHUB_DB_PATH=/mnt/shared/nexyhub.db

EXPOSE 5000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "-m", "nexyhub_ui.app"]
