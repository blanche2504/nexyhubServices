# test BLE scanner - works on any platform by mocking bleak

import os
import sys
import json
import asyncio
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
        # format_device extracts name, address, and RSSI from a bleak Device
        from nexyhub_ble.ble_scanner import format_device

        d = FakeDevice(name="Sensor", address="11:22:33:44:55:66", rssi=-60)
        result = format_device(d)
        self.assertEqual(result["name"], "Sensor")
        self.assertEqual(result["address"], "11:22:33:44:55:66")
        self.assertEqual(result["rssi"], -60)

    def test_format_device_no_name(self):
        # format_device uses '?' when the device has no name
        from nexyhub_ble.ble_scanner import format_device

        d = FakeDevice(name=None, address="11:22:33:44:55:66", rssi=-80)
        result = format_device(d)
        self.assertEqual(result["name"], "?")

    def test_write_devices(self):
        # write_devices writes a JSON file with the device list
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
        # write_devices writes an empty array when given no devices
        from nexyhub_ble.ble_scanner import write_devices

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ble_devices.json"
            write_devices([], dest)
            self.assertTrue(dest.exists())

    def test_wait_for_adapter_found(self):
        # wait_for_adapter returns True when the adapter path exists
        import nexyhub_ble.ble_scanner as mod
        saved_running = mod.running
        mod.running = True
        try:
            with patch("os.path.exists", return_value=True):
                from nexyhub_ble.ble_scanner import wait_for_adapter
                result = wait_for_adapter("hci0", timeout=1)
                self.assertTrue(result)
        finally:
            mod.running = saved_running

    def test_wait_for_adapter_not_found(self):
        # wait_for_adapter returns False when the adapter path never appears
        with patch("os.path.exists", return_value=False):
            from nexyhub_ble.ble_scanner import wait_for_adapter
            import nexyhub_ble.ble_scanner as mod
            mod.running = False
            result = wait_for_adapter("hci0", timeout=1)
            self.assertFalse(result)

    def test_bleak_import(self):
        # BleakScanner can be imported from the scanner module
        from nexyhub_ble.ble_scanner import BleakScanner
        self.assertIsNotNone(BleakScanner)

    @patch("nexyhub_ble.ble_scanner.BleakScanner")
    def test_scan_once_returns_devices(self, mock_bleak):
        # scan_once discovers nearby BLE devices and returns formatted records
        mock_bleak.discover = AsyncMock(return_value=[
            FakeDevice(name="S1", address="AA:BB:CC:DD:EE:01", rssi=-60),
            FakeDevice(name="S2", address="AA:BB:CC:DD:EE:02", rssi=-75),
        ])
        from nexyhub_ble.ble_scanner import scan_once
        result = asyncio.run(scan_once())
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "S1")
        self.assertEqual(result[1]["name"], "S2")
        self.assertEqual(result[0]["rssi"], -60)
        mock_bleak.discover.assert_awaited_once()

    @patch("nexyhub_ble.ble_scanner.BleakScanner")
    def test_scan_once_handles_discover_error(self, mock_bleak):
        # scan_once returns an empty list when discovery raises an exception
        mock_bleak.discover = AsyncMock(side_effect=Exception("scan timeout"))
        from nexyhub_ble.ble_scanner import scan_once
        result = asyncio.run(scan_once())
        self.assertEqual(result, [])

    def test_main_loop_scans_and_writes(self):
        # main_loop scans BLE devices and writes them to ble_devices.json
        import nexyhub_ble.ble_scanner as mod
        saved_running = mod.running
        try:
            with patch.object(mod, "wait_for_adapter", return_value=True):
                with patch.object(mod, "BleakScanner") as mock_bleak:
                    mock_bleak.discover = AsyncMock(return_value=[
                        FakeDevice(name="B1", address="AA:BB:CC:DD:EE:03"),
                    ])
                    with tempfile.TemporaryDirectory() as tmp:
                        with patch.object(mod, "SHARED_DIR", tmp):
                            with patch.object(mod, "POLL_SEC", 60):
                                async def run():
                                    mod.running = True
                                    task = asyncio.create_task(mod.main_loop())
                                    await asyncio.sleep(0.3)
                                    mod.running = False
                                    await asyncio.wait_for(task, timeout=3)
                                asyncio.run(run())
                                dest = Path(tmp) / "ble_devices.json"
                                self.assertTrue(dest.exists(), "write_devices should have been called")
                                data = json.loads(dest.read_text(encoding="utf-8"))
                                self.assertEqual(len(data), 1)
                                self.assertEqual(data[0]["name"], "B1")
        finally:
            mod.running = saved_running


if __name__ == "__main__":
    unittest.main(verbosity=2)
