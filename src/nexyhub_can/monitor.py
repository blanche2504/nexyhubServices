import os
import time
import signal
import can

from nexyhub_can.filters import parse_filters
from nexyhub_can.socketcan import create_bus, send_message, recv_message

CAN_INTERFACE = os.environ.get("CAN_INTERFACE", "can0")
RETRY_SEC = int(os.environ.get("CAN_RETRY_SEC", "3"))
FILTER_IDS_STR = os.environ.get("CAN_FILTER_IDS", "")

running = True


def log(level: str, msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def signal_handler(sig, frame) -> None:
    global running
    log("INFO", f"Received signal {sig}, shutdown...")
    running = False


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def wait_for_interface(ifname: str, timeout: int = 120) -> bool:
    start = time.time()
    while running:
        try:
            bus = can.Bus(interface="socketcan", channel=ifname, receive_own_messages=False)
            bus.shutdown()
            return True
        except OSError:
            elapsed = int(time.time() - start)
            if elapsed >= timeout:
                log("ERROR", f"{ifname} not available after {timeout}s")
                return False
            if elapsed % 10 == 0 and elapsed > 0:
                log("WAIT", f"Waiting for {ifname}... ({elapsed}s)")
            time.sleep(1)
        except Exception as e:
            log("ERROR", f"Unexpected error checking interface: {e}")
            time.sleep(RETRY_SEC)
    return False


def can_loop(ifname: str, filters: list, bus=None) -> str:
    bus = bus or create_bus(ifname, filters)

    try:
        while running:
            msg = recv_message(bus)
            if msg is None:
                continue

            if msg.is_error_frame:
                log("WARN", "Error frame received")
                continue

            if msg.is_remote_frame:
                log("RX", f"RTR ID=0x{msg.arbitration_id:03X}")
                continue

            try:
                text = msg.data.decode("utf-8", errors="ignore").strip("\x00").strip()
            except Exception:
                text = msg.data.hex()

            log("RX", f"ID=0x{msg.arbitration_id:03X} DLC={msg.dlc} DATA={text}")

            if "TESTCAN" in text.upper():
                if send_message(bus, msg.arbitration_id, b"ACK"):
                    log("TX", f"ID=0x{msg.arbitration_id:03X} DATA=ACK")

    finally:
        bus.shutdown()
        log("INFO", "CAN socket closed")

    return "shutdown" if not running else "reconnect"


def main() -> None:
    log("INFO", "=== nexyhub-can monitor started ===")
    log("INFO", f"Interface: {CAN_INTERFACE}")
    log("INFO", f"Retry: {RETRY_SEC}s")
    log("INFO", f"PID: {os.getpid()}")

    filters = parse_filters(FILTER_IDS_STR)
    if filters:
        log("INFO", f"Active filters: {len(filters)} rules")
    else:
        log("INFO", "No filters — accepting all IDs")

    while running:
        log("INFO", f"Waiting for {CAN_INTERFACE}...")
        if not wait_for_interface(CAN_INTERFACE):
            if not running:
                break
            log("WARN", f"{CAN_INTERFACE} not found, retrying in {RETRY_SEC}s...")
            time.sleep(RETRY_SEC)
            continue

        log("INFO", f"{CAN_INTERFACE} available, starting loop")

        result = can_loop(CAN_INTERFACE, filters)

        if result == "shutdown":
            break

        log("INFO", f"Reconnecting in {RETRY_SEC}s...")
        time.sleep(RETRY_SEC)

    log("INFO", "=== nexyhub-can monitor terminated ===")


if __name__ == "__main__":
    main()
