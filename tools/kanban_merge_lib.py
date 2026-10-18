"""Merge two edits of the SAME kanban row without losing either side (docs/166 section 3, BD-999).

Used by tools/merge_main_into_pr.py and tools/merge_train.py. Pure text functions, no git.

Old behaviour (lesson of 2026-10-18): when main AND the PR both edited a BD row, the PR's whole row was kept and
main's newer notes were silently dropped. Now `merge_row(base, main, pr, pr_label)` returns main's row with the PR's NEW
outcome text added:

  * APPENDED  the PR only added text at the end of the description (compared with the merge-base row): that added
              text goes at the end of main's description, before the final deps column. Title and first column are main's.
  * FALLBACK  the PR rewrote the middle of the row (or the row was added on both sides): main's description stays and
              the PR's whole description is appended as `**(from PR #N, check)** ...` so a person can tidy it.

Short columns (status, priority, deps): a side that changed it alone wins; if both changed it differently main's value
stays and the note says what the PR wanted. A row is `| id | status | priority | description | deps |`; the description
may itself contain `|` (everything between the 4th and the second-to-last bar).
"""

JOINER = " "


def split_row(row):
    """-> list of cells (not stripped) of a table row, or None if it does not look like one."""
    r = row.rstrip()
    if not r.startswith("|") or not r.endswith("|"):
        return None
    cells = r[1:-1].split("|")
    return cells if len(cells) >= 5 else None


def join_row(cells):
    return "|" + "|".join(cells) + "|"


def _desc(cells):
    return "|".join(cells[3:-1]).strip()


def merge_desc(base, main, pr, pr_label):
    """-> (text, mode, detail). mode: 'same', 'appended' or 'fallback'. `base` may be None (row added on both sides)."""
    if pr == main:
        return main, "same", ""
    if base is not None:
        if pr == base:
            return main, "same", "the PR did not change the description"
        if main == base:
            return pr, "pr-only", "main did not change the description"
        if pr.startswith(base):
            added = pr[len(base):].strip()
            if not added or added in main:
                return main, "same", "the PR's new text is already in main's row"
            return main + JOINER + added, "appended", "%d new character(s) of the PR's text added" % len(added)
    else:
        if main.startswith(pr):
            return main, "same", "main's row already contains the PR's text"
        if pr.startswith(main):
            added = pr[len(main):].strip()
            return main + JOINER + added, "appended", "%d new character(s) of the PR's text added" % len(added)
    return (main + JOINER + "**(from %s, check)** %s" % (pr_label, pr), "fallback",
            "the PR rewrote the middle of the row: its whole text was appended, please tidy it")


def merge_row(base, main, pr, pr_label="the PR"):
    """Merge the PR's edit of a row into main's row. `base` is the merge-base row or None.

    -> (merged row line, mode, notes) with mode 'appended', 'fallback', 'main' (nothing of the PR to add),
    'pr-only' (main left the description alone) or 'plain' (the rows could not be split: the PR's row is returned
    unchanged, like the old rule). `pr_label` names the PR in the fallback paragraph, for example 'PR #482'."""
    mc, pc = split_row(main), split_row(pr)
    bc = split_row(base) if base is not None else None
    if mc is None or pc is None or (base is not None and bc is None):
        return pr.rstrip(), "plain", ["row layout differs, kept the PR's row"]
    notes, out = [], list(mc)
    for i in (1, 2, -1):  # status, priority, deps: a side that changed it alone wins; the id column stays main's
        m, p = mc[i].strip(), pc[i].strip()
        b = bc[i].strip() if bc is not None else None
        if p == m or (b is not None and p == b):
            continue
        if b is not None and m == b:
            out[i] = pc[i]
        else:
            notes.append("column %d: both sides changed it, kept main's %r (the PR wanted %r)"
                         % (i % len(mc) + 1, m, p))
    text, mode, detail = merge_desc(_desc(bc) if bc is not None else None, _desc(mc), _desc(pc), pr_label)
    if mode in ("appended", "fallback", "pr-only"):
        out[3:-1] = [" " + text + " "]  # one padded description cell between main's other cells
    if detail:
        notes.insert(0, detail)
    mode = "main" if mode == "same" else mode
    return (main.rstrip() if mode == "main" and out == mc else join_row(out)), mode, notes
