"""One-file-per-row kanban (BD-1061, docs/191): library, converter (round trip), CLI, checks, and the cutover replay of
PRs that were made before it (tools/kanban_migrate_pr.py via merge_main_into_pr.py and merge_train.py).

All offline: temporary folders and temporary git repos only."""
import contextlib
import io
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kanban_lib as kl  # noqa: E402
import kanban_migrate as kmig  # noqa: E402
import kanban  # noqa: E402
import verify_kanban_merge as vkm  # noqa: E402
import verify_kanban_rows  # noqa: E402
import merge_main_into_pr as mm  # noqa: E402
import merge_train as mt  # noqa: E402
import next_bd_id  # noqa: E402
from test_merge_main_into_pr import Env, MergeHelperBase, kanban as kanban_text, row  # noqa: E402
from test_merge_train import FakeGh, pr_info  # noqa: E402

CR, LF = chr(13), chr(10)

# A legacy page with every oddity of the real one: two tables, stray " |" lines, a four-column row, a row without a
# closing bar, a row whose task text contains a bar, rows out of number order, and CRLF line endings.
MESSY = LF.join([
    "# Kanban", "", "Intro text.", "", "## Task index",
    "| ID | Status | Priority | Task | Dependencies |", "|---|---|---|---|---|",
    "| BD-010 | Done (2026-10-17, proof) | P0 | Ten **bold** `code` | BD-001 |",
    "| BD-002 | Backlog | P1 | Two has a | bar inside | BD-001, BD-010 |",
    "| BD-003 | Review / test | P2 | Four columns only |",
    "| BD-004 | Spike (flag off) | P3 | No closing bar at all",
    " |",
    "| BD-1000 | Backlog | P1 | Big number | None |",
    "", "### Later prose", "Some words.", "",
    "| ID | Status | Pri | Task | Depends on |", "| --- | --- | --- | --- | --- |",
    "| BD-005 | Blocked | P1 | Second table | None |",
    " |",
    "| BD-001 | Done | P0 | One | None |",
    "", ""])


def crlf(text):
    return text.replace(LF, CR + LF)


