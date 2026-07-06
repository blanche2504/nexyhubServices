import os
import time
import serial

from nexyhub_config.loader import load_config
from nexyhub_db.database import Database
from nexyhub_utils.daemon import log, running, setup_signals, init_alarms, wait_for_path

SERIAL_PORT = os.environ.get("SERIAL_PORT", "/dev/ttyLP6")
BAUDRATE = int(os.environ.get("BAUDRATE", "9600"))
PARITY = os.environ.get("PARITY", "N")
STOPBITS = int(os.environ.get("STOPBITS", "1"))
TIMEOUT = float(os.environ.get("SERIAL_TIMEOUT", "1.0"))

setup_signals()


def parity_to_pyserial(p: str):
    return {"N": serial.PARITY_NONE, "E": serial.PARITY_EVEN, "O": serial.PARITY_ODD}.get(p.upper(), serial.PARITY_NONE)


def stopbits_to_pyserial(s: int):
    return {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO}.get(s, serial.STOPBITS_ONE)


def serial_loop(ser: serial.Serial, db: Database | None = None, alarm_engine=None) -> None:
    while running:
        try:
            data = ser.readline()
            if not data:
                continue
            text = data.decode("utf-8", errors="ignore").strip("\x00").strip()
            log("serial", "RX", text)

            if db:
                db.insert_reading("serial", "rs232", text_value=text)

            if "TEST232" in text.upper():
                ser.write(b"ACK\n")
                log("serial", "TX", "ACK")
                if db:
                    db.insert_reading("serial", "rs232.ack", text_value="ACK")

            if alarm_engine:
                events = alarm_engine.evaluate({"serial": {"rs232": text}})
                for e in events:
                    log("serial", e["severity"].upper(), e["message"])
                    if db:
                        db.insert_alarm(e["name"], e["severity"], e["message"])

        except (serial.SerialException, OSError) as e:
            log("serial", "ERROR", f"Serial error: {e}")
            break


def main():
    cfg = load_config()
    db_path = os.environ.get("NEXYHUB_DB_PATH") or cfg.logging_db_path

    db = None
    try:
        db = Database(db_path, retention_days=cfg.logging_retention_days)
        log("serial", "INFO", f"DB logging to {db_path}")
    except Exception as e:
        log("serial", "WARN", f"DB init failed: {e}")

    alarm_engine = init_alarms(cfg)

    log("serial", "INFO", "=== nexyhub-serial monitor started ===")
    log("serial", "INFO", f"Port: {SERIAL_PORT} @ {BAUDRATE} baud")
    log("serial", "INFO", f"Parity: {PARITY}, Stopbits: {STOPBITS}, Timeout: {TIMEOUT}s")
    log("serial", "INFO", f"PID: {os.getpid()}")

    while running:
        log("serial", "INFO", f"Waiting for {SERIAL_PORT}...")
        if not wait_for_path(SERIAL_PORT):
            if not running:
                break
            log("serial", "WARN", f"{SERIAL_PORT} not found, retrying in 3s...")
            time.sleep(3)
            continue

        try:
            ser = serial.Serial(
                port=SERIAL_PORT,
                baudrate=BAUDRATE,
                parity=parity_to_pyserial(PARITY),
                stopbits=stopbits_to_pyserial(STOPBITS),
                timeout=TIMEOUT,
            )
            log("serial", "INFO", f"{SERIAL_PORT} opened")
        except serial.SerialException as e:
            log("serial", "ERROR", f"Can't open {SERIAL_PORT}: {e}")
            time.sleep(3)
            continue

        try:
            serial_loop(ser, db=db, alarm_engine=alarm_engine)
        except OSError:
            pass
        finally:
            try:
                ser.close()
                log("serial", "INFO", f"{SERIAL_PORT} closed")
            except Exception:
                pass

    if db:
        db.close()
    log("serial", "INFO", "=== nexyhub-serial monitor terminated ===")


if __name__ == "__main__":
    main()
