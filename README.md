# NexyHub Air — Training Project

Training container per NexyHub Air (NXP i.MX93 · OpenWRT 24.10 · Docker).

## Repository

```
src/
├── nexyhub_can/             # Epic 2 — CAN Bus Monitor
│   ├── can_types.py         Parsing frame ISO 11898, error flags
│   ├── filters.py           Filtri ID (singolo, range, misto)
│   ├── socketcan.py         SocketCAN raw API (bind, send, recv)
│   └── monitor.py           Main loop: wait → recv → respond (TESTCAN→ESEGUITO)
└── nexyhub_serial/          # Epic 3 — Serial Communication
    ├── serial_echo.py       RS-232 echo: TEST232 → ESEGUITO
    ├── rs485_echo.py        RS-485 echo con GPIO DE: TEST485 → ESEGUITO
    └── modbus_rtu.py        Modbus RTU read holding registers (polling)

tests/
├── test_can_monitor.py     14 unit test CAN (funzionano su Windows)
├── can_full_test.py        31 integration test CAN (WSL2 + Windows)
├── can_env_check.py        Verifica ambiente CAN nel container
├── can_integration.py      Test end-to-end CAN (richiede vcan)
└── test_serial.py          7 unit test seriale (mock pyserial)

Dockerfile.can              Immagine CAN (Epic 2)
Dockerfile.serial           Immagine seriale (Epic 3) con pyserial
entrypoint.sh               Init runner (esegue drop-in in /docker-entrypoint.d/)
init-ssh.sh                 Drop-in SSH (password runtime)
init-can.sh                 Drop-in CAN (ip link set can0 up)
build-can.sh                Build → docker save → .tar CAN
build-serial.sh             Build → docker save → .tar seriale
```

## Epic 2 — CAN Bus Monitor

### Build

```powershell
docker build -f Dockerfile.can -t nexyhub-can .
```

Per arm64 (deploy su NexyHub):
```powershell
$env:PLATFORM="linux/arm64"; .\build-can.sh
```

### Run

```powershell
docker run --rm nexyhub-can
```

Output: attende `can0` (su NexyHub fornita dalla piattaforma).
```
[INFO] === nexyhub-can monitor avviato ===
[INFO] Interfaccia: can0
[INFO] Attendo can0...
[WAIT] Attendo can0... (10s)
```

Per test, vedere [testing.md](testing.md).

### Variabili d'ambiente

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `CAN_INTERFACE` | `can0` | Nome interfaccia CAN |
| `CAN_BITRATE` | `500000` | Bitrate |
| `CAN_RETRY_SEC` | `3` | Attesa tra tentativi |
| `CAN_FILTER_IDS` | `""` | Filtri ID (es. `0x100-0x1FF,0x300`) |

---

## Epic 3 — Serial Communication

### RS-232 Echo (`/dev/ttyLP6`)

Risponde `ESEGUITO` a `TEST232`.

### RS-485 Echo (`/dev/ttyLP2` + `/dev/gpiochip1`)

Risponde `ESEGUITO` a `TEST485` con controllo GPIO DE.

### Modbus RTU (RS-485)

Polling holding registers su slave Modbus.

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

Per test, vedere [testing.md](testing.md).

### Variabili d'ambiente

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `SERIAL_PORT` | `/dev/ttyLP6` | Porta seriale |
| `BAUDRATE` | `9600` | Baud rate |
| `PARITY` | `N` | Parità (N/E/O) |
| `STOPBITS` | `1` | Stop bit |
| `SERIAL_TIMEOUT` | `1.0` | Timeout lettura |
| `GPIO_CHIP` | `/dev/gpiochip1` | Chip GPIO (RS-485) |
| `GPIO_DE_LINE` | `2` | Linea DE (RS-485) |
| `MODBUS_PORT` | `/dev/ttyLP2` | Porta Modbus |
| `MODBUS_SLAVE_ID` | `1` | Slave ID |
| `MODBUS_REGISTER_ADDR` | `0` | Indirizzo registro |
| `MODBUS_REGISTER_COUNT` | `1` | Numero registri |
| `MODBUS_POLL_SEC` | `10` | Intervallo polling |

---

## Tutti gli Episodi

### Entry point

| Comando | Modulo | Descrizione |
|---------|--------|-------------|
| `nexyhub-hello` | `nexyhub_hello:main` | Hello World (Epic 1) |
| `nexyhub-can` | `nexyhub_can.monitor:main` | CAN monitor (Epic 2) |
| `nexyhub-serial` | `nexyhub_serial.serial_echo:main` | RS-232 echo (Epic 3) |
| `nexyhub-rs485` | `nexyhub_serial.rs485_echo:main` | RS-485 echo (Epic 3) |
| `nexyhub-modbus` | `nexyhub_serial.modbus_rtu:main` | Modbus RTU (Epic 3) |

### Sviluppo locale

```bash
uv sync
uv run nexyhub-can       # CAN
uv run nexyhub-serial    # RS-232
uv run nexyhub-rs485     # RS-485
uv run nexyhub-modbus    # Modbus
uv run ruff check src/   # Lint
```

### SSH

Sviluppo (password a runtime):
```powershell
docker run --rm -e SSH_ROOT_PASSWORD=secret nexyhub-can
docker run --rm -e SSH_ROOT_PASSWORD=secret nexyhub-serial
```

Produzione (chiave pubblica — raccomandato):
```dockerfile
COPY authorized_keys /home/appuser/.ssh/authorized_keys
```
Porte SSH: 222 (Slot 1), 223 (Slot 2), 224 (Slot 3), 225 (Slot 4).

### Limitazioni

- Docker Desktop / WSL2: kernel Microsoft senza `vcan`. SocketCAN (`AF_CAN`) funziona, interfacce virtuali no. Sulla NexyHub `can0` è fornita dalla piattaforma.
- Dispositivi seriali (`/dev/ttyLP*`, `/dev/gpiochip*`) non esistono su Docker Desktop. Mock nei test copre tutta la logica.
- Build in due architetture: `linux/amd64` per test locale, `linux/arm64` per NexyHub.
