import os
import time
import signal
import serial

SERIAL_PORT = os.environ.get("SERIAL_PORT", "/dev/ttyLP2")
BAUDRATE = int(os.environ.get("BAUDRATE", "9600"))
TIMEOUT = float(os.environ.get("SERIAL_TIMEOUT", "1.0"))
GPIO_CHIP = os.environ.get("GPIO_CHIP", "/dev/gpiochip1")
GPIO_DE_LINE = int(os.environ.get("GPIO_DE_LINE", "2"))

running = True

try:
    import gpiod
except ImportError:
    gpiod = None


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


def setup_gpio():
    if gpiod is None:
        log("WARN", "libgpiod non disponibile, DE control disabilitato")
        return None
    try:
        chip = gpiod.Chip(GPIO_CHIP)
        config = gpiod.LineSettings(
            direction=gpiod.line.Direction.OUTPUT,
            output_value=gpiod.line.Value.INACTIVE,
        )
        req = chip.request_lines(config={GPIO_DE_LINE: config}, consumer="rs485-de")
        log("INFO", f"GPIO DE su {GPIO_CHIP} linea {GPIO_DE_LINE}")
        return req
    except Exception as e:
        log("WARN", f"GPIO setup fallito: {e}")
        return None


def rs485_loop(ser, gpio_req=None) -> None:
    while running:
        try:
            data = ser.readline()
            if not data:
                continue
            text = data.decode("utf-8", errors="ignore").strip("\x00").strip()
            log("RX", text)

            if "TEST485" in text.upper():
                if gpio_req is not None and gpiod is not None:
                    gpio_req.set_value(GPIO_DE_LINE, gpiod.line.Value.ACTIVE)
                ser.write(b"ESEGUITO\n")
                ser.flush()
                time.sleep(10 / BAUDRATE)
                if gpio_req is not None and gpiod is not None:
                    gpio_req.set_value(GPIO_DE_LINE, gpiod.line.Value.INACTIVE)
                log("TX", "ESEGUITO")
        except (serial.SerialException, OSError) as e:
            log("ERROR", f"Errore seriale: {e}")
            break


def main():
    log("INFO", "=== nexyhub-rs485 monitor avviato ===")
    log("INFO", f"Porta: {SERIAL_PORT} @ {BAUDRATE} baud")
    log("INFO", f"GPIO: {GPIO_CHIP} linea {GPIO_DE_LINE}")
    log("INFO", f"PID: {os.getpid()}")

    while running:
        log("INFO", f"Attendo {SERIAL_PORT}...")
        if not wait_for_device(SERIAL_PORT):
            if not running:
                break
            log("WARN", f"{SERIAL_PORT} non trovata, riprovo tra 3s...")
            time.sleep(3)
            continue

        try:
            ser = serial.Serial(port=SERIAL_PORT, baudrate=BAUDRATE, timeout=TIMEOUT)
            log("INFO", f"{SERIAL_PORT} aperta")
        except serial.SerialException as e:
            log("ERROR", f"Impossibile aprire {SERIAL_PORT}: {e}")
            time.sleep(3)
            continue

        gpio_req = setup_gpio()

        try:
            rs485_loop(ser, gpio_req)
        except OSError:
            pass
        finally:
            try:
                ser.close()
                log("INFO", f"{SERIAL_PORT} chiusa")
            except Exception:
                pass

    log("INFO", "=== nexyhub-rs485 monitor terminato ===")


if __name__ == "__main__":
    main()
