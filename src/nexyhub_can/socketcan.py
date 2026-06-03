import socket
import struct
import errno

from nexyhub_can.can_types import CAN_MTU, CAN_FMT


def create_socket(ifname: str, filters: list) -> socket.socket:
    s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
    CAN_RAW_ERR_FILTER = 2
    err_mask = struct.pack("<I", 0x1FFFFFFF)
    s.setsockopt(socket.SOL_CAN_RAW, CAN_RAW_ERR_FILTER, err_mask)
    if filters:
        raw = b"".join(struct.pack("<II", can_id, can_mask) for can_id, can_mask in filters)
        s.setsockopt(socket.SOL_CAN_RAW, socket.CAN_RAW_FILTER, raw)
    s.settimeout(1.0)
    s.bind((ifname,))
    return s


def send_frame(sock: socket.socket, arb_id: int, data: bytes) -> bool:
    padded = data.ljust(8, b"\x00")
    frame = struct.pack(CAN_FMT, arb_id, len(data), padded)
    try:
        sock.send(frame)
        return True
    except OSError as e:
        if e.errno == errno.ENETDOWN:
            pass
        elif e.errno == errno.ENOBUFS:
            pass
        return False


def recv_frame(sock: socket.socket) -> bytes | None:
    try:
        data = sock.recv(CAN_MTU)
        if len(data) < CAN_MTU:
            return None
        return data
    except socket.timeout:
        return None
    except OSError:
        return None
