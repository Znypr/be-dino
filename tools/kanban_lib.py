"""Shared code for the one-file-per-row kanban board (BD-1061, docs/191).

Where rows live:
  * AFTER the cutover (marker file docs/kanban/CUTOVER): one file per task, docs/kanban/rows/BD-NNNN.md. The file holds
    exactly the old table-row line (`| BD-NNN | status | P1 | task text | deps |`) plus one newline, LF endings.
  * BEFORE the cutover (and in old PR branches): the big table inside docs/07-kanban.md.
Every function that reads rows works on both layouts, so the tools keep working on old branches and in old tests.

Plain text and git only, no third-party packages.
"""
import re
import subprocess
from collections import OrderedDict
from pathlib import Path

ROWS_DIR = "docs/kanban/rows"
LEGACY = "docs/07-kanban.md"
CUTOVER = "docs/kanban/CUTOVER"
ROW_ID = re.compile(r"^\|\s*(BD-\d+)\s*\|")
FILE_NAME = re.compile(r"^BD-(\d+)\.md$")
TABLE_HEADER = re.compile(r"^\| ID \| Status \| Pri(?:ority)? \| Task \| Depend")
TABLE_SEPARATOR = re.compile(r"^\|[\s:|-]+\|?\s*$")
HEADER_LINE = "| ID | Status | Priority | Task | Dependencies |"
SEPARATOR_LINE = "|---|---|---|---|---|"
# "Review / test" must be tried before the bare legacy "Review".
STATUSES = ["Backlog", "Ready", "In progress", "In review", "Review / test", "Review", "Blocked", "Done",
            "Superseded", "Parked", "Spike"]


# ---------------------------------------------------------------- ids and names

def number(rid):
    """'BD-0061' / 'BD-61' -> 61."""
    return int(rid.split("-")[1])


def file_name(rid):
    """'BD-61' -> 'BD-0061.md' (at least four digits so the names sort like the numbers)."""
    return "BD-%04d.md" % number(rid)


def row_path(rid):
    return "%s/%s" % (ROWS_DIR, file_name(rid))


def row_id(line):
    m = ROW_ID.match(line)
    return m.group(1) if m else None


def canonical_id(rid):
    return "BD-%d" % number(rid)


# ---------------------------------------------------------------- one row

def parse_row(line):
    """-> dict(id, status, priority, text, deps, line). Tolerant: the task text may contain `|`, and a few old rows do
    not end with a closing bar (then deps is empty and the text runs to the end of the line)."""
    line = line.rstrip("\r\n")
    body = line.strip()
    closed = body.endswith("|")
    parts = body[1:-1].split("|") if closed else body[1:].split("|")
    if len(parts) < 4:
        return None
    if closed and len(parts) >= 5:
        text, deps = "|".join(parts[3:-1]).strip(), parts[-1].strip()
    else:  # a few old rows have only four columns (no dependencies) or no closing bar
        text, deps = "|".join(parts[3:]).strip(), ""
    return {"id": parts[0].strip(), "status": parts[1].strip(), "priority": parts[2].strip(), "text": text,
            "deps": deps, "line": line}


def normalise_status(raw):
    s = raw.strip().lower()
    for name in STATUSES:
        if s.startswith(name.lower()):
            return "Review / test" if name == "Review" else name
    return "Other"


def set_status(line, status):
    """Replace the status cell of a row, nothing else."""
    m = re.match(r"^(\|\s*BD-\d+\s*\|)([^|]*)(\|.*)$", line, re.S)
    if not m:
        raise ValueError("not a task row")
    return "%s %s %s" % (m.group(1), status, m.group(3))


def append_note(line, note):
    """Append an outcome sentence to the END of the task text (before the dependencies column), after one space."""
    note = note.strip()
    if not note:
        return line
    body = line.rstrip()
    if body.endswith("|"):
        head, _, deps = body[:-1].rpartition("|")
        if head.count("|") >= 3:  # id, status, priority, task are before the dependencies cell
            return "%s %s |%s|" % (head.rstrip(), note, deps)
    return body + " " + note


# ---------------------------------------------------------------- legacy table inside docs/07-kanban.md

