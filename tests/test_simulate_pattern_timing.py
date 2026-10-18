"""BD-1033: the pattern timing report (tools/simulate_pattern_timing.py) does the arithmetic right and prints every tier."""
from pathlib import Path
import math, sys, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import simulate_pattern_timing as sim  # noqa: E402

ROWS = [("01_blank", "Plain", "Common", 8000000), ("04_x", "Patches", "Uncommon", 1600000), ("06_y", "Waves", "Rare", 320000),
        ("02_z", "Islands", "Epic", 64000), ("07_w", "Diamonds", "Legendary", 16000)]
SCALE = sum(w for *_, w in ROWS)


class PatternTimingTests(unittest.TestCase):
    def test_wait_is_one_over_chance(self):
        mean, median, p90 = sim.wait(0.2)
        self.assertAlmostEqual(mean, 5.0)
        self.assertEqual(median, 4)          # 1 - 0.8^4 = 59% >= 50%, 0.8^3 gives 49%
        self.assertEqual(p90, math.ceil(math.log(0.1) / math.log(0.8)))
        self.assertGreater(sim.wait(0.001)[0], sim.wait(0.01)[0])

    def test_report_lists_each_tier_and_every_pattern(self):
        text = sim.report(ROWS, SCALE, {"01_blank": 50}, 100)
        for tier in ("Uncommon", "Rare", "Epic", "Legendary"):
            self.assertIn(tier + " ", text)
        self.assertNotIn("Mythic  ", text)   # no pattern in that tier, so no line
        for _, name, *_ in ROWS:
            self.assertIn(name, text)
        self.assertIn("50.000%", text)       # the seeded column

    def test_rarer_tier_waits_longer(self):
        text = sim.report(ROWS, SCALE, {}, 100)
        means = []
        for tier in ("Uncommon", "Rare", "Epic", "Legendary"):
            line = next(l for l in text.splitlines() if l.startswith(tier))
            means.append(float(line.split()[3]))
        self.assertEqual(means, sorted(means))


if __name__ == "__main__":
    unittest.main()
