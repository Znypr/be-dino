"""BD-095: Effects Full/Lite/Off distance LOD. Static wiring always; the Luau rule checks run when a runner exists."""
from pathlib import Path
import os, shutil, subprocess, sys, unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_settings


def luau():
    return os.environ.get('LUAU_RUNNER') or shutil.which('luau')


class EffectsLod(unittest.TestCase):
    def test_static_wiring(self):
        self.assertEqual(verify_settings.static_checks(), [])

    def test_module_is_pure(self):
        src = (ROOT / 'src/shared/EffectsLod.luau').read_text(encoding='utf-8')
        self.assertNotIn('GetService', src)
        for mode in ('full', 'lite', 'off'):
            self.assertIn(mode + ' =', src)

    @unittest.skipUnless(luau(), 'no Luau runner (set LUAU_RUNNER)')
    def test_rules_and_settings_model(self):
        out = subprocess.run([sys.executable, str(ROOT / 'tools/verify_settings.py'), '--runner', luau()], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn('Effects LOD checks passed', out.stdout)


if __name__ == '__main__':
    unittest.main()
