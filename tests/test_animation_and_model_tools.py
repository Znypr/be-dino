"""Tests for tools/animation_strip.py and tools/check_model_for_roblox.py (BD-641, BD-642, docs/163).

Part 1 needs no Blender: the verdict rules are exercised on small made-up numbers. Part 2 builds tiny fixtures with a SEPARATE headless
Blender (a box-limbed walker with a walk cycle and one broken copy per defect, and a set of small meshes) and checks that every defect
turns exactly the matching verdict to "check" / FAIL / WARN. Part 2 is skipped with a clear message if blender.exe is not installed.
"""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import animation_strip as A  # noqa: E402
import blender_headless  # noqa: E402
import check_model_for_roblox as M  # noqa: E402

BLENDER = blender_headless.find_blender()
FFMPEG = Path(A.FFMPEG)
def quiet(fn, *args):
    """Run a command-line main() without its report flooding the test output."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args)


NO_BLENDER = "Blender (blender.exe) was not found: install Blender or set the BLENDER environment variable to run these tests"


# ----------------------------------------------------------------------------------------------------------------------------------
class NameHelpers(unittest.TestCase):
    def test_left_right_names(self):
        self.assertEqual(A.mirror_name("foot.L"), "foot.R")
        self.assertEqual(A.mirror_name("Leg_r"), "Leg_l")
        self.assertEqual(A.mirror_name("LeftFoot"), "RightFoot")
        self.assertEqual(A.mirror_name("HindThighL"), "HindThighR")
        self.assertIsNone(A.mirror_name("spine"))
        self.assertEqual(A.tokens_side("foot.L"), "L")
        self.assertEqual(A.tokens_side("arm_right"), "R")
        self.assertIsNone(A.tokens_side("Body"))

    def test_easing_ratio(self):
        t = np.arange(24)
        sine = np.sin(2 * np.pi * t / 24)
        tri = np.abs((t / 24.0) * 4 % 4 - 2)
        sine_r = A.segment_ratios(sine)
        tri_r = A.segment_ratios(tri)
        self.assertTrue(sine_r and tri_r)
        self.assertAlmostEqual(A.weighted_median(sine_r), 1.57, delta=0.12)
        self.assertAlmostEqual(A.weighted_median(tri_r), 1.0, delta=0.1)

    def test_thresholds_have_reasons(self):
        for name, (value, reason) in A.THRESHOLDS.items():
            self.assertTrue(reason and len(reason) > 20, name)
        for name, (value, source, reason) in M.LIMITS.items():
            self.assertIn(source, ("Roblox", "project"), name)
            self.assertTrue(reason, name)
        self.assertEqual(M.LIMITS["max_tris_per_part"][0], 21844)


class PixelChecks(unittest.TestCase):
    def frames(self, shift_last=0, dup=False, freeze_at=None):
        out = []
        n = 25 if dup else 24
        for f in range(n):
            k = 0 if (dup and f == n - 1) else f
            ph = k / 24.0 + (shift_last if f == n - 1 else 0)
            x = int(48 + 30 * np.sin(2 * np.pi * ph))
            im = np.zeros((48, 96), dtype=np.float32)
            im[10:38, max(x - 14, 0):x + 14] = 200.0        # a wide bar: overlap changes smoothly with speed
            out.append(im)
        if freeze_at is not None:
            out[freeze_at + 1] = out[freeze_at].copy()
        return np.array(out)

    def result(self, rows, name):
        return next(r for r in rows if r.name == name).result

    def test_clean_loop(self):
        rows = A.analyse_pixels(self.frames(), 24.0)
        self.assertEqual(self.result(rows, "loop continuity"), "ok")
        self.assertEqual(self.result(rows, "frame rate"), "ok")
        self.assertEqual(self.result(rows, "foot sliding"), "n/a")

    def test_repeated_last_frame(self):
        rows = A.analyse_pixels(self.frames(dup=True), 24.0)
        self.assertEqual(self.result(rows, "loop continuity"), "check")

    def test_pop_and_hold(self):
        rows = A.analyse_pixels(self.frames(shift_last=0.4), 24.0)
        self.assertEqual(self.result(rows, "loop continuity"), "check")
        rows = A.analyse_pixels(self.frames(freeze_at=8), 24.0)
        self.assertEqual(self.result(rows, "held frames"), "check")

    def test_odd_frame_rate_and_length(self):
        rows = A.analyse_pixels(self.frames(), 23.0)
        self.assertEqual(self.result(rows, "frame rate"), "check")
        rows = A.analyse_pixels(self.frames()[:4], 240.0)
        self.assertEqual(self.result(rows, "duration"), "check")

    def test_no_action_file_is_reported(self):
        d = {"frames": [1], "fps": 24, "bones": {"a": {"parent": None, "head": [[0, 0, 0]], "tail": [[0, 0, 1]], "quat": [[1, 0, 0, 0]]}},
             "objects": {}, "action": None, "armatures": ["rig"], "keys": {}}
        rows, _, notes = A.analyse_probe(d)
        self.assertEqual(rows[0].name, "animation found")
        self.assertEqual(rows[0].result, "check")


class ModelRules(unittest.TestCase):
    """evaluate() on made-up probe numbers: no Blender needed."""

    @staticmethod
    def mesh(**over):
        m = {"name": "Body", "mesh": "Body", "parent": None, "parent_type": None, "hidden": False, "modifiers": [], "verts": 8, "edges": 18, "polys": 6,
             "box_min": [-1.75, -3.85, 0.0], "box_max": [1.75, 3.85, 6.6], "size": [3.5, 7.7, 6.6], "origin": [0.0, 0.0, 0.0],
             "scale": [1, 1, 1], "rotation_deg": [0, 0, 0], "local_scale": [1, 1, 1], "local_rotation_deg": [0, 0, 0],
             "tris": 12, "quads": 6, "ngons": 0, "open_edges": 0, "nonmanifold_edges": 0, "inconsistent_edges": 0, "loose_verts": 0, "loose_edges": 0,
             "duplicate_verts": 0, "zero_area_faces": 0, "signed_volume": 177.9, "closed": True, "shells": 1, "inside_out_shells": 0, "inside_out_tris": 0,
             "material_slots": 1, "empty_slots": 0, "faces_on_empty_slot": 0, "materials": ["Body"], "missing_images": [], "uv_layers": ["UVMap"],
             "color_attributes": [], "uv_overlap": 0.0, "uv_outside": 0.0, "vertex_groups": 0, "armature_modifier": False}
        m.update(over)
        return m

    def run_eval(self, meshes, **over):
        d = {"meshes": meshes, "armatures": [], "actions": [], "file_bytes": 100000, "kind": "blend", "blender": "x", "unit_scale": 1.0}
        d.update(over)
        return {f.name: f for f in M.evaluate(d)}

    def test_good_part_passes_everything(self):
        res = self.run_eval([self.mesh()])
        self.assertEqual([n for n, f in res.items() if f.status != "PASS"], [])

    def test_compy_reference_comes_from_the_game_data(self):
        w, h, l, src = M.reference_compy()
        self.assertEqual((w, h, l), (3.49, 6.6, 7.69))
        self.assertIn("ScaleLadder.luau", src)

    def test_each_rule(self):
        cases = [
            ("triangles per part", "FAIL", self.mesh(tris=21845)),
            ("triangles per part", "WARN", self.mesh(tris=18000)),
            ("size in studs", "FAIL", self.mesh(box_min=[-1500, 0, 0], box_max=[1500, 10, 10], size=[3000, 10, 10])),
            ("size in studs", "WARN", self.mesh(box_min=[-0.01, -0.01, 0], box_max=[0.01, 0.01, 0.02], size=[0.02, 0.02, 0.02])),
            ("pivot (origin) per part", "WARN", self.mesh(origin=[0, 0, 3.3])),
            ("pivot (origin) per part", "WARN", self.mesh(origin=[20, 0, 0])),
            ("scale and rotation applied", "WARN", self.mesh(local_scale=[2, 2, 2])),
            ("scale and rotation applied", "WARN", self.mesh(local_rotation_deg=[0, 0, 30])),
            ("face direction", "FAIL", self.mesh(inside_out_shells=1, inside_out_tris=12)),
            ("face direction", "WARN", self.mesh(inconsistent_edges=4)),
            ("loose vertices and edges", "WARN", self.mesh(loose_verts=1)),
            ("doubled vertices", "WARN", self.mesh(duplicate_verts=8)),
            ("zero-area faces", "WARN", self.mesh(zero_area_faces=2)),
            ("n-gons (faces with more than 4 corners)", "WARN", self.mesh(ngons=2)),
            ("materials and textures", "WARN", self.mesh(material_slots=0, materials=[])),
            ("materials and textures", "WARN", self.mesh(empty_slots=1)),
            ("materials and textures", "FAIL", self.mesh(missing_images=["skin.png"])),
            ("UV map", "WARN", self.mesh(uv_layers=[], uv_overlap=None, uv_outside=None)),
            ("overlapping UVs", "WARN", self.mesh(uv_overlap=0.4)),
            ("UVs outside 0..1", "WARN", self.mesh(uv_outside=0.3)),
        ]
        for name, want, m in cases:
            with self.subTest(rule=name, want=want):
                self.assertEqual(self.run_eval([m])[name].status, want)

    def test_vertex_colours_replace_a_missing_uv_map(self):
        res = self.run_eval([self.mesh(uv_layers=[], uv_overlap=None, uv_outside=None, color_attributes=["Col"])])
        self.assertEqual(res["UV map"].status, "PASS")
        self.assertIn("vertex colours", res["vertex colours"].name)
        self.assertIn("Col", res["vertex colours"].detail)

    def test_names_and_file_size(self):
        res = self.run_eval([self.mesh(name="Leg"), self.mesh(name="Leg.001")])
        self.assertEqual(res["part names"].status, "FAIL")
        res = self.run_eval([self.mesh(name="my part")])
        self.assertEqual(res["part names in scripts"].status, "WARN")
        res = self.run_eval([self.mesh(name="x" * 101)])
        self.assertEqual(res["part names"].status, "FAIL")
        self.assertEqual(self.run_eval([self.mesh()], file_bytes=12 * 1048576)["file size"].status, "WARN")
        self.assertEqual(self.run_eval([self.mesh()], file_bytes=25 * 1048576)["file size"].status, "FAIL")

    def test_bone_influences_and_armature(self):
        res = self.run_eval([self.mesh(vertex_groups=5, max_influences=6, armature_modifier=True)], armatures=[{"name": "Rig", "bones": 5}])
        self.assertEqual(res["bone influences"].status, "WARN")
        res = self.run_eval([self.mesh(armature_modifier=True)], armatures=[{"name": "Rig", "bones": 5}], actions=[{"name": "walk", "frame_range": [1, 24]}])
        self.assertIn("1 action", res["armature"].detail)
        res = self.run_eval([self.mesh()], armatures=[{"name": "Rig", "bones": 5}])
        self.assertEqual(res["armature follows mesh"].status, "WARN")

    def test_empty_file_fails(self):
        d = {"meshes": [], "armatures": [], "actions": [], "file_bytes": 1, "kind": "blend", "blender": "x"}
        self.assertEqual(M.evaluate(d)[0].status, "FAIL")


# ----------------------------------------------------------------------------------------------------------------------------------
@unittest.skipUnless(BLENDER, NO_BLENDER)
class AnimationWithBlender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="animtest_"))
        specs = ["ok", "okfbx", "loop:loop", "dup:dup", "jerk:jerk", "sink:sink", "slide:slide", "phase:phase"]
        code, text = blender_headless.run_script(ROOT / "tools/blender/make_test_walker.py", ["--multi", cls.tmp] + specs, BLENDER)
        assert code == 0 and "WALKER_OK" in text, text[-1500:]
        cls.rows = {}
        for name in ("ok", "okfbx", "loop", "dup", "jerk", "sink", "slide", "phase"):
            path = cls.tmp / ("walk_%s.%s" % (name, "fbx" if name == "okfbx" else "blend"))
            cls.rows[name] = cls.analyse(path)

    @classmethod
    def analyse(cls, path):
        j = cls.tmp / (path.stem + ".json")
        code, text = blender_headless.run_script(ROOT / "tools/blender_animation_probe.py", [path, j], BLENDER)
        assert code == 0 and j.exists(), text[-1500:]
        rows, tables, notes = A.analyse_probe(json.loads(j.read_text()))
        return {r.name: r for r in rows}

    def test_clean_walk_has_no_check(self):
        bad = [(n, r.measured) for n, r in self.rows["ok"].items() if r.result == "check"]
        self.assertEqual(bad, [])
        self.assertEqual(self.rows["ok"]["foot sliding"].result, "ok")
        self.assertEqual(self.rows["ok"]["easing"].result, "ok")
        self.assertIn("24.00", self.rows["ok"]["frame rate"].measured)
        self.assertIn("1.00 s", self.rows["ok"]["duration"].measured)

    def test_fbx_round_trip_still_judged(self):
        r = self.rows["okfbx"]
        self.assertEqual(r["loop continuity"].result, "ok")
        self.assertEqual(r["foot sliding"].result, "ok")
        self.assertEqual(r["ground penetration"].result, "ok")

    def test_pop_at_the_loop_point(self):
        r = self.rows["loop"]["loop continuity"]
        self.assertEqual(r.result, "check")
        self.assertIn("POP", r.measured)

    def test_repeated_first_frame(self):
        r = self.rows["dup"]["loop continuity"]
        self.assertEqual(r.result, "check")
        self.assertIn("repeats the first", r.measured)

    def test_jerk_spike(self):
        r = self.rows["jerk"]["jerkiness"]
        self.assertEqual(r.result, "check")
        self.assertIn("frame 9", r.measured)

    def test_ground_penetration(self):
        self.assertEqual(self.rows["sink"]["ground penetration"].result, "check")
        self.assertEqual(self.rows["ok"]["ground penetration"].result, "ok")

    def test_foot_sliding(self):
        self.assertEqual(self.rows["slide"]["foot sliding"].result, "check")

    def test_uneven_left_right_timing(self):
        self.assertEqual(self.rows["phase"]["left/right foot timing"].result, "check")
        self.assertEqual(self.rows["ok"]["left/right foot timing"].result, "ok")

    def test_each_defect_flags_its_own_row_and_the_clean_walk_does_not(self):
        wanted = {"loop": "loop continuity", "dup": "loop continuity", "jerk": "jerkiness", "sink": "ground penetration",
                  "slide": "foot sliding", "phase": "left/right foot timing"}
        for name, row in wanted.items():
            with self.subTest(defect=name):
                self.assertEqual(self.rows[name][row].result, "check")
                self.assertNotEqual(self.rows["ok"][row].result, "check")

    def test_command_line_writes_picture_and_report(self):
        out = self.tmp / "cli"
        code = quiet(A.main, [str(self.tmp / "walk_loop.blend"), "--out", str(out), "--count", "4", "--size", "128", "--strict"])
        self.assertEqual(code, 1)                                    # --strict: a "check" row makes the exit code 1
        png = out / "walk_loop_strip.png"
        self.assertTrue(png.exists())
        with Image.open(png) as im:
            self.assertEqual(im.size, (4 * 128, 128))
        text = (out / "walk_loop_report.txt").read_text(encoding="utf-8")
        self.assertIn("POP at the loop point", text)
        self.assertIn("Not judged here", text)
        code = quiet(A.main, [str(self.tmp / "walk_ok.blend"), "--out", str(out), "--count", "8", "--size", "96", "--no-render", "--strict"])
        self.assertEqual(code, 0)
        with Image.open(out / "walk_ok_strip.png") as im:
            self.assertEqual(im.size, (4 * 96, 2 * 96))


@unittest.skipUnless(FFMPEG.exists(), "ffmpeg was not found (C:/ffmpeg/bin, PATH or the FFMPEG variable): video tests skipped")
class VideoInput(unittest.TestCase):
    def test_mp4_and_image_folder(self):
        tmp = Path(tempfile.mkdtemp(prefix="vidtest_"))
        seq = tmp / "seq"
        seq.mkdir()
        for f in range(24):
            im = np.full((64, 96, 3), 230, dtype=np.uint8)
            x = int(48 + 30 * np.sin(2 * np.pi * f / 24))
            im[16:48, max(x - 14, 0):x + 14] = (200, 80, 40)
            Image.fromarray(im).save(seq / ("f_%04d.png" % (f + 1)))
        mp4 = tmp / "clip.mp4"
        subprocess.run([str(FFMPEG), "-v", "error", "-y", "-framerate", "24", "-i", str(seq / "f_%04d.png"), "-pix_fmt", "yuv420p", str(mp4)], check=True)
        for src in (seq, mp4):
            out = tmp / ("out_" + src.stem)
            self.assertEqual(quiet(A.main, [str(src), "--out", str(out), "--count", "6", "--size", "100"]), 0)
            text = next(out.glob("*_report.txt")).read_text(encoding="utf-8")
            self.assertIn("loop continuity", text)
            self.assertIn("needs bone data", text)
            png = next(out.glob("*_strip.png"))
            with Image.open(png) as im:
                self.assertEqual(im.size, (4 * 100, 2 * 100))


@unittest.skipUnless(BLENDER, NO_BLENDER)
class ModelWithBlender(unittest.TestCase):
    CASES = ["good", "flipped", "scaled", "ngon", "loose", "doubles", "nomat", "emptyslot", "uvoverlap", "nouv", "names", "heavy", "huge", "centre", "rigged"]

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="modeltest_"))
        code, text = blender_headless.run_script(ROOT / "tools/blender/make_test_models.py", [cls.tmp], BLENDER)
        assert code == 0 and "MODELS_OK" in text, text[-1500:]
        cls.probes = dict(zip(cls.CASES, M.probe_many([cls.tmp / (n + ".blend") for n in cls.CASES], BLENDER)))
        cls.res = {n: {f.name: f for f in M.evaluate(d)} for n, d in cls.probes.items()}

    def status(self, case, row):
        return self.res[case][row].status

    def test_good_box_passes_every_check(self):
        self.assertEqual([n for n, f in self.res["good"].items() if f.status != "PASS"], [])
        d = self.probes["good"]["meshes"][0]
        self.assertEqual(d["tris"], 12)
        self.assertAlmostEqual(d["size"][2], 6.6, places=3)
        self.assertIn("1.00x the Compy's height", self.res["good"]["size in studs"].detail)

    def test_each_broken_model_is_caught(self):
        expect = [
            ("flipped", "face direction", "FAIL"), ("scaled", "scale and rotation applied", "WARN"), ("ngon", "n-gons (faces with more than 4 corners)", "WARN"),
            ("loose", "loose vertices and edges", "WARN"), ("doubles", "doubled vertices", "WARN"), ("nomat", "materials and textures", "WARN"),
            ("emptyslot", "materials and textures", "WARN"), ("uvoverlap", "overlapping UVs", "WARN"), ("nouv", "UV map", "WARN"),
            ("names", "part names", "FAIL"), ("names", "part names in scripts", "WARN"), ("heavy", "triangles per part", "FAIL"),
            ("huge", "size in studs", "FAIL"), ("centre", "pivot (origin) per part", "WARN"),
        ]
        for case, row, want in expect:
            with self.subTest(case=case, row=row):
                self.assertEqual(self.status(case, row), want)

    def test_only_the_intended_rows_change(self):
        """Each defect file differs from the good one in its own row; the unrelated rows stay PASS."""
        unrelated = {"flipped": ["triangles per part", "scale and rotation applied", "materials and textures"],
                     "scaled": ["face direction", "triangles per part"], "nomat": ["face direction", "n-gons (faces with more than 4 corners)"]}
        for case, rows in unrelated.items():
            for row in rows:
                with self.subTest(case=case, row=row):
                    self.assertEqual(self.status(case, row), "PASS")

    def test_rigged_model_reports_armature_and_action(self):
        r = self.res["rigged"]["armature"]
        self.assertIn("1 armature", r.detail)
        self.assertIn("wave", r.detail)
        self.assertEqual(self.res["rigged"]["bone influences"].status, "PASS")

    def test_exit_codes_and_report(self):
        out = self.tmp / "report.txt"
        self.assertEqual(quiet(M.main, [str(self.tmp / "good.blend"), "--out", str(out)]), 0)
        self.assertIn("RESULT: PASS", out.read_text(encoding="utf-8"))
        self.assertEqual(quiet(M.main, [str(self.tmp / "heavy.blend"), str(self.tmp / "good.blend")]), 1)      # one FAIL among several files
        self.assertEqual(quiet(M.main, [str(self.tmp / "ngon.blend")]), 0)                                    # WARN only
        self.assertEqual(quiet(M.main, [str(self.tmp / "ngon.blend"), "--strict"]), 1)
        self.assertEqual(quiet(M.main, [str(self.tmp / "does_not_exist.blend")]), 2)

    def test_real_creature_file_is_read(self):
        f = ROOT / "assets/blender/creatures/fbx/creature_pteranodon.fbx"
        if not f.exists():
            self.skipTest("creature FBX not in this tree")
        d = M.probe(str(f), BLENDER)
        res = {x.name: x for x in M.evaluate(d)}
        self.assertEqual(d["meshes"][0]["tris"], 916)
        self.assertEqual(d["armatures"][0]["bones"], 12)
        self.assertEqual(res["triangles per part"].status, "PASS")


if __name__ == "__main__":
    unittest.main()
