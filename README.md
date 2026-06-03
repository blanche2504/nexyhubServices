# NexyHub Air — Training Project

Training containers for NexyHub Air (NXP i.MX93 · OpenWRT 24.10 · Docker).

## Epic 2 — CAN Bus Monitor

### Build

```powershell
docker build -f Dockerfile.can -t nexyhub-can .
```

For arm64 (deploy on NexyHub):
```powershell
$env:PLATFORM="linux/arm64"; .\build-can.sh
```

### Run

```powershell
docker run --rm nexyhub-can
```

Output: waits for `can0` (provided by platform on NexyHub).
```
[INFO] === nexyhub-can monitor started ===
[INFO] Interface: can0
[INFO] Waiting for can0...
[WAIT] Waiting for can0... (10s)
```

For tests, see [testing.md](testing.md).

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAN_INTERFACE` | `can0` | CAN interface name |
| `CAN_BITRATE` | `500000` | Bitrate |
| `CAN_RETRY_SEC` | `3` | Retry interval |
| `CAN_FILTER_IDS` | `""` | ID filters (e.g. `0x100-0x1FF,0x300`) |

---

## Epic 3 — Serial Communication

### RS-232 Echo (`/dev/ttyLP6`)

Responds `ESEGUITO` to `TEST232`.

### RS-485 Echo (`/dev/ttyLP2` + `/dev/gpiochip1`)

Responds `ESEGUITO` to `TEST485` with GPIO DE control.

### Modbus RTU (RS-485)

Polling holding registers on Modbus slave.

### Build

```powershell
docker build -f Dockerfile.serial -t nexyhub-serial .
```

### Run

```powershell
# RS-232 echo (default)
docker run --rm nexyhub-serial

# RS-485 echo
docker run --rm -e SERIAL_PORT=/dev/ttyLP2 nexyhub-serial .venv/bin/nexyhub-rs485

# Modbus RTU
docker run --rm -e SERIAL_PORT=/dev/ttyLP2 nexyhub-serial .venv/bin/nexyhub-modbus
```

For tests, see [testing.md](testing.md).

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERIAL_PORT` | `/dev/ttyLP6` | Serial port |
| `BAUDRATE` | `9600` | Baud rate |
| `PARITY` | `N` | Parity (N/E/O) |
| `STOPBITS` | `1` | Stop bits |
| `SERIAL_TIMEOUT` | `1.0` | Read timeout |
| `GPIO_CHIP` | `/dev/gpiochip1` | GPIO chip (RS-485) |
| `GPIO_DE_LINE` | `2` | DE line (RS-485) |
| `MODBUS_PORT` | `/dev/ttyLP2` | Modbus port |
| `MODBUS_SLAVE_ID` | `1` | Slave ID |
| `MODBUS_REGISTER_ADDR` | `0` | Register address |
| `MODBUS_REGISTER_COUNT` | `1` | Register count |
| `MODBUS_POLL_SEC` | `10` | Poll interval |

---

## All Epics

### Entry points

| Command | Module | Description |
|---------|--------|-------------|
| `nexyhub-hello` | `nexyhub_hello:main` | Hello World (Epic 1) |
| `nexyhub-can` | `nexyhub_can.monitor:main` | CAN monitor (Epic 2) |
| `nexyhub-serial` | `nexyhub_serial.serial_echo:main` | RS-232 echo (Epic 3) |
| `nexyhub-rs485` | `nexyhub_serial.rs485_echo:main` | RS-485 echo (Epic 3) |
| `nexyhub-modbus` | `nexyhub_serial.modbus_rtu:main` | Modbus RTU (Epic 3) |

### Local development

```bash
uv sync
uv run nexyhub-can       # CAN
uv run nexyhub-serial    # RS-232
uv run nexyhub-rs485     # RS-485
uv run nexyhub-modbus    # Modbus RTU
```

### SSH

Development (runtime password):
```powershell
docker run --rm -e SSH_ROOT_PASSWORD=secret nexyhub-can
docker run --rm -e SSH_ROOT_PASSWORD=secret nexyhub-serial
```

Production (public key — recommended):
```dockerfile
COPY authorized_keys /home/appuser/.ssh/authorized_keys
```
SSH ports: 222 (Slot 1), 223 (Slot 2), 224 (Slot 3), 225 (Slot 4).

### Limitations

- Docker Desktop / WSL2: Microsoft kernel without `vcan`. SocketCAN (`AF_CAN`) works, virtual interfaces do not. On NexyHub, `can0` is provided by the platform.
- Serial devices (`/dev/ttyLP*`, `/dev/gpiochip*`) do not exist on Docker Desktop. Mocks in tests cover all logic.
- Two-architecture builds: `linux/amd64` for local testing, `linux/arm64` for NexyHub.
