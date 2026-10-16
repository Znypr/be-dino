"""BD-249/250/251 source guards for the low-poly motion (no Luau runner needed; the numeric checks live in tools/verify_lowpoly_dinos.py)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSE = (ROOT / "src/shared/LowPolyPose.luau").read_text(encoding="utf-8")
ANIM = (ROOT / "src/client/LowPolyAnimator.client.luau").read_text(encoding="utf-8")


class LowPolyMotionTests(unittest.TestCase):
    def test_flag_gates_the_animator(self):
        self.assertIn("if not LowPoly.enabled() then return end", ANIM)

    def test_every_class_has_action_scales(self):
        for cls in ("Ground", "Armored", "Fly", "Water"):
            self.assertRegex(POSE, cls + r" = \{q = ")

    def test_every_skin_has_a_defeat(self):
        self.assertIn('Pose.Skins = {"Base", "Plush", "Clay", "Bricks"}', POSE)
        for skin in ("Base", "Plush", "Clay", "Bricks"):
            self.assertIn('kind == "%s"' % skin if skin != "Bricks" else "-- Bricks", POSE)
        self.assertIn("Pose.DefeatSeconds = 1.5", POSE)

    def test_defeat_is_wired_and_respects_reduce_motion(self):
        self.assertIn('RunState") == "Ending"', ANIM)
        self.assertIn("Pose.sampleDefeat(", ANIM)
        self.assertIn("if amp == 0 then rig.act = nil", ANIM)

    def test_body_never_moves_on_its_own_while_walking(self):
        self.assertRegex(POSE, r'if role == "body" then\n\s+-- BD-388')

    def test_head_peck_is_forward_in_studs(self):
        self.assertIn("Pose.PeckStuds = 0.4", POSE)
        self.assertIn("fwd = w * u * Pose.PeckStuds", POSE)


if __name__ == "__main__":
    unittest.main()
