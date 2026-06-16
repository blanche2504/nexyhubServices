import os
import time
import signal
import can

from nexyhub_can.filters import parse_filters
from nexyhub_can.socketcan import create_bus, send_message, recv_message
from nexyhub_config.loader import load_config
from nexyhub_db.database import Database
from nexyhub_alarms.engine import AlarmEngine
from nexyhub_alarms.rules import AlarmRule
from nexyhub_logs import log as file_log

CAN_INTERFACE = os.environ.get("CAN_INTERFACE", "can0")
RETRY_SEC = int(os.environ.get("CAN_RETRY_SEC", "3"))
FILTER_IDS_STR = os.environ.get("CAN_FILTER_IDS", "")

running = True


def log(level: str, msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)
    file_log("can", level, msg)


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


def can_loop(ifname: str, filters: list, bus=None, db=None, alarm_engine=None) -> str:
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

            key = f"id=0x{msg.arbitration_id:03X}"
            log("RX", f"{key} DLC={msg.dlc} DATA={text}")

            value = None
            if msg.data:
                value = float(msg.data[0])

            if db:
                db.insert_reading("can", key, value=value, text_value=text)

            if "TESTCAN" in text.upper():
                if send_message(bus, msg.arbitration_id, b"ACK"):
                    log("TX", f"{key} DATA=ACK")
                    if db:
                        db.insert_reading("can", f"{key}.ack", text_value="ACK")

            if alarm_engine:
                data = {"can": {key: text}}
                events = alarm_engine.evaluate(data)
                for e in events:
                    log(e["severity"].upper(), e["message"])
                    if db:
                        db.insert_alarm(e["name"], e["severity"], e["message"])

    finally:
        bus.shutdown()
        log("INFO", "CAN socket closed")

    return "shutdown" if not running else "reconnect"


def main() -> None:
    cfg = load_config()
    db_path = os.environ.get("NEXYHUB_DB_PATH") or cfg.logging_db_path
    can_iface = CAN_INTERFACE or cfg.can_interface

    db = None
    try:
        db = Database(db_path)
        log("INFO", f"DB logging to {db_path}")
    except Exception as e:
        log("WARN", f"DB init failed: {e}")

    alarm_engine = AlarmEngine()
    for a in cfg.alarms:
        try:
            rule = AlarmRule(**{k: v for k, v in a.items() if k in ["name", "source", "field", "min", "max", "hysteresis", "severity"]})
            alarm_engine.add_rule(rule)
        except Exception as e:
            log("WARN", f"Alarm rule '{a.get('name', '?')}' skipped: {e}")
    if alarm_engine.rules:
        log("INFO", f"Loaded {len(alarm_engine.rules)} alarm rules")
    else:
        log("INFO", "No alarm rules configured")

    log("INFO", "=== nexyhub-can monitor started ===")
    log("INFO", f"Interface: {can_iface}")
    log("INFO", f"Retry: {RETRY_SEC}s")
    log("INFO", f"PID: {os.getpid()}")

    filters = parse_filters(FILTER_IDS_STR)
    if filters:
        log("INFO", f"CAN filters: {len(filters)} rules")
    else:
        log("INFO", "No CAN filters — accepting all IDs")

    while running:
        log("INFO", f"Waiting for {can_iface}...")
        if not wait_for_interface(can_iface):
            if not running:
                break
            log("WARN", f"{can_iface} not found, retrying in {RETRY_SEC}s...")
            time.sleep(RETRY_SEC)
            continue

        log("INFO", f"{can_iface} available, starting loop")

        result = can_loop(can_iface, filters, db=db, alarm_engine=alarm_engine)

        if result == "shutdown":
            break

        log("INFO", f"Reconnecting in {RETRY_SEC}s...")
        time.sleep(RETRY_SEC)

    if db:
        db.close()
    log("INFO", "=== nexyhub-can monitor terminated ===")


if __name__ == "__main__":
    main()
