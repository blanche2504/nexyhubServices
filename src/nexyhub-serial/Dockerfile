FROM python:3.11-slim

LABEL maintainer="developer"
LABEL description="NexyHub Serial — RS-232 echo + RS-485 echo + Modbus RTU"
LABEL version="1.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/run/sshd /docker-entrypoint.d

COPY src/nexyhub-serial/sshd_config /etc/ssh/sshd_config
COPY src/nexyhub-serial/init-ssh.sh /docker-entrypoint.d/00-ssh.sh
COPY src/nexyhub-serial/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh /docker-entrypoint.d/00-ssh.sh

ENV SSH_ENABLED=true
ENV SSH_PORT=22
EXPOSE 22

RUN pip install --no-cache-dir pyserial pymodbus pyyaml

WORKDIR /app
COPY src/nexyhub-serial/nexyhub_serial/ /app/nexyhub_serial/
COPY src/shared/nexyhub_config/ /app/nexyhub_config/
COPY src/shared/nexyhub_db/ /app/nexyhub_db/
COPY src/shared/nexyhub_alarms/ /app/nexyhub_alarms/
COPY src/shared/nexyhub_logs/ /app/nexyhub_logs/
COPY src/shared/nexyhub_utils/ /app/nexyhub_utils/

ENV SSH_ROOT_PASSWORD=
ENV SERIAL_PORT=/dev/ttyLP6
ENV NEXYHUB_DB_PATH=/mnt/shared/nexyhub.db

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "-m", "nexyhub_serial.serial_echo"]
