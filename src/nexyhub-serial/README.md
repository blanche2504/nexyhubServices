# nexyhub-serial v1.0 — RS-232 + RS-485 + Modbus (slot 2)

Container Docker per comunicazione seriale su NexyHub Air:

- **RS-232** su `/dev/ttyLP6` — echo `TEST232` con risposta `ACK`
- **RS-485** su `/dev/ttyLP2` — echo `TEST485` con ACK e controllo GPIO DE
- **Modbus RTU** su `/dev/ttyLP2` — polling registri holding

## Build

```bash
# from repo root
docker build -t nexyhub-serial -f src/nexyhub-serial/Dockerfile .

# cross-compile per ARM64
PLATFORM=linux/arm64 sh src/nexyhub-serial/build.sh
```

## Run (locale)

```bash
bash run.sh serial
```

## LuCI — configurazione slot

| parametro | valore |
|-----------|--------|
| Immagine | `nexyhub-serial.tar` |
| Rete | bridge |
| Porte | `223:22` (SSH) |
| Volumi | volume condiviso → `/mnt/shared`, config → `/etc/nexyhub/config.yaml:ro` |
| Dispositivi | `/dev/ttyLP6`, `/dev/ttyLP2` |
| Riavvio | always |

### Variabili d'ambiente

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `SSH_ROOT_PASSWORD` | — | Password root SSH (obbligatoria) |
| `SERIAL_PORT` | `/dev/ttyLP6` | Porta seriale primaria |
| `NEXYHUB_DB_PATH` | `/mnt/shared/nexyhub.db` | Path database |

### Sottocomandi (override CMD)

| Comando | Descrizione |
|---------|-------------|
| `python3 -m nexyhub_serial.serial_echo` | RS-232 echo (default) |
| `python3 -m nexyhub_serial.rs485_echo` | RS-485 echo |
| `python3 -m nexyhub_serial.modbus_rtu` | Modbus RTU |

## Deploy

```bash
docker build -t nexyhub-serial -f src/nexyhub-serial/Dockerfile .
docker save -o nexyhub-serial.tar nexyhub-serial
# carica .tar via LuCI → Container panel
```
