#!/usr/bin/env python3
"""
Full CAN stack integration test.

Tests:
  - can.Message construction and attribute access
  - Filter parsing (single ID, range, mixed)
  - send_message / recv_message helpers
  - Virtual bus send/receive
  - TESTCAN response protocol via can_loop
  - Environment capabilities
"""

import os
import sys
import time
import subprocess
import threading
from unittest.mock import MagicMock
import can

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  OK {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}" + (f" - {detail}" if detail else ""))


def have_vcan(ifname: str = "vcan0") -> bool:
    try:
        import subprocess
        r = subprocess.run(["ip", "link", "show", ifname], capture_output=True, timeout=2)
        return r.returncode == 0
    except Exception:
        return False


def run_tests():
    global PASS, FAIL

    from nexyhub_can.filters import parse_filters
    from nexyhub_can.socketcan import send_message, recv_message
    from nexyhub_can.monitor import can_loop
    import nexyhub_can.monitor as mon

    # --- 1. can.Message construction and attributes ---
    print("\n1. can.Message construction & attributes")

    msg = can.Message(arbitration_id=0x123, data=b"\xDE\xAD\xBE\xEF", is_extended_id=False)
    check("11-bit ID", msg.arbitration_id == 0x123)
    check("data matches", msg.data == b"\xDE\xAD\xBE\xEF")
    check("DLC matches", msg.dlc == 4)
    check("not error frame", not msg.is_error_frame)
    check("not RTR", not msg.is_remote_frame)

    msg_ext = can.Message(arbitration_id=0x1FFFFFFF, data=b"", is_extended_id=True)
    check("extended ID flag", msg_ext.is_extended_id)

    msg_rtr = can.Message(arbitration_id=0x100, is_remote_frame=True, dlc=2)
    check("RTR frame detection", msg_rtr.is_remote_frame)

    # --- 2. Filter parsing ---
    print("\n2. Filter parsing")

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

    # --- 3. send_message / recv_message helpers ---
    print("\n3. send_message / recv_message helpers")

    bus = MagicMock()
    ok = send_message(bus, 0x200, b"TESTCAN")
    check("send_message returns True", ok)
    sent_msg = bus.send.call_args[0][0]
    check("msg arbitration_id", sent_msg.arbitration_id == 0x200)
    check("msg data", sent_msg.data == b"TESTCAN")

    bus.recv.return_value = can.Message(arbitration_id=0x100, data=b"RESPONSE")
    rx = recv_message(bus)
    check("recv_message returns msg", rx is not None)
    check("recv data", rx.data == b"RESPONSE")

    bus.send.side_effect = can.CanError("test")
    ok2 = send_message(bus, 0x100, b"FAIL")
    check("send_message handles error", not ok2)

    bus.recv.return_value = None
    rx2 = recv_message(bus)
    check("recv_message returns None on timeout", rx2 is None)

    # --- 4. Virtual bus send/receive (pure Python, no hardware) ---
    print("\n4. Virtual bus send/receive")

    try:
        vbus_a = can.Bus(interface="virtual", channel="nexyhub_test")
        vbus_b = can.Bus(interface="virtual", channel="nexyhub_test")

        frames = [
            can.Message(arbitration_id=0x100, data=b"HELLO"),
            can.Message(arbitration_id=0x200, data=b"TESTCAN"),
            can.Message(arbitration_id=0x300, data=b"WORLD"),
        ]
        for f in frames:
            vbus_a.send(f)

        received = 0
        for expected_id, expected_data in [(0x100, b"HELLO"), (0x200, b"TESTCAN"), (0x300, b"WORLD")]:
            rx = vbus_b.recv(timeout=0.5)
            if rx and rx.arbitration_id == expected_id and rx.data == expected_data:
                received += 1

        check("virtual bus: received all 3 frames", received == 3)

        vbus_a.shutdown()
        vbus_b.shutdown()

    except Exception as e:
        print(f"  SKIP virtual bus test: {e}")

    # --- 5. can_loop protocol handling (mock bus) ---
    print("\n5. Protocol handling (can_loop with mock bus)")

    def make_mock_bus(frames: list[can.Message]):
        bus = MagicMock()
        bus.recv.side_effect = list(frames) + [None]
        bus.send.return_value = None
        return bus

    # Test: receive TESTCAN, expect ACK response
    bus1 = make_mock_bus([can.Message(arbitration_id=0x200, data=b"TESTCAN")])

    result_holder = []
    t = threading.Thread(
        target=lambda: result_holder.append(can_loop("can0", [], bus=bus1)),
        daemon=True,
    )
    t.start()
    time.sleep(0.3)
    mon.running = False
    t.join(timeout=2)

    if bus1.send.call_args:
        sent = bus1.send.call_args[0][0]
        check("can_loop: TESTCAN sent ACK", sent.data == b"ACK")
    else:
        check("can_loop: TESTCAN sent ACK", False, "no response sent")

    # Test: receive non TESTCAN frame, expect no response
    mon.running = True
    bus2 = make_mock_bus([can.Message(arbitration_id=0x100, data=b"HELLO")])
    result_holder2 = []
    t2 = threading.Thread(
        target=lambda: result_holder2.append(can_loop("can0", [], bus=bus2)),
        daemon=True,
    )
    t2.start()
    time.sleep(0.3)
    mon.running = False
    t2.join(timeout=2)

    check("can_loop: non-TESTCAN gets no response", bus2.send.call_count == 0)

    # --- 6. Real SocketCAN via vcan (requires vcan kernel module) ---
    print("\n6. Real SocketCAN via vcan")

    if have_vcan("vcan0"):
        try:
            import can as can_mod
            bus_a = can_mod.Bus(interface="socketcan", channel="vcan0", receive_own_messages=False)
            bus_b = can_mod.Bus(interface="socketcan", channel="vcan0", receive_own_messages=True)

            frames = [
                can_mod.Message(arbitration_id=0x100, data=b"HELLO"),
                can_mod.Message(arbitration_id=0x200, data=b"TESTCAN"),
                can_mod.Message(arbitration_id=0x300, data=b"WORLD"),
            ]
            for f in frames:
                bus_a.send(f)

            received = 0
            for expected_id, expected_data in [(0x100, b"HELLO"), (0x200, b"TESTCAN"), (0x300, b"WORLD")]:
                rx = bus_b.recv(timeout=0.5)
                if rx and rx.arbitration_id == expected_id and rx.data == expected_data:
                    received += 1

            check("vcan: received all 3 frames", received == 3)

            bus_a.shutdown()
            bus_b.shutdown()

        except Exception as e:
            print(f"  SKIP vcan test: {e}")
    else:
        print("  SKIP vcan test: vcan0 not available")

    # --- 7. Environment capabilities (informational, not counted in FAIL) ---
    print("\n7. Environment capabilities")

    import socket

    def info(name: str, ok: bool):
        print(f"  {'OK' if ok else '--'} {name}")

    info("socket.AF_CAN", hasattr(socket, "AF_CAN"))
    info("socket.AF_UNIX", hasattr(socket, "AF_UNIX"))
    try:
        s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, 1)
        s.close()
        info("AF_CAN socket creation", True)
    except Exception:
        info("AF_CAN socket creation", False)

    for cmd in ["cansend", "candump", "slcand"]:
        try:
            r = subprocess.run(["which", cmd], capture_output=True, timeout=2)
            info(cmd, r.returncode == 0)
        except Exception:
            info(cmd, False)

    try:
        import can as can_mod
        info(f"python-can {can_mod.__version__}", True)
    except Exception:
        info("python-can import", False)


if __name__ == "__main__":
    run_tests()
    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed" + (f"  ({FAIL} failed)" if FAIL else "  All OK!"))
    sys.exit(0 if FAIL == 0 else 1)
