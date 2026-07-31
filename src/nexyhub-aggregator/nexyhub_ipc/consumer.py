import os
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from nexyhub_ipc.shared_mem import atomic_read, list_keys, SHARED_DIR
from nexyhub_utils.daemon import log, running, setup_signals

CONSUMER_PORT = int(os.environ.get("IPC_CONSUMER_PORT", "8000"))

setup_signals()


class IPCRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log("http", "HTTP", f"{self.client_address[0]} - {fmt % args}")

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
    log("ipc", "INFO", "=== nexyhub-ipc consumer started ===")
    log("ipc", "INFO", f"Shared dir: {SHARED_DIR}")
    log("ipc", "INFO", f"Listening on port {CONSUMER_PORT}")
    log("ipc", "INFO", f"PID: {os.getpid()}")

    server = create_server()
    log("ipc", "INFO", f"HTTP server ready on http://0.0.0.0:{CONSUMER_PORT}/")

    try:
        while running:
            server.timeout = 1.0
            server.handle_request()
    except Exception as e:
        if running:
            log("ipc", "ERROR", f"Server error: {e}")
    finally:
        server.server_close()
        log("ipc", "INFO", "=== nexyhub-ipc consumer terminated ===")


if __name__ == "__main__":
    main()
