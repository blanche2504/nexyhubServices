import os
import yaml

from nexyhub_config.schema import DEFAULT_CONFIG, DEFAULT_CONFIG_PATH, merge


class Config:
    def __init__(self, data: dict):
        self._data = data

    @property
    def can_interface(self) -> str:
        return self._data.get("can", {}).get("interface", "can0")

    @property
    def can_bitrate(self) -> int:
        return self._data.get("can", {}).get("bitrate", 500000)

    @property
    def can_filters(self) -> list:
        return self._data.get("can", {}).get("filters", [])

    @property
    def serial_rs232_port(self) -> str:
        return self._data.get("serial", {}).get("rs232", {}).get("port", "/dev/ttyLP6")

    @property
    def serial_rs232_baudrate(self) -> int:
        return self._data.get("serial", {}).get("rs232", {}).get("baudrate", 9600)

    @property
    def serial_rs485_port(self) -> str:
        return self._data.get("serial", {}).get("rs485", {}).get("port", "/dev/ttyLP2")

    @property
    def serial_rs485_baudrate(self) -> int:
        return self._data.get("serial", {}).get("rs485", {}).get("baudrate", 9600)

    @property
    def ble_adapter(self) -> str:
        return self._data.get("ble", {}).get("adapter", "hci0")

    @property
    def ble_scan_sec(self) -> int:
        return self._data.get("ble", {}).get("scan_sec", 10)

    @property
    def ble_poll_sec(self) -> int:
        return self._data.get("ble", {}).get("poll_sec", 10)

    @property
    def alarms(self) -> list:
        return self._data.get("alarms", [])

    @property
    def logging_db_path(self) -> str:
        return self._data.get("logging", {}).get("db_path", "/mnt/shared/nexyhub.db")

    @property
    def logging_retention_days(self) -> int:
        return self._data.get("logging", {}).get("retention_days", 30)

    @property
    def logging_batch_interval(self) -> int:
        return self._data.get("logging", {}).get("batch_interval", 10)

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
