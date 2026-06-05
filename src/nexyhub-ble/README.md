# nexyhub-ble BLE scanner (slot 3)

Uses `bleak` (cross-platform BLE library) for periodic Bluetooth Low Energy scans. Writes discovered devices to `ble_devices.json` in the shared volume.

## Build

```bash
# from repo root
bash run.sh build

# cross-compile for ARM64
PLATFORM=linux/arm64 sh src/nexyhub-ble/build.sh
```

## Run (local)

```bash
# requires D-Bus (hci0 adapter)
bash run.sh ble

# standalone
uv run nexyhub-ble
```

## LuCI slot configuration

| parameter | value                                                                                        |
| --------- | -------------------------------------------------------------------------------------------- |
| Image     | `nexyhub-ble.tar`                                                                            |
| Network   | bridge                                                                                       |
| Ports     | `224:22` (SSH)                                                                               |
| Volumes   | shared volume → `/mnt/shared`, config → `/etc/nexyhub/config.yaml:ro`, `/run/dbus:/run/dbus` |
| Devices   | none (BLE via D-Bus)                                                                         |
| Restart   | always                                                                                       |

### Environment variables

| Variable            | Default                  | Description                  |
| ------------------- | ------------------------ | ---------------------------- |
| `SSH_ROOT_PASSWORD` | —                        | Root SSH password (required) |
| `BLE_ADAPTER`       | `hci0`                   | BLE adapter name             |
| `BLE_SCAN_SEC`      | `10`                     | Scan duration (seconds)      |
| `BLE_POLL_SEC`      | `10`                     | Interval between scans       |
| `NEXYHUB_DB_PATH`   | `/mnt/shared/nexyhub.db` | Database path                |

## Deploy

```bash
bash run.sh build
bash run.sh export
# produces nexyhub-ble.tar — upload via LuCI → Container panel
```

BLE on Linux requires D-Bus — the container mounts `/run/dbus:/run/dbus` to communicate with the host's BlueZ daemon. The host must have a Bluetooth adapter (`hci0` by default).
