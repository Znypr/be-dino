"""BD-1261 soft blob shadow: flag and source checks (the Luau checks are tools/verify_blob_shadow.py, in CI)."""
import os
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


class BlobShadowTests(unittest.TestCase):
    def test_flag_ships_off_and_playtest_turns_it_on(self):
        import release_profiles as profiles
        text = read('src/shared/Config.luau')
        self.assertIn('    BlobShadowEnabled = false,\n', text)
        self.assertIn('BlobShadowEnabled = true', profiles.apply_profile(text, 'playtest')[0])
        self.assertIn('BlobShadowEnabled', [key for key, _ in profiles.REHEARSAL_ON])

    def test_source_guards(self):
        import verify_blob_shadow
        verify_blob_shadow.scan()

    def test_flag_off_keeps_the_three_discs(self):
        shadow = read('src/client/ContactShadow.client.luau')
        self.assertIn('if BLOB then Enum.PartType.Block else Enum.PartType.Cylinder', shadow)
        self.assertIn('for i, part in shadow.parts do', shadow)

    @unittest.skipUnless(os.environ.get('LUAU_RUNNER'), 'needs LUAU_RUNNER')
    def test_luau_rules(self):
        out = subprocess.run([sys.executable, str(ROOT / 'tools/verify_blob_shadow.py'), '--runner', os.environ['LUAU_RUNNER']],
                             capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)


if __name__ == '__main__':
    unittest.main()
