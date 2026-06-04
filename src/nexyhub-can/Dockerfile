FROM python:3.11-slim

LABEL maintainer="developer"
LABEL description="Container CAN bus Monitor per NexyHub Air"
LABEL version="1.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/run/sshd /docker-entrypoint.d

COPY src/nexyhub-can/sshd_config /etc/ssh/sshd_config
COPY src/nexyhub-can/init-ssh.sh /docker-entrypoint.d/00-ssh.sh
COPY src/nexyhub-can/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh /docker-entrypoint.d/00-ssh.sh

ENV SSH_ENABLED=true
ENV SSH_PORT=22
EXPOSE 22

RUN pip3 install --no-cache-dir python-can pyyaml

WORKDIR /app
COPY src/nexyhub-can/nexyhub_can/ /app/nexyhub_can/
COPY src/shared/nexyhub_config/ /app/nexyhub_config/
COPY src/shared/nexyhub_db/ /app/nexyhub_db/
COPY src/shared/nexyhub_alarms/ /app/nexyhub_alarms/

ENV CAN_INTERFACE=can0
ENV CAN_RETRY_SEC=3
ENV CAN_FILTER_IDS=
ENV SSH_ROOT_PASSWORD=
ENV NEXYHUB_DB_PATH=/mnt/shared/nexyhub.db

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "-m", "nexyhub_can.monitor"]
