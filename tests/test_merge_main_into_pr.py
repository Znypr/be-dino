"""tools/merge_main_into_pr.py against throwaway git repos (a bare 'origin', a dev clone, a tool clone)."""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import merge_main_into_pr as mm  # noqa: E402

ROW_HEAD = "| ID | Status | Priority | Task | Dependencies |\n|---|---|---|---|---|\n"


def row(n, status="Backlog", text=None):
    return "| BD-%d | %s | P2 | %s | None |" % (n, status, text or "**Task %d.** does something" % n)


def kanban(rows, eol="\n"):
    return ("# Kanban\n\nSome intro text.\n\n" + ROW_HEAD + "\n".join(rows) + "\n").replace("\n", eol)


class Env:
    """origin (bare) + dev (where history is made) + tool (the clone the helper runs in)."""

    def __init__(self, root, with_verifier=True, eol="\n"):
        self.root, self.eol = Path(root), eol
        cfg = self.root / "gitconfig"
        cfg.write_text("[user]\n name = t\n email = t@t\n[core]\n autocrlf = false\n[commit]\n gpgsign = false\n"
                       "[init]\n defaultBranch = main\n", encoding="utf-8")
        self.old_env = {k: os.environ.get(k) for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM")}
        os.environ["GIT_CONFIG_GLOBAL"], os.environ["GIT_CONFIG_NOSYSTEM"] = str(cfg), "1"
        self.origin, self.dev, self.tool = self.root / "origin.git", self.root / "dev", self.root / "tool"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True)
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.dev)], check=True, capture_output=True)
        (self.dev / "docs").mkdir()
        (self.dev / "tools").mkdir()
        if with_verifier:
            shutil.copy(TOOLS / "verify_kanban_merge.py", self.dev / "tools" / "verify_kanban_merge.py")

    def restore_env(self):
        for k, v in self.old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def git(self, *a, cwd=None):
        p = subprocess.run(["git", "-C", str(cwd or self.dev), *a], capture_output=True)
        if p.returncode:
            raise AssertionError("git %s: %s" % (a, p.stderr.decode()))
        return p.stdout.decode().strip()

    def write(self, name, text):
        p = self.dev / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def start_branch(self, name):
        self.git("checkout", "-q", "-b", name)

    def publish(self):
        self.git("push", "-q", "origin", "main")
        for b in self.git("branch", "--format=%(refname:short)").split():
            if b != "main":
                self.git("push", "-q", "origin", b)
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.tool)], check=True, capture_output=True)

    def run(self, branch, *flags):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mm.main([branch, "--repo", str(self.tool), *flags])
        return rc, buf.getvalue()

    def worktree_of(self, out):
        for line in out.splitlines():
            if line.startswith("throwaway worktree: "):
                return Path(line.split(": ", 1)[1].split(" (detached")[0])
        raise AssertionError("no worktree line in:\n" + out)


class MergeHelperBase(unittest.TestCase):
    eol = "\n"
    with_verifier = True

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = Env(self.tmp.name, self.with_verifier, self.eol)
        self.addCleanup(self.env.restore_env)

    def kan(self, rows):
        return kanban(rows, self.eol)

    def base_board(self, extra=()):
        e = self.env
        e.write("docs/07-kanban.md", self.kan([row(i) for i in range(1, 6)] + list(extra)))
        e.commit("base")
        e.git("push", "-q", "origin", "main")

    def final_rows(self, wt):
        raw = (wt / "docs" / "07-kanban.md").read_bytes().decode("utf-8")
        return raw, mm.vkm.rows_of(raw)


