# developer-can v1.0

Container Docker per monitoraggio CAN bus su NexyHub Air, basato su python-can con socketcan.

## Architettura

```
docker run
    │
    ▼
entrypoint.sh (generico)
    │
    ├── /docker-entrypoint.d/00-ssh.sh  →  avvia sshd in background
    │
    └── exec "$@"  →  CMD: python3 -m nexyhub_can.monitor (diventa PID 1)
```

L'applicazione si connette all'interfaccia CAN via socketcan, rimane in ascolto
dei messaggi e risponde automaticamente con un ACK a qualsiasi frame contenente
la stringa `TESTCAN`.

### Dipendenze shared

Il container copia i pacchetti condivisi dal repository principale:

| Pacchetto         | Path sorgente (repo) | Ruolo                            |
|-------------------|----------------------|----------------------------------|
| `nexyhub_config`  | `shared/nexyhub_config/` | Caricamento configurazione YAML |
| `nexyhub_db`      | `shared/nexyhub_db/`     | Logging su database SQLite       |
| `nexyhub_alarms`  | `shared/nexyhub_alarms/` | Motore regole allarmi            |

## Build

Esegui il build dalla root del repository:

```bash
docker build -t nexyhub-can -f developer-can-1.0/Dockerfile .
```

## Run

```bash
# Con interfaccia CAN reale
docker run -d \
    --name nexyhub-can \
    --network=none \
    --restart unless-stopped \
    -e SSH_ROOT_PASSWORD=mypassword \
    -e CAN_INTERFACE=can0 \
    -v /path/to/shared:/mnt/shared \
    nexyhub-can

# Con vcan0 (sviluppo)
docker run -d \
    --name nexyhub-can \
    --network=none \
    --restart unless-stopped \
    -e SSH_ROOT_PASSWORD=mypassword \
    -e CAN_INTERFACE=vcan0 \
    -v /path/to/shared:/mnt/shared \
    nexyhub-can
```

## Variabili d'ambiente

| Variabile            | Default                   | Descrizione                          |
|----------------------|---------------------------|--------------------------------------|
| `SSH_ENABLED`        | `true`                    | Abilita/disabilita SSH               |
| `SSH_ROOT_PASSWORD`  | —                         | Password root (obbligatoria se SSH)  |
| `SSH_PORT`           | `22`                      | Porta SSH                            |
| `CAN_INTERFACE`      | `can0`                    | Interfaccia CAN                      |
| `CAN_RETRY_SEC`      | `3`                       | Secondi tra retry                    |
| `CAN_FILTER_IDS`     | —                         | Filtri ID (es. `0x001,0x100-0x1FF`) |
| `NEXYHUB_DB_PATH`    | `/mnt/shared/nexyhub.db`  | Path database SQLite                 |
