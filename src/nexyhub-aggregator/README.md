# nexyhub-aggregator — contenitore aggregatore (slot 4)

Questo contenitore unifica il **consumer HTTP IPC** (porta `8000`) con la **dashboard Flask** (porta `5000`)
per NexyHub Air, fungendo da aggregatore centralizzato per lo slot 4.

## Architettura

```
nexyhub-aggregator (slot 4)

:8000 IPC Consumer HTTP API
- /status
- /data/<key>
- / (elenco chiavi)

:5000 Flask Dashboard
- dashboard
- /api/services
- /api/readings
- /api/alarms
- /api/status

volume condiviso
   /mnt/shared/
   ├── nexyhub.db (SQLite)
   ├── *.json (shared memory files)
   └── ...
```

## Requisiti

- volume condiviso montato su `/mnt/shared/` con il DB SQLite e i file JSON dello shared memory

## Build

```bash
cd developer-ipc-1.0
docker build -t nexyhub-aggregator .
```

## Esecuzione

```bash
docker run -d \
  --name nexyhub-aggregator \
  -p 5000:5000 \
  -p 8000:8000 \
  -v /percorso/shared:/mnt/shared \
  -e SSH_ROOT_PASSWORD=changeme \
  nexyhub-aggregator
```

### Variabili d'ambiente

| Variabile           | Default                  | Descrizione                  |
| ------------------- | ------------------------ | ---------------------------- |
| `FLASK_PORT`        | `5000`                   | Porta della dashboard Flask  |
| `NEXYHUB_DB_PATH`   | `/mnt/shared/nexyhub.db` | Percorso del database SQLite |
| `SSH_ENABLED`       | `true`                   | Abilita server SSH           |
| `SSH_ROOT_PASSWORD` | `""`                     | Password root per SSH        |
| `IPC_CONSUMER_PORT` | `8000`                   | Porta del consumer HTTP IPC  |

## Endpoint

### IPC Consumer (porta 8000)

| Percorso          | Descrizione                       |
| ----------------- | --------------------------------- |
| `GET /`           | Elenco chiavi nello shared memory |
| `GET /status`     | Stato del consumer                |
| `GET /data/<key>` | Legge un valore JSON              |

### Dashboard Flask (porta 5000)

| Percorso                     | Descrizione                    |
| ---------------------------- | ------------------------------ |
| `GET /`                      | Dashboard HTML interattiva     |
| `GET /api/services`          | Stato dei servizi (alive/dead) |
| `GET /api/readings`          | Ultime 100 letture             |
| `GET /api/readings/<source>` | Letture per sorgente           |
| `GET /api/alarms`            | Allarmi attivi e storico       |
| `GET /api/data/<key>`        | Dati dallo shared memory       |
