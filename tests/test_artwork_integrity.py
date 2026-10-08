"""Catch incomplete binary transfers of generated artwork saved to GitHub."""
from pathlib import Path
import hashlib
import json
import unittest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class ArtworkIntegrityTests(unittest.TestCase):
    def test_generated_sources_fully_decode_and_match_recorded_hashes(self):
        record = json.loads((ROOT / "resources/ui/v2/layers/file-integrity.json").read_text())
        self.assertEqual(len(record["files"]), 11)
        for asset in record["files"]:
            path = ROOT / asset["source"]
            with self.subTest(source=asset["source"]):
                self.assertEqual(path.stat().st_size, asset["bytes"])
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset["sha256"])
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    image.load()
                    self.assertEqual(image.mode, "RGBA")
                    self.assertEqual(list(image.size), asset["size"])
                    self.assertEqual(image.getchannel("A").getextrema(), (0, 255))
                    if "ring" in path.name:
                        self.assertEqual(image.getpixel((image.width // 2, image.height // 2))[3], 0)


if __name__ == "__main__":
    unittest.main()
