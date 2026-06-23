# nexyhub-aggregator v1.0 - dashboard + API (slot 4)

Runs a Flask dashboard on port 5000 and REST API. No peripherals required — only needs the shared volume to read the SQLite database and shared memory files written by the other services.

## Build

```bash
# from repo root
bash run.sh build

# cross-compile for ARM64
PLATFORM=linux/arm64 sh src/nexyhub-aggregator/build.sh
```

## Run (local)

```bash
bash run.sh consumer
# dashboard at http://localhost:5000

# standalone
uv run nexyhub-consumer
uv run nexyhub-ui
```

## LuCI slot configuration

| parameter | value                                                                 |
| --------- | --------------------------------------------------------------------- |
| Image     | `nexyhub-ipc.tar`                                                     |
| Network   | bridge                                                                |
| Ports     | `225:22` (SSH), `5000:5000` (dashboard)                               |
| Volumes   | shared volume → `/mnt/shared`, config → `/etc/nexyhub/config.yaml:ro` |
| Devices   | none                                                                  |
| Restart   | always                                                                |

### Env vars

| Variable            | Default                  | Description                  |
| ------------------- | ------------------------ | ---------------------------- |
| `SSH_ROOT_PASSWORD` | —                        | Root SSH password (required) |
| `FLASK_PORT`        | `5000`                   | Dashboard port               |
| `NEXYHUB_DB_PATH`   | `/mnt/shared/nexyhub.db` | Database path                |

### API endpoints

| Path                         | Description                                          |
| ---------------------------- | ---------------------------------------------------- |
| `GET /`                      | Dashboard HTML (Plotly charts)                       |
| `GET /api/services`          | Service status (alive/dead per slot)                 |
| `GET /api/readings`          | Last 100 readings                                    |
| `GET /api/readings/<source>` | Readings filtered by source (`can`, `serial`, `ble`) |
| `GET /api/alarms`            | Active alarms + history                              |
| `GET /api/status`            | Uptime, file count, alarm count                      |
| `GET /api/data/<key>`        | Shared memory data by key                            |
| `GET /api/logs`              | List available log services                          |
| `GET /api/logs/<service>`    | Last 200 log lines for a service                     |

## Deploy

```bash
bash run.sh build
bash run.sh export
# produces nexyhub-ipc.tar — upload via LuCI → Container panel
```

Alive/dead detection works by timestamp age: each service writes readings to the shared SQLite database. If no new reading arrives within 120 seconds (`SERVICE_TIMEOUT`), the dashboard marks the service as dead. This means a service with no traffic (e.g., CAN bus with no frames) will show as dead even if the container is still running.
This is bad, but i'm sure i can fix it another time.
