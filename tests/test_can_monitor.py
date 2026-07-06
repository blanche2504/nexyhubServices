import unittest
from unittest.mock import patch, MagicMock
import can

from nexyhub_can.filters import parse_filters
from nexyhub_can.socketcan import send_message, recv_message, create_bus


class TestFilters(unittest.TestCase):
    def test_empty(self):
        # parsing an empty filter string returns an empty list
        self.assertEqual(parse_filters(""), [])

    def test_single_id(self):
        # parsing a single can id produces one filter with full 11-bit mask
        f = parse_filters("0x123")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0], (0x123, 0x7FF))

    def test_range(self):
        # parsing an id range produces a filter with a non-full mask
        f = parse_filters("0x100-0x1FF")
        self.assertEqual(len(f), 1)
        cid, mask = f[0]
        self.assertNotEqual(mask, 0x7FF)

    def test_mixed(self):
        # parsing a comma-separated mix of ids and ranges returns the right count
        f = parse_filters("0x001,0x100-0x1FF,0x300")
        self.assertEqual(len(f), 3)


class TestSendMessage(unittest.TestCase):
    def test_send(self):
        # send_message constructs a proper can.Message and returns True on success
        bus = MagicMock()
        ok = send_message(bus, 0x123, b"ACK")
        self.assertTrue(ok)
        bus.send.assert_called_once()
        msg = bus.send.call_args[0][0]
        self.assertIsInstance(msg, can.Message)
        self.assertEqual(msg.arbitration_id, 0x123)
        self.assertEqual(msg.data, b"ACK")

    def test_send_os_error(self):
        # send_message handles OSError gracefully and returns False
        bus = MagicMock()
        bus.send.side_effect = OSError("test")
        ok = send_message(bus, 0x200, b"HELLO")
        self.assertFalse(ok)

    def test_send_can_error(self):
        # send_message handles CanError gracefully and returns False
        bus = MagicMock()
        bus.send.side_effect = can.CanError("test")
        ok = send_message(bus, 0x200, b"HELLO")
        self.assertFalse(ok)


class TestRecvMessage(unittest.TestCase):
    def test_recv_returns_message(self):
        # recv_message returns the received can.Message when one is available
        bus = MagicMock()
        expected = can.Message(arbitration_id=0x100, data=b"hello")
        bus.recv.return_value = expected
        result = recv_message(bus)
        self.assertIs(result, expected)

    def test_recv_timeout_returns_none(self):
        # recv_message returns None when recv times out
        bus = MagicMock()
        bus.recv.return_value = None
        result = recv_message(bus)
        self.assertIsNone(result)

    def test_recv_error_returns_none(self):
        # recv_message returns None when recv raises CanError
        bus = MagicMock()
        bus.recv.side_effect = can.CanError("test")
        result = recv_message(bus)
        self.assertIsNone(result)


class TestCreateBus(unittest.TestCase):
    @patch("nexyhub_can.socketcan.can.Bus")
    def test_create_no_filters(self, mock_bus_class):
        # create_bus without filters initialises the bus and does not call set_filters
        mock_instance = MagicMock()
        mock_bus_class.return_value = mock_instance
        bus = create_bus("can0", [])
        mock_bus_class.assert_called_once_with(
            interface="socketcan", channel="can0", receive_own_messages=False
        )
        mock_instance.set_filters.assert_not_called()

    @patch("nexyhub_can.socketcan.can.Bus")
    def test_create_with_filters(self, mock_bus_class):
        # create_bus with filters creates the bus and applies the filters
        mock_instance = MagicMock()
        mock_bus_class.return_value = mock_instance
        filters = parse_filters("0x123")
        bus = create_bus("can0", filters)
        mock_instance.set_filters.assert_called_once_with([(0x123, 0x7FF)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