class KanbanMergeTests(MergeHelperBase):
    def build_standard(self):
        """base 1-5; main edits BD-2 and appends BD-10; the PR edits BD-4 and appends BD-11."""
        e = self.env
        self.base_board()
        e.start_branch("pr")
        e.write("docs/07-kanban.md", self.kan([row(1), row(2), row(3), row(4, "Review / test", "**Task 4.** does something, PR evidence"),
                                              row(5), row(11, text="**PR new task.**")]))
        e.commit("pr work")
        e.git("checkout", "-q", "main")
        e.write("docs/07-kanban.md", self.kan([row(1), row(2, "Done", "**Task 2.** does something, shipped on main"),
                                              row(3), row(4), row(5), row(10, text="**Main new task.**")]))
        e.commit("main moves")
        e.publish()

    def test_both_sides_add_rows_and_edit_different_rows(self):
        self.build_standard()
        rc, out = self.env.run("pr")
        self.assertEqual(rc, 0, out)
        self.assertIn("DRY RUN", out)
        wt = self.env.worktree_of(out)
        raw, rows = self.final_rows(wt)
        self.assertNotIn("<<<<<<<", raw)
        self.assertEqual(sorted(rows), ["BD-1", "BD-10", "BD-11", "BD-2", "BD-3", "BD-4", "BD-5"])
        self.assertIn("shipped on main", rows["BD-2"])      # main's edit, PR did not touch it
        self.assertIn("PR evidence", rows["BD-4"])          # PR's edit, main did not touch it
        msg = self.env.git("log", "-1", "--format=%B", cwd=wt)
        self.assertTrue(msg.rstrip().endswith("Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"), msg)
        self.assertEqual(len(self.env.git("log", "-1", "--format=%P", cwd=wt).split()), 2)  # a real merge commit
        self.assertIn("kanban merge check ok", out)
        # dry run: origin's PR branch is untouched, and the worktree is still there
        self.assertEqual(self.env.git("rev-parse", "origin/pr", cwd=self.env.tool),
                         self.env.git("rev-parse", "refs/heads/pr", cwd=self.env.origin))
        self.assertNotEqual(self.env.git("rev-parse", "HEAD", cwd=wt), self.env.git("rev-parse", "refs/heads/pr", cwd=self.env.origin))
        self.assertTrue(wt.exists())

    def test_push_updates_branch_and_removes_worktree(self):
        self.build_standard()
        rc, out = self.env.run("pr", "--push")
        self.assertEqual(rc, 0, out)
        wt = self.env.worktree_of(out)
        self.assertIn("pushed: git push origin HEAD:pr", out)
        self.assertFalse(wt.exists())
        tip = self.env.git("log", "-1", "--format=%s", "refs/heads/pr", cwd=self.env.origin)
        self.assertEqual(tip, "Merge origin/main into pr")
        # a second run finds nothing to do
        rc, out = self.env.run("pr")
        self.assertEqual(rc, 0)
        self.assertIn("nothing to merge", out)

    def test_auto_merge_needs_push(self):
        self.build_standard()
        rc, out = self.env.run("pr", "--auto-merge")
        self.assertEqual(rc, 2)
        self.assertIn("--auto-merge needs --push", out)

    def test_title_changed_on_existing_row_warns_with_the_fix(self):
        e = self.env
        self.base_board()
        e.start_branch("pr")
        e.write("docs/07-kanban.md", self.kan([row(1), row(2), row(3), row(4, text="**A brand new title.** does something"), row(5)]))
        e.commit("retitle BD-4")
        e.git("checkout", "-q", "main")
        e.write("docs/07-kanban.md", self.kan([row(1), row(2, "Done", "**Task 2.** shipped"), row(3), row(4), row(5)]))
        e.commit("main moves")
        e.publish()
        rc, out = self.env.run("pr")
        self.assertIn("WARNING BD-4: the PR changed the title of an existing row", out)
        self.assertIn("Keep the ORIGINAL title and append the outcome", out)

    def test_same_id_new_on_both_sides_with_different_titles_stops(self):
        e = self.env
        self.base_board()
        e.start_branch("pr")
        e.write("docs/07-kanban.md", self.kan([row(i) for i in range(1, 6)] + [row(20, text="**Wolf howl.**")]))
        e.commit("pr adds 20")
        e.git("checkout", "-q", "main")
        e.write("docs/07-kanban.md", self.kan([row(i) for i in range(1, 6)] + [row(20, text="**Sound lab polish.**")]))
        e.commit("main adds 20")
        e.publish()
        rc, out = self.env.run("pr")
        self.assertEqual(rc, 3, out)
        self.assertIn("id collision", out)
        self.assertIn("next_bd_id.py", out)

    def test_clean_git_merge_still_checks_the_board(self):
        e = self.env
        self.base_board()
        e.start_branch("pr")
        e.write("docs/07-kanban.md", self.kan([row(1, "Done", "**Task 1.** ok"), row(2), row(3), row(4), row(5)]))
        e.commit("pr edits BD-1")
        e.git("checkout", "-q", "main")
        e.write("docs/07-kanban.md", self.kan([row(1), row(2), row(3), row(4), row(5, "Done", "**Task 5.** ok")]))
        e.commit("main edits BD-5")
        e.publish()
        rc, out = self.env.run("pr")
        self.assertEqual(rc, 0, out)
        self.assertIn("merge of origin/main: clean", out)
        _, rows = self.final_rows(self.env.worktree_of(out))
        self.assertIn("Done", rows["BD-1"])
        self.assertIn("Done", rows["BD-5"])


