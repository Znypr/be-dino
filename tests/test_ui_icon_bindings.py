"""Keep owner-upload bindings strict as the illustrated catalog grows."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bind_ui_icons", ROOT / "tools/bind_ui_icons.py")
BINDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BINDER)


class UIIconBindingTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(BINDER.BINDINGS.read_text())

    def compile(self, data):
        with patch.object(BINDER.Path, "read_text", return_value=json.dumps(data)):
            return BINDER.compile_bindings()

    def test_all_twelve_keys_and_empty_binding_fallback(self):
        self.assertEqual(len(self.data["assets"]), 12)
        self.assertEqual(BINDER.compile_bindings(), BINDER.OUTPUT.read_text())
        for entry in self.data["assets"]:
            entry["robloxAssetId"] = None
        self.assertEqual(self.compile(self.data).count('= ""'), 12)

    def test_rejects_invalid_duplicate_and_missing_keys(self):
        for key in ("clear", "not-valid", "leap"):
            data = copy.deepcopy(self.data)
            data["assets"][0]["key"] = key
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.compile(data)
        self.data["assets"].pop()
        with self.assertRaises(ValueError):
            self.compile(self.data)

    def test_rejects_invalid_ids(self):
        for asset_id in ("0", "-1", "123abc", "rbxassetid://123", "12.3"):
            self.data["assets"][0]["robloxAssetId"] = asset_id
            with self.subTest(asset_id=asset_id), self.assertRaises(ValueError):
                self.compile(self.data)

    def test_new_masters_decode_and_match_manifests(self):
        import hashlib
        from PIL import Image

        for key in ("leap", "weather", "rain", "thunder", "blizzard"):
            entry = next(asset for asset in self.data["assets"] if asset["key"] == key)
            path = BINDER.BINDINGS.parent / entry["source"]
            manifest = json.loads(path.with_suffix(".manifest.json").read_text())
            with self.subTest(key=key):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), manifest["sha256"])
                with Image.open(path) as image:
                    image.load()
                    self.assertEqual(image.mode, "RGBA")
                    self.assertEqual(list(image.size), manifest["dimensions"])
                    self.assertEqual(image.getchannel("A").getextrema(), (0, 255))
