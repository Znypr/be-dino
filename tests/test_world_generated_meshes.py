"""BD-206/207: the Roblox-generated world mesh id table is well formed and fully mapped."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src/shared/WorldGeneratedMeshes.luau").read_text()
KIT = (ROOT / "src/shared/WorldKitData.luau").read_text()
REGISTRY = (ROOT / "docs/77-asset-registry.md").read_text()
END = chr(10) + "}" + chr(10)
ASSETS_BLOCK = SRC.split("Generated.Assets = {")[1].split(END)[0]
REPLACEMENTS_BLOCK = SRC.split("Generated.Replacements = {")[1].split(END)[0]
EXPECTED = {
    "137262237243889", "123860208068220", "115520379209668", "132703556702568", "100306166052872", "71416776916365",
    "135107793396569", "101039067942415", "122546672856917", "84690157197711", "118262268018795", "125187345067740",
    "70576143860722", "71496347169753", "80664439797104", "102765517629578", "82545380144820",
}
BARE = ["world_boulder_bare_s", "world_boulder_bare_m", "world_boulder_bare_l"]
BARE_KINDS = {"rock_crystal", "rock_lava", "rock_pebbles", "rock_sand_cliff", "rock_mossy_boulder"}


class WorldGeneratedMeshTests(unittest.TestCase):
    def setUp(self):
        self.assets = dict(re.findall(r'^\s{4}(\w+) = \{assetId = "(\d+)"', SRC, re.M))
        self.placed = {k for k, placed in re.findall(r'^\s{4}(\w+) = \{assetId = "\d+", placed = (true|false)', SRC, re.M) if placed == "true"}
        table = SRC.split("local TREES = {")[1].split("\n}\n")[0]
        self.kitmap = dict(re.findall(r'(world_\w+) = "(\w+)"', table))

    def test_ids_are_numeric_unique_and_exactly_the_published_set(self):
        self.assertEqual(len(self.assets), 17)
        self.assertEqual(len(set(self.assets.values())), 17, "duplicated asset id")
        self.assertEqual(set(self.assets.values()), EXPECTED)
        self.assertEqual(len(re.findall(r'assetId = "', ASSETS_BLOCK)), 17)
        for value in self.assets.values():
            self.assertRegex(value, r"^[1-9][0-9]{8,17}$")

    def test_every_placed_kind_is_mapped_to_a_kit_id(self):
        used = set(self.kitmap.values()) | BARE_KINDS
        for key in self.placed:
            self.assertIn(key, used, f"{key} is not mapped to any kit id")
        for key in used:
            self.assertIn(key, self.assets, f"{key} mapped but has no asset id")
        for kit_id in list(self.kitmap) + BARE:
            self.assertIn(f"{kit_id}=", KIT, f"unknown kit id {kit_id}")
        for kind in BARE_KINDS:
            self.assertIn(f'"{kind}"', SRC.split("function Generated.visualFor")[1])

    def test_unplaced_kinds_are_the_food_and_nest_ones(self):
        self.assertEqual(set(self.assets) - self.placed, {"food_drumstick", "food_egg", "nest"})

    def test_every_id_has_an_asset_registry_line(self):
        for key, asset_id in self.assets.items():
            self.assertIn(asset_id, REGISTRY, f"{key} missing in docs/77")

    def test_v3_tree_replacements_are_wired_with_a_safe_fallback(self):
        """BD-462: three owner-approved V3 trees; empty ids (not uploaded) must change nothing; a filled id must be numeric."""
        entries = re.findall(r'^\s{4}(\w+) = \{assetId = "(\d*)", placed = true, replaces = "(\w+)"\}', REPLACEMENTS_BLOCK, re.M)
        self.assertEqual({k: r for k, _, r in entries}, {"tree_broadleaf_v3": "tree_broadleaf", "tree_pine_v3": "tree_pine", "tree_palm_v3": "tree_palm"})
        for key, asset_id, replaces in entries:
            self.assertIn(replaces, self.assets, f"{key} replaces an unknown key")
            self.assertIn(replaces, self.placed)
            if asset_id:
                self.assertRegex(asset_id, r"^[1-9][0-9]{8,17}$")
                self.assertNotIn(asset_id, self.assets.values(), "V3 id duplicates a current generated id")
        self.assertIn("info.assetId ~= \"\"", SRC, "replacementFor must ignore empty ids")
        arena = (ROOT / "src/server/Arena.luau").read_text()
        self.assertIn("Generated.replacementFor(key)", arena)
        self.assertIn("if not template and key and folder then template = folder:FindFirstChild(key) end", arena)
        loader = (ROOT / "src/server/ImportedResources.luau").read_text()
        self.assertIn('if asset.assetId~="" then table.insert(entries', loader, "loader must skip empty replacement ids")
        for fbx in ("world_tree_broad_v3", "world_tree_pine_v3", "world_tree_palm_v3"):
            self.assertTrue((ROOT / f"assets/blender/world/fbx_v3/{fbx}.fbx").exists())
            self.assertIn(fbx, REGISTRY)

    def test_fallback_and_flag_are_wired(self):
        arena = (ROOT / "src/server/Arena.luau").read_text()
        self.assertIn('generatedProp(id, biome or "meadow", roll or .5) or Resources.clone(id)', arena)
        self.assertIn("Config.WorldGeneratedMeshes", arena)
        self.assertIn("WorldGeneratedMeshes = true", (ROOT / "src/shared/Config.luau").read_text())


if __name__ == "__main__":
    unittest.main()
