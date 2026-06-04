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
    docker build -t nexyhub-hello -f Dockerfile .
    docker build -t nexyhub-can -f Dockerfile.can .
    docker build -t nexyhub-serial -f Dockerfile.serial .
    docker build -t nexyhub-ble -f Dockerfile.ble .
    docker build -t nexyhub-ipc -f Dockerfile.ipc .
}

run_can() {
    echo "starting CAN monitor..."
    docker run -d --rm \
        --name nexyhub-can \
        --network bridge \
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

run_rs485() {
    echo "starting RS-485 monitor..."
    docker run -d --rm \
        --name nexyhub-rs485 \
        --network bridge \
        -v "${CONFIG_DIR}/config.yaml:/etc/nexyhub/config.yaml:ro" \
        -v "${SHARED_DIR}:/mnt/shared" \
        -v /dev/ttyLP2:/dev/ttyLP2 \
        -e SSH_ROOT_PASSWORD=nexyhub \
        -e SERIAL_PORT=/dev/ttyLP2 \
        nexyhub-serial ./.venv/bin/nexyhub-rs485
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

run_producer() {
    echo "starting IPC producer..."
    docker run -d --rm \
        --name nexyhub-producer \
        --network bridge \
        -v "${CONFIG_DIR}/config.yaml:/etc/nexyhub/config.yaml:ro" \
        -v "${SHARED_DIR}:/mnt/shared" \
        -e SSH_ROOT_PASSWORD=nexyhub \
        nexyhub-ipc
}

run_consumer() {
    echo "starting IPC consumer..."
    docker run -d --rm \
        --name nexyhub-consumer \
        --network bridge \
        -p 8000:8000 \
        -v "${CONFIG_DIR}/config.yaml:/etc/nexyhub/config.yaml:ro" \
        -v "${SHARED_DIR}:/mnt/shared" \
        -e SSH_ROOT_PASSWORD=nexyhub \
        nexyhub-ipc ./.venv/bin/nexyhub-consumer
}

stop_all() {
    echo "stopping all containers..."
    docker stop nexyhub-can nexyhub-serial nexyhub-rs485 nexyhub-ble nexyhub-producer nexyhub-consumer 2>/dev/null || true
}

logs() {
    docker logs -f "$1"
}

case "${1:-help}" in
    build) build_all ;;
    can) run_can ;;
    serial) run_serial ;;
    rs485) run_rs485 ;;
    ble) run_ble ;;
    producer) run_producer ;;
    consumer) run_consumer ;;
    stop) stop_all ;;
    logs) shift; logs "$@" ;;
    *)
        echo "usage: $0 <command>"
        echo ""
        echo "commands:"
        echo "  build        build all docker images"
        echo "  can          start CAN monitor"
        echo "  serial       start RS-232 monitor"
        echo "  rs485        start RS-485 monitor"
        echo "  ble          start BLE scanner"
        echo "  producer     start IPC producer"
        echo "  consumer     start IPC consumer"
        echo "  stop         stop all containers"
        echo "  logs <name>  tail logs for a container"
        ;;
esac