class CrlfTests(KanbanMergeTests):
    eol = "\r\n"

    def test_crlf_file_stays_crlf_and_resolves(self):
        self.build_standard()
        rc, out = self.env.run("pr")
        self.assertEqual(rc, 0, out)
        raw, rows = self.final_rows(self.env.worktree_of(out))
        self.assertIn("\r\n", raw)
        self.assertFalse(raw.replace("\r\n", "").count("\n"), "a bare LF crept into a CRLF file")
        self.assertEqual(sorted(rows), ["BD-1", "BD-10", "BD-11", "BD-2", "BD-3", "BD-4", "BD-5"])


class NoVerifierInTree(MergeHelperBase):
    with_verifier = False

    def test_falls_back_to_the_built_in_board_check(self):
        e = self.env
        self.base_board()
        e.start_branch("pr")
        e.write("docs/07-kanban.md", self.kan([row(i) for i in range(1, 6)] + [row(11)]))
        e.commit("pr")
        e.git("checkout", "-q", "main")
        e.write("docs/07-kanban.md", self.kan([row(i) for i in range(1, 6)] + [row(10)]))
        e.commit("main")
        e.publish()
        rc, out = self.env.run("pr")
        self.assertEqual(rc, 0, out)
        self.assertIn("verify_kanban_merge (built-in copy): ok", out)


class OtherFilesTests(MergeHelperBase):
    def two_sided(self, name, base, pr, main_):
        e = self.env
        self.base_board()
        e.write(name, base)
        e.commit("doc base")
        e.git("push", "-q", "origin", "main")
        e.start_branch("pr")
        e.write(name, pr)
        e.commit("pr doc")
        e.git("checkout", "-q", "main")
        e.write(name, main_)
        e.commit("main doc")
        e.publish()

    def test_unknown_file_stops_and_shows_the_hunks(self):
        self.two_sided("docs/notes.txt", "a\nb\nc\n", "a\nPR\nc\n", "a\nMAIN\nc\n")
        rc, out = self.env.run("pr")
        self.assertEqual(rc, 3, out)
        self.assertIn("docs/notes.txt: not on the allowlist", out)
        self.assertIn("PR  | PR", out)
        self.assertIn("main| MAIN", out)
        wt = self.env.worktree_of(out)
        self.assertTrue(wt.exists())
        self.assertEqual(self.env.git("log", "-1", "--format=%s", cwd=wt), "pr doc")  # nothing committed
        self.assertTrue(self.env.git("rev-parse", "-q", "--verify", "MERGE_HEAD", cwd=wt))  # merge left open

    def table(self, rows):
        return "# Audit\n\n| Id | Sev | Finding |\n| --- | --- | --- |\n" + "\n".join(rows) + "\n"

    def test_table_rows_where_each_side_changed_a_different_row_merge(self):
        base = [f"| F{i} | P2 | finding {i} |" for i in range(1, 5)]
        pr = base[:2] + ["| F3 | P2 | finding 3, fixed by PR |"] + base[3:] + ["| F9 | P3 | PR extra |"]
        main_ = [base[0], "| F2 | P2 | finding 2, fixed on main |"] + base[2:] + ["| F8 | P3 | main extra |"]
        self.two_sided("docs/151-audit.md", self.table(base), self.table(pr), self.table(main_))
        rc, out = self.env.run("pr")
        self.assertEqual(rc, 0, out)
        self.assertIn("allowlist", out)
        text = (self.env.worktree_of(out) / "docs" / "151-audit.md").read_text(encoding="utf-8")
        self.assertNotIn("<<<<<<<", text)
        for want in ("fixed on main", "fixed by PR", "F8 | P3 | main extra", "F9 | P3 | PR extra"):
            self.assertIn(want, text)
        self.assertEqual(text.count("| F2 |"), 1)

    def test_table_row_edited_on_both_sides_goes_to_a_human(self):
        base = [f"| F{i} | P2 | finding {i} |" for i in range(1, 4)]
        pr = [base[0], "| F2 | P2 | PR version |", base[2]]
        main_ = [base[0], "| F2 | P2 | main version |", base[2]]
        self.two_sided("docs/151-audit.md", self.table(base), self.table(pr), self.table(main_))
        rc, out = self.env.run("pr")
        self.assertEqual(rc, 3, out)
        self.assertIn("both sides changed row 'F2' differently", out)


