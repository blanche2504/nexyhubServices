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

export_all() {
    echo "exporting images to .tar..."
    docker save -o nexyhub-can.tar nexyhub-can
    docker save -o nexyhub-serial.tar nexyhub-serial
    docker save -o nexyhub-ble.tar nexyhub-ble
    docker save -o nexyhub-ipc.tar nexyhub-ipc
    echo ""
    echo "=== exported tars ==="
    ls -lh nexyhub-*.tar
    echo ""
    echo "upload each .tar via LuCI web interface → Container panel"
}

run_can() {
    local net="${CAN_NETWORK:-bridge}"
    echo "starting CAN monitor (network: ${net})..."
    echo "  production: use bridge (platform maps can0)"
    echo "  local dev:  CAN_NETWORK=host to reach vcan0"
    docker run -d --rm \
        --name nexyhub-can \
        --network "${net}" \
        -v "${CONFIG_DIR}/config.yaml:/etc/nexyhub/config.yaml:ro" \
        -v "${SHARED_DIR}:/mnt/shared" \
        -e SSH_ROOT_PASSWORD=nexyhub \
        -e CAN_INTERFACE="${CAN_INTERFACE:-can0}" \
        nexyhub-can
}

run_serial() {
    local port="${SERIAL_PORT:-/dev/ttyLP6}"
    echo "starting serial monitor on ${port}..."
    docker run -d --rm \
        --name nexyhub-serial \
        --network bridge \
        --device "${port}:${port}" \
        -v "${CONFIG_DIR}/config.yaml:/etc/nexyhub/config.yaml:ro" \
        -v "${SHARED_DIR}:/mnt/shared" \
        -e SSH_ROOT_PASSWORD=nexyhub \
        -e SERIAL_PORT="${port}" \
        nexyhub-serial
}

run_ble() {
    echo "starting BLE scanner..."
    docker run -d --rm \
        --name nexyhub-ble \
        --network bridge \
        -v "${CONFIG_DIR}/config.yaml:/etc/nexyhub/config.yaml:ro" \
        -v "${SHARED_DIR}:/mnt/shared" \
        -v /run/dbus:/run/dbus \
        -e SSH_ROOT_PASSWORD=nexyhub \
        nexyhub-ble
}

run_simulate() {
    echo "starting elevator data simulator..."
    # create serial PTY pair (nohup to survive shell timeout)
    rm -f /tmp/nexyhub-pty /tmp/nexyhub-pty-peer 2>/dev/null
    nohup socat -d -d pty,link=/tmp/nexyhub-pty,raw,echo=0 \
                   pty,link=/tmp/nexyhub-pty-peer,raw,echo=0 \
      > /tmp/nexyhub-socat.log 2>&1 &
    SOCAT_PID=$!
    sleep 2

    PTY=$(readlink -f /tmp/nexyhub-pty)
    PEER=$(readlink -f /tmp/nexyhub-pty-peer)
    echo "serial PTY at ${PTY} (peer: ${PEER})"

    # restart serial container with host /dev mount so it can see the host PTY
    docker stop nexyhub-serial 2>/dev/null || true
    docker rm nexyhub-serial 2>/dev/null || true
    docker run -d --rm \
        --name nexyhub-serial \
        --network bridge \
        -v /dev:/dev \
        -v "${CONFIG_DIR}/config.yaml:/etc/nexyhub/config.yaml:ro" \
        -v "${SHARED_DIR}:/mnt/shared" \
        -e SSH_ROOT_PASSWORD=nexyhub \
        -e SERIAL_PORT="${PTY}" \
        nexyhub-serial
    echo "serial container restarted on ${PTY}"
    sleep 2

    # run the elevator simulator
    CAN_INTERFACE="${CAN_INTERFACE:-vcan0}" SERIAL_DEV="${PEER}" uv run python3 simulate.py

    echo "simulator done, cleaning up..."
    docker stop nexyhub-serial 2>/dev/null || true
    kill $SOCAT_PID 2>/dev/null || true
    rm -f /tmp/nexyhub-pty /tmp/nexyhub-pty-peer 2>/dev/null
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

run_up() {
    run_can
    run_serial
    run_ble
    run_consumer
    echo ""
    echo "all services started. dashboard at http://localhost:5000"
    echo "run 'CAN_INTERFACE=vcan0 bash run.sh simulate' to generate test data"
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
    export) export_all ;;
    up) run_up ;;
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
        echo "  export       export images to .tar for LuCI upload"
        echo "  up           start all services (slots 1-4)"
        echo "  can          start CAN monitor (slot 1)"
        echo "  serial       start RS-232/485 + Modbus (slot 2)"
        echo "  ble          start BLE scanner (slot 3)"
        echo "  consumer     start API + dashboard (slot 4, port 5000)"
        echo "  simulate     run elevator data simulator"
        echo "  stop         stop all containers"
        echo "  logs <name>  tail logs for a container"
        echo ""
        echo "env:"
        echo "  CAN_NETWORK=host    (default: bridge, use host for local vcan)"
        echo "  CAN_INTERFACE=vcan0 (default: can0)"
        echo "  SERIAL_PORT=...     (default: /dev/ttyLP6)"
        echo "  SERIAL_DEV=...      (simulate serial device, default: auto PTY peer)"
        ;;
esac
