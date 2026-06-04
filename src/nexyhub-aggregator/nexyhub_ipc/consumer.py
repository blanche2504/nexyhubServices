import os
import json
import time
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from nexyhub_ipc.shared_mem import atomic_read, list_keys, SHARED_DIR

CONSUMER_PORT = int(os.environ.get("IPC_CONSUMER_PORT", "8000"))

running = True


def log(level: str, msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def setup_signals():
    try:
        signal.signal(signal.SIGTERM, _handler)
        signal.signal(signal.SIGINT, _handler)
    except ValueError:
        pass


def _handler(sig, frame):
    global running
    log("INFO", f"Received signal {sig}, shutdown...")
    running = False


class IPCRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log("HTTP", f"{self.client_address[0]} - {fmt % args}")

    def _send_json(self, data: object, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/":
            keys = list_keys()
            self._send_json({"keys": keys, "shared_dir": str(SHARED_DIR)})

        elif path.startswith("/data/"):
            key = path[len("/data/"):]
            data = atomic_read(key)
            if data is not None:
                self._send_json(data)
            else:
                self._send_json({"error": f"Key '{key}' not found"}, 404)

        elif path == "/status":
            keys = list_keys()
            self._send_json({
                "status": "ok",
                "uptime": round(time.time() - start_time, 1),
                "shared_dir": str(SHARED_DIR),
                "file_count": len(keys),
                "files": keys,
            })

        else:
            self._send_json({"error": "Not found"}, 404)


start_time = time.time()


def create_server(port: int | None = None) -> HTTPServer:
    return HTTPServer(("0.0.0.0", port or CONSUMER_PORT), IPCRequestHandler)


def main() -> None:
    setup_signals()
    log("INFO", "=== nexyhub-ipc consumer started ===")
    log("INFO", f"Shared dir: {SHARED_DIR}")
    log("INFO", f"Listening on port {CONSUMER_PORT}")
    log("INFO", f"PID: {os.getpid()}")

    server = create_server()
    log("INFO", f"HTTP server ready on http://0.0.0.0:{CONSUMER_PORT}/")

    try:
        while running:
            server.timeout = 1.0
            server.handle_request()
    except Exception as e:
        if running:
            log("ERROR", f"Server error: {e}")
    finally:
        server.server_close()
        log("INFO", "=== nexyhub-ipc consumer terminated ===")


if __name__ == "__main__":
    main()
