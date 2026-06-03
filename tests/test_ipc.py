import os
import sys
import json
import time
import shutil
import unittest
import tempfile
import threading
from pathlib import Path
from http.client import HTTPConnection
from http.server import HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestSharedMem(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        import nexyhub_ipc.shared_mem as mod
        mod.SHARED_DIR = self.tmp

    def tearDown(self):
        import nexyhub_ipc.shared_mem as mod
        mod.SHARED_DIR = Path("/mnt/shared")
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_atomic_write_and_read(self):
        from nexyhub_ipc.shared_mem import atomic_write, atomic_read
        data = {"hello": "world", "num": 42}
        atomic_write("test.json", data)
        result = atomic_read("test.json")
        self.assertEqual(result, data)

    def test_atomic_write_with_subdir(self):
        from nexyhub_ipc.shared_mem import atomic_write, atomic_read
        data = {"nested": True}
        atomic_write("sub/dir/data.json", data)
        result = atomic_read("sub/dir/data.json")
        self.assertEqual(result, data)

    def test_read_missing(self):
        from nexyhub_ipc.shared_mem import atomic_read
        self.assertIsNone(atomic_read("nonexistent.json"))

    def test_read_corrupted(self):
        from nexyhub_ipc.shared_mem import atomic_read
        dest = self.tmp / "bad.json"
        dest.write_text("not json", encoding="utf-8")
        with self.assertRaises(ValueError):
            atomic_read("bad.json")

    def test_list_keys(self):
        from nexyhub_ipc.shared_mem import atomic_write, list_keys
        atomic_write("a.json", {"x": 1})
        atomic_write("b.json", {"y": 2})
        keys = list_keys()
        self.assertEqual(keys, ["a.json", "b.json"])

    def test_list_keys_empty(self):
        from nexyhub_ipc.shared_mem import list_keys
        self.assertEqual(list_keys(), [])


class TestConsumerHTTP(unittest.TestCase):
    PORT = 18990

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        import nexyhub_ipc.shared_mem as mod
        mod.SHARED_DIR = cls.tmp
        from nexyhub_ipc.shared_mem import atomic_write
        atomic_write("sensor.json", {"temp": 25.0})
        atomic_write("status.json", {"online": True})

        from nexyhub_ipc.consumer import create_server
        cls.server = create_server(cls.PORT)

        cls._server_thread = threading.Thread(
            target=cls.server.serve_forever,
            daemon=True,
        )
        cls._server_thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls._server_thread.join(timeout=2)
        import nexyhub_ipc.shared_mem as mod
        mod.SHARED_DIR = Path("/mnt/shared")
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _get(self, path: str) -> tuple[int, dict]:
        conn = HTTPConnection("127.0.0.1", self.PORT, timeout=3)
        try:
            conn.request("GET", path)
            resp = conn.getresponse()
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, body
        finally:
            conn.close()

    def test_root(self):
        status, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("keys", body)

    def test_read_existing_key(self):
        status, body = self._get("/data/sensor.json")
        self.assertEqual(status, 200)
        self.assertEqual(body["temp"], 25.0)

    def test_read_missing_key(self):
        status, body = self._get("/data/nonexistent.json")
        self.assertEqual(status, 404)

    def test_status(self):
        status, body = self._get("/status")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertIn("files", body)

    def test_unknown_route(self):
        status, body = self._get("/unknown")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
