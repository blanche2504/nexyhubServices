import os
import time

SHARED_DIR = os.environ.get("NEXYHUB_SHARED_DIR", "/mnt/shared")
LOG_DIR = os.path.join(SHARED_DIR, "logs")


def log(service: str, level: str, msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}\n"
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        path = os.path.join(LOG_DIR, f"{service}.log")
        with open(path, "a") as f:
            f.write(line)
    except Exception:
        pass
