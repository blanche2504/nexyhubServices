"""
Test CAN monitor — works on any platform by patching socket for AF_CAN.

Usage:
    uv run python tests/test_can_monitor.py
"""

import os
import sys
import struct
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nexyhub_can.can_types import CAN_FMT, CAN_ERR_FLAG, parse_frame, describe_error_flags
from nexyhub_can.filters import parse_filters
from nexyhub_can.socketcan import send_frame


CAN_ERR_BUSOFF = 0x00000040
CAN_ERR_RESTARTED = 0x00000100


def make_frame(arb_id: int, data: bytes) -> bytes:
    padded = data.ljust(8, b"\x00")
    return struct.pack(CAN_FMT, arb_id, len(data), padded)


def make_error_frame(flags: int) -> bytes:
    return struct.pack(CAN_FMT, CAN_ERR_FLAG | flags, 0, b"\x00" * 8)


class MockSocket:
    def __init__(self, family=None, stype=None, proto=None, fileno=None):
        self._frames = []
        self._sent = []
        self._closed = False

    def setsockopt(self, *args):
        pass

    def settimeout(self, t):
        pass

    def bind(self, addr):
        pass

    def recv(self, bufsize):
        if self._frames:
            return self._frames.pop(0)
        raise TimeoutError()

    def send(self, data):
        self._sent.append(data)
        return len(data)

    def close(self):
        self._closed = True


def _make_socket_patch(mock_sock):
    def socket_constructor(family=-1, stype=-1, proto=-1, fileno=None):
        return mock_sock
    return socket_constructor


CAN_PATCHES = {
    "AF_CAN": 29,
    "CAN_RAW": 1,
    "SOL_CAN_RAW": 1,
    "CAN_RAW_FILTER": 1,
    "CAN_RAW_ERR_FILTER": 2,
}


class TestCanTypes(unittest.TestCase):
    def test_parse_data_frame(self):
        frame = make_frame(0x123, b"\x01\x02\x03\x04")
        r = parse_frame(frame)
        self.assertEqual(r["id"], 0x123)
        self.assertEqual(r["dlc"], 4)
        self.assertEqual(r["data"], b"\x01\x02\x03\x04")
        self.assertFalse(r["is_error"])
        self.assertFalse(r["is_rtr"])
        self.assertFalse(r["is_extended"])

    def test_parse_error_frame(self):
        r = parse_frame(make_error_frame(CAN_ERR_BUSOFF))
        self.assertTrue(r["is_error"])
        self.assertTrue(r["error_flags"] & CAN_ERR_BUSOFF)

    def test_parse_rtr_frame(self):
        rtr_id = 0x100 | 0x40000000
        r = parse_frame(make_frame(rtr_id, b""))
        self.assertTrue(r["is_rtr"])

    def test_describe_busoff(self):
        self.assertIn("BUS-OFF", describe_error_flags(CAN_ERR_BUSOFF))

    def test_describe_restarted(self):
        self.assertIn("RESTARTED", describe_error_flags(CAN_ERR_RESTARTED))


class TestFilters(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(parse_filters(""), [])

    def test_single_id(self):
        f = parse_filters("0x123")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0], (0x123, 0x7FF))

    def test_range(self):
        f = parse_filters("0x100-0x1FF")
        self.assertEqual(len(f), 1)
        cid, mask = f[0]
        self.assertNotEqual(mask, 0x7FF)

    def test_mixed(self):
        f = parse_filters("0x001,0x100-0x1FF,0x300")
        self.assertEqual(len(f), 3)


class TestSendFrame(unittest.TestCase):
    def test_send(self):
        sock = MockSocket()
        ok = send_frame(sock, 0x123, b"ESEGUITO")
        self.assertTrue(ok)
        self.assertEqual(len(sock._sent), 1)

    def test_send_data_integrity(self):
        sock = MockSocket()
        send_frame(sock, 0x200, b"HELLO")
        parsed = parse_frame(sock._sent[0])
        self.assertEqual(parsed["id"], 0x200)
        self.assertEqual(parsed["data"], b"HELLO")


class TestCreateSocket(unittest.TestCase):
    def test_create_no_filters(self):
        import socket

        mock_sock = MockSocket()
        with (
            patch.object(socket, "socket", side_effect=_make_socket_patch(mock_sock)),
            patch.multiple(socket, **CAN_PATCHES, create=True),
        ):
            from nexyhub_can.socketcan import create_socket

            s = create_socket("can0", [])
            self.assertFalse(s._closed)

    def test_create_with_filters(self):
        import socket

        mock_sock = MockSocket()
        mock_sock._frames = [make_frame(0x123, b"TESTCAN")]

        with (
            patch.object(socket, "socket", side_effect=_make_socket_patch(mock_sock)),
            patch.multiple(socket, **CAN_PATCHES, create=True),
        ):
            from nexyhub_can.socketcan import create_socket, recv_frame

            filters = parse_filters("0x123")
            s = create_socket("can0", filters)
            data = recv_frame(s)
            self.assertIsNotNone(data)
            r = parse_frame(data)
            self.assertEqual(r["id"], 0x123)

    def test_recv_and_respond(self):
        import socket

        mock_sock = MockSocket()
        mock_sock._frames = [
            make_frame(0x100, b"HELLO"),
            make_frame(0x200, b"TESTCAN"),
            make_frame(0x300, b"BYE"),
        ]

        with (
            patch.object(socket, "socket", side_effect=_make_socket_patch(mock_sock)),
            patch.multiple(socket, **CAN_PATCHES, create=True),
        ):
            from nexyhub_can.socketcan import create_socket, recv_frame, send_frame

            s = create_socket("can0", [])
            rx = []
            for _ in range(3):
                data = recv_frame(s)
                if data:
                    rx.append(parse_frame(data))
            self.assertEqual(len(rx), 3)
            self.assertEqual(rx[0]["id"], 0x100)
            self.assertEqual(rx[1]["id"], 0x200)
            self.assertEqual(rx[2]["id"], 0x300)
            self.assertEqual(rx[0]["data"], b"HELLO")
            self.assertEqual(rx[1]["data"], b"TESTCAN")
            ok = send_frame(s, 0x200, b"ESEGUITO")
            self.assertTrue(ok)
            sent = parse_frame(s._sent[0])
            self.assertEqual(sent["data"], b"ESEGUITO")


if __name__ == "__main__":
    unittest.main(verbosity=2)
