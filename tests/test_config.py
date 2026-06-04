import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nexyhub_config.loader import load_config, read_config, Config


class TestConfigDefaults(unittest.TestCase):
    def test_load_without_file_returns_defaults(self):
        # load_config without a config file returns merged defaults
        cfg = load_config("/nonexistent/config.yaml")
        self.assertEqual(cfg.can_interface, "can0")
        self.assertEqual(cfg.can_bitrate, 500000)
        self.assertEqual(cfg.can_filters, [])

    def test_serial_defaults(self):
        cfg = load_config("/nonexistent/config.yaml")
        self.assertEqual(cfg.serial_rs232_port, "/dev/ttyLP6")
        self.assertEqual(cfg.serial_rs232_baudrate, 9600)
        self.assertEqual(cfg.serial_rs485_port, "/dev/ttyLP2")

    def test_ble_defaults(self):
        cfg = load_config("/nonexistent/config.yaml")
        self.assertEqual(cfg.ble_adapter, "hci0")
        self.assertEqual(cfg.ble_scan_sec, 10)

    def test_logging_defaults(self):
        cfg = load_config("/nonexistent/config.yaml")
        self.assertEqual(cfg.logging_db_path, "/mnt/shared/nexyhub.db")
        self.assertEqual(cfg.logging_retention_days, 30)

    def test_alarms_defaults(self):
        cfg = load_config("/nonexistent/config.yaml")
        self.assertEqual(cfg.alarms, [])

    def test_raw_returns_copy(self):
        cfg = load_config("/nonexistent/config.yaml")
        raw = cfg.raw()
        self.assertIn("can", raw)
        self.assertIn("serial", raw)
        self.assertIn("alarms", raw)
        self.assertIn("logging", raw)
        self.assertIn("ble", raw)


class TestConfigWithFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        self.tmp.write("""
can:
  interface: vcan0
  bitrate: 250000
  filters:
    - id: "0x100"
      name: "sensor_a"

serial:
  rs232:
    port: /dev/ttyLP0
    baudrate: 115200

alarms:
  - name: "high_temp"
    source: "can.sensor_a"
    max: 80.0
    severity: "critical"

logging:
  retention_days: 7
""")
        self.tmp.close()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_merge_overrides_can(self):
        cfg = load_config(self.tmp.name)
        self.assertEqual(cfg.can_interface, "vcan0")
        self.assertEqual(cfg.can_bitrate, 250000)

    def test_merge_overrides_serial(self):
        cfg = load_config(self.tmp.name)
        self.assertEqual(cfg.serial_rs232_port, "/dev/ttyLP0")
        self.assertEqual(cfg.serial_rs232_baudrate, 115200)
        # rs485 should still have defaults
        self.assertEqual(cfg.serial_rs485_port, "/dev/ttyLP2")

    def test_merge_overrides_alarms(self):
        cfg = load_config(self.tmp.name)
        self.assertEqual(len(cfg.alarms), 1)
        self.assertEqual(cfg.alarms[0]["name"], "high_temp")

    def test_merge_overrides_logging(self):
        cfg = load_config(self.tmp.name)
        self.assertEqual(cfg.logging_retention_days, 7)
        # db_path should still be default
        self.assertEqual(cfg.logging_db_path, "/mnt/shared/nexyhub.db")
