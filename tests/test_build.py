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
        # The current build/BeDino-Build<N>.rbxlx and manifest are generated (ignored, CI artifact).
        # If a local copy exists it must be fresh; otherwise only check the in-memory build is consistent.
        version = re.search(r'Build = "redesign-(\d+)"', (ROOT / "src/shared/Config.luau").read_text()).group(1)
        place = ROOT / f"build/BeDino-Build{version}.rbxlx"
        data, sources = packager.build()
        self.assertEqual(len(sources), len(list(ROOT.glob("src/**/*.luau"))))
        if place.exists():
            self.assertEqual(place.read_bytes(), data, "Local generated build is stale: run python tools/build.py")
            manifest = json.loads(place.with_suffix(".manifest.json").read_text())
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
        # BD-460 (docs/138): the BeDino_Meadow variant stays packaged with all its IDs but is NOT bound: the island uses the built-in Grass.
        self.assertIsNone(service.find("Properties/string[@name='GrassName']"))
        for base in ("Rock", "Wood"):
            self.assertEqual(service.find(f"Properties/string[@name='{base}Name']").text, "BeDino_" + {"Rock":"Stone", "Wood":"Bark"}[base])

    def test_visual_bindings_match_verified_manifest(self):
        spec = importlib.util.spec_from_file_location("visual_bindings", ROOT / "tools/bind_visual_assets.py")
        bindings = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bindings)
        for path, content in bindings.outputs().items():
            self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_lighting_technology_is_explicit_and_not_compatibility(self):
        # Unset/Compatibility makes Studio show the "Lighting Technology Migration" dialog on every open.
        root = ET.fromstring(packager.build()[0])
        lights = [n for n in root.iter("Item") if n.attrib["class"] == "Lighting"]
        self.assertEqual(len(lights), 1)
        tech = lights[0].find("Properties/token[@name='Technology']")
        self.assertIsNotNone(tech, "Lighting.Technology must be written explicitly")
        self.assertNotIn(tech.text, ("0", "Compatibility", "Legacy"))
        self.assertEqual(tech.text, "1", "Voxel")
        for path in ROOT.glob("src/**/*.luau"):
            self.assertNotRegex(path.read_text(encoding="utf-8"), r"Technology\s*=\s*Enum\.Technology\.(Compatibility|Legacy)", str(path))

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
