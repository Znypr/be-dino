#!/usr/bin/env python3
"""Look at and change the kanban board. Rows are files: docs/kanban/rows/BD-NNNN.md (BD-1061, docs/191).

  python tools/kanban.py list [--status "Review / test"] [--priority P1] [--text word] [--limit N]
  python tools/kanban.py show BD-123
  python tools/kanban.py board                       # counts by status and priority (same as tools/board_summary.py)
  python tools/kanban.py render > build/kanban.md    # the old full table, sorted by task number (for reading; never commit it)
  python tools/kanban.py set-status BD-123 "Review / test" --note "what was done, what is NOT verified"
  python tools/kanban.py add --title "Short title" --priority P1 [--status Backlog] [--deps "BD-1, BD-2"] [--text "more words"]
  python tools/kanban.py add --id BD-1100 ...        # use an id you reserved yourself (otherwise next_bd_id.py picks one)

`set-status` edits only that row's file: the status cell changes, the title stays, and `--note` is added to the END of the
task text (before the dependencies column), like the old "append the outcome" rule. `add` creates the file and refuses to
overwrite an existing one. Exit codes: 0 ok, 1 not found / bad input, 2 problem with the repository.
"""
import argparse
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import kanban_lib as kl  # noqa: E402
import board_summary  # noqa: E402

ROOT = TOOLS.parent
PRIORITIES = ("P0", "P1", "P2", "P3")


def need_rows(root):
    if not kl.has_row_files(root):
        print("This checkout has no %s yet (the kanban is still the table in %s). Merge origin/main, or run "
              "`python tools/kanban_migrate.py --apply` at the cutover." % (kl.ROWS_DIR, kl.LEGACY))
        return False
    return True


def short(line, width=110):
    info = kl.parse_row(line)
    if not info:
        return line[:width]
    text = " ".join(info["text"].replace("*", "").split())
    return "%s | %s | %s | %s" % (info["id"], info["status"][:22], info["priority"][:2], text[:width])


def cmd_list(a, root):
    rows = kl.read_rows(root)
    n = 0
    for rid, line in rows.items():
        info = kl.parse_row(line)
        if info is None:
            continue
        if a.status and kl.normalise_status(info["status"]) != kl.normalise_status(a.status) \
                and a.status.lower() not in info["status"].lower():
            continue
        if a.priority and info["priority"][:2].upper() != a.priority.upper():
            continue
        if a.text and a.text.lower() not in line.lower():
            continue
        print(short(line))
        n += 1
        if a.limit and n >= a.limit:
            break
    print("(%d row(s) shown of %d)" % (n, len(rows)), file=sys.stderr)
    return 0


def find(root, rid):
    """-> (id as written in the row, row line or None). BD-4, BD-04 and BD-004 all find the same row."""
    try:
        want = kl.number(rid)
    except (ValueError, IndexError):
        return rid, None
    for k, line in kl.read_rows(root).items():
        if kl.number(k) == want:
            return k, line
    return "BD-%d" % want, None


def cmd_show(a, root):
    rid, line = find(root, a.id)
    if line is None:
        print("%s not found" % rid)
        return 1
    info = kl.parse_row(line)
    if info:
        print("%s | %s | %s | deps: %s" % (rid, info["status"], info["priority"], info["deps"] or "-"))
        print(info["text"])
    else:
        print(line)
    return 0


def cmd_board(a, root):
    print(board_summary.block(list(kl.read_rows(root).values())))
    return 0


def cmd_render(a, root):
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.stdout.write(kl.render(kl.read_rows(root)))
    return 0


def write_back(root, rid, line):
    if kl.has_row_files(root):
        kl.write_row_file(root, rid, line)
        return
    # old layout (before the cutover): change the row in place inside the table, keeping the file's line endings
    path = Path(root) / kl.LEGACY
    raw = path.read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.split("\n")
    for i, l in enumerate(lines):
        if kl.row_id(l.rstrip("\r")) == rid:
            lines[i] = line + ("\r" if eol == "\r\n" else "")
            break
    path.write_bytes("\n".join(lines).encode("utf-8"))


def cmd_set_status(a, root):
    rid, line = find(root, a.id)
    if line is None:
        print("%s not found" % rid)
        return 1
    status = a.status.strip()
    if not status:
        print("the new status must not be empty")
        return 1
    if kl.normalise_status(status) == "Other":
        print("note: %r is not one of the usual statuses (%s)" % (status, ", ".join(s for s in kl.STATUSES if s != "Review")),
              file=sys.stderr)
    if kl.normalise_status(status) == "Done" and not a.note:
        print("Done needs recorded evidence: add --note with what proves it.")
        return 1
    new = kl.set_status(line, status)
    if a.note:
        new = kl.append_note(new, a.note)
    write_back(root, rid, new)
    print("%s -> %s%s" % (rid, status, " (+ note)" if a.note else ""))
    return 0


def next_id():
    p = subprocess.run([sys.executable, str(TOOLS / "next_bd_id.py")], capture_output=True)
    out = p.stdout.decode("utf-8", "replace").split()
    if p.returncode or not out or not out[0].startswith("BD-"):
        raise RuntimeError("tools/next_bd_id.py failed: " + p.stderr.decode("utf-8", "replace").strip()[-200:])
    return out[0]


def cmd_add(a, root):
    if not need_rows(root):
        return 2
    if a.priority not in PRIORITIES:
        print("priority must be one of %s" % ", ".join(PRIORITIES))
        return 1
    title = " ".join(a.title.split())
    if not title or "|" in title or "|" in (a.text or "") or "|" in (a.deps or "") or "\n" in (a.text or ""):
        print("title/text/deps must not be empty or contain `|` or line breaks")
        return 1
    rid = kl.canonical_id(a.id) if a.id else next_id()
    path = Path(root) / kl.row_path(rid)
    if path.exists() or find(root, rid)[1] is not None:
        print("%s already exists; pick a fresh number with `python tools/next_bd_id.py`" % rid)
        return 1
    body = "**%s**" % title + ((" " + " ".join(a.text.split())) if a.text else "")
    line = "| %s | %s | %s | %s | %s |" % (rid, a.status, a.priority, body, a.deps or "None")
    kl.write_row_file(root, rid, line)
    print("%s created: %s" % (rid, kl.row_path(rid)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(ROOT), help="the checkout to work in (default: this one)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", help="rows, one line each")
    p.add_argument("--status")
    p.add_argument("--priority")
    p.add_argument("--text")
    p.add_argument("--limit", type=int, default=0)
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("show", help="one row in full")
    p.add_argument("id")
    p.set_defaults(fn=cmd_show)
    sub.add_parser("board", help="counts").set_defaults(fn=cmd_board)
    sub.add_parser("render", help="the whole table on stdout").set_defaults(fn=cmd_render)
    p = sub.add_parser("set-status", help="change the status of one row")
    p.add_argument("id")
    p.add_argument("status")
    p.add_argument("--note", help="outcome sentence, appended to the end of the task text")
    p.set_defaults(fn=cmd_set_status)
    p = sub.add_parser("add", help="create a new row (next free number)")
    p.add_argument("--title", required=True)
    p.add_argument("--priority", required=True)
    p.add_argument("--status", default="Backlog")
    p.add_argument("--deps")
    p.add_argument("--text")
    p.add_argument("--id")
    p.set_defaults(fn=cmd_add)
    a = ap.parse_args(argv)
    root = Path(a.root)
    try:
        return a.fn(a, root)
    except (RuntimeError, OSError) as e:
        print("kanban: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
