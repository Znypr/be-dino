import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StudioSyncTests(unittest.TestCase):
    def test_utf8_source_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / 'source'
            (root / 'tools').mkdir(parents=True)
            (root / 'src/shared').mkdir(parents=True)
            (parent / 'Dino_Models').mkdir()
            tool = root / 'tools/studio_creature_sync.py'
            shutil.copyfile(ROOT / 'tools/studio_creature_sync.py', tool)
            source = "return 'Crystal \u2022 Egg'\n"
            (root / 'src/shared/Test.luau').write_text(source, encoding='utf-8')
            subprocess.run([sys.executable, str(tool)], check=True, capture_output=True)
            rows = json.loads((parent / 'Dino_Models/studio-creature-sync.json').read_text(encoding='utf-8'))
            self.assertEqual(rows[0]['source'], source)
            self.assertEqual(rows[0]['folder'], ['ReplicatedStorage', 'Shared'])
            self.assertEqual(rows[0]['class'], 'ModuleScript')


if __name__ == '__main__':
    unittest.main()
