import os
import json
import time
import signal
import asyncio
import argparse
from pathlib import Path

from nexyhub_config.loader import load_config
from nexyhub_db.database import Database

BLE_ADAPTER = os.environ.get("BLE_ADAPTER", "hci0")
SCAN_SEC = int(os.environ.get("BLE_SCAN_SEC", "10"))
SHARED_DIR = os.environ.get("BLE_SHARED_DIR", "/mnt/shared")
POLL_SEC = int(os.environ.get("BLE_POLL_SEC", "10"))

DESCRIPTION = "NexyHub BLE Scanner --- periodic Bluetooth Low Energy discovery"

running = True

try:
    from bleak import BleakScanner
except ImportError:
    BleakScanner = None


def log(level: str, msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def signal_handler(sig, frame) -> None:
    global running
    log("INFO", f"Received signal {sig}, shutdown...")
    running = False


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def write_devices(devices: list, dest: Path) -> None:
    tmp = dest.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(devices, indent=2), encoding="utf-8")
        tmp.rename(dest)
        log("INFO", f"Wrote {len(devices)} devices to {dest}")
    except Exception as e:
        log("ERROR", f"Write failed: {e}")


def format_device(device) -> dict:
    return {
        "name": device.name or "?",
        "address": device.address,
        "rssi": device.rssi,
        "metadata": device.metadata or {},
    }


async def scan_once() -> list:
    if BleakScanner is None:
        log("ERROR", "bleak not installed")
        return []
    log("INFO", f"BLE scan on {BLE_ADAPTER} ({SCAN_SEC}s)...")
    try:
        devices = await BleakScanner.discover(timeout=SCAN_SEC, adapter=BLE_ADAPTER)
        result = [format_device(d) for d in devices]
        log("INFO", f"Found {len(result)} devices")
        return result
    except Exception as e:
        log("ERROR", f"Scan failed: {e}")
        return []


def wait_for_adapter(adapter: str, timeout: int = 120) -> bool:
    start = time.time()
    while running:
        path = f"/sys/class/bluetooth/{adapter}"
        if os.path.exists(path):
            log("INFO", f"Adapter {adapter} found")
            return True
        elapsed = int(time.time() - start)
        if elapsed >= timeout:
            log("ERROR", f"{adapter} not available after {timeout}s")
            return False
        if elapsed % 10 == 0 and elapsed > 0:
            log("WAIT", f"Waiting for {adapter}... ({elapsed}s)")
        time.sleep(1)
    return False


async def main_loop(db=None):
    log("INFO", "=== nexyhub-ble scanner started ===")
    log("INFO", f"Adapter: {BLE_ADAPTER}")
    log("INFO", f"Scan: {SCAN_SEC}s, Poll: {POLL_SEC}s")
    log("INFO", f"Shared dir: {SHARED_DIR}")

    if BleakScanner is None:
        log("ERROR", "Install bleak: pip install bleak")
        return

    if not wait_for_adapter(BLE_ADAPTER):
        return

    output = Path(SHARED_DIR) / "ble_devices.json"

    while running:
        devices = await scan_once()
        if running:
            write_devices(devices, output)
            if db:
                for d in devices:
                    db.insert_reading("ble", d["address"], text_value=d["name"])
            if running:
                log("INFO", f"Next scan in {POLL_SEC}s...")
                for _ in range(POLL_SEC):
                    if not running:
                        break
                    await asyncio.sleep(1)

    log("INFO", "=== nexyhub-ble scanner terminated ===")


def main():
    global BLE_ADAPTER, SCAN_SEC, POLL_SEC, SHARED_DIR
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--adapter", default=BLE_ADAPTER, help="BLE adapter (default: %(default)s)")
    parser.add_argument("--scan-sec", type=int, default=SCAN_SEC, help="Scan duration (default: %(default)s)")
    parser.add_argument("--poll-sec", type=int, default=POLL_SEC, help="Poll interval (default: %(default)s)")
    parser.add_argument("--shared-dir", default=SHARED_DIR, help="Shared memory dir (default: %(default)s)")
    args = parser.parse_args()
    BLE_ADAPTER = args.adapter
    SCAN_SEC = args.scan_sec
    POLL_SEC = args.poll_sec
    SHARED_DIR = args.shared_dir

    cfg = load_config()
    db = None
    try:
        db = Database(cfg.logging_db_path)
        log("INFO", f"DB logging to {cfg.logging_db_path}")
    except Exception as e:
        log("WARN", f"DB init failed: {e}")

    asyncio.run(main_loop(db=db))

    if db:
        db.close()


if __name__ == "__main__":
    main()
