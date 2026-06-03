import os
import time
import signal
import random

from nexyhub_ipc.shared_mem import atomic_write, SHARED_DIR

PRODUCER_KEY = os.environ.get("IPC_PRODUCER_KEY", "producer/data.json")
INTERVAL_SEC = int(os.environ.get("IPC_INTERVAL_SEC", "5"))

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


def generate_sample() -> dict:
    return {
        "timestamp": time.time(),
        "source": "producer",
        "readings": [
            {"sensor": "temperature", "value": round(random.uniform(20, 30), 1), "unit": "C"},
            {"sensor": "humidity", "value": round(random.uniform(40, 70), 1), "unit": "%"},
            {"sensor": "pressure", "value": round(random.uniform(980, 1020), 1), "unit": "hPa"},
        ],
    }


def main() -> None:
    log("INFO", "=== nexyhub-ipc producer started ===")
    log("INFO", f"Shared dir: {SHARED_DIR}")
    log("INFO", f"Key: {PRODUCER_KEY}")
    log("INFO", f"Interval: {INTERVAL_SEC}s")
    log("INFO", f"PID: {os.getpid()}")

    while running:
        data = generate_sample()
        try:
            atomic_write(PRODUCER_KEY, data)
            log("INFO", f"Wrote {len(json.dumps(data))} bytes to {PRODUCER_KEY}")
        except OSError as e:
            log("ERROR", f"Write failed: {e}")

        for _ in range(INTERVAL_SEC):
            if not running:
                break
            time.sleep(1)

    log("INFO", "=== nexyhub-ipc producer terminated ===")


if __name__ == "__main__":
    import json
    main()
