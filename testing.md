# Testing

## Panoramica

52 test totali, nessuno richiede hardware reale.

| Suite | File | Test | Copertura |
|-------|------|------|-----------|
| CAN unit | `tests/test_can_monitor.py` | 14 | Parsing frame, filtri, socket, protocollo TESTCAN |
| CAN integration | `tests/can_full_test.py` | 31 | Encoding/decoding, socketpair, error frame, can_loop, ambiente |
| Serial unit | `tests/test_serial.py` | 7 | RS-232 echo, RS-485 echo, wait_for_device |

## CAN — Unit test

```bash
uv run python -m unittest tests/test_can_monitor.py -v
```

Testa frame parsing, ID filtri, socket creation, send/recv con protocollo TESTCAN. Tutto mockato (funziona su Windows).

## CAN — Integration test

```bash
uv run python tests/can_full_test.py
```

Usa `socket.socketpair()` su Linux o mock su Windows. Testa:
- Frame encoding/decoding
- Filtri (singolo, range, misto, reversed)
- Error frame (BUS-OFF, RESTARTED, combinati)
- `send_frame`, socket creation
- Protocollo TESTCAN → ESEGUITO via `can_loop()` con mock socket
- Ambiente (AF_CAN, AF_UNIX, can-utils)

## CAN — Environment check

```bash
uv run python tests/can_env_check.py

# Oppure dentro il container:
docker run --rm --entrypoint python nexyhub-can tests/can_env_check.py
```

## CAN — Nel container

```bash
docker run --rm -it nexyhub-can bash
python3 tests/can_full_test.py
python3 -m unittest tests/test_can_monitor.py -v
```

## Serial — Unit test

```bash
uv run python -m unittest tests/test_serial.py -v
```

Testa RS-232 echo (`TEST232` → `ESEGUITO`), RS-485 echo (`TEST485` → `ESEGUITO`), `wait_for_device`. Tutto mockato con `MockSerial`.

## Serial — Nel container

```bash
docker run --rm -it nexyhub-serial bash
python3 -m unittest tests/test_serial.py -v
```

## Eseguire tutti i test

```bash
uv run python -m unittest discover tests -v
```

## Struttura mock

I test usano mock per sostituire le dipendenze hardware:

| Libreria | Mock | File test |
|----------|------|-----------|
| `socket` (AF_CAN) | `MockSocket` con `unittest.mock.patch` | `test_can_monitor.py` |
| `serial` (pyserial) | `MockSerial` | `test_serial.py` |
| `os.path.exists` | `@patch("os.path.exists")` | `test_serial.py` |

## Container — Verifica ambiente

```bash
# Verifica SocketCAN
docker run --rm -it nexyhub-can bash
python3 -c "import socket; s=socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW); print('SocketCAN OK'); s.close()"
```

Limitazione nota: Docker Desktop / WSL2 non supporta `vcan`. AF_CAN è supportato, ma non si possono creare interfacce CAN virtuali. I device seriali (`/dev/ttyLP*`) non esistono su Docker Desktop. Tutta la logica è coperta da mock.