def split_legacy(text):
    """Split the text of the old docs/07-kanban.md.

    -> (rows, prose_lines, first_table_index)
    rows: list of (id, row line) in file order. prose_lines: every other line, with the table lines removed (original line
    endings kept, so CRLF files stay CRLF). first_table_index: where the first removed table started inside prose_lines
    (None if there was no table). Removed: BD rows, the `| ID | Status | ...` header and its `|---|` line, stray ` |`
    lines that sit inside a table, and the blank lines between table lines."""
    lines = text.split("\n")
    rows, prose, first, pending, in_table = [], [], None, [], False
    for i, raw in enumerate(lines):
        line = raw.rstrip("\r")
        is_row = ROW_ID.match(line) is not None
        is_header = TABLE_HEADER.match(line) is not None
        is_sep = (TABLE_SEPARATOR.match(line) is not None and in_table and bool(prose or pending)
                  and (lines[i - 1].rstrip("\r").startswith("| ID ") if i else False))
        is_stray = in_table and line.strip() in ("|", "") and line.strip() == "|"
        if is_row or is_header or is_sep or is_stray:
            if is_row:
                rows.append((ROW_ID.match(line).group(1), line))
            if not in_table:
                if first is None:
                    first = len(prose)
                in_table = True
            pending = []  # blank lines between table lines go away with the table
            continue
        if in_table and line.strip() == "":
            pending.append(raw)  # decide when the next line shows whether the table goes on
            continue
        if pending:
            prose.extend(pending[:1])  # a gap after a table: keep one blank line
            pending = []
        in_table = False
        prose.append(raw)
    return rows, prose, first  # blank lines after the last table are dropped: the file ends after the last prose line


def read_legacy_rows(text):
    """-> OrderedDict id -> row line, first copy of a repeated id wins (the old tools did the same)."""
    out = OrderedDict()
    for rid, line in split_legacy(text)[0]:
        out.setdefault(rid, line)
    return out


# ---------------------------------------------------------------- reading rows from disk or git

def sort_rows(rows):
    return OrderedDict(sorted(rows.items(), key=lambda kv: number(kv[0])))


def rows_dir(root):
    return Path(root) / ROWS_DIR


def has_row_files(root):
    return rows_dir(root).is_dir()


def read_row_file(path):
    """The first non-empty line of a row file (CR/LF stripped)."""
    raw = Path(path).read_bytes().decode("utf-8")
    for line in raw.splitlines():
        if line.strip():
            return line.rstrip("\r")
    return ""


def read_rows(root):
    """-> OrderedDict id -> row line, sorted by number. Row files when the repo has them, else the old table."""
    root = Path(root)
    out = OrderedDict()
    if has_row_files(root):
        for p in sorted(rows_dir(root).iterdir()):
            m = FILE_NAME.match(p.name)
            if not m or not p.is_file():
                continue
            line = read_row_file(p)
            rid = row_id(line) or "BD-%d" % int(m.group(1))
            out.setdefault(rid, line)
        return sort_rows(out)
    legacy = root / LEGACY
    if legacy.is_file():
        return sort_rows(read_legacy_rows(legacy.read_bytes().decode("utf-8")))
    return out


def row_numbers(root):
    """-> list of task numbers, one entry per row found (so a repeated number shows up twice): the row files by name and
    content, plus any rows still in the old table."""
    root = Path(root)
    nums = []
    if has_row_files(root):
        for p in rows_dir(root).iterdir():
            m = FILE_NAME.match(p.name)
            if m and p.is_file():
                nums.append(int(m.group(1)))
    legacy = root / LEGACY
    if legacy.is_file():
        nums += [number(rid) for rid, _ in split_legacy(legacy.read_bytes().decode("utf-8"))[0]]
    return nums


def git(repo, *args, check=True, binary=False):
    p = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", *args], capture_output=True)
    if check and p.returncode:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), p.stderr.decode("utf-8", "replace").strip()))
    return p.stdout if binary else p.stdout.decode("utf-8", "replace")


def ref_has_cutover(repo, ref):
    return subprocess.run(["git", "-C", str(repo), "cat-file", "-e", "%s:%s" % (ref, CUTOVER)],
                          capture_output=True).returncode == 0


def ref_row_blobs(repo, ref):
    """-> OrderedDict file path -> raw bytes, for the row files at a git ref ({} if the ref has none)."""
    out = git(repo, "ls-tree", "-r", ref, "--", ROWS_DIR, check=False)
    entries = []
    for l in out.splitlines():
        meta, _, path = l.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob":
            entries.append((path, parts[2]))
    result = OrderedDict()
    if not entries:
        return result
    feed = "".join(sha + "\n" for _, sha in entries).encode()
    p = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch"], input=feed, capture_output=True)
    if p.returncode:
        raise RuntimeError("git cat-file failed: " + p.stderr.decode("utf-8", "replace").strip())
    data, pos = p.stdout, 0
    for path, _sha in entries:
        end = data.index(b"\n", pos)
        size = int(data[pos:end].split()[2])
        result[path] = data[end + 1:end + 1 + size]
        pos = end + 1 + size + 1
    return result


