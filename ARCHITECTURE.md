# architecture

runs in docker containers on openwrt, with each service owning one or more hardware peripherals (can, serial, ble) and communicating through a shared sqlite database and shared memory volume.

## services

```
src/
  nexyhub_hello/    - demo entry point
  nexyhub_can/      - CAN bus monitor over socketcan (can0)
  nexyhub_serial/   - RS-232 (ttyLP6) / RS-485 (ttyLP2) echo + modbus RTU
  nexyhub_ble/      - BLE scanner with bleak (hci0)
  nexyhub_ipc/      - shared memory + HTTP consumer
  nexyhub_config/   - YAML config loader (deep merge, env override)
  nexyhub_db/       - SQLite wrapper (WAL mode, readings + alarms tables)
  nexyhub_alarms/   - threshold alarm engine (min/max, hysteresis, dedup)
  nexyhub_ui/       - Flask dashboard (Plotly graphs, REST API, services health)
```

### nexyhub_can

- uses python-can with socketcan interface
- monitors CAN bus, responds with ACK to TESTCAN frames
- stores readings with numeric value (first data byte) + text_value
- configurable via env vars (CAN_INTERFACE, CAN_FILTERS, CAN_BITRATE)

### nexyhub_serial

- uses pyserial for UART communication
- three sub-protocols:
    - serial_echo: listens for TEST232 on ttyLP6, replies with ACK
    - rs485_echo: same on ttyLP2 but toggles DE gpio before/after write
    - modbus_rtu: minimal modbus RTU client over RS-485

### nexyhub_ble

- uses bleak to scan nearby BLE devices every N seconds
- writes device list as JSON to shared memory (ble_devices.json)

### nexyhub_ipc

- producer: writes data to shared memory via atomic JSON writes
- consumer: HTTP server serving shared memory keys + SQLite readings via REST API

### nexyhub_config

- loads YAML from `/etc/nexyhub/config.yaml`
- deep-merges with defaults
- env vars override config values

### nexyhub_db

- sqlite with WAL mode
- two tables: `readings` (ts, source, key, value, text_value, unit) and `alarms` (ts, name, severity, message, cleared)
- automatic cleanup of readings older than retention_days

### nexyhub_alarms

- evaluates threshold rules (min/max with hysteresis)
- deduplicates active alarms
- clear-on-rearm when value returns within range

### nexyhub_ui

- flask app serving:
  - `/` — Plotly dashboard (services, readings graph, alarms)
  - `/api/services` — container health by DB timestamps + file freshness
  - `/api/readings` — latest 100 readings
  - `/api/alarms` — active + history
  - `/api/status` — uptime, file count, total readings

## peripheral mapping

| service | peripheral | handle      | access method      |
| ------- | ---------- | ----------- | ------------------ |
| can     | CAN bus    | can0        | socketcan (AF_CAN) |
| serial  | RS-232     | /dev/ttyLP6 | pyserial           |
| serial  | RS-485     | /dev/ttyLP2 | pyserial + gpiod   |
| ble     | BLE 5.3    | hci0        | bleak over dbus    |

## data flow

```
peripheral → service → SQLite DB (shared volume) + shared memory JSON
                            │
                    HTTP consumer (port 8000)
                            │
                    Flask UI dashboard (port 5000)
```

each service writes structured readings to the shared sqlite database.
the consumer container also exposes shared memory data over HTTP.
the dashboard reads from both db and shared memory for live views.

## container model

every container:

- runs as non-privileged (no --privileged)
- uses bridge networking (no --network host outside test)
- mounts only its assigned peripherals
- includes SSH for debug (port 22, mapped to slot port)
- entrypoint starts sshd then the app process

## constraints (from platform rules)

- each peripheral owned by exactly one container (no sharing)
- all containers boot in parallel (no startup order)
- auto-restart on crash (restart: always)
- no host namespace access
- no kernel module loading from containers
- images are signed before deployment
