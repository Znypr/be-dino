import hashlib
import json
from pathlib import Path
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / 'resources/monetization/product-icons'


class ProductIconTests(unittest.TestCase):
    def test_completed_masters_match_manifest(self):
        manifest = json.loads((ICONS / 'manifest.json').read_text())
        self.assertEqual([a['crystals'] for a in manifest['assets']], [500, 1500, 4000, 10000, 25000])
        for asset in manifest['assets']:
            path = ICONS / asset['file']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset['sha256'])
            self.assertTrue(asset['prompt'])
            with Image.open(path) as image:
                self.assertEqual(image.size, tuple(manifest['dimensions']))
                self.assertEqual(image.mode, 'RGBA')
                self.assertEqual(image.getchannel('A').getextrema(), (0, 255))

    def test_no_upload_claim_or_missing_sixth_delivery(self):
        manifest = json.loads((ICONS / 'manifest.json').read_text())
        self.assertFalse(manifest['uploadedToRoblox'])
        fallback = manifest['largestPackFallback']
        self.assertEqual(fallback['crystals'], 90000)
        self.assertTrue((ICONS / fallback['file']).is_file())
