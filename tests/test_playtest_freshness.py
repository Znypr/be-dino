"""BD-1043: playtest build stamp (tools/build.py) and freshness check (tools/playtest_freshness.py)."""
import contextlib
import importlib.util
import io
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


packager = load("build")
fresh = load("playtest_freshness")
SOURCE = (ROOT / "src/shared/Config.luau").read_text(encoding="utf-8")
COMMIT = "1b5576fd" + "0" * 32


class StampTests(unittest.TestCase):
    def test_short_commit_is_empty_safe(self):
        self.assertEqual(packager.short_commit(None), "")
        self.assertEqual(packager.short_commit("not-a-hash"), "")
        self.assertEqual(packager.short_commit(COMMIT), "1b5576fd")
        self.assertEqual(packager.short_commit(COMMIT, True), "1b5576fd*")

    def test_empty_stamp_leaves_source_unchanged(self):
        self.assertEqual(packager.stamp_build_label(SOURCE, ""), SOURCE)

    def test_stamp_changes_only_the_build_line(self):
        stamped = packager.stamp_build_label(SOURCE, "1b5576fd")
        before, after = SOURCE.splitlines(), stamped.splitlines()
        self.assertEqual(len(before), len(after))
        changed = [(a, b) for a, b in zip(before, after) if a != b]
        self.assertEqual(len(changed), 1)
        self.assertRegex(changed[0][1], r'^    Build = "redesign-\d+ 1b5576fd",')

    def test_unsafe_stamp_refused(self):
        with self.assertRaises(ValueError):
            packager.stamp_build_label(SOURCE, '1b5576fd"; evil')

    def test_playtest_place_carries_stamp_default_does_not(self):
        import xml.etree.ElementTree as ET
        data, _, report = packager.build_profile("playtest", stamp="1b5576fd")
        self.assertTrue(report.ok, report.errors)
        self.assertRegex(self.config_of(data), r'Build = "redesign-\d+ 1b5576fd",')
        plain, _, _ = packager.build_profile("playtest")
        self.assertNotRegex(self.config_of(plain), r'Build = "redesign-\d+ ')
        default, _ = packager.build()
        self.assertNotRegex(self.config_of(default), r'Build = "redesign-\d+ ')
        self.assertEqual(default, packager.build()[0])

    def test_other_profiles_are_not_stamped(self):
        data, _, _ = packager.build_profile("all-on-rehearsal", stamp="1b5576fd")
        self.assertNotRegex(self.config_of(data), r'Build = "redesign-\d+ ')

    @staticmethod
    def config_of(data):
        import xml.etree.ElementTree as ET
        for node in ET.fromstring(data).iter("ProtectedString"):
            if node.text and "Build = " in node.text and "WalkSpeed" in node.text:
                return node.text
        raise AssertionError("Config not found in place")


class FreshnessTests(unittest.TestCase):
    def make_repo(self, directory):
        def git(*args):
            subprocess.run(["git", *args], cwd=directory, check=True, capture_output=True)
        git("init", "-q", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "t")
        git("config", "commit.gpgsign", "false")
        shas = []
        for subject in ["Start", "Feature one (BD-100)", "Docs only", "Feature two (BD-101)"]:
            (Path(directory) / "f.txt").write_text(subject)
            git("add", "-A")
            git("commit", "-q", "-m", subject)
            shas.append(subprocess.run(["git", "rev-parse", "HEAD"], cwd=directory, capture_output=True, text=True).stdout.strip())
        return shas

    def test_behind_counts_and_lists_feature_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            shas = self.make_repo(tmp)
            count, subjects = fresh.behind(shas[0], "main", Path(tmp))
            self.assertEqual(count, 3)
            self.assertEqual(fresh.feature_rows(subjects), ["Feature two (BD-101)", "Feature one (BD-100)"])
            self.assertEqual(fresh.behind(shas[3], "main", Path(tmp))[0], 0)
            with self.assertRaises(fresh.Unknown):
                fresh.behind("f" * 40, "main", Path(tmp))

    def test_report_text(self):
        self.assertEqual(fresh.report(0, [], False), ["up to date"])
        lines = fresh.report(3, ["Feature two (BD-101)", "Docs only"], True)
        self.assertEqual(lines[0], "3 commits behind origin/main")
        self.assertIn("  - Feature two (BD-101)", lines)
        self.assertNotIn("  - Docs only", lines)
        self.assertTrue(any("uncommitted" in line for line in lines))
        self.assertEqual(fresh.report(1, [], False)[0], "1 commit behind origin/main")

    def test_read_stamp_from_manifest_and_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            place = Path(tmp) / "x-playtest.rbxlx"
            place.write_text('    Build = "redesign-020 abcdef12*",\n')
            self.assertEqual(fresh.read_stamp(place), ("abcdef12", True, "x-playtest.rbxlx"))
            place.with_suffix(".manifest.json").write_text(json.dumps({"git_commit": COMMIT, "git_dirty": False}))
            self.assertEqual(fresh.read_stamp(place), (COMMIT, False, "x-playtest.manifest.json"))
            self.assertEqual(fresh.read_stamp(place.with_suffix(".manifest.json"))[0], COMMIT)
            plain = Path(tmp) / "plain.rbxlx"
            plain.write_text('    Build = "redesign-020",\n')
            with self.assertRaises(fresh.Unknown):
                fresh.read_stamp(plain)

    def test_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            plain = Path(tmp) / "plain.rbxlx"
            plain.write_text('    Build = "redesign-020",\n')
            self.assertEqual(fresh.main([str(plain)]), 2)
            self.assertEqual(fresh.main([str(plain), "--warn-only"]), 0)
            self.assertEqual(fresh.main([str(Path(tmp) / "missing.rbxlx")]), 2)
            head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
            ok = Path(tmp) / "ok.manifest.json"
            ok.write_text(json.dumps({"git_commit": head, "git_dirty": False}))
            # HEAD is never behind itself when compared with itself
            self.assertEqual(fresh.main([str(ok), "--ref", "HEAD"]), 0)
            old = Path(tmp) / "old.manifest.json"
            first = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.split()[0]
            old.write_text(json.dumps({"git_commit": first, "git_dirty": False}))
            self.assertEqual(fresh.main([str(old), "--ref", "HEAD"]), 1)
            self.assertEqual(fresh.main([str(old), "--ref", "HEAD", "--warn-only"]), 0)


if __name__ == "__main__":
    unittest.main()
