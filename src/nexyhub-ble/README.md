# NexyHub BLE Scanner — Container per sviluppatori

Container BLE scanner per **NexyHub Air**. Utilizza la libreria `bleak` per eseguire scansioni Bluetooth Low Energy periodiche e scrive i risultati in memoria condivisa (shared memory).

## Mount richiesti

| Mount host          | Mount container |
|---------------------|-----------------|
| `/run/dbus`         | `/run/dbus`     |

## Variabili d'ambiente

| Variabile          | Default  | Descrizione                     |
|--------------------|----------|---------------------------------|
| `BLE_ADAPTER`      | `hci0`   | Adattatore BLE                  |
| `BLE_SCAN_SEC`     | `10`     | Durata scansione (secondi)      |
| `BLE_POLL_SEC`     | `10`     | Intervallo tra scansioni        |
| `BLE_SHARED_DIR`   | `/mnt/shared` | Directory output condivisa |
| `SSH_ENABLED`      | `true`   | Abilita server SSH              |
| `SSH_PORT`         | `22`     | Porta SSH                       |
| `SSH_ROOT_PASSWORD`| `""`     | Password root per SSH           |

## Build

```bash
docker build -t nexyhub-ble:dev ./developer-ble-1.0
```

## Esecuzione

```bash
docker run -d \
  --name nexyhub-ble \
  --network host \
  --privileged \
  -v /run/dbus:/run/dbus \
  -e SSH_ROOT_PASSWORD=mypass \
  nexyhub-ble:dev
```

Il container esegue `python3 -m nexyhub_ble.ble_scanner` e scrive il file `ble_devices.json` nella directory condivisa (`/mnt/shared`).
