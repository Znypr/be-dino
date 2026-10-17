"""tools/next_bd_id.py and tools/verify_kanban_merge.py against throwaway git repos."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import next_bd_id  # noqa: E402
import verify_kanban_merge as vkm  # noqa: E402


def row(n, status="Backlog", text=None):
    return "| BD-%d | %s | P2 | %s | None |" % (n, status, text or "Task number %d does something" % n)


def kanban(rows):
    return "# Kanban\n\n| ID | Status | Priority | Task | Dependencies |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n"


class Repo:
    def __init__(self, path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.git("init", "-q", "-b", "main")
        (self.path / "docs").mkdir(exist_ok=True)

    def git(self, *a):
        p = subprocess.run(["git", "-C", str(self.path), "-c", "user.name=t", "-c", "user.email=t@t",
                            "-c", "commit.gpgsign=false", *a], capture_output=True)
        if p.returncode:
            raise AssertionError(p.stderr.decode())
        return p.stdout.decode().strip()

    def write(self, rows, name="07-kanban.md"):
        (self.path / "docs" / name).write_text(kanban(rows), encoding="utf-8", newline="\n")

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)


class KanbanMergeCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.r = Repo(self.tmp.name)
        vkm.ROOT = self.r.path
        self.r.write([row(1), row(2, "Review / test"), row(3)])
        self.r.commit("v1")
        self.r.git("branch", "feature")  # feature starts here
        self.r.write([row(1), row(2, "Done", "Task number 2 does something, shipped"), row(3), row(4, text="Wolf howl")])
        self.r.commit("main moves on: BD-2 updated, BD-4 added")

    def run_check(self):
        mb, dupes, stale, notes = vkm.check("main", "feature")
        return dupes, stale, notes

    def test_clean_branch_passes_and_behind_row_is_only_a_note(self):
        self.r.git("checkout", "-q", "feature")
        self.r.write([row(1), row(2, "Review / test"), row(3), row(5, text="My own new task")])
        self.r.commit("add BD-5")
        dupes, stale, notes = self.run_check()
        self.assertEqual((dupes, stale), ([], []))
        self.assertIn("BD-2", notes)  # behind main but untouched: git merges it cleanly

    def test_same_id_added_twice_fails(self):
        self.r.git("checkout", "-q", "feature")
        self.r.write([row(1), row(2, "Review / test"), row(3), row(4, text="Sound lab polish")])
        self.r.commit("also claim BD-4")
        dupes, stale, _ = self.run_check()
        self.assertEqual([d[0] for d in dupes], ["BD-4"])
        self.assertEqual(stale, [])

    def test_same_id_same_title_is_not_a_duplicate(self):
        self.r.git("checkout", "-q", "feature")
        self.r.write([row(1), row(2, "Review / test"), row(3), row(4, text="Wolf howl")])
        self.r.commit("same row as main")
        dupes, _, _ = self.run_check()
        self.assertEqual(dupes, [])

    def test_stale_row_put_back_by_merge_resolution_fails_and_fix_repairs_it(self):
        self.r.git("checkout", "-q", "feature")
        self.r.write([row(1), row(2, "Review / test"), row(3), row(5, text="mine")])
        self.r.commit("add BD-5")
        # merge main, then resolve "taking my side" for the whole table: BD-2 goes back to its old text
        self.r.git("merge", "-q", "-s", "ours", "main")
        dupes, stale, _ = self.run_check()
        # the 'ours' merge keeps feature's BD-2 (old) and lacks BD-4; BD-2 differs from main and is an old version
        self.assertEqual([s[0] for s in stale], ["BD-2"])
        vkm.apply_fix("main", stale)
        fixed = vkm.rows_of((self.r.path / "docs" / "07-kanban.md").read_text(encoding="utf-8"))
        self.assertIn("shipped", fixed["BD-2"])

    def test_own_new_edit_of_a_row_is_not_stale(self):
        self.r.git("checkout", "-q", "feature")
        self.r.write([row(1, "Done", "Task number 1 does something, my evidence"), row(2, "Review / test"), row(3)])
        self.r.commit("update BD-1")
        _, stale, _ = self.run_check()
        self.assertEqual(stale, [])


class NextId(unittest.TestCase):
    def test_next_id_sees_main_open_pr_branch_and_reservations(self):
        with tempfile.TemporaryDirectory() as tmp:
            origin = Repo(Path(tmp) / "origin")
            origin.write([row(10), row(11)])
            origin.commit("main")
            origin.git("checkout", "-q", "-b", "pr-branch")
            origin.write([row(10), row(11), row(15, text="claimed in a PR")])
            (origin.path / "docs" / "99-notes.md").write_text("mentions BD-17 here\n", encoding="utf-8")
            origin.commit("pr")
            origin.git("checkout", "-q", "main")
            clone = Path(tmp) / "clone"
            subprocess.run(["git", "clone", "-q", str(origin.path), str(clone)], check=True, capture_output=True)
            old_root, old_prs = next_bd_id.ROOT, next_bd_id.open_prs
            next_bd_id.ROOT = clone
            next_bd_id.open_prs = lambda: ([{"number": 7, "headRefName": "pr-branch", "title": "BD-16: a thing"}], None)
            try:
                notes = []
                used, top, _ = next_bd_id.collect("bd", notes)
                self.assertEqual(max(used), 17)  # BD-17 only in a doc on the PR branch
                self.assertIn(16, used)          # from the PR title
                self.assertEqual(notes, [])
                # without gh: main + worktrees only, with a warning
                next_bd_id.open_prs = lambda: (None, "gh not available")
                notes = []
                used, _, _ = next_bd_id.collect("bd", notes)
                self.assertEqual(max(used), 11)
                self.assertTrue(any("NOT open PRs" in n for n in notes))
            finally:
                next_bd_id.ROOT, next_bd_id.open_prs = old_root, old_prs


if __name__ == "__main__":
    unittest.main()
