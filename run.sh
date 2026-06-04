#!/bin/sh
# simulate production environment locally
# no docker-compose -- all params set via docker run flags
# matches how the luci web interface configures containers

set -e

SHARED_DIR="${HOME}/nexyhub-shared"
CONFIG_DIR="${HOME}/nexyhub-config"

mkdir -p "${SHARED_DIR}" "${CONFIG_DIR}"

# copy default config if not present
if [ ! -f "${CONFIG_DIR}/config.yaml" ]; then
    cp config.yaml "${CONFIG_DIR}/config.yaml"
    echo "created default config at ${CONFIG_DIR}/config.yaml"
fi

build_all() {
    echo "building images..."
    docker build -t nexyhub-can -f src/nexyhub-can/Dockerfile .
    docker build -t nexyhub-serial -f src/nexyhub-serial/Dockerfile .
    docker build -t nexyhub-ble -f src/nexyhub-ble/Dockerfile .
    docker build -t nexyhub-ipc -f src/nexyhub-aggregator/Dockerfile .
}

run_can() {
    echo "starting CAN monitor..."
    # use --network host to access host vcan/can interfaces
    # in production the platform handles this
    docker run -d --rm \
        --name nexyhub-can \
        --network host \
        -v "${CONFIG_DIR}/config.yaml:/etc/nexyhub/config.yaml:ro" \
        -v "${SHARED_DIR}:/mnt/shared" \
        -e SSH_ROOT_PASSWORD=nexyhub \
        -e CAN_INTERFACE="${CAN_INTERFACE:-vcan0}" \
        nexyhub-can
}

run_serial() {
    local port="${SERIAL_PORT:-/dev/ttyLP6}"
    echo "starting serial monitor on ${port}..."
    docker run -d --rm \
        --name nexyhub-serial \
        --network bridge \
        -v "${CONFIG_DIR}/config.yaml:/etc/nexyhub/config.yaml:ro" \
        -v "${SHARED_DIR}:/mnt/shared" \
        -v "${port}:${port}" \
        -e SSH_ROOT_PASSWORD=nexyhub \
        -e SERIAL_PORT="${port}" \
        nexyhub-serial
}

run_simulate() {
    echo "starting elevator data simulator..."
    # create serial PTY
    rm -f /tmp/ttyLP6 /tmp/ttyLP6-peer 2>/dev/null
    socat -d -d pty,link=/tmp/ttyLP6,raw,echo=0 pty,link=/tmp/ttyLP6-peer,raw,echo=0 &
    SOCAT_PID=$!
    sleep 1
    echo "serial PTY at /tmp/ttyLP6 (peer: /tmp/ttyLP6-peer)"

    # symlink for serial container
    sudo ln -sf /tmp/ttyLP6 /dev/ttyLP6 2>/dev/null; true

    # start simulator
    uv run python3 simulate.py
    kill $SOCAT_PID 2>/dev/null; true
}

run_consumer() {
    echo "starting IPC aggregator (API + UI)..."
    docker run -d --rm \
        --name nexyhub-consumer \
        --network bridge \
        -p 5000:5000 \
        -v "${CONFIG_DIR}/config.yaml:/etc/nexyhub/config.yaml:ro" \
        -v "${SHARED_DIR}:/mnt/shared" \
        -e SSH_ROOT_PASSWORD=nexyhub \
        nexyhub-ipc
}

stop_all() {
    echo "stopping all containers..."
    docker stop nexyhub-can nexyhub-serial nexyhub-ble nexyhub-consumer 2>/dev/null || true
}

logs() {
    docker logs -f "$1"
}

case "${1:-help}" in
    build) build_all ;;
    can) run_can ;;
    serial) run_serial ;;
    ble) run_ble ;;
    consumer) run_consumer ;;
    simulate) run_simulate ;;
    stop) stop_all ;;
    logs) shift; logs "$@" ;;
    *)
        echo "usage: $0 <command>"
        echo ""
        echo "commands:"
        echo "  build        build all docker images"
        echo "  can          start CAN monitor (slot 1)"
        echo "  serial       start RS-232/485 + Modbus (slot 2)"
        echo "  ble          start BLE scanner (slot 3)"
        echo "  consumer     start API + dashboard (slot 4, port 5000)"
        echo "  simulate     run elevator data simulator"
        echo "  stop         stop all containers"
        echo "  logs <name>  tail logs for a container"
        ;;
esac
