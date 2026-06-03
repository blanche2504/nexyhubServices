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


def log(level: str, msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def signal_handler(sig, frame) -> None:
    global running
    log("INFO", f"Ricevuto segnale {sig}, shutdown...")
    running = False


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def wait_for_device(dev: str, timeout: int = 120) -> bool:
    start = time.time()
    while running:
        if os.path.exists(dev):
            log("INFO", f"Device {dev} trovato")
            return True
        elapsed = int(time.time() - start)
        if elapsed >= timeout:
            log("ERROR", f"{dev} non disponibile dopo {timeout}s")
            return False
        if elapsed % 10 == 0 and elapsed > 0:
            log("WAIT", f"Attendo {dev}... ({elapsed}s)")
        time.sleep(1)
    return False


def main():
    log("INFO", "=== nexyhub-modbus avviato ===")
    log("INFO", f"Porta: {SERIAL_PORT} @ {BAUDRATE} baud")
    log("INFO", f"Slave ID: {SLAVE_ID}, Register: {REGISTER_ADDR}, Count: {REGISTER_COUNT}")
    log("INFO", f"Poll: {POLL_SEC}s")
    log("INFO", f"PID: {os.getpid()}")

    if pymodbus is None:
        log("ERROR", "pymodbus non installato")
        return

    while running:
        log("INFO", f"Attendo {SERIAL_PORT}...")
        if not wait_for_device(SERIAL_PORT):
            if not running:
                break
            log("WARN", f"{SERIAL_PORT} non trovata, riprovo tra 3s...")
            time.sleep(3)
            continue

        client = ModbusSerialClient(
            port=SERIAL_PORT,
            baudrate=BAUDRATE,
            timeout=TIMEOUT,
        )

        try:
            client.connect()
            log("INFO", f"Connesso a {SERIAL_PORT}")
        except Exception as e:
            log("ERROR", f"Connessione fallita: {e}")
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
                    log("ERROR", f"Lettura fallita: {e}")
                time.sleep(POLL_SEC)
        except OSError:
            pass
        finally:
            try:
                client.close()
                log("INFO", "Connessione Modbus chiusa")
            except Exception:
                pass

    log("INFO", "=== nexyhub-modbus terminato ===")


if __name__ == "__main__":
    main()
