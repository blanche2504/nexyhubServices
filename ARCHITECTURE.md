# architecture

it runs in docker containers on openwrt, with each service owning one or more hardware peripherals (can, serial, ble) and communicating through a shared memory volume

## services

```
src/
  nexyhub_hello/  - demo
  nexyhub_can/    - can bus monitor over socketcan (can0)
  nexyhub_serial/ - rs-232 (ttyLP6) / rs-485 (ttyLP2) echo + modbus rtu
  nexyhub_ble/    - BLE scanner with bleak (hci0)
  nexyhub_ipc/    - shared memory + HTTP consumer for inter-container data
```

### nexyhub_can

- uses python-can with socketcan interface
- parses CAN IDs and ID ranges for hardware filters
- runs a monitor loop: reads frames from the bus and responds to TESTCAN with ACK
- configurable via env vars (CAN_INTERFACE, CAN_FILTERS, CAN_BITRATE)
- entrypoint: `init-can.sh` brings up can0 then starts the python process

### nexyhub_serial

- uses pyserial for UART communication
- three sub-protocols:
    - serial_echo: listens for TEST232 on ttyLP6, replies with ACK
    - rs485_echo: same on ttyLP2 but toggles DE gpio line before/after write
    - modbus_rtu: minimal modbus RTU client over rs-485
- configurable via SERIAL_PORT env var
- entrypoint: waits for device to appear before starting

### nexyhub_ble

- uses bleak to scan nearby BLE devices every N seconds
- writes device list as JSON to shared memory (ble_devices.json)
- configurable via BLE_ADAPTER, POLL_SEC env vars
- needs /run/dbus mounted for BlueZ access

### nexyhub_ipc

- two components:
    - producer: writes data to shared memory via atomic JSON writes
    - consumer: HTTP server that serves shared memory keys via REST API
- shared memory dir is a docker volume mounted at /mnt/shared
- atomic writes use a temp + rename pattern to prevent partial reads

## peripheral mapping

| service | peripheral | handle      | access method      |
| ------- | ---------- | ----------- | ------------------ |
| can     | can bus    | can0        | socketcan (AF_CAN) |
| serial  | rs-232     | /dev/ttyLP6 | pyserial           |
| serial  | rs-485     | /dev/ttyLP2 | pyserial + gpiod   |
| ble     | BLE 5.3    | hci0        | bleak over dbus    |

## data flow

```
peripheral → service → shared memory (json) → HTTP consumer → REST API → UI / external
```

each service reads from its peripheral and writes structured data to the shared volume
the consumer container exposes this data over HTTP for the dashboard or external clients

## container model

every container:

- runs as non-privileged (no --privileged)
- uses bridge networking (no --network host outside test)
- mounts only its assigned peripherals
- includes SSH for debug access (port 22, mapped to slot port)
- entrypoint starts sshd then the app process

## constraints (from platform rules)

- each peripheral owned by exactly one container (no sharing)
- all containers boot in parallel (no startup order)
- auto-restart on crash (restart: always)
- no host namespace access
- no kernel module loading from containers
- images are signed before deployment
