"""BD-1289: the ChatGPT image relay saves posted pictures under a safe name and serves its page."""
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import chatgpt_image_relay as relay  # noqa: E402


class RelayTests(unittest.TestCase):
    def test_safe_name(self):
        self.assertEqual(relay.safe_name("card-art.png"), "card-art.png")
        self.assertIsNone(relay.safe_name("../evil.png"))
        self.assertIsNone(relay.safe_name("noext"))

    def test_snippet_mentions_name(self):
        self.assertIn('"x.png"', relay.SNIPPET % '"x.png"')

    def test_post_saves_file_and_get_serves_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = {"left": 1, "ok": False}
            srv = HTTPServer(("127.0.0.1", 0), relay.make_handler(state, out))
            port = srv.server_address[1]
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            page = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5).read()
            self.assertIn(b"beDinoRelay", page)
            req = urllib.request.Request(f"http://127.0.0.1:{port}/save?name=a.png", data=b"\x89PNGdata", method="POST")
            self.assertEqual(urllib.request.urlopen(req, timeout=5).status, 200)
            t.join(timeout=5)
            self.assertEqual((out / "a.png").read_bytes(), b"\x89PNGdata")
            self.assertTrue(state["ok"])


if __name__ == "__main__":
    unittest.main()
