"""docs/173: tools/bind_secret_species.py binds a real model id and a MEASURED box, and refuses everything else. Offline, scratch copies only."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import bind_secret_species as bind  # noqa: E402

FILES = [bind.CONFIG, bind.REGISTRY, bind.LADDER, bind.BOXES, bind.BOUND]


def scratch():
    root = Path(tempfile.mkdtemp(prefix="bind_secret_"))
    for rel in FILES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, root / rel)
    return root


class PlanTests(unittest.TestCase):
    def test_the_foxosaurus_numbers_are_the_shipped_ones(self):
        got = bind.plan("Ground", (3.8, 8.4, 8.0))
        self.assertEqual((got["scale"], got["row"], got["snout"], got["head"]), (0.79, (3.0, 6.64, 6.32), 3.16, 1.39))
        ladder = (ROOT / bind.LADDER).read_text(encoding="utf-8")
        self.assertIn("foxosaurus = {scale = 0.79, tier = 1, basis = \"height\", target = 6.60, width = 3.00, height = 6.64, length = 6.32, snout = 3.16, headLength = 1.39, measured = true}", ladder)

    def test_fly_and_water_are_sized_by_bulk_ground_by_height(self):
        self.assertEqual(bind.plan("Fly", (4.0, 8.0, 9.0))["basis"], "bulk")
        self.assertEqual(bind.plan("Water", (4.0, 8.0, 9.0))["basis"], "bulk")
        self.assertEqual(bind.plan("Ground", (4.0, 8.0, 9.0))["basis"], "height")

    def test_the_size_lands_within_two_percent_of_the_rule(self):
        for cls, box in (("Ground", (3.1, 7.7, 5.2)), ("Fly", (6.0, 5.0, 7.0)), ("Water", (4.4, 9.0, 12.0))):
            got = bind.plan(cls, box)
            self.assertLessEqual(abs(bind.size_of(got["basis"], got["row"]) - got["target"]), 0.02 * got["target"] + 1e-9, cls)

    def test_a_measured_head_length_is_scaled_and_flagged(self):
        got = bind.plan("Ground", (3.8, 8.4, 8.0), head_length=1.5)
        self.assertTrue(got["head_measured"])
        self.assertEqual(got["head"], round(1.5 * 0.79, 2))
        self.assertFalse(bind.plan("Ground", (3.8, 8.4, 8.0))["head_measured"])

    def test_junk_boxes_are_refused(self):
        for box in ((0, 8, 8), (-1, 8, 8), (float("nan"), 8, 8), (float("inf"), 8, 8), (1, 2), (True, 8, 8), ("a", 8, 8)):
            with self.assertRaises(ValueError, msg=str(box)):
                bind.plan("Ground", box)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            bind.plan("Ground", (3.0, 80.0, 3.0))  # a 80-stud model needs scale 0.08: not a real scale-1 box


class ApplyTests(unittest.TestCase):
    def test_binding_an_empty_slot_edits_all_five_places_consistently(self):
        root = scratch()
        try:
            bind.apply("budgiesaurus", 1234567890123, (4.0, 8.0, 9.0), None, "v2", False, root)
            cfg = (root / bind.CONFIG).read_text(encoding="utf-8")
            self.assertIn('class = "Fly", weight = 10, assetId = 1234567890123 }', cfg)
            reg = (root / bind.REGISTRY).read_text(encoding="utf-8")
            self.assertIn('budgiesaurus = {assetId = 1234567890123, version = "v2", scale = 0.84, tier = 1, class = "Fly"},', reg)
            self.assertTrue(reg.rstrip().endswith("}"))
            ladder = (root / bind.LADDER).read_text(encoding="utf-8")
            self.assertIn("budgiesaurus = {scale = 0.84, tier = 1, basis = \"bulk\", target = 5.55, width = 3.36, height = 6.72, length = 7.56, snout = 3.78, headLength = 1.66, measured = true},", ladder)
            boxes = (root / bind.BOXES).read_text(encoding="utf-8")
            self.assertIn("'budgiesaurus': (3.36, 6.72, 7.56),", boxes)
            bound = (root / bind.BOUND).read_text(encoding="utf-8")
            self.assertIn("BOUND_IDS = {'budgiesaurus': 1234567890123, 'foxosaurus': 112996440434481}", bound)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_refusals(self):
        root = scratch()
        try:
            for species, asset in (("budgiesaurus", 12345), ("budgiesaurus", 0), ("budgiesaurus", -5), ("nosuchbird", 1234567890123),
                                   ("budgiesaurus", 12345678901234567890), ("duck", 112996440434481)):
                with self.assertRaises(ValueError, msg=f"{species} {asset}"):
                    bind.apply(species, asset, (4.0, 8.0, 9.0), None, "v1", False, root)
            with self.assertRaises(ValueError):  # the fox is already bound
                bind.apply("foxosaurus", 1234567890123, (3.8, 8.4, 8.0), None, "v1", False, root)
            bind.apply("foxosaurus", 112996440434481, (3.8, 8.4, 8.0), None, "v2", True, root)  # --replace with the same id is allowed
            self.assertEqual((root / bind.REGISTRY).read_text(encoding="utf-8").count("foxosaurus = {"), 1)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_the_shipped_tree_is_the_tool_output_for_the_fox(self):
        root = scratch()
        try:
            for rel in (bind.CONFIG, bind.REGISTRY, bind.LADDER, bind.BOXES, bind.BOUND):
                before = (root / rel).read_text(encoding="utf-8")
                self.assertTrue(before)
            bind.apply("foxosaurus", 112996440434481, (3.8, 8.4, 8.0), None, "v2", True, root)
            for rel in (bind.CONFIG, bind.REGISTRY, bind.LADDER, bind.BOUND):
                self.assertEqual((root / rel).read_text(encoding="utf-8"), (ROOT / rel).read_text(encoding="utf-8"), rel)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