def first_line(raw):
    for l in raw.decode("utf-8", "replace").splitlines():
        if l.strip():
            return l.rstrip("\r")
    return ""


def ref_row_files(repo, ref):
    """-> OrderedDict file path -> row line, for the row files at a git ref ({} if the ref has none)."""
    return OrderedDict((path, first_line(raw)) for path, raw in ref_row_blobs(repo, ref).items())


def rows_at(repo, ref):
    """-> OrderedDict id -> row line at a git ref, in whichever layout the ref has."""
    files = ref_row_files(repo, ref)
    out = OrderedDict()
    if files:
        for path, line in files.items():
            m = FILE_NAME.match(path.rsplit("/", 1)[-1])
            rid = row_id(line) or ("BD-%d" % int(m.group(1)) if m else None)
            if rid:
                out.setdefault(rid, line)
        return sort_rows(out)
    text = git(repo, "show", "%s:%s" % (ref, LEGACY), check=False)
    return sort_rows(read_legacy_rows(text))


# ---------------------------------------------------------------- writing and rendering

def write_row_file(root, rid, line):
    """Write docs/kanban/rows/BD-NNNN.md = the row line + LF. Returns True if the file changed."""
    path = Path(root) / row_path(rid)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (line.rstrip("\r\n") + "\n").encode("utf-8")
    if path.exists() and path.read_bytes() == data:
        return False
    path.write_bytes(data)
    return True


def render(rows):
    """The old full table for reading (LF): header, separator, rows sorted by number."""
    return "\n".join([HEADER_LINE, SEPARATOR_LINE] + list(sort_rows(rows).values())) + "\n"


def check_row_entries(entries):
    """Static checks of row files. entries: list of (file name, bytes). -> list of problems (plain words)."""
    problems, seen = [], {}
    for name, raw in sorted(entries):
        if name == ".gitkeep":
            continue
        m = FILE_NAME.match(name)
        if not m:
            problems.append("%s/%s: not a row file (rows are named BD-0001.md, BD-0002.md, ...)" % (ROWS_DIR, name))
            continue
        n = int(m.group(1))
        want = "BD-%04d.md" % n
        if name != want:
            problems.append("%s: the file name must be %s (zero-padded to 4 digits)" % (name, want))
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            problems.append("%s: not valid UTF-8" % name)
            continue
        if "\r" in text:
            problems.append("%s: has a CR character; row files use plain LF line endings (.gitattributes sets eol=lf)" % name)
            text = text.replace("\r", "")
        lines = [l for l in text.split("\n") if l.strip()]
        if len(lines) != 1 or not text.endswith("\n") or text.endswith("\n\n"):
            problems.append("%s: must be exactly one row line followed by one newline (found %d line(s))" % (name, len(lines)))
            continue
        rid = row_id(lines[0])
        if rid is None:
            problems.append("%s: the line does not start with `| BD-%d |`" % (name, n))
            continue
        if number(rid) != n:
            problems.append("%s: the row inside is %s, so the file name must be %s" % (name, rid, file_name(rid)))
        info = parse_row(lines[0])
        if info is None or not info["status"]:
            problems.append("%s: the row has no status/priority/task columns" % name)
        if number(rid) in seen:
            problems.append("%s and %s are the same task number %d" % (seen[number(rid)], name, number(rid)))
        seen[number(rid)] = name
    return problems


def stray_legacy_rows(text):
    return [rid for rid, _ in split_legacy(text)[0]]


def stray_message(stray):
    return ("%s still has %d task row(s) (%s...): rows now live in %s, one file each; move yours with "
            "`python tools/kanban_migrate_pr.py <your PR or branch>`" % (LEGACY, len(stray), ", ".join(stray[:3]), ROWS_DIR))


def check_rows_dir(root):
    """Static checks of the row files on disk in `root` (and of leftover rows in docs/07-kanban.md after the cutover)."""
    root = Path(root)
    d = rows_dir(root)
    if not d.is_dir():
        return []
    problems = check_row_entries([(p.name, p.read_bytes()) for p in sorted(d.iterdir()) if p.is_file()])
    for p in d.iterdir():
        if p.is_dir():
            problems.append("%s/%s: folders are not allowed here" % (ROWS_DIR, p.name))
    legacy = root / LEGACY
    if (root / CUTOVER).exists() and legacy.is_file():
        stray = stray_legacy_rows(legacy.read_bytes().decode("utf-8"))
        if stray:
            problems.append(stray_message(stray))
    return problems
