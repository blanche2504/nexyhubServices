import os

DEFAULT_CONFIG_PATH = os.environ.get("NEXYHUB_CONFIG", "/etc/nexyhub/config.yaml")

DEFAULT_CONFIG = {
    "can": {
        "interface": "can0",
        "bitrate": 500000,
        "filters": [],
    },
    "serial": {
        "rs232": {"port": "/dev/ttyLP6", "baudrate": 9600, "parity": "N", "stopbits": 1},
        "rs485": {"port": "/dev/ttyLP2", "baudrate": 9600},
    },
    "ble": {
        "adapter": "hci0",
        "scan_sec": 10,
        "poll_sec": 10,
    },
    "alarms": [],
    "logging": {
        "db_path": "/mnt/shared/nexyhub.db",
        "retention_days": 30,
        "batch_interval": 10,
    },
}


def merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = merge(result[k], v)
        else:
            result[k] = v
    return result
