"""tools/kanban_merge_lib.py: merging two edits of one kanban row without dropping either side."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import kanban_merge_lib as kml  # noqa: E402


def row(status="Backlog", desc="**Task.** does something", deps="None", n=621):
    return "| BD-%d | %s | P2 | %s | %s |" % (n, status, desc, deps)


BASE = row()


class MergeRowTests(unittest.TestCase):
    def test_pr_appended_and_main_appended(self):
        main = row(desc="**Task.** does something Main note: audio fixed.")
        pr = row("Review / test", desc="**Task.** does something Outcome 2026-10-18: PR evidence.")
        merged, mode, notes = kml.merge_row(BASE, main, pr, "PR #7")
        self.assertEqual(mode, "appended", notes)
        self.assertEqual(merged, row("Review / test", "**Task.** does something Main note: audio fixed. "
                                                      "Outcome 2026-10-18: PR evidence."))
        self.assertTrue(merged.startswith("| BD-621 | Review / test | P2 | **Task.**"))
        self.assertTrue(merged.endswith(" | None |"))

    def test_main_status_wins_when_both_changed_it_and_the_note_says_so(self):
        main = row("Done", desc="**Task.** does something Main note.")
        pr = row("Review / test", desc="**Task.** does something PR outcome.")
        merged, mode, notes = kml.merge_row(BASE, main, pr, "PR #7")
        self.assertEqual(mode, "appended")
        self.assertIn("| Done |", merged)
        self.assertTrue(any("Review / test" in n for n in notes), notes)
        self.assertIn("Main note. PR outcome.", merged)

    def test_pr_rewrote_the_middle_falls_back_and_keeps_both(self):
        main = row(desc="**Task.** does something Main note.")
        pr = row(desc="**Task.** does a different thing entirely.")
        merged, mode, notes = kml.merge_row(BASE, main, pr, "PR #7")
        self.assertEqual(mode, "fallback")
        self.assertIn("**Task.** does something Main note.", merged)
        self.assertIn("**(from PR #7, check)** **Task.** does a different thing entirely.", merged)
        self.assertTrue(merged.endswith(" | None |"))
        self.assertTrue(merged.startswith("| BD-621 | Backlog | P2 | **Task.**"))

    def test_main_unchanged_description_takes_the_pr_text(self):
        pr = row("Review / test", desc="**Task.** does something, rewritten in the middle")
        merged, mode, _ = kml.merge_row(BASE, BASE.replace("Backlog", "Done"), pr, "PR #7")
        self.assertEqual(mode, "pr-only")
        self.assertIn("rewritten in the middle", merged)
        self.assertIn("| Done |", merged)  # main changed the status alone, the PR the description alone

    def test_pr_did_not_change_the_description(self):
        main = row(desc="**Task.** does something Main note.")
        pr = row("Review / test")
        merged, mode, _ = kml.merge_row(BASE, main, pr, "PR #7")
        self.assertEqual(mode, "main")
        self.assertIn("| Review / test |", merged)  # the PR's status change (main kept Backlog) is taken
        self.assertIn("Main note.", merged)

    def test_added_text_already_in_main_is_not_duplicated(self):
        main = row(desc="**Task.** does something Outcome: done.")
        pr = row(desc="**Task.** does something Outcome: done.")
        merged, mode, _ = kml.merge_row(BASE, main, pr, "PR #7")
        self.assertEqual((merged, mode), (main, "main"))

    def test_row_added_on_both_sides_appends_or_falls_back(self):
        main = row(desc="**New task.** short")
        pr = row(desc="**New task.** short plus the PR's longer tail")
        merged, mode, _ = kml.merge_row(None, main, pr, "PR #7")
        self.assertEqual(mode, "appended")
        self.assertIn("short plus the PR's longer tail", merged)
        merged2, mode2, _ = kml.merge_row(None, pr, main, "PR #7")  # PR's text is the older prefix
        self.assertEqual((merged2, mode2), (pr, "main"))
        other = row(desc="**New task.** different words")
        _, mode3, _ = kml.merge_row(None, main, other, "PR #7")
        self.assertEqual(mode3, "fallback")

    def test_pipes_inside_the_description_survive(self):
        base = row(desc="**Task.** uses `a | b`")
        main = row(desc="**Task.** uses `a | b` Main note.")
        pr = row(desc="**Task.** uses `a | b` PR outcome.")
        merged, mode, _ = kml.merge_row(base, main, pr, "PR #7")
        self.assertEqual(mode, "appended")
        self.assertEqual(merged, row(desc="**Task.** uses `a | b` Main note. PR outcome."))

    def test_unsplittable_row_keeps_the_pr_row_like_before(self):
        merged, mode, _ = kml.merge_row("not a row", "also not", "still not  ", "PR #7")
        self.assertEqual((merged, mode), ("still not", "plain"))


if __name__ == "__main__":
    unittest.main()
