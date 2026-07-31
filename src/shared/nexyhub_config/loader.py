import os
import yaml

from nexyhub_config.schema import DEFAULT_CONFIG, DEFAULT_CONFIG_PATH, merge


_ATTRS = {
    "can_interface": ("can", "interface"),
    "can_bitrate": ("can", "bitrate"),
    "can_filters": ("can", "filters"),
    "serial_rs232_port": ("serial", "rs232", "port"),
    "serial_rs232_baudrate": ("serial", "rs232", "baudrate"),
    "serial_rs485_port": ("serial", "rs485", "port"),
    "serial_rs485_baudrate": ("serial", "rs485", "baudrate"),
    "ble_adapter": ("ble", "adapter"),
    "ble_scan_sec": ("ble", "scan_sec"),
    "ble_poll_sec": ("ble", "poll_sec"),
    "alarms": ("alarms",),
    "logging_db_path": ("logging", "db_path"),
    "logging_retention_days": ("logging", "retention_days"),
    "logging_batch_interval": ("logging", "batch_interval"),
}

_DEFAULTS = {
    "can_interface": "can0",
    "can_bitrate": 500000,
    "can_filters": [],
    "serial_rs232_port": "/dev/ttyLP6",
    "serial_rs232_baudrate": 9600,
    "serial_rs485_port": "/dev/ttyLP2",
    "serial_rs485_baudrate": 9600,
    "ble_adapter": "hci0",
    "ble_scan_sec": 10,
    "ble_poll_sec": 10,
    "alarms": [],
    "logging_db_path": "/mnt/shared/nexyhub.db",
    "logging_retention_days": 30,
    "logging_batch_interval": 10,
}


class Config:
    def __init__(self, data: dict):
        self._data = data

    def __getattr__(self, name: str):
        if name.startswith("_") or name not in _ATTRS:
            raise AttributeError(name)
        keys = _ATTRS[name]
        val = self._data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
                if val is None:
                    return _DEFAULTS.get(name)
            else:
                return _DEFAULTS.get(name)
        return val

    def raw(self) -> dict:
        return dict(self._data)


def read_config(path: str | None = None) -> dict:
    path = path or DEFAULT_CONFIG_PATH
    if not os.path.exists(path):
        return dict(DEFAULT_CONFIG)
    with open(path, "r") as f:
        user = yaml.safe_load(f) or {}
    return merge(DEFAULT_CONFIG, user)


def load_config(path: str | None = None) -> Config:
    return Config(read_config(path))
