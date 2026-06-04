# nexyhub-ble v1.0 — BLE scanner (slot 3)

Container BLE scanner per NexyHub Air. Usa `bleak` per scansioni periodiche e scrive
`ble_devices.json` nella memoria condivisa.

## Build

```bash
# from repo root
docker build -t nexyhub-ble -f src/nexyhub-ble/Dockerfile .

# cross-compile per ARM64
PLATFORM=linux/arm64 sh src/nexyhub-ble/build.sh
```

## Run (locale)

```bash
bash run.sh ble
```

## LuCI — configurazione slot

| parametro | valore |
|-----------|--------|
| Immagine | `nexyhub-ble.tar` |
| Rete | bridge |
| Porte | `224:22` (SSH) |
| Volumi | volume condiviso → `/mnt/shared`, config → `/etc/nexyhub/config.yaml:ro`, `/run/dbus:/run/dbus` |
| Dispositivi | nessuno (BLE via D-Bus) |
| Riavvio | always |

### Variabili d'ambiente

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `SSH_ROOT_PASSWORD` | — | Password root SSH (obbligatoria) |
| `BLE_ADAPTER` | `hci0` | Adattatore BLE |
| `BLE_SCAN_SEC` | `10` | Durata scansione (secondi) |
| `BLE_POLL_SEC` | `10` | Intervallo tra scansioni |
| `NEXYHUB_DB_PATH` | `/mnt/shared/nexyhub.db` | Path database |

## Deploy

```bash
docker build -t nexyhub-ble -f src/nexyhub-ble/Dockerfile .
docker save -o nexyhub-ble.tar nexyhub-ble
# carica .tar via LuCI → Container panel
```