class UnitTests(unittest.TestCase):
    def test_pr_edit_wins_only_if_pr_changed_the_row(self):
        base = {"BD-1": row(1), "BD-2": row(2), "BD-3": row(3)}
        ours = [row(1, "Done"), row(2), row(7)]
        theirs = [row(1), row(2, "Done"), row(3, "Done"), row(8)]
        rep = mm.KanbanReport()
        out = mm.resolve_kanban_hunk(ours, theirs, base, rep)
        self.assertEqual(out[0], row(1, "Done"))   # PR changed it
        self.assertEqual(out[1], row(2, "Done"))   # PR left it: main's
        self.assertEqual(out[2], row(3, "Done"))
        self.assertEqual(out[3], row(8))
        self.assertEqual(out[4], row(7))           # PR-only row kept
        self.assertEqual(sorted(rep.kept_pr), ["BD-1"])
        self.assertEqual(sorted(rep.took_main), ["BD-2"])

    def test_both_changed_keeps_pr_and_flags_it(self):
        base = {"BD-1": row(1)}
        rep = mm.KanbanReport()
        out = mm.resolve_kanban_hunk([row(1, "Done")], [row(1, "Review / test")], base, rep)
        self.assertEqual(out, [row(1, "Done")])
        self.assertEqual(rep.both_changed, ["BD-1"])

    def test_non_row_hunk_takes_main(self):
        rep = mm.KanbanReport()
        out = mm.resolve_kanban_hunk(["Counts: old"], ["Counts: new"], {}, rep)
        self.assertEqual(out, ["Counts: new"])
        self.assertEqual(rep.nonrow_hunks, 1)
        self.assertEqual(rep.dropped_text, [["Counts: old"]])

    def test_duplicate_rows_keep_the_pr_edit_else_the_longest(self):
        base = {"BD-1": row(1), "BD-2": row(2)}
        main_text = kanban([row(1), row(2, text="**Task 2.** short")])
        text = kanban([row(1), row(1, "Done", "**Task 1.** PR evidence"), row(2, text="**Task 2.** short"),
                       row(2, text="**Task 2.** a much longer duplicate copy of the row")])
        rep = mm.KanbanReport()
        new = mm.dedupe_rows(text, main_text, base, rep)
        rows = mm.vkm.rows_of(new)
        self.assertEqual(new.count("| BD-1 |"), 1)
        self.assertEqual(new.count("| BD-2 |"), 1)
        self.assertIn("PR evidence", rows["BD-1"])
        self.assertIn("much longer", rows["BD-2"])
        self.assertEqual(sorted(rep.deduped), ["BD-1", "BD-2"])

    def test_title_warning_for_collision_lookalike(self):
        main_rows = {"BD-9": row(9, text="**Main title.** x")}
        warns = mm.title_warnings(kanban([row(9, text="**Other title.** y")]), main_rows, {})
        self.assertEqual(len(warns), 1)
        self.assertIn("id collision", warns[0])
        self.assertIn("append your outcome at the END", warns[0])

    def test_same_title_longer_tail_gives_no_title_warning(self):
        long_title = "**A long and descriptive title of the task that goes past the seventy character window.**"
        main_rows = {"BD-9": row(9, text=long_title + " Details.")}
        mine = kanban([row(9, text=long_title + " Details. Outcome: done, with evidence.")])
        self.assertEqual(mm.title_warnings(mine, main_rows, {}), [])


if __name__ == "__main__":
    unittest.main()
