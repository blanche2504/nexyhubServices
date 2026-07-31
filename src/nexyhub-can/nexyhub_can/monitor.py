import os
import time
from typing import Optional

import can

from nexyhub_can.filters import parse_filters
from nexyhub_can.socketcan import create_bus, send_message, recv_message
from nexyhub_config.loader import load_config
from nexyhub_db.database import Database
from nexyhub_utils.daemon import log, running, setup_signals, init_alarms

CAN_INTERFACE = os.environ.get("CAN_INTERFACE", "can0")
CAN_BITRATE = os.environ.get("CAN_BITRATE", "")
RETRY_SEC = int(os.environ.get("CAN_RETRY_SEC", "3"))
FILTER_IDS_STR = os.environ.get("CAN_FILTER_IDS", "")

setup_signals()


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
                log("can", "ERROR", f"{ifname} not available after {timeout}s")
                return False
            if elapsed % 10 == 0 and elapsed > 0:
                log("can", "WAIT", f"Waiting for {ifname}... ({elapsed}s)")
            time.sleep(1)
        except Exception as e:
            log("can", "ERROR", f"Unexpected error checking interface: {e}")
            time.sleep(RETRY_SEC)
    return False


def can_loop(ifname: str, filters: list, bus=None, db: Optional[Database] = None, alarm_engine=None) -> bool:
    bus = bus or create_bus(ifname, filters)

    try:
        while running:
            msg = recv_message(bus)
            if msg is None:
                continue

            if msg.is_error_frame:
                log("can", "WARN", "Error frame received")
                continue

            if msg.is_remote_frame:
                log("can", "RX", f"RTR ID=0x{msg.arbitration_id:03X}")
                continue

            try:
                text = msg.data.decode("utf-8", errors="ignore").strip("\x00").strip()
            except Exception:
                text = msg.data.hex()

            key = f"id=0x{msg.arbitration_id:03X}"
            log("can", "RX", f"{key} DLC={msg.dlc} DATA={text}")

            value = None
            if msg.data:
                value = float(msg.data[0])

            try:
                if db:
                    db.insert_reading("can", key, value=value, text_value=text)

                if "TESTCAN" in text.upper():
                    if send_message(bus, msg.arbitration_id, b"ACK"):
                        log("can", "TX", f"{key} DATA=ACK")
                        if db:
                            db.insert_reading("can", f"{key}.ack", text_value="ACK")

                if alarm_engine:
                    data = {"can": {key: text}}
                    events = alarm_engine.evaluate(data)
                    for e in events:
                        log("can", e["severity"].upper(), e["message"])
                        if db:
                            db.insert_alarm(e["name"], e["severity"], e["message"])
            except Exception as e:
                log("can", "WARN", f"DB/alarm processing failed: {e}")

    finally:
        bus.shutdown()
        log("can", "INFO", "CAN socket closed")

    return not running


def main() -> None:
    cfg = load_config()
    db_path = os.environ.get("NEXYHUB_DB_PATH") or cfg.logging_db_path
    can_iface = CAN_INTERFACE or cfg.can_interface

    db = None
    try:
        db = Database(db_path, retention_days=cfg.logging_retention_days)
        log("can", "INFO", f"DB logging to {db_path}")
    except Exception as e:
        log("can", "WARN", f"DB init failed: {e}")

    alarm_engine = init_alarms(cfg)

    log("can", "INFO", "=== nexyhub-can monitor started ===")
    log("can", "INFO", f"Interface: {can_iface}")
    log("can", "INFO", f"Bitrate: {CAN_BITRATE or '(from config)'}")
    log("can", "INFO", f"Retry: {RETRY_SEC}s")
    log("can", "INFO", f"PID: {os.getpid()}")

    filters = parse_filters(FILTER_IDS_STR)
    if filters:
        log("can", "INFO", f"CAN filters: {len(filters)} rules")
    else:
        log("can", "INFO", "No CAN filters — accepting all IDs")

    while running:
        log("can", "INFO", f"Waiting for {can_iface}...")
        if not wait_for_interface(can_iface):
            if not running:
                break
            log("can", "WARN", f"{can_iface} not found, retrying in {RETRY_SEC}s...")
            time.sleep(RETRY_SEC)
            continue

        log("can", "INFO", f"{can_iface} available, starting loop")

        if can_loop(can_iface, filters, db=db, alarm_engine=alarm_engine):
            break

        log("can", "INFO", f"Reconnecting in {RETRY_SEC}s...")
        time.sleep(RETRY_SEC)

    if db:
        db.close()
    log("can", "INFO", "=== nexyhub-can monitor terminated ===")


if __name__ == "__main__":
    main()
