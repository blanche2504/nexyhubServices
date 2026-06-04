# nexyhub-can v1.0 — CAN bus monitor (slot 1)

Container Docker per monitoraggio CAN bus su NexyHub Air, basato su python-can con socketcan.
Risponde con ACK a frame contenenti `TESTCAN`. Registra letture su DB SQLite condiviso.

## Build

```bash
# from repo root
docker build -t nexyhub-can -f src/nexyhub-can/Dockerfile .

# cross-compile for ARM64
PLATFORM=linux/arm64 sh src/nexyhub-can/build.sh
```

## Run (locale)

```bash
# con vcan (sviluppo locale)
CAN_NETWORK=host CAN_INTERFACE=vcan0 bash run.sh can

# produzione (bridge, piattaforma mappa can0)
bash run.sh can
```

## LuCI — configurazione slot

| parametro | valore |
|-----------|--------|
| Immagine | `nexyhub-can.tar` |
| Rete | bridge |
| Porte | `222:22` (SSH) |
| Volumi | volume condiviso → `/mnt/shared`, config → `/etc/nexyhub/config.yaml:ro` |
| Dispositivi | can0 (mappato dalla piattaforma) |
| Riavvio | always |

### Variabili d'ambiente

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `SSH_ROOT_PASSWORD` | — | Password root SSH (obbligatoria) |
| `CAN_INTERFACE` | `can0` | Interfaccia CAN |
| `CAN_RETRY_SEC` | `3` | Secondi tra tentativi |
| `CAN_FILTER_IDS` | — | Filtri ID (es. `0x001,0x100-0x1FF`) |
| `NEXYHUB_DB_PATH` | `/mnt/shared/nexyhub.db` | Path database |

## Deploy

```bash
# 1. build
docker build -t nexyhub-can -f src/nexyhub-can/Dockerfile .

# 2. esporta .tar
docker save -o nexyhub-can.tar nexyhub-can

# 3. carica via LuCI → Container panel
# 4. configura env/volumi/porte come da tabella sopra
```
