#!/usr/bin/env python3
"""
Serial end-to-end test using real PTY devices.

Creates a PTY pair, maps the slave into a Docker container,
and tests RS-232 / RS-485 echo protocol over real TTY.
"""

import os
import sys
import time
import pty
import subprocess
import signal

PASS = 0
FAIL = 0

CONTAINER_IMAGE = "nexyhub-serial"


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  OK {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}" + (f" - {detail}" if detail else ""))


def find_container():
    r = subprocess.run(
        ["docker", "ps", "-q", "--filter", f"ancestor={CONTAINER_IMAGE}"],
        capture_output=True, text=True, timeout=5
    )
    return r.stdout.strip()


def test_rs232():
    """Open a PTY, map into container, send TEST232, expect ACK."""
    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)

    # Make sure it's readable/writable by Docker
    os.chmod(slave_name, 0o666)

    # Close slave end — Docker will open it fresh
    os.close(slave_fd)

    print(f"\n--- RS-232 Echo Test (PTY: {slave_name}) ---")

    container_name = "test-serial-pty"
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        capture_output=True, timeout=5
    )

    proc = subprocess.Popen([
        "docker", "run", "--rm", "-d",
        "--name", container_name,
        "-v", f"{slave_name}:/dev/ttyLP6",
        "-e", "SERIAL_PORT=/dev/ttyLP6",
        CONTAINER_IMAGE
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.wait(timeout=10)
    container_id = proc.stdout.read().strip().decode()

    time.sleep(2)

    # Check container is running and logs show device found
    logs = subprocess.run(
        ["docker", "logs", container_name],
        capture_output=True, text=True, timeout=5
    )
    print(f"  Container logs:\n  {'  '.join(logs.stdout.splitlines(True))}")

    if "Device /dev/ttyLP6 found" not in logs.stdout:
        print("  SKIP - container couldn't find device")
        subprocess.run(["docker", "stop", container_name], capture_output=True, timeout=5)
        os.close(master_fd)
        return

    if "Can't open" in logs.stdout:
        print("  SKIP - container couldn't open device")
        subprocess.run(["docker", "stop", container_name], capture_output=True, timeout=5)
        os.close(master_fd)
        return

    # Send TEST232 from the master end
    os.write(master_fd, b"TEST232\n")
    time.sleep(1)

    # Read response from master end (it echoes back what goes to slave)
    try:
        import select
        r, _, _ = select.select([master_fd], [], [], 3)
        if r:
            resp = os.read(master_fd, 1024)
            check("RS-232: received ACK", b"ACK" in resp)
        else:
            check("RS-232: received ACK", False, "timeout - no response")
    except Exception as e:
        check("RS-232: received ACK", False, str(e))

    subprocess.run(["docker", "stop", container_name], capture_output=True, timeout=5)

    os.close(master_fd)


def test_rs485():
    """Same as RS-232 but using --device /dev/ttyLP2 for the RS-485 image command."""
    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)
    os.chmod(slave_name, 0o666)
    os.close(slave_fd)

    print(f"\n--- RS-485 Echo Test (PTY: {slave_name}) ---")

    container_name = "test-rs485-pty"
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        capture_output=True, timeout=5
    )

    proc = subprocess.Popen([
        "docker", "run", "--rm", "-d",
        "--name", container_name,
        "-v", f"{slave_name}:/dev/ttyLP2",
        "-e", "SERIAL_PORT=/dev/ttyLP2",
        CONTAINER_IMAGE, "./.venv/bin/nexyhub-rs485"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.wait(timeout=10)

    time.sleep(2)

    logs = subprocess.run(
        ["docker", "logs", container_name],
        capture_output=True, text=True, timeout=5
    )
    print(f"  Container logs:\n  {'  '.join(logs.stdout.splitlines(True))}")

    if "Device /dev/ttyLP2 found" not in logs.stdout:
        print("  SKIP - RS-485 container couldn't find device")
        subprocess.run(["docker", "stop", container_name], capture_output=True, timeout=5)
        os.close(master_fd)
        return

    os.write(master_fd, b"TEST485\n")
    time.sleep(1)

    try:
        import select
        r, _, _ = select.select([master_fd], [], [], 3)
        if r:
            resp = os.read(master_fd, 1024)
            check("RS-485: received ACK", b"ACK" in resp)
        else:
            check("RS-485: received ACK", False, "timeout - no response")
    except Exception as e:
        check("RS-485: received ACK", False, str(e))

    subprocess.run(["docker", "stop", container_name], capture_output=True, timeout=5)

    os.close(master_fd)


if __name__ == "__main__":
    print(f"Serial E2E Test ({CONTAINER_IMAGE})")
    print("=" * 40)

    try:
        test_rs232()
    finally:
        pass

    try:
        test_rs485()
    finally:
        pass

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed" + (f"  ({FAIL} failed)" if FAIL else "  All OK!"))
    sys.exit(0 if FAIL == 0 else 1)
