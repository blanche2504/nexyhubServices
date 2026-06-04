FROM python:3.11-slim

LABEL maintainer="developer"
LABEL description="NexyHub Hello World — Epic 1"
LABEL version="0.1.0"

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && mkdir -p /docker-entrypoint.d

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/run/sshd

COPY sshd_config /etc/ssh/sshd_config
COPY init-ssh.sh /docker-entrypoint.d/00-ssh.sh
RUN chmod +x /docker-entrypoint.d/00-ssh.sh

ENV SSH_ENABLED=true
ENV SSH_PORT=22

COPY config.yaml /etc/nexyhub/config.yaml

EXPOSE 22

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY README.md pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY src/ src/
RUN uv sync --no-dev --frozen

ENV PYTHONUNBUFFERED=1
ENV SSH_ROOT_PASSWORD=""

ENTRYPOINT ["/entrypoint.sh"]
CMD ["./.venv/bin/nexyhub-hello"]
