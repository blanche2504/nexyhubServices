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

## prerequisites

CAN simulation needs vcan:
```bash
sudo modprobe vcan
sudo ip link add vcan0 type vcan
sudo ip link set vcan0 up
```

## how to run

```bash
# build all images
bash run.sh build

# start all services (slots 1-4)
CAN_NETWORK=host CAN_INTERFACE=vcan0 bash run.sh up

# generate elevator test data (auto-creates serial PTY, feeds CAN + serial)
CAN_INTERFACE=vcan0 bash run.sh simulate

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
- readings table (latest rows)
- time-series graph with key selector dropdown
- live log viewer with per-service dropdown (auto-refresh every 3s)
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

### simulate workflow

`bash run.sh simulate` does everything in one step:

1. creates a PTY pair with socat (no sudo needed)
2. restarts the serial container with host `/dev` mount so it can see the host PTY
3. runs the elevator simulator which sends CAN frames on vcan0 and serial commands
4. on exit, stops the serial container and cleans up the PTY

Serial protocol: `TEST232` → `ACK` (RS-232 echo), `TEST485` → `ACK` (RS-485 with DE gpio).

### e2e prerequisites

CAN test needs vcan:
```bash
sudo modprobe vcan
sudo ip link add vcan0 type vcan
sudo ip link set vcan0 up
```

On real hardware, `run.sh serial` maps the UART via `--device` (no PTY needed).
For local dev testing, `run.sh simulate` creates a virtual PTY and mounts host `/dev`.

see [TESTING.md](TESTING.md) for details.
