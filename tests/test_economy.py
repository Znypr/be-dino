import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("economy", ROOT / "tools/economy_sim.py")
economy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(economy)


class EconomyTests(unittest.TestCase):
    def test_exact_totals_and_tier_order(self):
        for score in range(economy.MAX_CATCH_SCORE + 1):
            allocation = economy.allocate_tiers(score)
            self.assertEqual(sum(allocation), score)
            self.assertTrue(all(a >= b for a, b in zip(allocation, allocation[1:])))

    def test_total_is_strictly_increasing(self):
        for score in range(economy.MAX_CATCH_SCORE):
            self.assertLess(
                economy.total_run_copies(score),
                economy.total_run_copies(score + 1),
            )

    def test_eligibility_boundaries(self):
        self.assertEqual(economy.allocate_tiers(24), (24,))
        self.assertEqual(economy.allocate_tiers(25), (20, 5))
        self.assertEqual(economy.allocate_tiers(100), (77, 19, 4))
        self.assertEqual(economy.allocate_tiers(400), (303, 75, 18, 4))
        self.assertEqual(economy.allocate_tiers(1600), (1203, 300, 75, 18, 4))

    def test_mutation_risk_is_measured(self):
        self.assertEqual(economy.first_score_for_common_copies(50), 62)

    def test_chests_are_independent(self):
        for score in (0, 9, 10, 99, 100, 499, 500, 5000):
            before = economy.total_run_copies(score)
            _ = economy.earned_chests(score)
            self.assertEqual(economy.total_run_copies(score), before)
        self.assertEqual(economy.earned_chests(9), 0)
        self.assertEqual(economy.earned_chests(10), 1)
        self.assertEqual(economy.earned_chests(100), 2)
        self.assertEqual(economy.earned_chests(500), 3)

    def test_invalid_scores_rejected(self):
        for value in (-1, economy.MAX_CATCH_SCORE + 1, 1.5, "10"):
            with self.assertRaises((TypeError, ValueError)):
                economy.allocate_tiers(value)


if __name__ == "__main__":
    unittest.main()
