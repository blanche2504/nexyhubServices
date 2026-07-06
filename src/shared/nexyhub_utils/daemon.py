import os
import time
import signal
from typing import Callable

from nexyhub_alarms.engine import AlarmEngine
from nexyhub_alarms.rules import AlarmRule
from nexyhub_logs import log as file_log


def log(service: str, level: str, msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)
    file_log(service, level, msg)


running = True


def _signal_handler(sig, frame) -> None:
    global running
    log("daemon", "INFO", f"Received signal {sig}, shutdown...")
    running = False


def setup_signals():
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)


def wait_for_path(path: str, timeout: int = 120, label: str = "") -> bool:
    global running
    start = time.time()
    label = label or path
    while running:
        if os.path.exists(path):
            log("daemon", "INFO", f"{label} found")
            return True
        elapsed = int(time.time() - start)
        if elapsed >= timeout:
            log("daemon", "ERROR", f"{label} not available after {timeout}s")
            return False
        if elapsed % 10 == 0 and elapsed > 0:
            log("daemon", "WAIT", f"Waiting for {label}... ({elapsed}s)")
        time.sleep(1)
    return False


def init_alarms(cfg) -> AlarmEngine:
    engine = AlarmEngine()
    for a in cfg.alarms:
        try:
            rule = AlarmRule(**{k: v for k, v in a.items() if k in ["name", "source", "field", "min", "max", "hysteresis", "severity"]})
            engine.add_rule(rule)
        except Exception as e:
            log("daemon", "WARN", f"Alarm rule '{a.get('name', '?')}' skipped: {e}")
    if engine.rules:
        log("daemon", "INFO", f"Loaded {len(engine.rules)} alarm rules")
    else:
        log("daemon", "INFO", "No alarm rules configured")
    return engine
