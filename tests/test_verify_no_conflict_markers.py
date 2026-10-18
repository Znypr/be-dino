"""tools/verify_no_conflict_markers.py: a temp git repo, nothing that only exists on the owner PC."""
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import verify_no_conflict_markers as vncm  # noqa: E402

# Built from pieces so this test file itself never has a marker at the start of a line.
OPEN, BASE, MID, CLOSE = "<" * 7, "|" * 7, "=" * 7, ">" * 7


class ScanTextTests(unittest.TestCase):
    def kinds(self, text):
        return [(n, k) for n, _, k in vncm.scan_text(text)]

    def test_full_block_lf_and_crlf_are_both_found(self):
        block = ["intro", OPEN + " HEAD", "mine", BASE + " base", "old", MID, "theirs", CLOSE + " origin/main", "outro"]
        for eol in ("\n", "\r\n"):
            hits = self.kinds(eol.join(block) + eol)
            self.assertEqual([n for n, _ in hits], [2, 4, 6, 8], repr(eol))

    def test_markers_without_label_at_end_of_line(self):
        self.assertEqual(self.kinds(OPEN + "\r\n" + CLOSE), [(1, OPEN), (2, CLOSE)])

    def test_setext_underline_alone_is_not_a_marker(self):
        self.assertEqual(self.kinds("Title\n" + MID + "\nmore\n"), [])

    def test_equals_after_a_closed_block_is_not_flagged(self):
        text = "\n".join([OPEN + " a", MID, CLOSE + " b", "Heading", MID, "x"])
        self.assertEqual([n for n, _ in self.kinds(text)], [1, 2, 3])

    def test_equals_after_an_unclosed_open_is_flagged(self):
        self.assertEqual([n for n, _ in self.kinds(OPEN + " x\nmid\n" + MID + "\n")], [1, 3])

    def test_lookalikes_are_not_markers(self):
        for line in ("<<<<<< six", OPEN + "<", OPEN + "x", " " + OPEN + " indented", "text " + OPEN + " mid",
                     "|" * 8, ">" * 8, "| a | b |", "=" * 8):
            self.assertEqual(vncm.scan_text(line + "\n"), [], line)


class RepoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.old = {k: os.environ.get(k) for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM")}
        cfg = self.root / "gitconfig"
        cfg.write_text("[user]\n name = t\n email = t@t\n[core]\n autocrlf = false\n", encoding="utf-8")
        os.environ["GIT_CONFIG_GLOBAL"], os.environ["GIT_CONFIG_NOSYSTEM"] = str(cfg), "1"
        self.addCleanup(self.restore)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "-C", str(self.repo), "init", "-q"], check=True)

    def restore(self):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def add(self, name, data):
        p = self.repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
        subprocess.run(["git", "-C", str(self.repo), "add", "--", name], check=True)

    def run_main(self, *extra):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = vncm.main(["--root", str(self.repo), *extra])
        return rc, buf.getvalue()

    def test_clean_repo_passes(self):
        self.add("docs/a.md", "# A\n\nTitle\n" + MID + "\n")
        rc, out = self.run_main()
        self.assertEqual(rc, 0, out)
        self.assertIn("ok", out)

    def test_leftover_block_in_a_crlf_doc_fails_with_file_and_line(self):
        self.add("docs/07-kanban.md", "\r\n".join(["| BD-1 | a |", OPEN + " HEAD", "x", MID, "y", CLOSE + " main", ""]))
        rc, out = self.run_main()
        self.assertEqual(rc, 1, out)
        self.assertIn("docs/07-kanban.md:2:", out)
        self.assertIn("docs/07-kanban.md:4:", out)
        self.assertIn("docs/07-kanban.md:6:", out)
        self.assertIn("Delete", out)  # plain-words fix hint

    def test_binary_file_is_skipped(self):
        self.add("art/x.bin", b"\x00\x01" + OPEN.encode() + b" HEAD\n")
        rc, out = self.run_main()
        self.assertEqual(rc, 0, out)

    def test_allowlist_skips_a_file_with_a_reason(self):
        self.add("tests/fixture.txt", OPEN + " HEAD\nx\n" + CLOSE + " b\n")
        self.assertTrue(vncm.scan(self.repo))
        self.assertEqual(vncm.scan(self.repo, {"tests/fixture.txt": "fixture on purpose"}), [])

    def test_untracked_file_is_not_scanned(self):
        (self.repo / "scratch.txt").write_text(OPEN + " HEAD\n", encoding="utf-8")
        rc, out = self.run_main()
        self.assertEqual(rc, 0, out)

    def test_not_a_git_repo_is_exit_2(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = vncm.main(["--root", str(self.root / "nothing-here")])
        self.assertEqual(rc, 2, buf.getvalue())

    def test_plain_folder_without_git_is_scanned(self):
        # the rehearsal runs the verifiers in a scratch COPY of the tree (no .git): scan the folder instead of failing
        folder = self.root / "plain-copy"
        folder.mkdir()
        (folder / "a.md").write_text("fine\n", encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = vncm.main(["--root", str(folder)])
        self.assertEqual(rc, 0, buf.getvalue())
        (folder / "b.md").write_text(("<" * 7) + " HEAD\nx\n", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = vncm.main(["--root", str(folder)])
        self.assertEqual(rc, 1)

    def test_allowlist_entries_have_reasons(self):
        for name, why in vncm.ALLOWLIST.items():
            self.assertTrue(why.strip(), name)


if __name__ == "__main__":
    unittest.main()
