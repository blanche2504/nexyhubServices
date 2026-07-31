# nexyhub-serial RS-232 + RS-485 + Modbus (slot 2)

- **RS-232** on `/dev/ttyLP6` — echo protocol: expects `TEST232`, replies `ACK`
- **RS-485** on `/dev/ttyLP2` — echo protocol: expects `TEST485`, replies `ACK` with GPIO DE (Driver Enable) line toggling
- **Modbus RTU** on `/dev/ttyLP2` — polls holding registers from a Modbus slave

## Build

```bash
# from repo root
bash run.sh build

# cross-compile for ARM64
PLATFORM=linux/arm64 sh src/nexyhub-serial/build.sh
```

## Run locally

```bash
# production — needs real UART
bash run.sh serial

# dev with virtual serial PTY (auto-configures serial container)
CAN_INTERFACE=vcan0 bash run.sh simulate

# standalone local run (no Docker)
uv run nexyhub-serial
uv run nexyhub-rs485
uv run nexyhub-modbus
```

## LuCI slot configuration

| parameter | value |
|-----------|-------|
| Image | `nexyhub-serial.tar` |
| Network | bridge |
| Ports | `223:22` (SSH) |
| Volumes | shared volume → `/mnt/shared`, config → `/etc/nexyhub/config.yaml:ro` |
| Devices | `/dev/ttyLP6`, `/dev/ttyLP2` |
| Restart | always |

### Env vars

| Variable | Default | Description |
|----------|---------|-------------|
| `SSH_ROOT_PASSWORD` | — | Root SSH password (required) |
| `SERIAL_PORT` | `/dev/ttyLP6` | RS-232 port |
| `BAUDRATE` | `9600` | RS-232 baud rate |
| `PARITY` | `N` | RS-232 parity (`N`, `E`, `O`) |
| `STOPBITS` | `1` | RS-232 stop bits (`1`, `2`) |
| `SERIAL_TIMEOUT` | `1.0` | RS-232 read timeout (seconds) |
| `NEXYHUB_DB_PATH` | `/mnt/shared/nexyhub.db` | Database path |

Modbus uses separate env vars: `MODBUS_PORT`, `MODBUS_BAUDRATE`, `MODBUS_TIMEOUT` (defaults match RS-485 on `/dev/ttyLP2`, 9600, 1.0s).

### Subcommands

| Command | Description |
|---------|-------------|
| `python3 -m nexyhub_serial.serial_echo` | RS-232 echo (container default) |
| `python3 -m nexyhub_serial.rs485_echo` | RS-485 echo |
| `python3 -m nexyhub_serial.modbus_rtu` | Modbus RTU |

RS-485 uses a GPIO line for Driver Enable (DE) control — the container asserts DE before transmitting and releases it after the last stop bit. This is required by RS-485 half-duplex hardware.

## Deploy

```bash
bash run.sh build
bash run.sh export
# produces nexyhub-serial.tar — upload via LuCI → Container panel
```
