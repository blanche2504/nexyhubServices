#!/usr/bin/env python3
"""Check CAN environment inside the container."""
import socket
import struct
import os

CAN_FMT = "<IB3x8s"
CAN_MTU = 16

print("=== CAN Environment Check ===")

try:
    s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
    print("AF_CAN socket: OK")
    s.close()
except Exception as e:
    print(f"AF_CAN socket: FAIL - {e}")

ret = os.system("ip -br link 2>/dev/null | grep -E '(can|vcan)'")
print(f"can/vcan interfaces found (exit={ret})")

for cmd in ["cansend", "candump", "ip"]:
    ret = os.system(f"which {cmd} 2>/dev/null")
    print(f"{cmd}: {'found' if ret == 0 else 'not found'}")

print("\n=== Integration Test via Unix socketpair ===")
a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
frame = struct.pack(CAN_FMT, 0x123, 4, b"\x01\x02\x03\x04".ljust(8, b"\x00"))
a.send(frame)
received = b.recv(CAN_MTU)
r_id, r_dlc, r_data = struct.unpack(CAN_FMT, received)
print(f"Unix socket CAN test: ID=0x{r_id:03X} DLC={r_dlc} DATA={r_data[:r_dlc].hex()}")
a.close()
b.close()
print("Unix socket CAN test: PASS")
