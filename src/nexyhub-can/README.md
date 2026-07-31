# nexyhub-can CAN bus monitor (slot 1)

Uses `python-can` with `socketcan` (linux native CAN interface) to monitor CAN frames. Responds with ACK to frames containing `TESTCAN`. Writes readings to the shared SQLite database.

## Build

```bash
# from repo root
bash run.sh build

# cross-compile for ARM64
PLATFORM=linux/arm64 sh src/nexyhub-can/build.sh
```

## Run (local)

```bash
# only for dev - host network to reach vcan0
CAN_NETWORK=host CAN_INTERFACE=vcan0 bash run.sh can

# production — bridge (platform maps physical can0)
bash run.sh can

# all services + elevator simulator (auto-configures CAN for local dev)
CAN_INTERFACE=vcan0 bash run.sh simulate
```

## LuCI slot configuration

| parameter | value                                                                 |
| --------- | --------------------------------------------------------------------- |
| Image     | `nexyhub-can.tar`                                                     |
| Network   | bridge                                                                |
| Ports     | `222:22` (SSH)                                                        |
| Volumes   | shared volume → `/mnt/shared`, config → `/etc/nexyhub/config.yaml:ro` |
| Devices   | can0 (mapped by the platform)                                         |
| Restart   | always                                                                |

IMPORTANT: BITRATE MUST BE 125kbps

### Env vars

| Variable            | Default                  | Description                           |
| ------------------- | ------------------------ | ------------------------------------- |
| `SSH_ROOT_PASSWORD` | —                        | Root SSH password (required)          |
| `CAN_INTERFACE`     | `can0`                   | CAN interface name                    |
| `CAN_RETRY_SEC`     | `3`                      | Seconds between connection retries    |
| `CAN_FILTER_IDS`    | —                        | ID filters (e.g. `0x001,0x100-0x1FF`) |
| `NEXYHUB_DB_PATH`   | `/mnt/shared/nexyhub.db` | SQLite database path                  |

## Deploy

```bash
# 1. build
bash run.sh build

# 2. export to .tar
bash run.sh export

# 3. upload .tar via LuCI → Container panel
# 4. configure env/volumes/ports per table above
```
