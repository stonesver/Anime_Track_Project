import json
import socket
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tools.visual_validation.server import SAMPLE_RECORD, build_server


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class VisualValidationServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = free_port()
        cls.server = build_server("127.0.0.1", cls.port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def get_json(self, path: str) -> dict:
        with urlopen(self.url(path), timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_json(self, path: str, payload: dict) -> dict:
        request = Request(
            self.url(path),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_health_endpoint(self):
        self.assertEqual(self.get_json("/api/health"), {"ok": True, "service": "visual_validation"})

    def test_static_index_served(self):
        with urlopen(self.url("/"), timeout=5) as response:
            body = response.read().decode("utf-8")
        self.assertIn("Anime Track 功能验证台", body)

    def test_normalize_anime_endpoint(self):
        result = self.post_json("/api/anime/normalize", SAMPLE_RECORD)
        self.assertTrue(result["ok"])
        self.assertEqual(result["operation"], "normalize_anime")
        self.assertEqual(result["data"]["title_cn"], "示例动画")

    def test_unknown_endpoint_returns_404_json(self):
        with self.assertRaises(HTTPError) as ctx:
            self.get_json("/api/missing")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
