"""BD-1305: tools/art_audit.py groups versions into one family and maps archived files back to their old place."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import art_audit  # noqa: E402


class ArtAuditTest(unittest.TestCase):
    def test_versions_fold_into_one_family(self):
        v1 = art_audit.split_name("resources/ui/v2/icons/trail-ember-v1.png")
        v2 = art_audit.split_name("resources/ui/v2/icons/trail-ember-v2.png")
        old = art_audit.split_name("resources/archive/ui/v2/icons/trail-ember-v1.png")
        self.assertEqual(v1[0], v2[0])
        self.assertEqual(v1[0], old[0])
        self.assertLess(v1[1], v2[1])
        self.assertEqual(art_audit.split_name("assets/blender/creatures/textures/compy_v2/Compy_V2_Body.png")[0],
                         art_audit.split_name("assets/blender/creatures/textures/compy_v3/Compy_V3_Body.png")[0])

    def test_kinds(self):
        self.assertEqual(art_audit.split_name("resources/ui/v2/items/potion-lucky-sip-512.png")[2], "upload-copy")
        self.assertEqual(art_audit.split_name("resources/ui/v2/candidates/art-batch2/crystals-l-B.png")[2], "candidate")
        self.assertEqual(art_audit.split_name("resources/ui/v2/icons/crystals-l-v1.png")[2], "final")

    def test_unarchived_and_decisions(self):
        self.assertEqual(art_audit.unarchived("resources/archive/ui/v2/components/close.png"), "resources/ui/v2/components/close.png")
        self.assertEqual(art_audit.unarchived("resources/ui/v2/icons/home.png"), "resources/ui/v2/icons/home.png")
        self.assertEqual(art_audit.decision("resources/archive/ui/v2/components/close.png")[0], "archive")
        self.assertEqual(art_audit.decision("resources/patterns/candidates/a-A1.png")[0], "keep")


if __name__ == "__main__":
    unittest.main()
