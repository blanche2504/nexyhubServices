import os
import time
import serial

from nexyhub_config.loader import load_config
from nexyhub_db.database import Database
from nexyhub_utils.daemon import log, running, setup_signals, init_alarms, wait_for_path

SERIAL_PORT = os.environ.get("SERIAL_PORT", "/dev/ttyLP2")
BAUDRATE = int(os.environ.get("BAUDRATE", "9600"))
TIMEOUT = float(os.environ.get("SERIAL_TIMEOUT", "1.0"))
GPIO_CHIP = os.environ.get("GPIO_CHIP", "/dev/gpiochip1")
GPIO_DE_LINE = int(os.environ.get("GPIO_DE_LINE", "2"))

setup_signals()

try:
    import gpiod
except ImportError:
    gpiod = None


def setup_gpio():
    if gpiod is None:
        log("rs485", "WARN", "libgpiod not available, DE control disabled")
        return None
    try:
        chip = gpiod.Chip(GPIO_CHIP)
        config = gpiod.LineSettings(
            direction=gpiod.line.Direction.OUTPUT,
            output_value=gpiod.line.Value.INACTIVE,
        )
        req = chip.request_lines(config={GPIO_DE_LINE: config}, consumer="rs485-de")
        log("rs485", "INFO", f"GPIO DE on {GPIO_CHIP} line {GPIO_DE_LINE}")
        return req
    except Exception as e:
        log("rs485", "WARN", f"GPIO setup failed: {e}")
        return None


def rs485_loop(ser: serial.Serial, gpio_req=None, db: Database | None = None, alarm_engine=None) -> None:
    while running:
        try:
            data = ser.readline()
            if not data:
                continue
            text = data.decode("utf-8", errors="ignore").strip("\x00").strip()
            log("rs485", "RX", text)

            if db:
                db.insert_reading("serial", "rs485", text_value=text)

            if "TEST485" in text.upper():
                if gpio_req is not None and gpiod is not None:
                    gpio_req.set_value(GPIO_DE_LINE, gpiod.line.Value.ACTIVE)
                ser.write(b"ACK\n")
                ser.flush()
                time.sleep(10 / BAUDRATE)
                if gpio_req is not None and gpiod is not None:
                    gpio_req.set_value(GPIO_DE_LINE, gpiod.line.Value.INACTIVE)
                log("rs485", "TX", "ACK")
                if db:
                    db.insert_reading("serial", "rs485.ack", text_value="ACK")

            if alarm_engine:
                events = alarm_engine.evaluate({"serial": {"rs485": text}})
                for e in events:
                    log("rs485", e["severity"].upper(), e["message"])
                    if db:
                        db.insert_alarm(e["name"], e["severity"], e["message"])

        except (serial.SerialException, OSError) as e:
            log("rs485", "ERROR", f"Serial error: {e}")
            break


def main():
    cfg = load_config()
    db_path = cfg.logging_db_path

    db = None
    try:
        db = Database(db_path, retention_days=cfg.logging_retention_days)
        log("rs485", "INFO", f"DB logging to {db_path}")
    except Exception as e:
        log("rs485", "WARN", f"DB init failed: {e}")

    alarm_engine = init_alarms(cfg)

    log("rs485", "INFO", "=== nexyhub-rs485 monitor started ===")
    log("rs485", "INFO", f"Port: {SERIAL_PORT} @ {BAUDRATE} baud")
    log("rs485", "INFO", f"GPIO: {GPIO_CHIP} line {GPIO_DE_LINE}")
    log("rs485", "INFO", f"PID: {os.getpid()}")

    while running:
        log("rs485", "INFO", f"Waiting for {SERIAL_PORT}...")
        if not wait_for_path(SERIAL_PORT):
            if not running:
                break
            log("rs485", "WARN", f"{SERIAL_PORT} not found, retrying in 3s...")
            time.sleep(3)
            continue

        try:
            ser = serial.Serial(port=SERIAL_PORT, baudrate=BAUDRATE, timeout=TIMEOUT)
            log("rs485", "INFO", f"{SERIAL_PORT} opened")
        except serial.SerialException as e:
            log("rs485", "ERROR", f"Can't open {SERIAL_PORT}: {e}")
            time.sleep(3)
            continue

        gpio_req = setup_gpio()

        try:
            rs485_loop(ser, gpio_req, db=db, alarm_engine=alarm_engine)
        except OSError:
            pass
        finally:
            try:
                ser.close()
                log("rs485", "INFO", f"{SERIAL_PORT} closed")
            except Exception:
                pass

    if db:
        db.close()
    log("rs485", "INFO", "=== nexyhub-rs485 monitor terminated ===")


if __name__ == "__main__":
    main()
