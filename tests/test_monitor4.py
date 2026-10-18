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

    def test_maximize_only_for_studio_and_blender(self):
        self.assertTrue(m.may_maximize("studio", "x.rbxlx - Roblox Studio"))
        self.assertTrue(m.may_maximize("blender", "Cockatoo - Blender"))
        self.assertFalse(m.may_maximize("edge", "Claude - Edge"))
        self.assertFalse(m.may_maximize(None, "Notepad"))
        self.assertFalse(m.may_maximize("studio", "C:/x/Place1.rbxl - Roblox Studio"))  # the owner's window, even if misclassified
        # classify() already hides Place1, so it can never reach may_maximize
        self.assertFalse(m.may_maximize(m.classify("Place1.rbxl - Roblox Studio", "RobloxStudioBeta.exe"), "Place1.rbxl"))

    def test_splash(self):
        self.assertTrue(m.is_splash("RobloxStudio"))
        self.assertFalse(m.is_splash("x.rbxlx - Roblox Studio"))

    def test_is_maximised_on(self):
        mon = (3840, 0, 5120, 720)
        self.assertTrue(m.is_maximised_on(mon, (3832, -8, 5128, 712)))
        self.assertFalse(m.is_maximised_on(mon, (4000, 100, 4500, 565)))

    def test_cli_flags(self):
        import argparse  # the parser lives in main(); check the constants used by launch
        self.assertEqual(m.MAXIMIZE_KINDS, ("studio", "blender"))
        self.assertEqual(m.SW_SHOWMAXIMIZED, 3)


if __name__ == "__main__":
    unittest.main()
