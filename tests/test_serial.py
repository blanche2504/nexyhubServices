"""
Test serial monitor — works on any platform by mocking pyserial.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class MockSerial:
    def __init__(self, **kwargs):
        self._buffer = []
        self._written = []
        self._closed = False
        self._exhausted = False

    def write(self, data):
        self._written.append(data)
        return len(data)

    def readline(self):
        if self._exhausted:
            raise OSError("device disconnected")
        if self._buffer:
            return self._buffer.pop(0)
        self._exhausted = True
        raise OSError("device disconnected")

    def close(self):
        self._closed = True

    def flush(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TestSerialEcho(unittest.TestCase):
    def test_echo_eseguito(self):
        from nexyhub_serial.serial_echo import serial_loop

        ser = MockSerial()
        ser._buffer = [b"TEST232\n"]
        serial_loop(ser)
        self.assertGreaterEqual(len(ser._written), 1)
        self.assertIn(b"ESEGUITO", ser._written[0])

    def test_no_response_for_other(self):
        from nexyhub_serial.serial_echo import serial_loop

        ser = MockSerial()
        ser._buffer = [b"HELLO\n"]
        serial_loop(ser)
        self.assertEqual(len(ser._written), 0)

    def test_empty_line_skips(self):
        from nexyhub_serial.serial_echo import serial_loop

        ser = MockSerial()
        ser._buffer = [b"", b"TEST232\n"]
        serial_loop(ser)
        self.assertGreaterEqual(len(ser._written), 1)

    def test_wait_for_device_found(self):
        with patch("os.path.exists", return_value=True):
            from nexyhub_serial.serial_echo import wait_for_device
            result = wait_for_device("/dev/ttyLP6", timeout=1)
            self.assertTrue(result)

    def test_wait_for_device_not_found(self):
        with patch("os.path.exists", return_value=False):
            from nexyhub_serial.serial_echo import wait_for_device
            import nexyhub_serial.serial_echo as mod
            mod.running = False
            result = wait_for_device("/dev/ttyLP6", timeout=1)
            self.assertFalse(result)


class TestRS485Echo(unittest.TestCase):
    def test_rs485_echo_eseguito(self):
        from nexyhub_serial.rs485_echo import rs485_loop

        ser = MockSerial()
        ser._buffer = [b"TEST485\n"]
        rs485_loop(ser)
        self.assertGreaterEqual(len(ser._written), 1)
        self.assertIn(b"ESEGUITO", ser._written[0])

    def test_rs485_no_response_for_other(self):
        from nexyhub_serial.rs485_echo import rs485_loop

        ser = MockSerial()
        ser._buffer = [b"HELLO\n"]
        rs485_loop(ser)
        self.assertEqual(len(ser._written), 0)


class TestModbusRTU(unittest.TestCase):
    def test_modbus_import(self):
        from nexyhub_serial.modbus_rtu import pymodbus
        self.assertIsNotNone(pymodbus, "pymodbus should be importable")

    def test_modbus_main_no_device(self):
        import nexyhub_serial.modbus_rtu as mod
        mod.running = False
        with patch("os.path.exists", return_value=False):
            try:
                mod.main()
            except Exception as e:
                self.fail(f"main() raised {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