class LibraryTests(unittest.TestCase):
    def test_names_and_ids(self):
        self.assertEqual(kl.file_name("BD-61"), "BD-0061.md")
        self.assertEqual(kl.file_name("BD-004"), "BD-0004.md")
        self.assertEqual(kl.file_name("BD-12345"), "BD-12345.md")
        self.assertEqual(kl.row_path("BD-7"), "docs/kanban/rows/BD-0007.md")
        self.assertEqual(kl.number("BD-004"), 4)

    def test_parse_row_handles_all_shapes(self):
        a = kl.parse_row("| BD-1 | Backlog | P1 | Task | BD-2 |")
        self.assertEqual((a["status"], a["priority"], a["text"], a["deps"]), ("Backlog", "P1", "Task", "BD-2"))
        b = kl.parse_row("| BD-2 | Backlog | P1 | has | bar | None |")
        self.assertEqual((b["text"], b["deps"]), ("has | bar", "None"))
        c = kl.parse_row("| BD-3 | Done | P1 | four columns |")
        self.assertEqual((c["text"], c["deps"]), ("four columns", ""))
        d = kl.parse_row("| BD-4 | Done | P1 | no closing bar")
        self.assertEqual((d["text"], d["deps"]), ("no closing bar", ""))

    def test_set_status_and_append_note(self):
        line = "| BD-1 | Backlog | P1 | **Title.** words | BD-2 |"
        self.assertEqual(kl.set_status(line, "Done"), "| BD-1 | Done | P1 | **Title.** words | BD-2 |")
        self.assertEqual(kl.append_note(line, "Outcome."), "| BD-1 | Backlog | P1 | **Title.** words Outcome. | BD-2 |")
        self.assertEqual(kl.append_note("| BD-1 | Backlog | P1 | no closing bar", "Out."), "| BD-1 | Backlog | P1 | no closing bar Out.")
        self.assertEqual(kl.append_note(line, "  "), line)

    def test_split_legacy_takes_tables_and_strays_and_keeps_the_prose(self):
        rows, prose, first = kl.split_legacy(MESSY)
        self.assertEqual([r[0] for r in rows], ["BD-010", "BD-002", "BD-003", "BD-004", "BD-1000", "BD-005", "BD-001"])
        text = LF.join(prose)
        self.assertNotIn("| BD-", text)
        self.assertNotIn("| ID |", text)
        self.assertNotIn("| --- |", text)
        self.assertEqual(prose[first - 1], "## Task index")
        self.assertIn("### Later prose", text)
        self.assertIn("Some words.", text)


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir()

    def legacy(self, text):
        (self.root / "docs" / "07-kanban.md").write_bytes(text.encode("utf-8"))

    def test_round_trip_is_lossless_for_every_oddity(self):
        for text in (MESSY, crlf(MESSY)):
            self.legacy(text)
            old = kl.read_legacy_rows(text)
            msg, rc = kmig.apply(self.root)
            self.assertEqual(rc, 0, msg)
            new = kl.read_rows(self.root)
            self.assertEqual(dict(new), dict(old))                      # same ids, same row lines, character for character
            self.assertEqual(sorted(kl.number(k) for k in new), [1, 2, 3, 4, 5, 10, 1000])
            for rid, line in old.items():
                raw = (self.root / kl.row_path(rid)).read_bytes()
                self.assertEqual(raw, (line + LF).encode("utf-8"))      # file = the old line + one LF, nothing else
                a, b = kl.parse_row(line), kl.parse_row(raw.decode("utf-8"))
                self.assertEqual([a[k] for k in ("id", "status", "priority", "text", "deps")],
                                 [b[k] for k in ("id", "status", "priority", "text", "deps")])
            rendered = {l for l in kl.render(new).split(LF)[2:] if l}
            self.assertEqual(rendered, set(old.values()))               # render() gives the old table back (sorted by number)
            self.assertEqual(kl.check_rows_dir(self.root), [])
            shutil.rmtree(self.root / "docs" / "kanban")

    def test_page_loses_rows_gets_section_and_marker_and_keeps_crlf(self):
        self.legacy(crlf(MESSY))
        kmig.apply(self.root)
        page = (self.root / "docs" / "07-kanban.md").read_bytes().decode("utf-8")
        self.assertIsNone(re.search(r"(?m)^\| BD-", page))
        self.assertIn("docs/kanban/rows/", page)
        self.assertIn("Later prose", page)
        self.assertNotIn(LF.join(["a", "b"]).replace(LF, CR + CR + LF), page)
        self.assertEqual(page.count(CR + LF), page.count(LF), "every line ending is still CRLF")
        self.assertTrue((self.root / kl.CUTOVER).exists())

    def test_apply_is_idempotent_and_says_so_when_nothing_is_left(self):
        self.legacy(MESSY)
        kmig.apply(self.root)
        before = {p.name: p.read_bytes() for p in (self.root / kl.ROWS_DIR).iterdir()}
        page = (self.root / "docs" / "07-kanban.md").read_bytes()
        msg, rc = kmig.apply(self.root)
        self.assertEqual(rc, 0)
        self.assertIn("nothing to move", msg)
        self.assertEqual(page, (self.root / "docs" / "07-kanban.md").read_bytes())
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.root / kl.ROWS_DIR).iterdir()})

    def test_apply_twice_from_the_same_old_text_changes_nothing(self):
        (self.root / "g").mkdir()
        env = Env(self.root / "g", True)
        self.addCleanup(env.restore_env)
        env.write("docs/07-kanban.md", MESSY)
        env.commit("old")
        for _ in range(2):
            msg, rc = kmig.apply(env.dev, "HEAD")
            self.assertEqual(rc, 0, msg)
        self.assertEqual(env.git("status", "--porcelain", "--", "docs/kanban").count("??"), 1)  # the new folder, only once

    def test_dry_run_writes_nothing(self):
        self.legacy(MESSY)
        msg, rc = kmig.apply(self.root, write=False)
        self.assertEqual(rc, 0)
        self.assertFalse((self.root / "docs" / "kanban").exists())
        self.assertIn(" BD-", " " + "".join(kl.read_legacy_rows(MESSY)))

    def test_repeated_id_with_different_text_is_refused(self):
        self.legacy(MESSY + LF.join(["| BD-001 | Backlog | P1 | Other text | None |", ""]))
        msg, rc = kmig.apply(self.root)
        self.assertEqual(rc, 1)
        self.assertIn("BD-001", msg)
        self.assertFalse((self.root / "docs" / "kanban").exists())

    def test_the_real_checkout_has_a_consistent_board(self):
        """Whatever layout this checkout has, its rows are readable and the static check passes."""
        root = TOOLS.parent
        rows = kl.read_rows(root)
        self.assertGreater(len(rows), 100)
        self.assertEqual(kl.check_rows_dir(root), [])


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "07-kanban.md").write_bytes(MESSY.encode("utf-8"))
        kmig.apply(self.root)

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = kanban.main(["--root", str(self.root), *argv])
        return rc, out.getvalue()

    def test_list_filters(self):
        rc, out = self.run_cli("list", "--status", "Done")
        self.assertEqual(sorted(l.split(" | ")[0] for l in out.splitlines()), ["BD-001", "BD-010"])
        rc, out = self.run_cli("list", "--priority", "P1", "--text", "bar")
        self.assertEqual([l.split(" | ")[0] for l in out.splitlines()], ["BD-002"])
        rc, out = self.run_cli("list", "--status", "Review")
        self.assertEqual([l.split(" | ")[0] for l in out.splitlines()], ["BD-003"])

    def test_show_finds_by_number_whatever_the_padding(self):
        for name in ("BD-2", "BD-002", "bd-02"):
            rc, out = self.run_cli("show", name.upper())
            self.assertEqual(rc, 0, name)
            self.assertIn("Two has a | bar inside", out)
        rc, out = self.run_cli("show", "BD-99")
        self.assertEqual(rc, 1)

    def test_board_matches_board_summary(self):
        import board_summary
        rc, out = self.run_cli("board")
        self.assertEqual(out.strip(), board_summary.block(list(kl.read_rows(self.root).values())).strip())
        self.assertIn("7 tasks", out)

    def test_render_is_the_old_table_sorted(self):
        out = io.StringIO()
        out.reconfigure = lambda **k: None
        old = sys.stdout
        buf = io.StringIO()
        buf.reconfigure = lambda **k: None
        sys.stdout = buf
        try:
            kanban.main(["--root", str(self.root), "render"])
        finally:
            sys.stdout = old
        lines = buf.getvalue().split(LF)
        self.assertEqual(lines[0], kl.HEADER_LINE)
        self.assertEqual([l.split(" | ")[0] for l in lines[2:] if l], ["| BD-001", "| BD-002", "| BD-003", "| BD-004", "| BD-005",
                                                                      "| BD-010", "| BD-1000"])

    def test_set_status_edits_only_that_file_keeps_title_and_appends_the_note(self):
        before = {p.name: p.read_bytes() for p in (self.root / kl.ROWS_DIR).iterdir()}
        rc, out = self.run_cli("set-status", "BD-2", "Review / test", "--note", "Built; Studio not checked.")
        self.assertEqual(rc, 0, out)
        after = {p.name: p.read_bytes() for p in (self.root / kl.ROWS_DIR).iterdir()}
        self.assertEqual([k for k in after if after[k] != before[k]], ["BD-0002.md"])
        self.assertEqual(after["BD-0002.md"].decode("utf-8"),
                         "| BD-002 | Review / test | P1 | Two has a | bar inside Built; Studio not checked. | BD-001, BD-010 |" + LF)

    def test_done_needs_a_note(self):
        rc, out = self.run_cli("set-status", "BD-2", "Done")
        self.assertEqual(rc, 1)
        self.assertIn("evidence", out)
        self.assertIn("Backlog", (self.root / kl.row_path("BD-002")).read_text(encoding="utf-8"))

    def test_add_creates_a_file_and_refuses_to_overwrite(self):
        rc, out = self.run_cli("add", "--id", "BD-1001", "--title", "A new task", "--priority", "P1", "--deps", "BD-1000")
        self.assertEqual(rc, 0, out)
        self.assertEqual((self.root / "docs/kanban/rows/BD-1001.md").read_text(encoding="utf-8"),
                         "| BD-1001 | Backlog | P1 | **A new task** | BD-1000 |" + LF)
        rc, out = self.run_cli("add", "--id", "BD-1001", "--title", "Again", "--priority", "P1")
        self.assertEqual(rc, 1)
        rc, out = self.run_cli("add", "--id", "BD-1002", "--title", "bad | bar", "--priority", "P1")
        self.assertEqual(rc, 1)
        rc, out = self.run_cli("add", "--id", "BD-1002", "--title", "ok", "--priority", "P9")
        self.assertEqual(rc, 1)

    def test_add_without_id_uses_next_bd_id(self):
        old = kanban.next_id
        kanban.next_id = lambda: "BD-1234"
        try:
            rc, out = self.run_cli("add", "--title", "Auto id", "--priority", "P2")
        finally:
            kanban.next_id = old
        self.assertEqual(rc, 0, out)
        self.assertTrue((self.root / "docs/kanban/rows/BD-1234.md").exists())


