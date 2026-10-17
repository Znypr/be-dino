"""Every tools/verify_*.py must run in CI (BD-004 release dry run, docs/148), or be listed here with a reason.

A verifier that CI never runs is dead weight: it can rot without anyone noticing, and tools/release_playtest.py reads its
command list from the workflow, so an orphan is also missing from the release rehearsal. Found by the 2026-10-17 dry run:
tools/verify_safe_eggs_line.py (BD-365) had never been added to the workflow.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/build-generated-place.yml"

# verifier file name -> why CI does not run it. Keep this empty if you can: add the line to the workflow instead.
NOT_IN_CI: dict[str, str] = {}


class CiVerifierCoverageTests(unittest.TestCase):
    def test_every_verifier_is_in_the_workflow_or_excluded_with_a_reason(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        orphans = sorted(
            p.name for p in (ROOT / "tools").glob("verify_*.py")
            if f"tools/{p.name}" not in workflow and p.name not in NOT_IN_CI
        )
        self.assertEqual(orphans, [], "not run by .github/workflows/build-generated-place.yml (add a line there, or list it in "
                                      "NOT_IN_CI with a reason): " + ", ".join(orphans))

    def test_exclusions_are_real_and_explained(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for name, reason in NOT_IN_CI.items():
            self.assertTrue((ROOT / "tools" / name).is_file(), f"{name} is listed in NOT_IN_CI but does not exist")
            self.assertNotIn(f"tools/{name}", workflow, f"{name} is in the workflow now: drop it from NOT_IN_CI")
            self.assertTrue(reason.strip(), f"{name} needs a reason")


if __name__ == "__main__":
    unittest.main()
