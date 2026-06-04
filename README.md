# NexyHub Services

IoT gateway app in python made during my internship at Vimec.
Made to run on a Nexyhub Air.

## Tools used

- Zed - IDE
- uv - python package manager
- docker
- opencode - AI assistant

## Project architecture

```
src/
  nexyhub_hello/    - entry point
  nexyhub_can/      - CAN bus monitor over socketcan
  nexyhub_serial/   - rs-232/rs-485 echo + modbus rtu
  nexyhub_ble/      - BLE device scanner
  nexyhub_ipc/      - shared memory + HTTP consumer
tests/              - unit + e2e tests
```

each service has its own docker image (see dockerfile, dockerfile.can, etc)

## How to run

```
uv run nexyhub-hello
uv run nexyhub-can
uv run nexyhub-serial
uv run nexyhub-rs485
uv run nexyhub-modbus
uv run nexyhub-ble
uv run nexyhub-producer
uv run nexyhub-consumer
```

## How to test

```
uv run pytest
```

see [TESTING.md](TESTING.md) for details
