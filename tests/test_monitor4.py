import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import monitor4 as m  # noqa: E402


class Monitor4Tests(unittest.TestCase):
    def test_place1_is_never_ours(self):
        self.assertIsNone(m.classify("C:/x/Place1.rbxl - Roblox Studio", "RobloxStudioBeta.exe"))
        self.assertEqual(m.classify("other.rbxlx - Roblox Studio", "RobloxStudioBeta.exe"), "studio")

    def test_kinds(self):
        self.assertEqual(m.classify("Cockatoo [x] - Blender", "blender.exe"), "blender")
        self.assertIsNone(m.classify("Some page", "msedge.exe"))  # the owner's own Edge is left alone
        self.assertEqual(m.classify("Claude (MCP) - Edge", "msedge.exe", "Claude"), "edge")
        self.assertEqual(m.classify("Any page", "msedge.exe", "*"), "edge")
        self.assertIsNone(m.classify("Notepad", "notepad.exe"))

    def test_pick_virtual(self):
        mons = [{"index": 1, "rect": (0, 0, 1920, 1080), "size": (1920, 1080)}, {"index": 2, "rect": (1920, 0, 3200, 720), "size": (1280, 720)}]
        self.assertEqual(m.pick_virtual(mons)["index"], 2)
        self.assertEqual(m.pick_virtual(mons, index=1)["index"], 1)
        self.assertIsNone(m.pick_virtual(mons[:1]))

    def test_target_rect_fits_and_centres(self):
        mon = (3840, 0, 5120, 720)
        x, y, w, h = m.target_rect(mon, (0, 0, 1000, 600))
        self.assertEqual((w, h), (1000, 600))
        self.assertTrue(3840 <= x and x + w <= 5120 and 0 <= y and y + h <= 720)
        x, y, w, h = m.target_rect(mon, (0, 0, 3000, 2000))  # too big: fit to the monitor
        self.assertEqual((w, h), (1280, 720))
        x, y, w, h = m.target_rect(mon, (0, 0, 100, 100))  # tiny: made usable
        self.assertEqual((w, h), (1280, 720))


if __name__ == "__main__":
    unittest.main()
