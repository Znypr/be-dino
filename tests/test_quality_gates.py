"""BD-409..413: the quality-gate tools run on their committed probe data and on synthetic inputs."""
from pathlib import Path
import os, shutil, subprocess, sys, tempfile, unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'qa'))
import ground_report, budget_report


def luau():
    return os.environ.get('LUAU_RUNNER') or shutil.which('luau')


class GroundReport(unittest.TestCase):
    def test_committed_probe_passes(self):
        self.assertEqual(ground_report.evaluate(ground_report.DEFAULT.read_text())[3], [])

    def test_sunk_tree_fails(self):
        text = 'PLACE\tisland\t10\t0\nKIND\tisland\tworld_tree_pine_l\t10\t3\t0\t2.50\t0.00\n'
        self.assertEqual(len(ground_report.evaluate(text)[3]), 1)

    def test_floating_plant_over_allowance_fails(self):
        text = 'PLACE\tisland\t10\t0\nKIND\tisland\tworld_bush_a\t10\t0\t2\t0.00\t2.00\n'
        self.assertEqual(len(ground_report.evaluate(text)[3]), 1)

    def test_rim_piece_design_allowance(self):
        text = 'PLACE\tcave\t4\t0\nKIND\tcave\tcave_wall_pillar\t4\t4\t0\t0.50\t0.00\n'
        self.assertEqual(ground_report.evaluate(text)[3], [])


class BudgetReport(unittest.TestCase):
    def test_committed_probe_passes(self):
        self.assertEqual(budget_report.check(budget_report.DEFAULT.read_text())[1], 0)

    def test_over_cap_fails(self):
        self.assertGreater(budget_report.check('BUD\tcave_hub\t999\t0\t0\t0\t0\n')[1], 0)


class Luminance(unittest.TestCase):
    def test_ranges(self):
        import luminance
        self.assertTrue(luminance.verdict('cave_heart', 0.29)[0])
        self.assertFalse(luminance.verdict('cave_heart', 0.5)[0])
        self.assertFalse(luminance.verdict('island', 0.1)[0])

    def test_measure_flat_image(self):
        import luminance
        from PIL import Image
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / 'g.png'
            Image.new('RGB', (100, 100), (128, 128, 128)).save(f)
            mean, _, _ = luminance.measure(f, (0, 0, 1, 1))
            self.assertAlmostEqual(mean, 128 / 255, places=3)


@unittest.skipUnless(luau(), 'no Luau runner (set LUAU_RUNNER)')
class PaletteAndOverlap(unittest.TestCase):
    def test_palette_gate_on_committed_probe(self):
        out = subprocess.run([sys.executable, str(ROOT / 'tools/qa/palette_report.py'), '--runner', luau()], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_island_overlap_gate(self):
        out = subprocess.run([sys.executable, str(ROOT / 'tools/verify_world_overlap.py'), '--runner', luau()], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)


class SourceRules(unittest.TestCase):
    def test_generated_prop_pivot_is_at_the_bottom(self):
        arena = (ROOT / 'src/server/Arena.luau').read_text()
        self.assertIn('mesh.PivotOffset = CFrame.new(0, -mesh.Size.Y / 2, 0)', arena)
        self.assertIn('p.layer == "rock" or p.layer == "landmark"', arena)

    def test_shop_crystals_are_amber(self):
        props = (ROOT / 'src/shared/CaveHubProps.luau').read_text()
        self.assertIn('hub_crystal_s = {color = {255, 190, 60}', props)
        self.assertIn('hub_crystal_l = {color = {255, 190, 60}', props)


if __name__ == '__main__':
    unittest.main()
