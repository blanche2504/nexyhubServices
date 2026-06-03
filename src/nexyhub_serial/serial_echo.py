import os
import time
import signal
import serial

SERIAL_PORT = os.environ.get("SERIAL_PORT", "/dev/ttyLP6")
BAUDRATE = int(os.environ.get("BAUDRATE", "9600"))
PARITY = os.environ.get("PARITY", "N")
STOPBITS = int(os.environ.get("STOPBITS", "1"))
TIMEOUT = float(os.environ.get("SERIAL_TIMEOUT", "1.0"))

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


def parity_to_pyserial(p: str):
    return {"N": serial.PARITY_NONE, "E": serial.PARITY_EVEN, "O": serial.PARITY_ODD}.get(p.upper(), serial.PARITY_NONE)


def stopbits_to_pyserial(s: int):
    return {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO}.get(s, serial.STOPBITS_ONE)


def wait_for_device(dev: str, timeout: int = 120) -> bool:
    start = time.time()
    while running:
        if os.path.exists(dev):
            log("INFO", f"Device {dev} found")
            return True
        elapsed = int(time.time() - start)
        if elapsed >= timeout:
            log("ERROR", f"{dev} not available after {timeout}s")
            return False
        if elapsed % 10 == 0 and elapsed > 0:
            log("WAIT", f"Waiting for {dev}... ({elapsed}s)")
        time.sleep(1)
    return False


def serial_loop(ser) -> None:
    while running:
        try:
            data = ser.readline()
            if not data:
                continue
            text = data.decode("utf-8", errors="ignore").strip("\x00").strip()
            log("RX", text)

            if "TEST232" in text.upper():
                ser.write(b"ESEGUITO\n")
                log("TX", "ESEGUITO")
        except (serial.SerialException, OSError) as e:
            log("ERROR", f"Serial error: {e}")
            break


def main():
    log("INFO", "=== nexyhub-serial monitor started ===")
    log("INFO", f"Port: {SERIAL_PORT} @ {BAUDRATE} baud")
    log("INFO", f"Parity: {PARITY}, Stopbits: {STOPBITS}, Timeout: {TIMEOUT}s")
    log("INFO", f"PID: {os.getpid()}")

    while running:
        log("INFO", f"Waiting for {SERIAL_PORT}...")
        if not wait_for_device(SERIAL_PORT):
            if not running:
                break
            log("WARN", f"{SERIAL_PORT} not found, retrying in 3s...")
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
            log("INFO", f"{SERIAL_PORT} opened")
        except serial.SerialException as e:
            log("ERROR", f"Can't open {SERIAL_PORT}: {e}")
            time.sleep(3)
            continue

        try:
            serial_loop(ser)
        except OSError:
            pass
        finally:
            try:
                ser.close()
                log("INFO", f"{SERIAL_PORT} closed")
            except Exception:
                pass

    log("INFO", "=== nexyhub-serial monitor terminated ===")


if __name__ == "__main__":
    main()
