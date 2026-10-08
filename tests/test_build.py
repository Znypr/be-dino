import importlib.util
import json
import hashlib
import re
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("packager", ROOT / "tools/build.py")
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class BuildTests(unittest.TestCase):
    def test_deterministic_and_exact_source_roundtrip(self):
        data, sources = packager.build()
        self.assertEqual(data, packager.build()[0])
        root = ET.fromstring(data)
        actual = [node.text for node in root.findall(".//ProtectedString[@name='Source']")]
        expected = [p.read_text(encoding="utf-8") for p in ROOT.glob("src/**/*.luau")]
        self.assertCountEqual(actual, expected)
        self.assertEqual(len(sources), len(expected))
        refs = [node.attrib["referent"] for node in root.iter("Item")]
        self.assertEqual(len(refs), len(set(refs)))

    def test_current_delivery_matches_source_and_manifest(self):
        version = re.search(r'Build = "redesign-(\d+)"', (ROOT / "src/shared/Config.luau").read_text()).group(1)
        place = ROOT / f"build/BeDino-Build{version}.rbxlx"
        manifest = json.loads(place.with_suffix(".manifest.json").read_text())
        data, sources = packager.build()
        self.assertEqual(place.read_bytes(), data, "Rebuild the current delivery after source changes")
        self.assertEqual(manifest["place_sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(manifest["sources"], sources)

    def test_script_execution_locations(self):
        root = ET.fromstring(packager.build()[0])
        def lookup(parent, name):
            return next(n for n in parent.findall("Item") if n.find("Properties/string[@name='Name']").text == name)
        server = lookup(lookup(lookup(root, "ServerScriptService"), "Server"), "Bootstrap")
        client = lookup(lookup(lookup(lookup(root, "StarterPlayer"), "StarterPlayerScripts"), "Client"), "Bootstrap")
        shared = lookup(lookup(lookup(root, "ReplicatedStorage"), "Shared"), "Config")
        self.assertEqual(server.attrib["class"], "Script")
        self.assertEqual(client.attrib["class"], "LocalScript")
        self.assertEqual(shared.attrib["class"], "ModuleScript")

    def test_authored_world_materials_are_packaged(self):
        root = ET.fromstring(packager.build()[0])
        service = next(n for n in root.findall("Item") if n.attrib["class"] == "MaterialService")
        variants = service.findall("Item")
        self.assertEqual(len(variants), 3)
        for variant in variants:
            self.assertEqual(variant.attrib["class"], "MaterialVariant")
            for key in ("ColorMap", "NormalMap", "RoughnessMap", "MetalnessMap"):
                self.assertRegex(variant.find(f"Properties/Content[@name='{key}']/url").text, r"^rbxassetid://[0-9]+$")
        for base in ("Grass", "Rock", "Wood"):
            self.assertEqual(service.find(f"Properties/string[@name='{base}Name']").text, "BeDino_" + {"Grass":"Meadow", "Rock":"Stone", "Wood":"Bark"}[base])

    def test_visual_bindings_match_verified_manifest(self):
        spec = importlib.util.spec_from_file_location("visual_bindings", ROOT / "tools/bind_visual_assets.py")
        bindings = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bindings)
        for path, content in bindings.outputs().items():
            self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_unsupported_property_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "default.project.json"
            path.write_text(json.dumps({"name": "test", "tree": {"$className": "DataModel",
                "Workspace": {"$className": "Workspace", "$properties": {"Gravity": 10}}}}))
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                packager.build(path)

    def test_missing_sources_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "default.project.json"
            path.write_text(json.dumps({"name": "test", "tree": {"$className": "DataModel",
                "Code": {"$path": "missing"}}}))
            with self.assertRaisesRegex(ValueError, "Missing source"):
                packager.build(path)

    def test_xml_special_characters_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "src").mkdir()
            source = '-- A < B & C > D\nreturn "]]>"\n'
            (folder / "src/Example.luau").write_text(source, encoding="utf-8")
            path = folder / "default.project.json"
            path.write_text(json.dumps({"name": "test", "tree": {"$className": "DataModel",
                "Code": {"$path": "src"}}}))
            xml = ET.fromstring(packager.build(path)[0])
            self.assertEqual(xml.find(".//ProtectedString").text, source)


if __name__ == "__main__":
    unittest.main()
