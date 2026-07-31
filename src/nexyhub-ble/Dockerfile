FROM python:3.11-slim

LABEL maintainer="developer"
LABEL description="NexyHub BLE Scanner — developer container"
LABEL version="1.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    libdbus-1-3 \
    bluez \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/run/sshd /docker-entrypoint.d

COPY src/nexyhub-ble/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
COPY src/nexyhub-ble/sshd_config /etc/ssh/sshd_config
COPY src/nexyhub-ble/init-ssh.sh /docker-entrypoint.d/00-ssh.sh
RUN chmod +x /docker-entrypoint.d/00-ssh.sh

ENV SSH_ENABLED=true
ENV SSH_PORT=22
EXPOSE 22

RUN pip install --no-cache-dir bleak pyyaml

WORKDIR /app
COPY src/nexyhub-ble/nexyhub_ble/ /app/nexyhub_ble/
COPY src/shared/nexyhub_config/ /app/nexyhub_config/
COPY src/shared/nexyhub_db/ /app/nexyhub_db/
COPY src/shared/nexyhub_logs/ /app/nexyhub_logs/
COPY src/shared/nexyhub_utils/ /app/nexyhub_utils/

ENV SSH_ROOT_PASSWORD=
ENV BLE_ADAPTER=hci0
ENV BLE_SCAN_SEC=10
ENV BLE_POLL_SEC=10
ENV BLE_SHARED_DIR=/mnt/shared
ENV NEXYHUB_DB_PATH=/mnt/shared/nexyhub.db

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "-m", "nexyhub_ble.ble_scanner"]
