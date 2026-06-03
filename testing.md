# Testing

## Overview

63 total tests, none require real hardware.

| Suite | File | Tests | Coverage |
|-------|------|-------|----------|
| CAN unit | `tests/test_can_monitor.py` | 12 | Frame parsing, filters, socket, TESTCAN protocol |
| CAN integration | `tests/can_full_test.py` | 24 | Encoding/decoding, virtual bus, error frame, can_loop, environment |
| Serial unit | `tests/test_serial.py` | 9 | RS-232 echo, RS-485 echo, wait_for_device |
| BLE unit | `tests/test_ble.py` | 7 | Device formatting, adapter wait, JSON write |
| IPC unit | `tests/test_ipc.py` | 11 | Atomic read/write, subdirs, key listing, HTTP server |

## CAN — Unit test

```bash
uv run python -m unittest tests/test_can_monitor.py -v
```

Tests frame parsing, ID filters, bus creation, send/recv with TESTCAN protocol. All mocked (works on Windows).

## CAN — Integration test

```bash
uv run python tests/can_full_test.py
```

Uses `can.Bus(interface='virtual')` for loopback. Tests:
- `can.Message` construction and attributes
- Filters (single, range, mixed, reversed)
- `send_message` / `recv_message` helpers
- Virtual bus send/receive
- TESTCAN protocol via `can_loop()` with mock bus
- Environment (AF_CAN, AF_UNIX, can-utils, python-can version)

## CAN — Inside container

```bash
docker run --rm -it nexyhub-can bash
python3 tests/can_full_test.py
python3 -m unittest tests/test_can_monitor.py -v
```

## Serial — Unit test

```bash
uv run python -m unittest tests/test_serial.py -v
```

Tests RS-232 echo (`TEST232` → `ESEGUITO`), RS-485 echo (`TEST485` → `ESEGUITO`), `wait_for_device`. All mocked with `MockSerial`.

## Serial — Inside container

```bash
docker run --rm -it nexyhub-serial bash
python3 -m unittest tests/test_serial.py -v
```

## BLE — Unit test

```bash
uv run python -m unittest tests/test_ble.py -v
```

Tests `format_device`, `wait_for_adapter`, `write_devices`. All mocked (works on Windows).

## BLE — Inside container

```bash
docker run --rm -it nexyhub-ble bash
python3 -m unittest tests/test_ble.py -v
```

## IPC — Unit test

```bash
uv run python -m unittest tests/test_ipc.py -v
```

Tests `SharedMem` atomic write/read, key listing, corrupted file handling and `ConsumerHTTP` routes
(`/`, `/status`, `/<key>`). No shared volume needed (uses temp dirs).

## IPC — Inside container

```bash
docker run --rm -it nexyhub-ipc bash
python3 -m unittest tests/test_ipc.py -v
```

## Run all tests

```bash
uv run python -m unittest discover tests -v
```

## Mock structure

Tests use mocks to replace hardware dependencies:

| Library | Mock | Test file |
|---------|------|-----------|
| `socket` (AF_CAN) | `unittest.mock.patch` + `MagicMock` | `test_can_monitor.py` |
| `serial` (pyserial) | `MockSerial` | `test_serial.py` |
| `os.path.exists` | `@patch("os.path.exists")` | `test_serial.py` |
| `bleak.BleakScanner` | `AsyncMock` | `test_ble.py` |
| `dbus_next.aio.MessageBus` | `AsyncMock` | `test_ble.py` |
| N/A (file I/O) | `tempfile.TemporaryDirectory` | `test_ipc.py` |
| N/A (HTTP server) | `http.client` | `test_ipc.py` |

## Container — Environment check

```bash
# Verify SocketCAN
docker run --rm -it nexyhub-can bash
python3 -c "import socket; s=socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW); print('SocketCAN OK'); s.close()"
```

```bash
# Verify BLE (requires BlueZ D-Bus)
docker run --rm -it nexyhub-ble bash
python3 -c "from bleak import BleakScanner; print('bleak OK')"
```

Note: Docker Desktop / WSL2 does not support `vcan`. AF_CAN is supported but virtual CAN interfaces cannot be created. Serial devices (`/dev/ttyLP*`) and BLE adapter (`/dev/hci0`) do not exist on Docker Desktop. All logic is covered by mocks.