class CliBeforeTheCutover(unittest.TestCase):
    """In an old checkout (the table is still in docs/07-kanban.md) the read commands work and set-status edits the table row."""

    def test_list_show_and_set_status_on_the_old_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "07-kanban.md").write_bytes(crlf(MESSY).encode("utf-8"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(kanban.main(["--root", str(root), "show", "BD-5"]), 0)
                self.assertEqual(kanban.main(["--root", str(root), "set-status", "BD-5", "Review / test", "--note", "Built."]), 0)
                self.assertEqual(kanban.main(["--root", str(root), "add", "--title", "x", "--priority", "P1"]), 2)
            self.assertIn("Second table", out.getvalue())
            raw = (root / "docs" / "07-kanban.md").read_bytes().decode("utf-8")
            self.assertIn("| BD-005 | Review / test | P1 | Second table Built. | None |" + CR + LF, raw)
            self.assertEqual(raw.count(CR + LF), raw.count(LF))


class RowFileChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "07-kanban.md").write_bytes(MESSY.encode("utf-8"))
        kmig.apply(self.root)
        self.rows = self.root / kl.ROWS_DIR

    def problems(self):
        return kl.check_rows_dir(self.root)

    def test_clean_tree_passes(self):
        self.assertEqual(self.problems(), [])

    def test_wrong_name_two_files_for_one_id_and_foreign_files(self):
        shutil.copy(self.rows / "BD-0001.md", self.rows / "BD-1.md")
        (self.rows / "notes.txt").write_text("x", encoding="utf-8")
        text = "\n".join(self.problems())
        self.assertIn("BD-1.md: the file name must be BD-0001.md", text)
        self.assertIn("same task number 1", text)
        self.assertIn("notes.txt: not a row file", text)

    def test_file_name_must_match_the_row_inside(self):
        (self.rows / "BD-0007.md").write_text("| BD-8 | Backlog | P1 | wrong file | None |" + LF, encoding="utf-8")
        self.assertIn("BD-0007.md: the row inside is BD-8", "\n".join(self.problems()))

    def test_one_line_lf_only_and_a_row(self):
        (self.rows / "BD-0001.md").write_bytes(b"| BD-1 | Done | P0 | One | None |\r\n")
        (self.rows / "BD-0002.md").write_bytes(b"| BD-2 | Done | P0 | One | None |\n\n")
        (self.rows / "BD-0003.md").write_bytes(b"not a row\n")
        (self.rows / "BD-0004.md").write_bytes(b"| BD-4 | Done | P0 | a | None |\n| BD-5 | Done | P0 | b | None |\n")
        text = "\n".join(self.problems())
        self.assertIn("BD-0001.md: has a CR", text)
        self.assertIn("BD-0002.md: must be exactly one row line", text)
        self.assertIn("BD-0003.md: the line does not start", text)
        self.assertIn("BD-0004.md: must be exactly one row line", text)

    def test_rows_left_in_the_page_after_the_cutover_are_flagged(self):
        page = self.root / "docs" / "07-kanban.md"
        page.write_bytes(page.read_bytes() + b"| BD-77 | Backlog | P1 | back again | None |\n")
        text = "\n".join(self.problems())
        self.assertIn("still has 1 task row", text)
        self.assertIn("kanban_migrate_pr.py", text)

    def test_script_prints_and_returns(self):
        old = verify_kanban_rows.ROOT
        verify_kanban_rows.ROOT = self.root
        try:
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(verify_kanban_rows.main(), 0)
            (self.rows / "BD-0007.md").write_text("junk\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as out2:
                self.assertEqual(verify_kanban_rows.main(), 1)
        finally:
            verify_kanban_rows.ROOT = old
        self.assertIn("FAIL", out2.getvalue())
        self.assertIn("kanban rows ok", out.getvalue())

    def test_before_the_cutover_there_is_nothing_to_check(self):
        shutil.rmtree(self.root / "docs" / "kanban")
        old = verify_kanban_rows.ROOT
        verify_kanban_rows.ROOT = self.root
        try:
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(verify_kanban_rows.main(), 0)
        finally:
            verify_kanban_rows.ROOT = old
        self.assertIn("nothing to check", out.getvalue())


class NextIdSeesRowFiles(unittest.TestCase):
    def test_worktree_scan_reads_row_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "kanban" / "rows").mkdir(parents=True)
            (root / "docs" / "kanban" / "rows" / "BD-0900.md").write_text(
                "| BD-900 | Backlog | P1 | mentions BD-950 | None |" + LF, encoding="utf-8")
            self.assertEqual(next_bd_id.scan_worktree(root, "bd"), {900, 950})


# ---------------------------------------------------------------- the cutover replay of old PRs

class CutoverBase(MergeHelperBase):
    """Main is a board in the OLD layout; `cut_over()` makes the cutover commit on main with the real converter."""

    def old_main(self):
        self.base_board()

    def cut_over(self, message="cutover"):
        e = self.env
        e.git("checkout", "-q", "main")
        msg, rc = kmig.apply(e.dev)
        self.assertEqual(rc, 0, msg)
        e.commit(message)

    def old_pr(self, name, rows, text=None, title=None):
        e = self.env
        e.git("checkout", "-q", "main")
        e.start_branch(name)
        board = self.kan(rows)
        if text is not None:
            board = board.replace("Some intro text.", text)
        if title is not None:
            board = board.replace("# Kanban", title)
        e.write("docs/07-kanban.md", board)
        e.commit("work on " + name)

    def rows_dir(self, wt):
        return {p.name: p.read_text(encoding="utf-8") for p in (wt / kl.ROWS_DIR).iterdir()}

    def run_ok(self, branch, *flags):
        rc, out = self.env.run(branch, *flags)
        self.assertEqual(rc, 0, out)
        return self.env.worktree_of(out), out


class StandardReplay:
    """Shared by the LF and the CRLF run (the real page has CRLF line endings). Needs CutoverBase."""

    def standard(self):
        """base 1-5. The PR (made before the cutover) edits BD-4 and adds BD-11. Main edits BD-2, adds BD-10, then cuts over."""
        e = self.env
        self.old_main()
        self.old_pr("pr", [row(1), row(2), row(3), row(4, "Review / test", "**Task 4.** does something, PR evidence"),
                           row(5), row(11, text="**PR new task.**")])
        e.git("checkout", "-q", "main")
        e.write("docs/07-kanban.md", self.kan([row(1), row(2, "Done", "**Task 2.** does something, shipped on main"),
                                               row(3), row(4), row(5), row(10, text="**Main new task.**")]))
        e.commit("main moves")
        self.cut_over()
        e.publish()

    def test_the_prs_row_changes_become_row_files_and_main_stays_as_it_is(self):
        self.standard()
        wt, out = self.run_ok("pr")
        self.assertIn("its row changes are moved over", out)
        self.assertIn("new rows: BD-11", out)
        rows = self.rows_dir(wt)
        self.assertEqual(sorted(rows), ["BD-0001.md", "BD-0002.md", "BD-0003.md", "BD-0004.md", "BD-0005.md",
                                        "BD-0010.md", "BD-0011.md"])
        self.assertIn("PR evidence", rows["BD-0004.md"])          # the PR's edit
        self.assertIn("Review / test", rows["BD-0004.md"])
        self.assertIn("shipped on main", rows["BD-0002.md"])      # main's edit survives
        self.assertIn("PR new task", rows["BD-0011.md"])
        self.assertIn("Main new task", rows["BD-0010.md"])
        page = (wt / "docs" / "07-kanban.md").read_bytes().decode("utf-8")
        self.assertIsNone(re.search(r"(?m)^\| BD-", page))
        self.assertEqual(page.rstrip(), self.env.git("show", "origin/main:docs/07-kanban.md", cwd=self.env.tool).replace(CR, "").rstrip().replace(LF, self.eol))  # main's page, unchanged
        self.assertIn("kanban merge check ok", out)
        self.assertEqual(self.env.git("status", "--porcelain", cwd=wt), "")
        msg = self.env.git("log", "-1", "--format=%B", cwd=wt)
        self.assertIn("Kanban cutover: moved this PR's row changes", msg)

    def test_the_page_text_edit_of_the_pr_is_kept_by_a_three_way_merge(self):
        e = self.env
        self.old_main()
        self.old_pr("pr", [row(i) for i in range(1, 6)], title="# Kanban PR title")
        e.git("checkout", "-q", "main")
        e.write("docs/07-kanban.md", self.kan([row(i) for i in range(1, 6)]).replace("Some intro text.", "Some intro text. Main words."))
        e.commit("main edits the intro line")
        self.cut_over()
        e.publish()
        wt, out = self.run_ok("pr")
        page = (wt / "docs" / "07-kanban.md").read_bytes().decode("utf-8")
        self.assertIn("# Kanban PR title", page)
        self.assertIn("Some intro text. Main words.", page)
        self.assertIsNone(re.search(r"(?m)^\| BD-", page))
        self.assertIn("3-way merge", out)



class ReplayOfOldPrs(StandardReplay, CutoverBase):
    def test_a_clash_in_the_page_text_goes_to_a_human(self):
        e = self.env
        self.old_main()
        self.old_pr("pr", [row(i) for i in range(1, 6)], text="Some intro text. PR words.")
        e.git("checkout", "-q", "main")
        e.write("docs/07-kanban.md", self.kan([row(i) for i in range(1, 6)]).replace("Some intro text.", "Some intro text. Main words."))
        e.commit("main edits the same line")
        self.cut_over()
        e.publish()
        rc, out = e.run("pr")
        self.assertEqual(rc, 3, out)
        self.assertIn("clashes with main's version of the page", out)

    def test_both_sides_appended_to_the_same_row_and_both_are_kept(self):
        e = self.env
        self.old_main()
        self.old_pr("pr", [row(1), row(2), row(3, "Review / test", "**Task 3.** does something. PR outcome."), row(4), row(5)])
        e.git("checkout", "-q", "main")
        e.write("docs/07-kanban.md", self.kan([row(1), row(2), row(3, text="**Task 3.** does something. Main note."),
                                               row(4), row(5)]))
        e.commit("main appends to BD-3")
        self.cut_over()
        e.publish()
        wt, out = self.run_ok("pr")
        r3 = self.rows_dir(wt)["BD-0003.md"]
        self.assertIn("MERGED BD-3", out)
        self.assertIn("Main note.", r3)
        self.assertIn("PR outcome.", r3)

    def test_same_id_added_as_a_different_task_stops(self):
        e = self.env
        self.old_main()
        self.old_pr("pr", [row(i) for i in range(1, 6)] + [row(10, text="**PR task.** one thing")])
        e.git("checkout", "-q", "main")
        e.write("docs/07-kanban.md", self.kan([row(i) for i in range(1, 6)] + [row(10, text="**Other task.** another thing")]))
        e.commit("main uses BD-10 too")
        self.cut_over()
        e.publish()
        rc, out = e.run("pr")
        self.assertEqual(rc, 3, out)
        self.assertIn("id collision", out)

    def test_a_row_removed_by_the_pr_is_reported_not_deleted(self):
        e = self.env
        self.old_main()
        self.old_pr("pr", [row(1), row(2), row(3), row(4)])  # BD-5 removed
        e.git("checkout", "-q", "main")
        e.write("docs/07-kanban.md", self.kan([row(i) for i in range(1, 6)] + [row(10, text="**Main new task.**")]))
        e.commit("main moves")
        self.cut_over()
        e.publish()
        wt, out = self.run_ok("pr")
        self.assertIn("the PR removed BD-5", out)
        self.assertIn("BD-0005.md", self.rows_dir(wt))

    def test_a_pr_that_never_touched_the_board_just_gets_the_row_files(self):
        e = self.env
        self.old_main()
        e.git("checkout", "-q", "main")
        e.start_branch("pr")
        e.write("docs/notes.md", "hello\n")
        e.commit("notes only")
        e.git("checkout", "-q", "main")
        e.write("docs/07-kanban.md", self.kan([row(1, "Done", "**Task 1.** shipped")] + [row(i) for i in range(2, 6)]))
        e.commit("main moves")
        self.cut_over()
        e.publish()
        wt, out = self.run_ok("pr")
        self.assertIn("shipped", self.rows_dir(wt)["BD-0001.md"])
        self.assertTrue((wt / "docs" / "notes.md").exists())

    def test_the_cli_wrapper_migrates_and_says_when_there_is_nothing_to_do(self):
        import kanban_migrate_pr as kmp
        self.standard()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = kmp.main(["pr", "--repo", str(self.env.tool)])
        self.assertEqual(rc, 0, out.getvalue())
        self.assertIn("was made before the cutover", out.getvalue())
        self.assertIn("kanban cutover: moved", out.getvalue())

    def test_the_cli_wrapper_does_nothing_before_the_cutover(self):
        import kanban_migrate_pr as kmp
        self.old_main()
        self.old_pr("pr", [row(i) for i in range(1, 6)] + [row(11, text="**PR new task.**")])
        self.env.publish()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = kmp.main(["pr", "--repo", str(self.env.tool)])
        self.assertEqual(rc, 0)
        self.assertIn("nothing to migrate", out.getvalue())




class ReplayOfOldPrsCrlf(StandardReplay, CutoverBase):
    eol = CR + LF


class RowFileMergesAfterTheCutover(CutoverBase):
    """PRs made after the cutover: git merges rows per file; the helper only merges a row both sides edited."""

    def setUp(self):
        super().setUp()
        self.old_main()
        self.cut_over()

    def new_pr(self, name, files):
        e = self.env
        e.git("checkout", "-q", "main")
        e.start_branch(name)
        for path, text in files.items():
            e.write(path, text)
        e.commit("work on " + name)

    def main_moves(self, files):
        e = self.env
        e.git("checkout", "-q", "main")
        for path, text in files.items():
            e.write(path, text)
        e.commit("main moves")

    def test_different_rows_merge_without_any_help(self):
        self.new_pr("pr", {kl.row_path("BD-4"): row(4, "Review / test", "**Task 4.** does something, PR evidence") + LF,
                           kl.row_path("BD-11"): row(11, text="**PR new task.**") + LF})
        self.main_moves({kl.row_path("BD-2"): row(2, "Done", "**Task 2.** does something, shipped on main") + LF,
                         kl.row_path("BD-10"): row(10, text="**Main new task.**") + LF})
        self.env.publish()
        wt, out = self.run_ok("pr")
        rows = self.rows_dir(wt)
        self.assertEqual(len(rows), 7)
        self.assertIn("shipped on main", rows["BD-0002.md"])
        self.assertIn("PR evidence", rows["BD-0004.md"])
        self.assertIn("kanban merge check ok", out)

    def test_the_same_row_edited_on_both_sides_is_merged(self):
        self.new_pr("pr", {kl.row_path("BD-3"): row(3, "Review / test", "**Task 3.** does something. PR outcome.") + LF})
        self.main_moves({kl.row_path("BD-3"): row(3, text="**Task 3.** does something. Main note.") + LF})
        self.env.publish()
        wt, out = self.run_ok("pr")
        r3 = self.rows_dir(wt)["BD-0003.md"]
        self.assertIn("MERGED BD-3", out)
        self.assertIn("Main note.", r3)
        self.assertIn("PR outcome.", r3)
        self.assertEqual(r3.count(LF), 1)
        self.assertIn("Review / test", r3)
        self.assertEqual(self.env.git("status", "--porcelain", cwd=wt), "")

    def test_the_same_new_id_with_different_titles_stops(self):
        self.new_pr("pr", {kl.row_path("BD-10"): row(10, text="**PR task.** one") + LF})
        self.main_moves({kl.row_path("BD-10"): row(10, text="**Main task.** other") + LF})
        self.env.publish()
        rc, out = self.env.run("pr")
        self.assertEqual(rc, 3, out)
        self.assertIn("id collision", out)

    def test_a_row_deleted_on_one_side_and_edited_on_the_other_stops(self):
        self.new_pr("pr", {kl.row_path("BD-3"): row(3, "Done", "**Task 3.** edited by the PR") + LF})
        e = self.env
        e.git("checkout", "-q", "main")
        e.git("rm", "-q", kl.row_path("BD-3"))
        e.commit("main removes BD-3")
        e.publish()
        rc, out = e.run("pr")
        self.assertEqual(rc, 3, out)
        self.assertIn("BD-0003.md", out)

    def test_page_text_both_sides_only_added_text_keeps_both(self):
        page = (self.env.dev / "docs" / "07-kanban.md").read_bytes().decode("utf-8").replace(CR, "")
        self.new_pr("pr", {"docs/07-kanban.md": page.replace("Some intro text.", "Some intro text.\n\n- PR decision.")})
        self.main_moves({"docs/07-kanban.md": page.replace("Some intro text.", "Some intro text.\n\n- Main decision.")})
        self.env.publish()
        wt, out = self.run_ok("pr")
        text = (wt / "docs" / "07-kanban.md").read_bytes().decode("utf-8")
        self.assertIn("- PR decision.", text)
        self.assertIn("- Main decision.", text)


class ResyncForTheCutover(unittest.TestCase):
    """The lead's one command: the cutover branch catches up with a main that is still in the old layout."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = Env(self.tmp.name, True)
        self.addCleanup(self.env.restore_env)

    def build(self, intro_change=None):
        e = self.env
        e.write("docs/07-kanban.md", kanban_text([row(i) for i in range(1, 6)]))
        e.commit("old board")
        e.git("push", "-q", "origin", "main")
        e.start_branch("cut")
        msg, rc = kmig.apply(e.dev)
        self.assertEqual(rc, 0, msg)
        e.write(kl.row_path("BD-60"), row(60, text="**Mine.**") + LF)  # a row that exists only in the cutover branch
        e.commit("cutover")
        e.git("checkout", "-q", "main")
        board = kanban_text([row(1), row(2, "Done", "**Task 2.** shipped on main"), row(3), row(4), row(5), row(10, text="**Main new.**")])
        if intro_change:
            board = board.replace("Some intro text.", intro_change)
        e.write("docs/07-kanban.md", board)
        e.commit("main moves")
        e.git("push", "-q", "origin", "main")
        e.git("checkout", "-q", "cut")

    def test_resync_merges_main_and_rereads_its_rows(self):
        self.build(intro_change="Some intro text. Main words.")
        msg, rc = kmig.resync(self.env.dev)
        self.assertEqual(rc, 0, msg)
        self.assertIn("committed", msg)
        rows = kl.read_rows(self.env.dev)
        self.assertIn("shipped on main", rows["BD-2"])
        self.assertIn("BD-10", rows)
        self.assertIn("BD-60", rows)                       # the branch's own new row is untouched
        page = (self.env.dev / "docs" / "07-kanban.md").read_text(encoding="utf-8")
        self.assertIn("Main words.", page)                 # main's newest page text
        self.assertIsNone(re.search(r"(?m)^\| BD-", page))
        self.assertEqual(len(self.env.git("log", "-1", "--format=%P").split()), 2, "a real merge commit")
        self.assertEqual(self.env.git("status", "--porcelain"), "")
        self.assertEqual(kl.check_rows_dir(self.env.dev), [])
        msg, rc = kmig.resync(self.env.dev)                # second run: nothing left to do
        self.assertEqual(rc, 0, msg)
        self.assertIn("nothing to commit", msg)

    def test_resync_refuses_a_dirty_tree(self):
        self.build()
        (self.env.dev / "docs" / "07-kanban.md").write_text("changed\n", encoding="utf-8")
        msg, rc = kmig.resync(self.env.dev)
        self.assertEqual(rc, 2)
        self.assertIn("uncommitted", msg)

    def test_resync_stops_and_undoes_the_merge_when_another_file_conflicts(self):
        e = self.env
        e.write("docs/notes.md", "one\n")
        e.write("docs/07-kanban.md", kanban_text([row(1)]))
        e.commit("old board")
        e.git("push", "-q", "origin", "main")
        e.start_branch("cut")
        kmig.apply(e.dev)
        e.write("docs/notes.md", "branch\n")
        e.commit("cutover and notes")
        e.git("checkout", "-q", "main")
        e.write("docs/notes.md", "main\n")
        e.commit("main notes")
        e.git("push", "-q", "origin", "main")
        e.git("checkout", "-q", "cut")
        msg, rc = kmig.resync(e.dev)
        self.assertEqual(rc, 1)
        self.assertIn("docs/notes.md", msg)
        self.assertEqual(e.git("status", "--porcelain"), "")


class VerifyAfterTheCutover(unittest.TestCase):
    """verify_kanban_merge against real temporary repos."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = Env(self.tmp.name, True)
        self.addCleanup(self.env.restore_env)
        self.old_root = vkm.ROOT
        self.addCleanup(setattr, vkm, "ROOT", self.old_root)
        vkm.ROOT = self.env.dev
        e = self.env
        e.write("docs/07-kanban.md", kanban_text([row(i) for i in range(1, 6)]))
        e.commit("old board")
        e.git("branch", "old-pr")
        msg, rc = kmig.apply(e.dev)
        self.assertEqual(rc, 0, msg)
        e.commit("cutover")

    def check(self, head, base="main"):
        mb = vkm.git("merge-base", base, head).strip()
        return vkm.check(base, head)[1:], vkm.check_files(base, head, mb)

    def pr(self, name, files, delete=(), message=None):
        e = self.env
        e.git("checkout", "-q", "main")
        e.start_branch(name)
        for path, text in files.items():
            e.write(path, text)
        for path in delete:
            e.git("rm", "-q", path)
        e.git("add", "-A")
        e.git("commit", "-q", "-m", message or "work")

    def test_a_clean_pr_passes(self):
        self.pr("ok", {kl.row_path("BD-9"): row(9, text="**New.**") + LF})
        (dupes, stale, notes), problems = self.check("ok")
        self.assertEqual((dupes, stale, problems), ([], [], []))

    def test_bad_file_name_is_reported(self):
        self.pr("bad", {"docs/kanban/rows/BD-9.md": row(9) + LF})
        _, problems = self.check("bad")
        self.assertTrue(any("must be BD-0009.md" in p for p in problems), problems)

    def test_removing_a_row_needs_a_trailer(self):
        self.pr("gone", {}, delete=[kl.row_path("BD-3")])
        _, problems = self.check("gone")
        self.assertTrue(any("removes row(s) BD-3" in p for p in problems), problems)
        self.pr("gone2", {}, delete=[kl.row_path("BD-3")], message="remove a test row\n\nKanban-Remove: BD-3")
        _, problems = self.check("gone2")
        self.assertEqual(problems, [])

    def test_same_new_id_with_another_title_is_a_collision(self):
        self.pr("clash", {kl.row_path("BD-9"): row(9, text="**Mine.** one") + LF})
        e = self.env
        e.git("checkout", "-q", "main")
        e.write(kl.row_path("BD-9"), row(9, text="**Theirs.** two") + LF)
        e.commit("main takes BD-9")
        (dupes, _, _), _ = self.check("clash")
        self.assertEqual([d[0] for d in dupes], ["BD-9"])

    def test_a_row_put_back_in_the_page_is_reported(self):
        page = (self.env.dev / "docs" / "07-kanban.md").read_text(encoding="utf-8")
        self.pr("back", {"docs/07-kanban.md": page + "\n" + row(7) + "\n"})
        _, problems = self.check("back")
        self.assertTrue(any("still has 1 task row" in p for p in problems), problems)

    def test_an_old_pr_that_edits_the_old_table_is_told_to_migrate(self):
        e = self.env
        e.git("checkout", "-q", "old-pr")
        e.write("docs/07-kanban.md", kanban_text([row(i) for i in range(1, 5)] + [row(5, "Done", "**Task 5.** changed")]))
        e.commit("old-style edit")
        _, problems = self.check("old-pr")
        self.assertTrue(any("kanban_migrate_pr.py" in p for p in problems), problems)

    def test_an_old_pr_that_never_touched_rows_is_fine(self):
        e = self.env
        e.git("checkout", "-q", "old-pr")
        e.write("docs/notes.md", "x\n")
        e.commit("notes only")
        _, problems = self.check("old-pr")
        self.assertEqual(problems, [])

    def test_the_cutover_pr_itself_passes_against_an_old_base(self):
        e = self.env
        e.git("branch", "old-main", "old-pr")
        (dupes, stale, _), problems = self.check("main", base="old-main")
        self.assertEqual((dupes, stale, problems), ([], [], []))
        e.git("checkout", "-q", "main")
        e.git("rm", "-q", kl.row_path("BD-2"))
        e.commit("cutover loses a row")
        _, problems = self.check("main", base="old-main")
        self.assertTrue(any("BD-2" in p for p in problems), problems)


class TrainWithOldAndNewPrs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = Env(self.tmp.name, True)
        self.addCleanup(self.env.restore_env)
        e = self.env
        e.write("docs/07-kanban.md", kanban_text([row(i) for i in range(1, 6)]))
        e.commit("old board")
        e.git("push", "-q", "origin", "main")
        # PR 11 made before the cutover: edits BD-4, adds BD-11
        e.start_branch("pr11")
        e.write("docs/07-kanban.md", kanban_text([row(1), row(2), row(3), row(4, "Review / test", "**Task 4.** does something, PR 11 evidence"),
                                                 row(5), row(11, text="**Eleven.**")]))
        e.commit("pr11")
        e.git("checkout", "-q", "main")
        msg, rc = kmig.apply(e.dev)
        self.assertEqual(rc, 0, msg)
        e.commit("cutover")
        # PR 12 made after the cutover: edits BD-4's neighbour BD-5 and adds BD-12; PR 13 appends to BD-4 as well
        e.start_branch("pr12")
        e.write(kl.row_path("BD-5"), row(5, "Review / test", "**Task 5.** does something, PR 12 evidence") + LF)
        e.write(kl.row_path("BD-12"), row(12, text="**Twelve.**") + LF)
        e.commit("pr12")
        e.git("checkout", "-q", "main")
        e.start_branch("pr13")
        e.write(kl.row_path("BD-4"), row(4, text="**Task 4.** does something, PR 13 note") + LF)
        e.commit("pr13")
        e.git("checkout", "-q", "main")
        e.publish()

    def test_train_replays_the_old_pr_and_merges_the_new_ones(self):
        gh = FakeGh([pr_info(11, "pr11"), pr_info(12, "pr12"), pr_info(13, "pr13")])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mt.main(["11", "12", "13", "--repo", str(self.env.tool), "--stamp", "t1", "--keep"], gh=gh)
        out = buf.getvalue()
        self.assertEqual(rc, 0, out)
        self.assertIn("merged:  #11, #12, #13", out)
        wt = self.env.worktree_of(out)
        rows = {p.name: p.read_text(encoding="utf-8") for p in (wt / kl.ROWS_DIR).iterdir()}
        self.assertEqual(sorted(rows), ["BD-0001.md", "BD-0002.md", "BD-0003.md", "BD-0004.md", "BD-0005.md", "BD-0011.md", "BD-0012.md"])
        self.assertIn("PR 11 evidence", rows["BD-0004.md"])   # replayed from the old table; PR 13 edited the same row too
        self.assertIn("PR 13 note", rows["BD-0004.md"])       # ... and its edit is merged in, not lost
        self.assertIn("PR 12 evidence", rows["BD-0005.md"])
        self.assertIsNone(re.search(r"(?m)^\| BD-", (wt / "docs" / "07-kanban.md").read_text(encoding="utf-8")))
        self.assertEqual(self.env.git("status", "--porcelain", cwd=wt), "")
        shutil.rmtree(wt.parent, ignore_errors=True)
        self.env.git("worktree", "prune", cwd=self.env.tool)


if __name__ == "__main__":
    unittest.main()
