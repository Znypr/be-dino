#!/usr/bin/env python3
"""Fail if any tracked text file still holds git conflict markers (docs/166, BD-999).

  python tools/verify_no_conflict_markers.py            # scan every tracked file of this checkout
  python tools/verify_no_conflict_markers.py --root DIR  # scan another checkout (the merge tools do this)

Why: on 2026-10-18 the lead committed leftover `<<<<<<<` / `|||||||` / `=======` / `>>>>>>>` lines in docs because a
regex did not match CRLF line endings, and nothing noticed. This check reads every line with the line ending removed
(CRLF and LF look the same), so that cannot happen again.

What counts as a marker:
  * a line that STARTS with exactly 7 of `<`, `>` or `|` followed by a space or the end of the line;
  * a line that is exactly 7 `=` ONLY when a `<<<<<<<` line came earlier in the same file and no `>>>>>>>` closed it
    (so a markdown "=======" heading underline is never flagged on its own).

Binary files (a NUL byte) are skipped. Files that must contain markers on purpose are listed in ALLOWLIST with a
reason: add a line there only for a test fixture or a quoted third-party text, never for a real leftover.
Exit code 0 = clean, 1 = at least one marker found, 2 = could not list the files.
"""
import argparse
import re
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# path (forward slashes, relative to the repo root) -> why it may contain marker-looking lines.
ALLOWLIST: dict[str, str] = {}

MARKER = re.compile(r"^(<{7}|>{7}|\|{7})( |$)")
EQUALS = "======="
SIZE_LIMIT = 32 * 1024 * 1024


def tracked_files(root):
    p = subprocess.run(["git", "-C", str(root), "-c", "core.quotepath=off", "ls-files", "-z"], capture_output=True)
    if p.returncode:
        # Not a git checkout (the rehearsal runs the verifiers in a scratch COPY of the tree): walk the folder instead.
        if not os.path.isdir(root):
            raise RuntimeError("not a folder: " + str(root))
        skip = {".git", "build", "node_modules", "__pycache__"}
        found = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip]
            for name in filenames:
                found.append(os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/"))
        return found
    return [n for n in p.stdout.decode("utf-8", "replace").split("\0") if n]


def scan_text(text):
    """-> list of (line number, the line, what it is). CRLF safe: a line is split on \\n and a trailing \\r is dropped."""
    hits, open_at = [], None
    for number, raw in enumerate(text.split("\n"), 1):
        line = raw[:-1] if raw.endswith("\r") else raw
        m = MARKER.match(line)
        if m:
            hits.append((number, line, m.group(1)))
            if m.group(1) == "<" * 7:
                open_at = number
            elif m.group(1) == ">" * 7:
                open_at = None
        elif line == EQUALS and open_at is not None:
            hits.append((number, line, EQUALS))
    return hits


HINTS = {
    "<" * 7: "start of a conflict block (your side). Keep the right text, delete this line, the |||||||/=======/>>>>>>> "
             "lines of the same block and the text you do not want.",
    ">" * 7: "end of a conflict block. Delete this line and the rest of the block you do not want.",
    "|" * 7: "start of the merge-base text in a conflict block. Delete this line and the base text up to the =======.",
    EQUALS: "divider inside an unfinished conflict block. Delete it together with the text you do not want.",
}


def scan(root, allowlist=None):
    """-> list of (relative path, line number, line, hint). Raises RuntimeError if git cannot list the files."""
    root = Path(root)
    allow = ALLOWLIST if allowlist is None else allowlist
    out = []
    for name in tracked_files(root):
        if name in allow:
            continue
        path = root / name
        try:
            if not path.is_file() or path.stat().st_size > SIZE_LIMIT:
                continue
            raw = path.read_bytes()
        except OSError:
            continue
        if b"\0" in raw[:8192]:
            continue
        for number, line, kind in scan_text(raw.decode("utf-8", "replace")):
            out.append((name, number, line, HINTS[kind]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(ROOT), help="the checkout to scan (default: this one)")
    a = ap.parse_args(argv)
    try:
        hits = scan(a.root)
    except RuntimeError as e:
        print("verify_no_conflict_markers: %s" % e)
        return 2
    for name, number, line, hint in hits:
        print("%s:%d: %s   <- %s" % (name, number, line[:60], hint))
    if hits:
        print("FAIL: %d leftover conflict marker line(s) in %d file(s). Fix them, then commit again."
              % (len(hits), len({h[0] for h in hits})))
        return 1
    print("ok: no conflict markers in tracked files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
