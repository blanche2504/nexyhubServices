import os
import time
import signal
import errno
import socket

from nexyhub_can.can_types import (
    CAN_ERR_BUSOFF, CAN_ERR_RESTARTED,
    parse_frame, describe_error_flags,
)
from nexyhub_can.filters import parse_filters
from nexyhub_can.socketcan import create_socket, send_frame, recv_frame

CAN_INTERFACE = os.environ.get("CAN_INTERFACE", "can0")
RETRY_SEC = int(os.environ.get("CAN_RETRY_SEC", "3"))
FILTER_IDS_STR = os.environ.get("CAN_FILTER_IDS", "")

running = True


def log(level: str, msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def signal_handler(sig, frame) -> None:
    global running
    log("INFO", f"Ricevuto segnale {sig}, shutdown...")
    running = False


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def wait_for_interface(ifname: str, timeout: int = 120) -> bool:
    start = time.time()
    while running:
        try:
            s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
            s.bind((ifname,))
            s.close()
            return True
        except OSError as e:
            if e.errno == errno.ENODEV:
                elapsed = int(time.time() - start)
                if elapsed >= timeout:
                    log("ERROR", f"{ifname} non disponibile dopo {timeout}s")
                    return False
                if elapsed % 10 == 0 and elapsed > 0:
                    log("WAIT", f"Attendo {ifname}... ({elapsed}s)")
                time.sleep(1)
            elif e.errno == errno.ENETDOWN:
                log("WAIT", f"{ifname} presente ma DOWN, attendo UP...")
                time.sleep(1)
            else:
                log("ERROR", f"Errore verifica {ifname}: {e}")
                time.sleep(RETRY_SEC)
        except Exception as e:
            log("ERROR", f"Errore inatteso verifica interfaccia: {e}")
            time.sleep(RETRY_SEC)
    return False


def can_loop(ifname: str, filters: list, sock=None) -> str:
    sock = sock or create_socket(ifname, filters)
    bus_off_count = 0

    try:
        while running:
            data = recv_frame(sock)
            if data is None:
                continue

            frame = parse_frame(data)

            if frame["is_error"]:
                desc = describe_error_flags(frame["error_flags"])
                if frame["error_flags"] & CAN_ERR_BUSOFF:
                    bus_off_count += 1
                    log("WARN", f"BUS-OFF rilevato (#{bus_off_count})")
                elif frame["error_flags"] & CAN_ERR_RESTARTED:
                    log("INFO", "CAN controller RESTARTED")
                    bus_off_count = 0
                else:
                    log("WARN", f"Error frame: {desc}")
                continue

            if frame["is_rtr"]:
                log("RX", f"RTR ID=0x{frame['id']:03X}")
                continue

            try:
                text = frame["data"].decode("utf-8", errors="ignore").strip("\x00").strip()
            except Exception:
                text = frame["data"].hex()

            log("RX", f"ID=0x{frame['id']:03X} DLC={frame['dlc']} DATA={text}")

            if "TESTCAN" in text.upper():
                if send_frame(sock, frame["id"], b"ESEGUITO"):
                    log("TX", f"ID=0x{frame['id']:03X} DATA=ESEGUITO")

    finally:
        sock.close()
        log("INFO", "Socket CAN chiuso")

    return "shutdown" if not running else "reconnect"


def main() -> None:
    log("INFO", "=== nexyhub-can monitor avviato ===")
    log("INFO", f"Interfaccia: {CAN_INTERFACE}")
    log("INFO", f"Retry: {RETRY_SEC}s")
    log("INFO", f"PID: {os.getpid()}")

    filters = parse_filters(FILTER_IDS_STR)
    if filters:
        log("INFO", f"Filtri attivi: {len(filters)} regole")
    else:
        log("INFO", "Nessun filtro — accetto tutti gli ID")

    while running:
        log("INFO", f"Attendo {CAN_INTERFACE}...")
        if not wait_for_interface(CAN_INTERFACE):
            if not running:
                break
            log("WARN", f"{CAN_INTERFACE} non trovata, riprovo tra {RETRY_SEC}s...")
            time.sleep(RETRY_SEC)
            continue

        log("INFO", f"{CAN_INTERFACE} disponibile, avvio loop")

        result = can_loop(CAN_INTERFACE, filters)

        if result == "shutdown":
            break

        log("INFO", f"Riconnessione tra {RETRY_SEC}s...")
        time.sleep(RETRY_SEC)

    log("INFO", "=== nexyhub-can monitor terminato ===")


if __name__ == "__main__":
    main()
