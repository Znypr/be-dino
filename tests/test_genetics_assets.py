"""Verify neutral skin assets remain reproducible, owner-bound PNG masters."""
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class GeneticsAssetTests(unittest.TestCase):
    def test_authored_surfaces_match_bindings_and_are_packaged(self):
        manifest = json.loads((ROOT / "resources/genetics/texture-bindings.json").read_text())
        model = ET.parse(ROOT / "resources/roblox/GeneSurfaces.rbxmx").getroot().find("Item")
        rows = {p.find("Properties/string[@name='Name']").text: p for p in model.findall("Item")}
        self.assertEqual(len(rows), 38)
        for row in manifest["textures"]:
            surface = rows[row["id"]]
            self.assertEqual(surface.attrib["class"], "SurfaceAppearance")
            self.assertEqual(surface.find("Properties/Content[@name='ColorMap']/url").text,
                             "rbxassetid://" + row["assetId"])
        place = ET.parse(ROOT / "build/BeDino-Build019.rbxlx").getroot()
        self.assertEqual(sum(p.attrib["class"] == "SurfaceAppearance" for p in place.iter("Item")), 38)

    def test_all_six_species_have_verified_neutral_textures(self):
        manifest = json.loads((ROOT / "resources/genetics/texture-bindings.json").read_text())
        self.assertEqual(manifest["owner"]["id"], 7285577648)
        self.assertEqual(len(manifest["textures"]), 38)
        self.assertEqual({row["species"] for row in manifest["textures"]},
                         {"compy", "raptor", "triceratops", "stegosaurus", "tyrannosaurus", "ankylosaurus"})
        self.assertEqual(len({row["id"] for row in manifest["textures"]}), 38)
        self.assertEqual(len({row["assetId"] for row in manifest["textures"]}), 38)
        for row in manifest["textures"]:
            self.assertTrue(row["assetId"].isdecimal() and int(row["assetId"]) > 0)
            with Image.open(ROOT / "resources/genetics" / row["path"]) as image:
                self.assertEqual(image.mode, "RGBA")
                self.assertEqual(image.size, (512, 512))
                pixels = np.asarray(image)
            self.assertTrue(np.array_equal(pixels[:, :, 0], pixels[:, :, 1]))
            self.assertTrue(np.array_equal(pixels[:, :, 1], pixels[:, :, 2]))
            self.assertGreater(np.ptp(pixels[:, :, 0]), 0)


if __name__ == "__main__":
    unittest.main()
