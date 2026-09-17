import importlib.util
import json
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
