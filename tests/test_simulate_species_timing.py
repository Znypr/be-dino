"""BD-1032: species rarity timing (tools/simulate_species_timing.py) reads the real Config and meets the owner's goal."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("simulate_species_timing", ROOT / "tools/simulate_species_timing.py")
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)
CFG = sim.load_config()


class SpeciesTimingTests(unittest.TestCase):
    def test_base_weights_are_the_docs_186_numbers(self):
        chances = sim.tier_chances(CFG, 1)
        for got, want in zip(chances, [.91, .085, .0042, .0007, .0001]):
            self.assertAlmostEqual(got, want, places=9)

    def test_compy_is_40_percent_of_common(self):
        common = [(s, w) for s, w in CFG["weights"] if CFG["tiers"][s] == 1]
        self.assertAlmostEqual(dict(common)["compy"] / sum(w for _, w in common), 0.4, places=9)

    def test_normal_run_is_not_lifted_and_big_run_lifts_rare_up_about_2x(self):
        base = sim.tier_chances(CFG, 1)
        self.assertEqual(sim.tier_chances(CFG, 15), base)
        big = sim.tier_chances(CFG, 120)
        for tier in (2, 3, 4):
            self.assertAlmostEqual(big[tier] / base[tier], 2.0, delta=0.02)
        self.assertAlmostEqual(big[1] / base[1], 1.0, delta=0.01)
        self.assertEqual(sim.tier_chances(CFG, 1000), big)  # capped

    def test_median_first_rare_or_better_is_30_to_60_minutes_at_3_eggs_a_minute(self):
        rows = {r["tier"]: r for r in sim.table(CFG, 3.0, 15)["rows"]}
        self.assertGreaterEqual(rows["Rare"]["median_min"], 30)
        self.assertLessEqual(rows["Rare"]["median_min"], 60)
        # a new kind of dinosaur still comes early: first Uncommon within a few minutes, and in the right order
        self.assertLess(rows["Uncommon"]["median_min"], 5)
        self.assertLess(rows["Rare"]["median_min"], rows["Epic"]["median_min"])
        self.assertLess(rows["Epic"]["median_min"], rows["Legendary"]["median_min"])

    def test_rare_in_the_first_12_eggs_is_unlikely(self):
        within = sim.table(CFG, 3.0, 15)["rare_within"]
        self.assertLess(within[12], 0.08)  # was 39% before BD-1032
        self.assertGreater(within[90], 0.30)
        self.assertLess(within[90], 0.45)

    def test_quantile_and_sample_agree(self):
        self.assertEqual(sim.eggs_to_quantile(0.5, 0.5), 1)
        self.assertEqual(sim.eggs_to_quantile(0.005, 0.5), 139)
        sampled = sim.sample(CFG, 15, 300)
        exact = {r["tier"]: r["median_eggs"] for r in sim.table(CFG, 3.0, 15)["rows"]}
        for tier in ("Uncommon", "Rare"):
            self.assertAlmostEqual(sampled[tier] / exact[tier], 1.0, delta=0.35)

    def test_render_mentions_every_tier(self):
        text = sim.render(CFG, 3.0, 15, (12, 90), 0)
        for tier in ("Uncommon", "Rare", "Epic", "Legendary", "first 12 eggs", "first 90 eggs"):
            self.assertIn(tier, text)


if __name__ == "__main__":
    unittest.main()
