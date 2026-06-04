import os
import time
import signal

SERIAL_PORT = os.environ.get("MODBUS_PORT", "/dev/ttyLP2")
BAUDRATE = int(os.environ.get("MODBUS_BAUDRATE", "9600"))
TIMEOUT = float(os.environ.get("MODBUS_TIMEOUT", "1.0"))
SLAVE_ID = int(os.environ.get("MODBUS_SLAVE_ID", "1"))
REGISTER_ADDR = int(os.environ.get("MODBUS_REGISTER_ADDR", "0"))
REGISTER_COUNT = int(os.environ.get("MODBUS_REGISTER_COUNT", "1"))
POLL_SEC = int(os.environ.get("MODBUS_POLL_SEC", "10"))

running = True

try:
    import pymodbus
    from pymodbus.client import ModbusSerialClient
except ImportError:
    pymodbus = None


from nexyhub_logs import log as file_log


def log(level: str, msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)
    file_log("modbus", level, msg)


def signal_handler(sig, frame) -> None:
    global running
    log("INFO", f"Received signal {sig}, shutdown...")
    running = False


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


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


def main():
    log("INFO", "=== nexyhub-modbus started ===")
    log("INFO", f"Port: {SERIAL_PORT} @ {BAUDRATE} baud")
    log("INFO", f"Slave ID: {SLAVE_ID}, Register: {REGISTER_ADDR}, Count: {REGISTER_COUNT}")
    log("INFO", f"Poll: {POLL_SEC}s")
    log("INFO", f"PID: {os.getpid()}")

    if pymodbus is None:
        log("ERROR", "pymodbus not installed")
        return

    while running:
        log("INFO", f"Waiting for {SERIAL_PORT}...")
        if not wait_for_device(SERIAL_PORT):
            if not running:
                break
            log("WARN", f"{SERIAL_PORT} not found, retrying in 3s...")
            time.sleep(3)
            continue

        client = ModbusSerialClient(
            port=SERIAL_PORT,
            baudrate=BAUDRATE,
            timeout=TIMEOUT,
        )

        try:
            client.connect()
            log("INFO", f"Connected to {SERIAL_PORT}")
        except Exception as e:
            log("ERROR", f"Connection failed: {e}")
            time.sleep(3)
            continue

        try:
            while running:
                try:
                    result = client.read_holding_registers(REGISTER_ADDR, REGISTER_COUNT, slave=SLAVE_ID)
                    if result.isError():
                        log("ERROR", f"Modbus error: {result}")
                    else:
                        values = result.registers
                        log("INFO", f"Register {REGISTER_ADDR}: {values}")
                except Exception as e:
                    log("ERROR", f"Read failed: {e}")
                time.sleep(POLL_SEC)
        except OSError:
            pass
        finally:
            try:
                client.close()
                log("INFO", "Modbus connection closed")
            except Exception:
                pass

    log("INFO", "=== nexyhub-modbus terminated ===")


if __name__ == "__main__":
    main()
