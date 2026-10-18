"""BD-1036: the colour timing report (tools/simulate_colour_timing.py) treats the shown colour rarity as the rarer of two slots."""
from pathlib import Path
import sys, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import simulate_colour_timing as sim  # noqa: E402

ROWS = [("white", "Cream", "Common", 4000000), ("blue", "Blue", "Common", 4000000), ("green", "Green", "Uncommon", 1600000),
        ("pink", "Pink", "Rare", 320000), ("red", "Red", "Mythic", 80000)]
SCALE = sum(w for *_, w in ROWS)


class ColourTimingTests(unittest.TestCase):
    def test_dino_tier_chances_sum_to_one_and_favour_the_rarer_colour(self):
        dino, slot = sim.dino_tier(ROWS, SCALE), sim.per_slot(ROWS, SCALE)
        self.assertAlmostEqual(sum(dino.values()), 1.0)
        self.assertAlmostEqual(dino["Common"], slot["Common"] ** 2)           # both slots Common
        for tier in ("Uncommon", "Rare", "Mythic"):
            self.assertGreater(dino[tier], slot[tier])                       # two tries at a rare colour

    def test_report_lists_each_tier_in_order(self):
        text = sim.report(ROWS, SCALE, {"Common": 50}, 100)
        positions = [text.index(t) for t in ("Common", "Uncommon", "Rare", "Mythic")]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Cream, Blue", text)


if __name__ == "__main__":
    unittest.main()
