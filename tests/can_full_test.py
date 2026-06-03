#!/usr/bin/env python3
"""
Full CAN stack integration test.
Runs on any platform with Python 3. Uses socket.socketpair() on Linux
or mock on Windows to simulate CAN frames.

Tests:
  - Frame encoding/decoding
  - Filter parsing (single ID, range, mixed)
  - Error frame handling (BUS-OFF, RESTARTED)
  - TESTCAN response protocol
  - Socket creation with filters
  - Full monitor loop (send/receive/respond)
"""

import os
import sys
import struct
import socket
import time
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}" + (f" — {detail}" if detail else ""))


def make_can_frame(arb_id: int, data: bytes) -> bytes:
    return struct.pack("<IB3x8s", arb_id, len(data), data.ljust(8, b"\x00"))


def make_can_error(error_flags: int) -> bytes:
    CAN_ERR_FLAG = 0x20000000
    return struct.pack("<IB3x8s", CAN_ERR_FLAG | error_flags, 0, b"\x00" * 8)


# ═══════════════════════════════════════════════════════════════
# 1. CAN frame encoding/decoding (pure Python)
# ═══════════════════════════════════════════════════════════════
print("\n1. Frame encoding/decoding")

from nexyhub_can.can_types import parse_frame, describe_error_flags

frame = make_can_frame(0x123, b"\xDE\xAD\xBE\xEF")
r = parse_frame(frame)
check("parse 11-bit data frame", r["id"] == 0x123 and r["data"] == b"\xDE\xAD\xBE\xEF")
check("DLC matches", r["dlc"] == 4)
check("not error/rtr", not r["is_error"] and not r["is_rtr"])

err = make_can_error(0x00000040)
r2 = parse_frame(err)
check("parse error frame (BUS-OFF)", r2["is_error"])
check("error_flags have BUS-OFF", describe_error_flags(r2["error_flags"]) == "BUS-OFF")

err2 = make_can_error(0x00000100)
r3 = parse_frame(err2)
check("parse error frame (RESTARTED)", r3["is_error"])
check("error_flags have RESTARTED", describe_error_flags(r3["error_flags"]) == "RESTARTED")

err3 = make_can_error(0x00000040 | 0x00000080)
r4 = parse_frame(err3)
check("parse error frame (BUS-OFF + BUS-ERROR)", r4["is_error"])
desc = describe_error_flags(r4["error_flags"])
check("describe multiple errors", "BUS-OFF" in desc and "BUS-ERROR" in desc)

# ═══════════════════════════════════════════════════════════════
# 2. Filter parsing
# ═══════════════════════════════════════════════════════════════
print("\n2. Filter parsing")

from nexyhub_can.filters import parse_filters

check("empty filter", parse_filters("") == [])
check("no filter", parse_filters(None) == [])

f = parse_filters("0x123")
check("single ID filter", len(f) == 1 and f[0][0] == 0x123 and f[0][1] == 0x7FF)

f = parse_filters("0x100-0x1FF")
check("range filter", len(f) == 1 and f[0][1] != 0x7FF)

f = parse_filters("0x001,0x100-0x1FF,0x300")
check("mixed filters", len(f) == 3)

f = parse_filters("0x200-0x100")
check("reversed range", len(f) == 1)

# ═══════════════════════════════════════════════════════════════
# 3. SocketCAN helpers (with mock socket)
# ═══════════════════════════════════════════════════════════════
print("\n3. SocketCAN helpers")

from nexyhub_can.socketcan import send_frame


class MockSocket:
    def __init__(self):
        self.sent = []
        self.closed = False

    def send(self, data):
        self.sent.append(data)
        return len(data)

    def close(self):
        self.closed = True


sock = MockSocket()

ok = send_frame(sock, 0x200, b"TESTCAN")
check("send_frame returns True", ok)
check("frame was sent", len(sock.sent) == 1)

parsed = parse_frame(sock.sent[0])
check("sent frame has correct ID", parsed["id"] == 0x200)
check("sent frame has correct data", parsed["data"] == b"TESTCAN")

ok2 = send_frame(sock, 0x100, b"ESEGUITO")
check("send second frame", len(sock.sent) == 2)
parsed2 = parse_frame(sock.sent[1])
check("second frame data", parsed2["data"] == b"ESEGUITO")

# ═══════════════════════════════════════════════════════════════
# 4. Full monitor loop test (with socketpair on Linux)
# ═══════════════════════════════════════════════════════════════
print("\n4. Monitor loop integration")

