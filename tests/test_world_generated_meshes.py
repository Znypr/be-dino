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
PROPS_BLOCK = SRC.split("Generated.Props = {")[1].split(END)[0]
COLOSSAL_BLOCK = SRC.split("Generated.Colossal = {")[1].split(END)[0]
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

    PROP_ENTRY = r'^\s{4}(\w+) = \{assetId = "(\d*)", placed = (true|false), tris = (\d+), size = \{([\d., ]+)\}\}'

    def prop_entries(self, prefix):
        return [e for e in re.findall(self.PROP_ENTRY, PROPS_BLOCK, re.M) if e[0].startswith(prefix)]

    def check_prop_entries(self, entries, step):
        slots = (ROOT / "tools/asset_slots.json").read_text()
        for key, asset_id, placed, tris, size in entries:
            self.assertEqual(placed, "true", f"{key}: placed = true means a placement rule reads it once the id is filled ({step} step 2)")
            if asset_id:
                self.assertRegex(asset_id, r"^[1-9][0-9]{8,17}$")
                self.assertNotIn(asset_id, self.assets.values(), "prop id duplicates a current generated id")
            self.assertTrue((ROOT / f"assets/blender/world/fbx_v3/{key}.fbx").exists())
            self.assertIn(key, REGISTRY)
            self.assertIn(f'"name": "{key}"', slots)
            self.assertIn(f"{tris} tris", PROPS_BLOCK.split(f"{key} = ")[1].split(chr(10))[0], f"{key}: tris field and comment disagree")
            dims = [float(v) for v in size.split(",")]
            self.assertEqual(len(dims), 3)
            self.assertTrue(all(0.5 < d < 12 for d in dims), f"{key}: size {dims} is not a plausible mesh size in studs")

    def test_ground_props_are_wired_for_placement_but_unbound(self):
        """BD-464 step 2: eight ground props, empty ids (not uploaded) so nothing is placed; FBX, registry, slot rows and sizes exist; the
        loader skips empty ids; Arena and BiomePlacement place a key only when its id is valid (and its template loaded)."""
        entries = self.prop_entries("ground_")
        self.assertEqual({e[0] for e in entries}, {"ground_rock_small_v3", "ground_rock_medium_v3", "ground_rock_mossy_v3", "ground_log_fallen_v3",
                                                   "ground_stump_roots_v3", "ground_mushrooms_v3", "ground_bush_round_v3", "ground_bush_berry_v3"})
        self.check_prop_entries(entries, "BD-464")
        loader = (ROOT / "src/server/ImportedResources.luau").read_text()
        self.assertIn('for key,asset in GeneratedMeshes.Props do if asset.assetId~="" then', loader, "loader must skip empty prop ids")
        self.check_placement_gate()

    def test_plants_are_wired_for_placement_but_unbound(self):
        """BD-463 step 2: eight plants (grass tufts, jungle plant, flower clusters, fern), empty ids (not uploaded) so nothing is placed;
        FBX + registry + slot rows exist; placement is gated on a valid id."""
        entries = self.prop_entries("plant_")
        self.assertEqual({e[0] for e in entries}, {"plant_grass_broad_v3", "plant_grass_arch_v3", "plant_grass_low_v3", "plant_jungle_leaf_v3",
                                                   "plant_flowers_daisy_v3", "plant_flowers_yellow_v3", "plant_flowers_red_v3", "plant_fern_arch_v3"})
        self.check_prop_entries(entries, "BD-463")
        self.check_placement_gate()

    def check_placement_gate(self):
        bp = (ROOT / "src/shared/BiomePlacement.luau").read_text()
        arena = (ROOT / "src/server/Arena.luau").read_text()
        self.assertNotRegex(bp, r"require\([^)]*WorldGeneratedMeshes", "BiomePlacement stays pure: it only sees options.props")
        self.assertIn("function BiomePlacement.validAssetId", bp)
        self.assertIn("BiomePlacement.validAssetId(entry.assetId)", bp, "a key is live only with a valid pasted id")
        self.assertIn("BiomePlacement.withProps(options.kit, options.props)", bp)
        self.assertIn("props = propEntries", arena, "Arena hands only the live keys to generate")
        self.assertIn("Generated.validId(entry.assetId)", arena)
        self.assertIn("if Config.WorldGeneratedMeshes and generatedFolder then", arena, "no generated meshes -> no new props")
        self.assertIn("template and template:IsA(\"MeshPart\")", arena, "a key whose template failed to load is never placed")
        self.assertIn("function Generated.validId", SRC)
        # the two id rules agree
        for fn in (bp, SRC):
            self.assertIn('#id >= 9 and #id <= 18 and string.match(id, "^[1-9]%d*$") == id', fn)

    def test_colossal_ancient_trees_are_baked_but_unbound_and_gated_to_the_colossal_layer(self):
        """BD-474: three colossal trees x LOD0/LOD1, empty ids (not uploaded), a safe stand-in fallback, used by the colossal layer only."""
        entries = re.findall(r'^\s{4}(\w+) = \{assetId = "(\d*)", placed = (true|false), lod = (0|1), kit = "(\w+)", standIn = "(\w+)", tris = (\d+)', COLOSSAL_BLOCK, re.M)
        keys = {k for k, *_ in entries}
        self.assertEqual(keys, {"tree_colossal_broadleaf_v3", "tree_colossal_pine_v3", "tree_colossal_palm_v3",
                                "tree_colossal_broadleaf_v3_lod1", "tree_colossal_pine_v3_lod1", "tree_colossal_palm_v3_lod1"})
        fbx_name = {"broadleaf": "broad", "pine": "pine", "palm": "palm"}
        for key, asset_id, placed, lod, kit, stand_in, tris in entries:
            self.assertEqual(placed, "true", f"{key}: BD-475 swaps LOD0 and LOD1 by distance, both are used")
            self.assertEqual(key.endswith("_lod1"), lod == "1")
            self.assertIn(f"{kit}=", KIT, f"{key}: unknown kit id {kit}")
            self.assertTrue(kit.endswith("_l"), "colossal meshes stand in for the size-l kit trees")
            self.assertIn(stand_in, self.assets, f"{key}: stand-in {stand_in} is not a current generated mesh")
            if asset_id:
                self.assertRegex(asset_id, r"^[1-9][0-9]{8,17}$")
                self.assertNotIn(asset_id, self.assets.values(), "colossal id duplicates a current generated id")
            fam = key.split("_")[2]
            fbx = f"world_tree_colossal_{fbx_name[fam]}_v3" + ("_lod1" if lod == "1" else "")
            self.assertTrue((ROOT / f"assets/blender/world/fbx_v3/{fbx}.fbx").exists(), fbx)
            self.assertIn(fbx, REGISTRY)
            # docs/139 s9: LOD0 about 4,000 tris (at most 4,200), LOD1 about 1,000 (800 to 1,100)
            if lod == "0":
                self.assertTrue(3500 <= int(tris) <= 4200, f"{key} LOD0 tris {tris}")
            else:
                self.assertTrue(800 <= int(tris) <= 1100, f"{key} LOD1 tris {tris}")
        self.assertEqual({e[4] for e in entries}, {"world_tree_canopy_l", "world_tree_conifer_l", "world_tree_cycad_l"})
        self.assertIn('info.lod == 0 and info.kit == kitId and info.assetId ~= ""', SRC, "colossalFor must ignore empty ids and LOD1")
        arena = (ROOT / "src/server/Arena.luau").read_text()
        self.assertIn('local colossalKey = if layer == "colossal" then Generated.colossalFor(id) else nil', arena, "ordinary size-l trees must keep their meshes")
        self.assertIn("p.layer) or Resources.clone(p.id)", arena, "the placement layer must reach generatedProp")
        # BD-475: the ancient tree is only used as a LOD0 + LOD1 pair; sizes and trunk numbers feed ColossalRules
        self.assertIn('if near and near:IsA("MeshPart") and far and far:IsA("MeshPart") then', arena, "a LOD0 without its LOD1 keeps the stand-in")
        for key, *_ in entries:
            row = [line for line in COLOSSAL_BLOCK.splitlines() if line.strip().startswith(key + " = ")][0]
            self.assertRegex(row, r"size = \{[\d., ]+\}, base = \{[-\d., ]+\}", f"{key} needs size and base for the LOD1 pivot shift")
        self.assertIn("if not template and key and folder then template = folder:FindFirstChild(key) end", arena, "stand-in fallback")
        loader = (ROOT / "src/server/ImportedResources.luau").read_text()
        self.assertIn('for key,asset in GeneratedMeshes.Colossal do if asset.assetId~="" then', loader, "loader must skip empty colossal ids")


    def test_fallback_and_flag_are_wired(self):
        arena = (ROOT / "src/server/Arena.luau").read_text()
        self.assertIn('generatedProp(id, biome or "meadow", roll or .5) or Resources.clone(id)', arena)
        self.assertIn("Config.WorldGeneratedMeshes", arena)
        self.assertIn("WorldGeneratedMeshes = true", (ROOT / "src/shared/Config.luau").read_text())


if __name__ == "__main__":
    unittest.main()
