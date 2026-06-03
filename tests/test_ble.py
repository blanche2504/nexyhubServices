"""
Test BLE scanner — works on any platform by mocking bleak.
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class FakeDevice:
    def __init__(self, name="TestDev", address="AA:BB:CC:DD:EE:FF", rssi=-50, metadata=None):
        self.name = name
        self.address = address
        self.rssi = rssi
        self.metadata = metadata or {}


class TestBLEScanner(unittest.TestCase):
    def test_format_device(self):
        from nexyhub_ble.ble_scanner import format_device

        d = FakeDevice(name="Sensor", address="11:22:33:44:55:66", rssi=-60)
        result = format_device(d)
        self.assertEqual(result["name"], "Sensor")
        self.assertEqual(result["address"], "11:22:33:44:55:66")
        self.assertEqual(result["rssi"], -60)

    def test_format_device_no_name(self):
        from nexyhub_ble.ble_scanner import format_device

        d = FakeDevice(name=None, address="11:22:33:44:55:66", rssi=-80)
        result = format_device(d)
        self.assertEqual(result["name"], "?")

    def test_write_devices(self):
        from nexyhub_ble.ble_scanner import write_devices

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ble_devices.json"
            devices = [{"name": "A", "address": "11:22:33:44:55:66", "rssi": -50}]
            write_devices(devices, dest)
            self.assertTrue(dest.exists())
            data = json.loads(dest.read_text(encoding="utf-8"))
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["name"], "A")

    def test_write_devices_empty(self):
        from nexyhub_ble.ble_scanner import write_devices

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ble_devices.json"
            write_devices([], dest)
            self.assertTrue(dest.exists())

    def test_wait_for_adapter_found(self):
        with patch("os.path.exists", return_value=True):
            from nexyhub_ble.ble_scanner import wait_for_adapter
            result = wait_for_adapter("hci0", timeout=1)
            self.assertTrue(result)

    def test_wait_for_adapter_not_found(self):
        with patch("os.path.exists", return_value=False):
            from nexyhub_ble.ble_scanner import wait_for_adapter
            import nexyhub_ble.ble_scanner as mod
            mod.running = False
            result = wait_for_adapter("hci0", timeout=1)
            self.assertFalse(result)

    def test_bleak_import(self):
        from nexyhub_ble.ble_scanner import BleakScanner
        self.assertIsNotNone(BleakScanner)


if __name__ == "__main__":
    unittest.main(verbosity=2)
