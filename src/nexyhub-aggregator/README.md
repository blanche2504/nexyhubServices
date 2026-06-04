# nexyhub-aggregator v1.0 — dashboard + API (slot 4)

Container aggregatore per NexyHub Air. Unisce la dashboard Flask (porta 5000) e le API REST.
Nessuna periferica richiesta — solo volume condiviso per leggere DB e shared memory.

## Build

```bash
# from repo root
docker build -t nexyhub-ipc -f src/nexyhub-aggregator/Dockerfile .

# cross-compile per ARM64
PLATFORM=linux/arm64 sh src/nexyhub-aggregator/build.sh
```

## Run (locale)

```bash
bash run.sh consumer
# dashboard su http://localhost:5000
```

## LuCI — configurazione slot

| parametro | valore |
|-----------|--------|
| Immagine | `nexyhub-ipc.tar` |
| Rete | bridge |
| Porte | `225:22` (SSH), `5000:5000` (dashboard) |
| Volumi | volume condiviso → `/mnt/shared`, config → `/etc/nexyhub/config.yaml:ro` |
| Dispositivi | nessuno |
| Riavvio | always |

### Variabili d'ambiente

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `SSH_ROOT_PASSWORD` | — | Password root SSH (obbligatoria) |
| `FLASK_PORT` | `5000` | Porta dashboard |
| `NEXYHUB_DB_PATH` | `/mnt/shared/nexyhub.db` | Path database |

### Endpoint

| Percorso | Descrizione |
|----------|-------------|
| `GET /` | Dashboard HTML (Plotly) |
| `GET /api/services` | Stato servizi (alive/dead) |
| `GET /api/readings` | Ultime 100 letture |
| `GET /api/readings/<source>` | Letture per sorgente |
| `GET /api/alarms` | Allarmi attivi + storico |
| `GET /api/status` | Uptime, conteggi |

## Deploy

```bash
docker build -t nexyhub-ipc -f src/nexyhub-aggregator/Dockerfile .
docker save -o nexyhub-ipc.tar nexyhub-ipc
# carica .tar via LuCI → Container panel
```
