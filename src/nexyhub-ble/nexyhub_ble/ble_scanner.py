import os
import json
import asyncio
import argparse
from pathlib import Path

from nexyhub_config.loader import load_config
from nexyhub_db.database import Database
from nexyhub_utils.daemon import log, running, setup_signals, wait_for_path

BLE_ADAPTER = os.environ.get("BLE_ADAPTER", "hci0")
SCAN_SEC = int(os.environ.get("BLE_SCAN_SEC", "10"))
SHARED_DIR = os.environ.get("BLE_SHARED_DIR", "/mnt/shared")
POLL_SEC = int(os.environ.get("BLE_POLL_SEC", "10"))

DESCRIPTION = "NexyHub BLE Scanner --- periodic Bluetooth Low Energy discovery"

setup_signals()

try:
    from bleak import BleakScanner
except ImportError:
    BleakScanner = None


def write_devices(devices: list, dest: Path) -> None:
    tmp = dest.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(devices, indent=2), encoding="utf-8")
        tmp.rename(dest)
        log("ble", "INFO", f"Wrote {len(devices)} devices to {dest}")
    except Exception as e:
        log("ble", "ERROR", f"Write failed: {e}")


def format_device(device) -> dict:
    return {
        "name": device.name or "?",
        "address": device.address,
        "rssi": device.rssi,
        "metadata": device.metadata or {},
    }


async def scan_once() -> list:
    if BleakScanner is None:
        log("ble", "ERROR", "bleak not installed")
        return []
    log("ble", "INFO", f"BLE scan on {BLE_ADAPTER} ({SCAN_SEC}s)...")
    try:
        devices = await BleakScanner.discover(timeout=SCAN_SEC, adapter=BLE_ADAPTER)
        result = [format_device(d) for d in devices]
        log("ble", "INFO", f"Found {len(result)} devices")
        return result
    except Exception as e:
        log("ble", "ERROR", f"Scan failed: {e}")
        return []


async def main_loop(db=None):
    log("ble", "INFO", "=== nexyhub-ble scanner started ===")
    log("ble", "INFO", f"Adapter: {BLE_ADAPTER}")
    log("ble", "INFO", f"Scan: {SCAN_SEC}s, Poll: {POLL_SEC}s")
    log("ble", "INFO", f"Shared dir: {SHARED_DIR}")

    if BleakScanner is None:
        log("ble", "ERROR", "Install bleak: pip install bleak")
        return

    if not wait_for_path(f"/sys/class/bluetooth/{BLE_ADAPTER}", label=BLE_ADAPTER):
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
                log("ble", "INFO", f"Next scan in {POLL_SEC}s...")
                for _ in range(POLL_SEC):
                    if not running:
                        break
                    await asyncio.sleep(1)

    log("ble", "INFO", "=== nexyhub-ble scanner terminated ===")


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
        db_path = os.environ.get("NEXYHUB_DB_PATH") or cfg.logging_db_path
        db = Database(db_path, retention_days=cfg.logging_retention_days)
        log("ble", "INFO", f"DB logging to {db_path}")
    except Exception as e:
        log("ble", "WARN", f"DB init failed: {e}")

    asyncio.run(main_loop(db=db))

    if db:
        db.close()


if __name__ == "__main__":
    main()
