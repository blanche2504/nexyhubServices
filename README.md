# nexyhub services

python IoT gateway for the NexyHub Air platform — acquires, processes, and exposes data from CAN bus, RS-232, RS-485, and BLE peripherals.

## architecture

```
src/
  nexyhub_hello/    - entry point demo
  nexyhub_can/      - CAN bus monitor over socketcan
  nexyhub_serial/   - RS-232 / RS-485 echo + modbus RTU
  nexyhub_ble/      - BLE device scanner (bleak)
  nexyhub_ipc/      - shared memory + HTTP consumer
  nexyhub_config/   - YAML config loader with deep merge
  nexyhub_db/       - SQLite wrapper (readings + alarms)
  nexyhub_alarms/   - threshold alarm engine
  nexyhub_ui/       - Flask dashboard + REST API
```

each service has its own docker image (see Dockerfile, Dockerfile.can, etc).

all services share a sqlite db on a mounted volume at `/mnt/shared/nexyhub.db`.

## how to run

```bash
# build all images
bash run.sh build

# start services
bash run.sh can        # CAN bus monitor
bash run.sh serial     # RS-232 echo
bash run.sh consumer   # HTTP API (port 8000)
bash run.sh ui         # dashboard (port 5000)

# generate elevator data for testing
uv run python3 simulate.py &

# stop everything
bash run.sh stop
```

single commands to run locally (without docker):

```
uv run nexyhub-can
uv run nexyhub-serial
uv run nexyhub-consumer
uv run nexyhub-ble
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

```
uv run pytest
```

see [TESTING.md](TESTING.md) for details.
