"""Tests for tools/worktree_hygiene.py (docs/170, BD-660).

Builds a throw-away git repository in a temp folder with a local bare 'origin' and worktrees in every interesting state:
clean and pushed, dirty (untracked file), unpushed commit, locked, recent activity, loose (outside the allowed folder),
plus an unregistered copy. Nothing outside the temp folder is touched.
"""
from pathlib import Path
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import worktree_hygiene as wh  # noqa: E402

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@example.com", GIT_CONFIG_NOSYSTEM="1")


def run(cwd, *args):
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed in {cwd}: {r.stderr}")
    return r.stdout.strip()


def rmtree(path):
    def onerr(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onerror=onerr)


def age_head(path, hours):
    gd = wh.gitdir_of(Path(path))
    t = time.time() - hours * 3600
    os.utime(gd / "HEAD", (t, t))


class WorktreeHygieneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wth_")).resolve()
        self.addCleanup(rmtree, self.tmp)
        self.origin = self.tmp / "origin.git"
        run(self.tmp, "init", "-q", "--bare", "-b", "main", str(self.origin))
        self.main = self.tmp / "box" / "main"
        self.main.parent.mkdir()
        run(self.main.parent, "clone", "-q", str(self.origin), str(self.main))
        run(self.main, "checkout", "-q", "-b", "main")
        (self.main / "a.txt").write_text("a\n")
        run(self.main, "add", "a.txt")
        run(self.main, "commit", "-q", "-m", "first")
        run(self.main, "push", "-q", "origin", "main")
        (self.main / ".git" / "info" / "exclude").write_text(".claude/\n")
        self.agents = self.main / ".claude" / "worktrees"
        self.agents.mkdir(parents=True)

        self.w = {}
        self.w["clean"] = self.add("clean", commit=True, push=True)
        self.w["dirty"] = self.add("dirty", commit=True, push=True)
        (self.w["dirty"] / "unsaved.txt").write_text("not committed\n")
        self.w["unpushed"] = self.add("unpushed", commit=True, push=False)
        self.w["locked"] = self.add("locked", commit=True, push=True)
        run(self.main, "worktree", "lock", "--reason", "in use", str(self.w["locked"]))
        self.w["recent"] = self.add("recent", commit=True, push=True)
        self.w["merged"] = self.add("merged", commit=False, push=False)  # same commit as origin/main
        # a loose sibling next to the main checkout (the 2026-10-18 problem)
        self.w["loose"] = self.add("loose", commit=True, push=True, where=self.main.parent)
        # an unregistered folder that has a .git
        self.stray = self.main.parent / "stray-copy"
        self.stray.mkdir()
        run(self.stray, "init", "-q")
        for k, p in self.w.items():
            if k != "recent":
                age_head(p, 10)
        run(self.main, "fetch", "-q", "origin")

    def add(self, name, commit, push, where=None):
        path = (where or self.agents) / name
        run(self.main, "worktree", "add", "-q", "-b", f"feat-{name}", str(path), "main")
        if commit:
            (path / f"{name}.txt").write_text(name + "\n")
            run(path, "add", f"{name}.txt")
            run(path, "commit", "-q", "-m", name)
        if push:
            run(path, "push", "-q", "origin", f"feat-{name}")
        return path

    def rows(self, **kw):
        rep = wh.audit(self.main, **kw)
        return rep, {Path(r["path"]).name: r for r in rep["rows"]}

    # ---- audit ----
    def test_audit_reports_every_state(self):
        rep, rows = self.rows()
        self.assertEqual(wh.norm(rep["main"]), wh.norm(self.main))
        self.assertTrue(rows["main"]["is_main"])
        self.assertEqual(rows["clean"]["dirty"], [])
        self.assertEqual(rows["clean"]["unpushed"], 0)
        self.assertGreater(rows["clean"]["size_bytes"], 0)
        self.assertEqual(len(rows["dirty"]["dirty"]), 1)
        self.assertIn("unsaved.txt", rows["dirty"]["dirty"][0])
        self.assertEqual(rows["unpushed"]["unpushed"], 1)
        self.assertTrue(rows["locked"]["locked"])
        self.assertEqual(rows["locked"]["lock_reason"], "in use")
        self.assertTrue(rows["merged"]["in_main"])
        self.assertFalse(rows["clean"]["in_main"])
        self.assertLess(rows["recent"]["age_hours"], 1)
        self.assertGreater(rows["clean"]["age_hours"], 9)
        self.assertEqual(rows["clean"]["branch"], "feat-clean")

    def test_loose_and_unregistered_are_flagged(self):
        rep, rows = self.rows()
        self.assertTrue(rows["clean"]["allowed"])
        self.assertFalse(rows["loose"]["allowed"])
        self.assertEqual([wh.norm(u["path"]) for u in rep["unregistered"]], [wh.norm(self.stray)])
        t = wh.totals(rep, 6)
        self.assertEqual(t["loose"], 1)
        self.assertEqual(t["unsaved"], 1)
        self.assertEqual(t["unpushed"], 1)
        self.assertEqual(t["locked"], 1)
        self.assertEqual(t["unregistered"], 1)

    def test_scratchpad_path_counts_as_allowed(self):
        p = Path("C:/Users/x/AppData/Local/Temp/claude/proj/abc/scratchpad/tool1")
        self.assertTrue(wh.in_allowed_place(p, self.main))
        self.assertFalse(wh.in_allowed_place(Path("C:/Users/x/Documents/be-dino-copy"), self.main))

    def test_blockers(self):
        _, rows = self.rows()
        self.assertEqual(wh.blockers(rows["clean"], 6), [])
        self.assertEqual(wh.blockers(rows["merged"], 6), [])
        self.assertEqual(wh.blockers(rows["loose"], 6), [])  # loose is flagged, but a clean loose copy is removable
        self.assertTrue(any("unsaved" in b for b in wh.blockers(rows["dirty"], 6)))
        self.assertTrue(any("unpushed" in b for b in wh.blockers(rows["unpushed"], 6)))
        self.assertTrue(any("locked" in b for b in wh.blockers(rows["locked"], 6)))
        self.assertTrue(any("recent" in b for b in wh.blockers(rows["recent"], 6)))
        self.assertEqual(wh.blockers(rows["recent"], 0), [])
        self.assertEqual(wh.blockers(rows["main"], 6), ["main checkout"])
        self.assertTrue(any("--keep" in b for b in wh.blockers(rows["clean"], 6, keep=["worktrees/CLEAN"])))

    def test_audit_cli_prints_table_and_totals_and_writes_md(self):
        md = self.tmp / "out" / "audit.md"
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "worktree_hygiene.py"), "--repo", str(self.main), "audit",
                            "--md", str(md)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        for word in ("UNSAVED", "UNPUSHED", "LOOSE", "stray-copy", "safe to remove", "unregistered folders"):
            self.assertIn(word, r.stdout)
        self.assertIn("unsaved.txt", md.read_text(encoding="utf-8"))

    # ---- clean ----
    def test_clean_dry_run_removes_nothing(self):
        lines = []
        res = wh.clean(self.main, go=False, log=lines.append)
        self.assertEqual(sorted(Path(p).name for p in res["candidates"]), ["clean", "loose", "merged"])
        self.assertEqual(res["removed"], [])
        for p in self.w.values():
            self.assertTrue(p.exists())
        self.assertTrue(any("dry run" in ln.lower() for ln in lines))

    def test_clean_go_removes_only_safe_worktrees_and_keeps_branches(self):
        res = wh.clean(self.main, go=True, log=lambda s: None)
        self.assertEqual(sorted(Path(p).name for p in res["removed"]), ["clean", "loose", "merged"])
        self.assertEqual(res["failed"], [])
        for name in ("clean", "loose", "merged"):
            self.assertFalse(self.w[name].exists(), name)
        for name in ("dirty", "unpushed", "locked", "recent"):
            self.assertTrue(self.w[name].exists(), name)
        self.assertTrue((self.w["dirty"] / "unsaved.txt").exists())
        self.assertTrue(self.main.exists())
        self.assertTrue(self.stray.exists())
        branches = run(self.main, "branch", "--list").split()
        for name in ("clean", "loose", "merged", "dirty", "unpushed", "locked", "recent"):
            self.assertIn(f"feat-{name}", branches)

    def test_clean_min_age_zero_includes_recent(self):
        res = wh.clean(self.main, go=False, min_age_hours=0, log=lambda s: None)
        self.assertIn("recent", [Path(p).name for p in res["candidates"]])
        self.assertNotIn("locked", [Path(p).name for p in res["candidates"]])

    def test_clean_rechecks_dirty_right_before_removal(self):
        real_git = wh.git
        target = str(self.w["clean"])

        def sneaky(repo, *args, **kw):
            # the moment clean re-checks this worktree, a helper saves a new file in it
            if args[:1] == ("status",) and "--ignored=traditional" not in args and wh.slash(repo) == wh.slash(target):
                (self.w["clean"] / "late.txt").write_text("late\n")
            return real_git(repo, *args, **kw)

        wh.git = sneaky
        try:
            res = wh.clean(self.main, go=True, log=lambda s: None)
        finally:
            wh.git = real_git
        self.assertTrue(self.w["clean"].exists())
        self.assertTrue((self.w["clean"] / "late.txt").exists())
        self.assertNotIn(target, [wh.slash(p) for p in res["removed"]])
        self.assertFalse(self.w["merged"].exists())

    def test_clean_never_forces_prunes_or_touches_branches_and_config(self):
        real_git = wh.git
        calls = []

        def spy(repo, *args, **kw):
            calls.append(args)
            return real_git(repo, *args, **kw)

        wh.git = spy
        try:
            wh.clean(self.main, go=True, log=lambda s: None)
        finally:
            wh.git = real_git
        flat = [a for c in calls for a in c]
        for bad in ("--force", "-f", "-D", "config", "reset", "clean", "checkout", "gc"):
            self.assertNotIn(bad, flat)
        self.assertNotIn(("worktree", "prune"), [c[:2] for c in calls])
        removes = [c for c in calls if c[:2] == ("worktree", "remove")]
        self.assertEqual(len(removes), 3)
        for c in removes:
            self.assertEqual(len(c), 3)  # worktree remove <path>, nothing else
        src = (ROOT / "tools" / "worktree_hygiene.py").read_text(encoding="utf-8")
        for bad in ("rmtree", "rm -rf", "os.remove", "os.unlink", "shutil"):
            self.assertNotIn(bad, src)

    def test_clean_refuses_main_checkout_even_when_asked_from_a_worktree(self):
        res = wh.clean(self.w["clean"], go=True, log=lambda s: None)  # --repo points inside a worktree
        self.assertTrue(self.main.exists())
        self.assertNotIn(wh.slash(self.main), [wh.slash(p) for p in res["removed"]])

    def test_default_is_dry_run_in_the_command_line(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "worktree_hygiene.py"), "--repo", str(self.main), "clean"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("DRY RUN", r.stdout)
        self.assertTrue(self.w["clean"].exists())

    # ---- prune-report ----
    def test_prune_report_lists_missing_folder_and_changes_nothing(self):
        self.assertEqual(wh.prune_report(self.main), [])
        rmtree(self.w["merged"])  # a folder deleted by hand: git still has the record
        before = run(self.main, "worktree", "list", "--porcelain")
        lines = wh.prune_report(self.main)
        self.assertEqual(len(lines), 1)
        self.assertIn("merged", lines[0])
        self.assertEqual(run(self.main, "worktree", "list", "--porcelain"), before)
        rep, rows = self.rows()
        self.assertFalse(rows["merged"]["exists"])
        self.assertTrue(any("missing" in b for b in wh.blockers(rows["merged"], 6)))


if __name__ == "__main__":
    unittest.main()