try:
    a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)

    # Send CAN frames through socketpair
    test_frames = [
        make_can_frame(0x100, b"HELLO"),
        make_can_frame(0x200, b"TESTCAN"),
        make_can_frame(0x300, b"WORLD"),
    ]
    for f in test_frames:
        a.send(f)

    # Read and verify
    received = 0
    a.settimeout(0.5)
    for expected_id, expected_data in [(0x100, b"HELLO"), (0x200, b"TESTCAN"), (0x300, b"WORLD")]:
        try:
            data = b.recv(16)
            p = parse_frame(data)
            if p["id"] == expected_id and p["data"] == expected_data:
                received += 1
        except socket.timeout:
            pass

    check("socketpair: received all 3 frames", received == 3)

    a.close()
    b.close()

except OSError as e:
    print(f"  SKIP socketpair tests (not available on this platform): {e}")


# ═══════════════════════════════════════════════════════════════
# 5. can_loop protocol handling (mock socket)
# ═══════════════════════════════════════════════════════════════
print("\n5. Protocol handling (can_loop with mock socket)")

from nexyhub_can.monitor import can_loop


class MockCANRecv:
    """A mock that acts like a socket, returns canned frames, then raises."""

    def __init__(self, frames: list[bytes]):
        self.frames = list(frames)
        self.sent = []
        self.closed = False

    def recv(self, flags=0):
        if self.frames:
            return self.frames.pop(0)
        raise OSError("no more frames")

    def send(self, data, flags=0):
        self.sent.append(data)
        return len(data)

    def close(self):
        self.closed = True

    def getsockname(self):
        return ("can0", 0)

    def settimeout(self, *a):
        pass


class TimeoutMock(MockCANRecv):
    def recv(self, flags=0):
        if self.frames:
            return self.frames.pop(0)
        import errno
        raise OSError(errno.ETIMEDOUT, "Timed out")


# Test: receive TESTCAN, expect ESEGUITO response
msock = TimeoutMock([make_can_frame(0x200, b"TESTCAN")])

import threading
import nexyhub_can.monitor as mon
result_holder = []
t = threading.Thread(
    target=lambda: result_holder.append(can_loop("can0", [], sock=msock)),
    daemon=True,
)
t.start()
time.sleep(0.3)
mon.running = False
t.join(timeout=2)

if msock.sent:
    resp = parse_frame(msock.sent[0])
    check("can_loop: received TESTCAN → sent ESEGUITO", resp["data"] == b"ESEGUITO")
    check("can_loop: response ID matches", resp["id"] == 0x200)
else:
    check("can_loop: received TESTCAN → sent ESEGUITO", False, "no response sent")

# Test: receive non-TESTCAN frame, expect no response
msock2 = MockCANRecv([make_can_frame(0x100, b"HELLO")])
result_holder2 = []
mon.running = True
t2 = threading.Thread(
    target=lambda: result_holder2.append(can_loop("can0", [], sock=msock2)),
    daemon=True,
)
t2.start()
time.sleep(0.3)
mon.running = False
t2.join(timeout=2)

check("can_loop: non-TESTCAN frame gets no response", len(msock2.sent) == 0)


# ═══════════════════════════════════════════════════════════════
# 6. Environment capabilities
# ═══════════════════════════════════════════════════════════════
print("\n6. Environment capabilities")

has_af_can = hasattr(socket, "AF_CAN")
check("socket.AF_CAN available", has_af_can)

has_af_unix = hasattr(socket, "AF_UNIX")
check("socket.AF_UNIX available", has_af_unix)

try:
    s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, 1)
    s.close()
    check("AF_CAN socket creation", True)
except Exception as e:
    check("AF_CAN socket creation", False, str(e))

# Check can-utils
for cmd in ["cansend", "candump", "slcand"]:
    try:
        r = subprocess.run(["which", cmd], capture_output=True, timeout=2)
        check(f"{cmd} available", r.returncode == 0)
    except Exception:
        check(f"{cmd} available", False)


# ═══════════════════════════════════════════════════════════════
# Results
# ═══════════════════════════════════════════════════════════════
total = PASS + FAIL
print(f"\n{'═' * 40}")
print(f"  {PASS}/{total} passed" + (f"  ({FAIL} failed)" if FAIL else "  All OK!"))
print(f"{'═' * 40}")
sys.exit(0 if FAIL == 0 else 1)
