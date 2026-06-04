# nexyhub services

python IoT gateway for the NexyHub Air platform — acquires, processes, and exposes data from CAN bus, RS-232, RS-485, and BLE peripherals.

## architecture

each service is a self-contained project in `src/` with its own Dockerfile, entrypoint, and README:

```
src/
  nexyhub-can/         CAN bus monitor (socketcan)
  nexyhub-serial/      RS-232 / RS-485 / Modbus (pyserial)
  nexyhub-ble/         BLE scanner (bleak)
  nexyhub-aggregator/  HTTP API + Flask dashboard
  shared/              common packages (config, db, alarms)
```

shared packages provide YAML config loading, SQLite logging, and threshold alarm
evaluation — used by all services.

## slot mapping

| slot | directory       | peripheral              | port  |
|------|-----------------|-------------------------|-------|
| 1    | nexyhub-can     | can0 (socketcan)        | —     |
| 2    | nexyhub-serial  | ttyLP6, ttyLP2 (serial) | —     |
| 3    | nexyhub-ble     | hci0 (bleak + dbus)     | —     |
| 4    | nexyhub-aggregator | — (shared volume)    | 5000  |

## how to run

```bash
# build all images
bash run.sh build

# start services
bash run.sh can        # slot 1 — CAN
bash run.sh serial     # slot 2 — serial
bash run.sh consumer   # slot 4 — dashboard (port 5000)

# generate elevator data for testing
uv run python3 simulate.py &

# stop everything
bash run.sh stop
```

single commands to run locally (without docker):

```
uv run nexyhub-can
uv run nexyhub-serial
uv run nexyhub-ble
uv run nexyhub-consumer
uv run nexyhub-ui
uv run simulate.py
```

## configuration

all services read `/etc/nexyhub/config.yaml` (yaml with sensible defaults).
see [CONFIG.md](CONFIG.md) for the full schema.

## dashboard

open `http://localhost:5000` in a browser.

- services health (alive/dead per container)
- readings table (latest 50 rows)
- time-series graph with key selector
- active alarms panel

## how to test

```bash
uv run pytest
```

| test file | what it covers |
|-----------|----------------|
| tests/test_can_monitor.py | filter parsing, send/recv helpers, bus creation (mocked) |
| tests/test_serial.py | RS-232 echo, RS-485 echo + DE gpio, Modbus RTU import, wait_for_device (mocked) |
| tests/test_ble.py | device formatting, scan, write, main loop (mocked) |
| tests/test_ipc.py | shared mem atomic read/write, HTTP consumer endpoints |
| tests/serial_e2e_test.py | RS-232 + RS-485 echo over real PTY via Docker |
| tests/can_full_test.py | full CAN stack: message construction, filters, virtual bus, protocol, vcan |

### e2e prerequisites

CAN test needs vcan:
```bash
sudo modprobe vcan
sudo ip link add vcan0 type vcan
sudo ip link set vcan0 up
```

Serial test creates a PTY pair and maps it into the container with `-v` bind mount.
The protocol expects `TEST232` / `TEST485` and replies with `ACK`.

see [TESTING.md](TESTING.md) for details.
