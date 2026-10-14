"""World kit MeshPart bindings: generated Luau matches the JSON, strict validation, null = native fallback."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bind_worldkit_meshes", ROOT / "tools/bind_worldkit_meshes.py")
BINDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BINDER)


class WorldKitMeshBindingTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(BINDER.BINDINGS.read_text())
        self.ids = [a["id"] for a in json.loads(BINDER.MANIFEST.read_text())["assets"]]

    def test_generated_file_is_current_and_covers_the_kit(self):
        self.assertEqual(BINDER.compile_bindings(), BINDER.OUTPUT.read_text())
        text = BINDER.OUTPUT.read_text()
        self.assertEqual(text.count("meshId ="), 41)
        self.assertIn("world_tree_dead_m", text)
        self.assertEqual(self.data["missing"], [])

    def test_every_id_is_bound_or_missing(self):
        data = copy.deepcopy(self.data)
        del data["meshes"]["food_egg_a"]
        with self.assertRaises(ValueError):
            BINDER.compile_bindings(data, self.ids)

    def test_rejects_unknown_ids_bad_urls_and_wrong_scale(self):
        data = copy.deepcopy(self.data)
        data["meshes"]["not_a_kit_id"] = data["meshes"]["food_egg_a"]
        with self.assertRaises(ValueError):
            BINDER.compile_bindings(data, self.ids)
        for key, value in (("meshId", "rbxassetid://0"), ("meshId", "123"), ("scale", 0.02)):
            data = copy.deepcopy(self.data)
            data["meshes"]["food_egg_a"][key] = value
            with self.assertRaises(ValueError, msg=(key, value)):
                BINDER.compile_bindings(data, self.ids)

    def test_runtime_loader_and_budget_wiring(self):
        loader = (ROOT / "src/server/ImportedResources.luau").read_text()
        self.assertIn("CreateMeshPartAsync", loader)
        self.assertIn("Color3.new(1,1,1)", loader)
        placement = (ROOT / "src/shared/BiomePlacement.luau").read_text()
        self.assertIn("PartBudget", placement)
        self.assertNotIn("TriangleBudget", placement)
        workflow = (ROOT / ".github/workflows/build-generated-place.yml").read_text()
        self.assertIn("bind_worldkit_meshes.py --check", workflow)
        self.assertIn("verify_world_art.py", workflow)


if __name__ == "__main__":
    unittest.main()
