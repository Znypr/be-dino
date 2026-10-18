"""tools/merge_train.py against throwaway git repos (a bare 'origin', a dev clone, a tool clone) and a fake gh.

No network, no real gh, nothing that only exists on the owner PC.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_train as mt  # noqa: E402
from test_merge_main_into_pr import Env, kanban, row  # noqa: E402

TRAIN_PR_URL = "https://github.com/Znypr/be-dino/pull/900"


def pr_info(number, branch, **kw):
    d = {"number": number, "title": "PR %d work" % number, "headRefName": branch, "baseRefName": "main",
         "isDraft": False, "isCrossRepository": False, "state": "OPEN"}
    d.update(kw)
    return d


class FakeGh:
    """The `gh` runner: answers pr list / view from a table, records everything else."""

    def __init__(self, prs, create_fails=False):
        self.prs = {p["number"]: p for p in prs}
        self.calls = []
        self.create_fails = create_fails
        self.train_body = ""

    def __call__(self, args):
        self.calls.append(list(args))
        if args[:2] == ["pr", "list"]:
            return 0, json.dumps([p for p in self.prs.values() if p["state"] == "OPEN"]), ""
        if args[:2] == ["pr", "view"]:
            n = int(args[2])
            if n == 900:
                return 0, json.dumps({"number": 900, "state": self.prs.get(900, {}).get("state", "OPEN"),
                                      "body": self.train_body}), ""
            if n not in self.prs:
                return 1, "", "no such PR"
            return 0, json.dumps(self.prs[n]), ""
        if args[:2] == ["pr", "create"]:
            self.train_body = args[args.index("--body") + 1]
            return (1, "", "boom") if self.create_fails else (0, TRAIN_PR_URL + "\n", "")
        if args[:2] == ["pr", "merge"]:
            return 0, "", ""
        return 1, "", "unexpected gh call: %r" % (args,)

    def calls_of(self, *prefix):
        return [c for c in self.calls if c[:len(prefix)] == list(prefix)]


class TrainBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = Env(self.tmp.name, True)
        self.addCleanup(self.env.restore_env)
        e = self.env
        e.write("docs/07-kanban.md", kanban([row(i) for i in range(1, 6)]))
        e.write("docs/notes.md", "line one\nline two\nline three\n")
        e.commit("base")
        e.git("push", "-q", "origin", "main")

    def pr_branch(self, name, board_rows=None, notes=None, extra_files=None):
        e = self.env
        e.git("checkout", "-q", "main")
        e.start_branch(name)
        if board_rows is not None:
            e.write("docs/07-kanban.md", kanban(board_rows))
        if notes is not None:
            e.write("docs/notes.md", notes)
        for k, v in (extra_files or {}).items():
            e.write(k, v)
        e.commit("work on " + name)

    def main_moves(self, board_rows, notes=None):
        e = self.env
        e.git("checkout", "-q", "main")
        e.write("docs/07-kanban.md", kanban(board_rows))
        if notes is not None:
            e.write("docs/notes.md", notes)
        e.commit("main moves")

    def publish(self):
        self.env.git("checkout", "-q", "main")
        self.env.publish()

    def run_train(self, gh, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mt.main([*argv, "--repo", str(self.env.tool), "--stamp", "t1"], gh=gh)
        return rc, buf.getvalue()

    def origin_has(self, ref):
        p = self.env.git("branch", "--list", ref, cwd=self.env.origin)
        return bool(p.strip())

    def standard(self):
        """base 1-5. PR 11 edits BD-4 + adds BD-11, PR 12 edits BD-5 + adds BD-12, main edits BD-2 + adds BD-10."""
        self.pr_branch("pr11", [row(1), row(2), row(3), row(4, "Review / test", "**Task 4.** does something, PR 11 evidence"),
                                row(5), row(11, text="**Eleven.**")])
        self.pr_branch("pr12", [row(1), row(2), row(3), row(4), row(5, "Done", "**Task 5.** does something, PR 12 evidence"),
                                row(12, text="**Twelve.**")])
        self.main_moves([row(1), row(2, "Done", "**Task 2.** does something, shipped on main"), row(3), row(4), row(5),
                         row(10, text="**Main new task.**")])
        self.publish()


class TrainTests(TrainBase):
    def test_dry_run_merges_kanban_rows_and_pushes_nothing(self):
        self.standard()
        gh = FakeGh([pr_info(11, "pr11"), pr_info(12, "pr12")])
        rc, out = self.run_train(gh, "11", "12")
        self.assertEqual(rc, 0, out)
        self.assertIn("DRY RUN", out)
        self.assertIn("merged:  #11, #12", out)
        self.assertIn("skipped: none", out)
        self.assertFalse(self.origin_has("train/*"), "a dry run must not push")
        self.assertEqual(gh.calls_of("pr", "create"), [])
        self.assertEqual(gh.calls_of("pr", "merge"), [])
        wt = self.env.worktree_of(out)
        self.assertFalse(wt.exists(), "the dry-run worktree is removed unless --keep")

    def test_keep_leaves_the_worktree_with_the_right_board(self):
        self.standard()
        gh = FakeGh([pr_info(11, "pr11"), pr_info(12, "pr12")])
        rc, out = self.run_train(gh, "11", "12", "--keep")
        self.assertEqual(rc, 0, out)
        wt = self.env.worktree_of(out)
        self.assertTrue(wt.exists())
        raw = (wt / "docs" / "07-kanban.md").read_bytes().decode("utf-8")
        self.assertNotIn("<<<<<<<", raw)
        rows = mt.vkm.rows_of(raw)
        self.assertEqual(sorted(rows), ["BD-1", "BD-10", "BD-11", "BD-12", "BD-2", "BD-3", "BD-4", "BD-5"])
        self.assertIn("shipped on main", rows["BD-2"])       # no PR touched it: the train's (main's) text
        self.assertIn("PR 11 evidence", rows["BD-4"])        # only PR 11 changed it
        self.assertIn("PR 12 evidence", rows["BD-5"])        # only PR 12 changed it
        parents = self.env.git("log", "--merges", "--format=%P", "origin/main..HEAD", cwd=wt).splitlines()
        self.assertEqual(len(parents), 2)
        self.assertTrue(all(len(p.split()) == 2 for p in parents), "one real merge commit per PR")
        msg = self.env.git("log", "-1", "--format=%B", cwd=wt)
        self.assertIn("Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>", msg)

    def test_push_opens_one_pr_with_a_merge_commit_and_auto_merge(self):
        self.standard()
        gh = FakeGh([pr_info(11, "pr11"), pr_info(12, "pr12")])
        rc, out = self.run_train(gh, "11", "12", "--push")
        self.assertEqual(rc, 0, out)
        self.assertTrue(self.origin_has("train/t1"))
        self.assertIn(TRAIN_PR_URL, out)
        creates = gh.calls_of("pr", "create")
        self.assertEqual(len(creates), 1)
        c = creates[0]
        self.assertEqual(c[c.index("--head") + 1], "train/t1")
        self.assertEqual(c[c.index("--base") + 1], "main")
        body = c[c.index("--body") + 1]
        self.assertIn("Train-PRs: 11, 12", body)
        self.assertIn("\U0001F916 Generated with [Claude Code](https://claude.com/claude-code)", body)
        merges = gh.calls_of("pr", "merge")
        self.assertEqual(merges, [["pr", "merge", "900", "--repo", "Znypr/be-dino", "--merge", "--auto"]])
        # the original heads are ancestors of the train branch: GitHub will mark the PRs merged
        for b in ("pr11", "pr12"):
            self.env.git("merge-base", "--is-ancestor", "refs/heads/" + b, "refs/heads/train/t1", cwd=self.env.origin)
        # the tool never moved a PR branch or main
        self.assertEqual(self.env.git("rev-parse", "refs/heads/main", cwd=self.env.origin),
                         self.env.git("rev-parse", "origin/main", cwd=self.env.tool))
        self.assertFalse(self.env.worktree_of(out).exists())

    def test_non_kanban_conflict_is_skipped_and_named(self):
        self.pr_branch("pr11", [row(1), row(2), row(3), row(4, text="**Task 4.** edit 11"), row(5)],
                       notes="line one\nPR eleven changed this\nline three\n")
        self.pr_branch("pr12", [row(i) for i in range(1, 6)] + [row(12, text="**Twelve.**")])
        self.pr_branch("pr13", [row(i) for i in range(1, 6)] + [row(13, text="**Thirteen.**")],
                       notes="line one\nPR thirteen changed this\nline three\n")
        self.publish()
        gh = FakeGh([pr_info(11, "pr11"), pr_info(12, "pr12"), pr_info(13, "pr13")])
        rc, out = self.run_train(gh, "11", "12", "13", "--keep")
        self.assertEqual(rc, 0, out)
        self.assertIn("merged:  #11, #12", out)
        self.assertIn("#13: needs a human, conflicting files: docs/notes.md", out)
        wt = self.env.worktree_of(out)
        self.assertEqual(self.env.git("status", "--porcelain", cwd=wt), "", "the aborted merge left nothing behind")
        notes = (wt / "docs" / "notes.md").read_text(encoding="utf-8")
        self.assertIn("PR eleven changed this", notes)
        self.assertNotIn("<<<<<<<", notes)
        rows = mt.vkm.rows_of((wt / "docs" / "07-kanban.md").read_bytes().decode("utf-8"))
        self.assertIn("BD-12", rows)
        self.assertNotIn("BD-13", rows)

    def test_pr_pushed_with_skipped_list_in_the_body(self):
        self.pr_branch("pr11", notes="line one\nPR eleven\nline three\n")
        self.pr_branch("pr13", notes="line one\nPR thirteen\nline three\n")
        self.publish()
        gh = FakeGh([pr_info(11, "pr11"), pr_info(13, "pr13")])
        rc, out = self.run_train(gh, "11", "13", "--push")
        self.assertEqual(rc, 0, out)
        body = gh.train_body
        self.assertIn("Train-PRs: 11", body)
        self.assertIn("- #13: needs a human", body)
        self.assertNotIn("13,", body.split("Train-PRs:")[1].splitlines()[0])

    def test_nothing_mergeable_returns_1_and_pushes_nothing(self):
        self.pr_branch("pr13", notes="line one\nPR thirteen\nline three\n")
        self.main_moves([row(i) for i in range(1, 6)], notes="line one\nmain changed it\nline three\n")
        self.publish()
        gh = FakeGh([pr_info(13, "pr13")])
        rc, out = self.run_train(gh, "13", "--push")
        self.assertEqual(rc, 1, out)
        self.assertIn("nothing could be merged", out)
        self.assertFalse(self.origin_has("train/*"))
        self.assertEqual(gh.calls_of("pr", "create"), [])

    def test_failed_pr_create_reports_the_pushed_branch(self):
        self.standard()
        gh = FakeGh([pr_info(11, "pr11"), pr_info(12, "pr12")], create_fails=True)
        rc, out = self.run_train(gh, "11", "--push")
        self.assertEqual(rc, 1, out)
        self.assertIn("open the PR by hand", out)
        self.assertEqual(gh.calls_of("pr", "merge"), [])

    def test_existing_train_branch_name_is_not_reused(self):
        self.standard()
        self.env.git("checkout", "-q", "main")
        self.env.git("push", "-q", "origin", "main:refs/heads/train/t1")
        gh = FakeGh([pr_info(11, "pr11")])
        rc, out = self.run_train(gh, "11", "--push")
        self.assertEqual(rc, 0, out)
        self.assertTrue(self.origin_has("train/t1-2"))

    def test_already_contained_pr_is_listed_not_merged_twice(self):
        self.standard()
        gh = FakeGh([pr_info(11, "pr11")])
        self.run_train(gh, "11", "--push")
        self.env.git("fetch", "-q", "origin", cwd=self.env.dev)
        # land the train on main (what GitHub's merge commit does), then ask again
        self.env.git("update-ref", "refs/heads/main", "refs/heads/train/t1", cwd=self.env.origin)
        rc, out = self.run_train(FakeGh([pr_info(11, "pr11")]), "11")
        self.assertEqual(rc, 1, out)
        self.assertIn("#11: its branch is already part of the train / main", out)


class SelectionTests(TrainBase):
    def prs(self):
        return [pr_info(11, "pr11"), pr_info(12, "pr12"), pr_info(13, "pr13"), pr_info(14, "pr14", isDraft=True),
                pr_info(15, "pr15", baseRefName="release"), pr_info(16, "train/0101-0000"),
                pr_info(17, "pr17", isCrossRepository=True), pr_info(18, "pr18")]

    def test_auto_select_skips_drafts_excluded_held_trains_forks_and_other_bases(self):
        self.pr_branch("pr11", [row(i) for i in range(1, 6)] + [row(11)])
        self.pr_branch("pr12", [row(i) for i in range(1, 6)] + [row(12)])
        self.pr_branch("pr13", [row(i) for i in range(1, 6)] + [row(13)])
        self.pr_branch("pr18", [row(i) for i in range(1, 6)] + [row(18)])
        self.publish()
        gh = FakeGh(self.prs())
        rc, out = self.run_train(gh, "--auto-select", "--exclude", "12", "--hold", "18")
        self.assertEqual(rc, 0, out)
        self.assertIn("merged:  #11, #13", out)
        for needle in ("#12: excluded", "#18: held", "#14: draft", "#16: an earlier merge train PR",
                       "#15: its base is release, not main", "#17: comes from a fork"):
            self.assertIn(needle, out)
        self.assertEqual(gh.calls_of("pr", "list")[0][:2], ["pr", "list"])

    def test_explicit_pr_with_other_base_is_skipped_with_a_message(self):
        self.pr_branch("pr11", [row(i) for i in range(1, 6)] + [row(11)])
        self.publish()
        gh = FakeGh([pr_info(11, "pr11"), pr_info(15, "pr15", baseRefName="release")])
        rc, out = self.run_train(gh, "11", "15")
        self.assertEqual(rc, 0, out)
        self.assertIn("#15: its base is release, not main", out)

    def test_no_arguments_is_a_usage_error(self):
        rc, out = self.run_train(FakeGh([]))
        self.assertEqual(rc, 2)
        self.assertIn("--auto-select", out)

    def test_unknown_pr_stops_before_any_git_work(self):
        rc, out = self.run_train(FakeGh([]), "99")
        self.assertEqual(rc, 2, out)
        self.assertIn("cannot ask GitHub", out)


class AfterTests(unittest.TestCase):
    def run_after(self, gh):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mt.main(["--after", "900"], gh=gh)
        return rc, buf.getvalue()

    def test_all_original_prs_merged(self):
        gh = FakeGh([pr_info(11, "a", state="MERGED"), pr_info(12, "b", state="MERGED"), pr_info(900, "train/x", state="MERGED")])
        gh.train_body = "Merge train.\n\nTrain-PRs: 11, 12\n\nfooter"
        rc, out = self.run_after(gh)
        self.assertEqual(rc, 0, out)
        self.assertIn("None of them is still open", out)

    def test_original_still_open_is_listed_with_a_hint(self):
        gh = FakeGh([pr_info(11, "a", state="MERGED"), pr_info(12, "b", state="OPEN"), pr_info(900, "train/x", state="MERGED")])
        gh.train_body = "Train-PRs: 11, 12"
        rc, out = self.run_after(gh)
        self.assertEqual(rc, 1, out)
        self.assertIn("Still OPEN on GitHub: #12", out)
        self.assertIn("Hint:", out)
        self.assertIn("merge commit", out)

    def test_train_pr_not_merged_yet(self):
        gh = FakeGh([pr_info(900, "train/x", state="OPEN")])
        rc, out = self.run_after(gh)
        self.assertEqual(rc, 0)
        self.assertIn("not MERGED yet", out)


if __name__ == "__main__":
    unittest.main()
