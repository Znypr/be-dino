#!/usr/bin/env python3
"""Print the next free BD task id (and optionally reserve several), so parallel agents stop colliding.

  python tools/next_bd_id.py              # next free id, e.g. BD-530; also reserved for 48 h
  python tools/next_bd_id.py --reserve 3  # three consecutive free ids, reserved
  python tools/next_bd_id.py --peek       # just look, reserve nothing
  python tools/next_bd_id.py --doc        # next free docs/NN-*.md number instead (same rules)
  python tools/next_bd_id.py -v           # also say where the highest number came from

"Free" means higher than every BD id mentioned anywhere under docs/ on:
  * origin/main,
  * the head branch of every open PR (`gh pr list`), plus those PR titles and branch names,
  * every other git worktree of this clone with activity in the last 3 days: its docs/07-kanban.md
    read from disk, so rows an agent wrote but has not pushed are seen, and
  * ids already handed out by this tool on this machine (reservations are kept in the shared
    git dir, so every worktree of this clone sees them; they expire after 48 h).
If `gh` is missing or offline it falls back to origin/main + local worktrees and says so on stderr.
See AGENTS.md "Picking numbers".
"""
import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BD = re.compile(r"BD-(\d+)")
BRANCH_BD = re.compile(r"bd[-_]?(\d{2,})", re.I)
RESERVE_TTL = 48 * 3600
WORKTREE_AGE = 3 * 24 * 3600


def git(*args, check=False):
    p = subprocess.run(["git", "-C", str(ROOT), "-c", "core.quotepath=off", *args], capture_output=True)
    if check and p.returncode:
        raise RuntimeError(p.stderr.decode("utf-8", "replace").strip())
    return p.returncode, p.stdout.decode("utf-8", "replace")


def ref_exists(ref):
    return git("rev-parse", "--verify", "--quiet", ref + "^{commit}")[0] == 0


def open_prs():
    """Return (list of {number, headRefName, title}, None) or (None, reason)."""
    try:
        p = subprocess.run(["gh", "pr", "list", "--state", "open", "--limit", "300",
                            "--json", "number,headRefName,title"], capture_output=True, cwd=str(ROOT), timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, "gh not available (%s)" % e.__class__.__name__
    if p.returncode:
        err = p.stderr.decode("utf-8", "replace").strip().splitlines()
        return None, "gh failed: " + (err[-1] if err else "exit %d" % p.returncode)
    try:
        return json.loads(p.stdout.decode("utf-8", "replace")), None
    except ValueError:
        return None, "gh returned unreadable JSON"


def ids_in_ref(ref):
    rc, out = git("grep", "-ohE", "BD-[0-9]+", ref, "--", "docs/")
    return {int(m) for m in BD.findall(out)} if rc in (0, 1) else set()


def doc_numbers_in_ref(ref):
    rc, out = git("ls-tree", "--name-only", ref, "docs/")
    return {int(m.group(1)) for m in (re.match(r"docs/(\d+)-", l) for l in out.splitlines()) if m}


def worktree_activity(path):
    """Newest mtime among the worktree's git index/HEAD and its kanban file (0 if unknown)."""
    newest = 0.0
    cands = [path / "docs" / "07-kanban.md"]
    try:
        text = (path / ".git").read_text(encoding="utf-8").strip()
        if text.startswith("gitdir:"):
            gd = Path(text[7:].strip())
            cands += [gd / "index", gd / "HEAD"]
    except OSError:
        pass
    for c in cands:
        try:
            newest = max(newest, c.stat().st_mtime)
        except OSError:
            pass
    return newest


def live_worktrees():
    """Other worktrees of this clone that saw git or kanban activity in the last WORKTREE_AGE seconds.

    Old leftovers are skipped: a repo with hundreds of stale worktrees would otherwise take minutes."""
    rc, out = git("worktree", "list", "--porcelain")
    here = Path(git("rev-parse", "--show-toplevel")[1].strip() or ROOT)
    keep, cutoff = [], time.time() - WORKTREE_AGE
    for block in out.split("\n\n"):
        first = next((l for l in block.splitlines() if l.startswith("worktree ")), None)
        flags = {l.split(" ")[0] for l in block.splitlines()}
        if not first or "prunable" in flags or "bare" in flags:
            continue
        p = Path(first[len("worktree "):])
        try:
            if not p.is_dir() or p.samefile(here):
                continue
        except OSError:
            continue
        if worktree_activity(p) >= cutoff:
            keep.append(p)
    return keep


def scan_worktree(path, kind):
    """Numbers used by a worktree's own files, read straight from disk (so unpushed, even unsaved-to-git work counts).

    BD ids: its docs/07-kanban.md (where rows are claimed).
    Doc numbers: the docs/NN-*.md file names it has."""
    docs = path / "docs"
    try:
        names = os.listdir(docs)
    except OSError:
        return set()
    if kind == "doc":
        return {int(m.group(1)) for m in (re.match(r"(\d+)-", f) for f in names) if m}
    try:
        return {int(m) for m in BD.findall((docs / "07-kanban.md").read_text(encoding="utf-8", errors="replace"))}
    except OSError:
        return set()


def reservation_file():
    rc, out = git("rev-parse", "--git-common-dir")
    d = Path(out.strip())
    if not d.is_absolute():
        d = ROOT / d
    return d / "bd-id-reservations.json"


class Lock:
    def __init__(self, path):
        self.path = str(path) + ".lock"

    def __enter__(self):
        for _ in range(100):
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                try:  # stale lock from a crashed run
                    if time.time() - os.path.getmtime(self.path) > 30:
                        os.remove(self.path)
                except OSError:
                    pass
                time.sleep(0.1)
        raise RuntimeError("could not lock " + self.path)

    def __exit__(self, *exc):
        os.close(self.fd)
        try:
            os.remove(self.path)
        except OSError:
            pass


def load_reservations(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    now = time.time()
    return {k: v for k, v in data.items() if isinstance(v, (int, float)) and now - v < RESERVE_TTL}


def collect(kind, notes):
    """Return (set of numbers in use, (max, where), number of sources scanned)."""
    scan = ids_in_ref if kind == "bd" else doc_numbers_in_ref
    jobs = []  # (label, callable)
    git("fetch", "--quiet", "origin")  # best effort; offline just means older refs
    if ref_exists("origin/main"):
        jobs.append(("origin/main", lambda: scan("origin/main")))
    else:
        notes.append("origin/main not found")
    prs, why = open_prs()
    extra = {}  # numbers named only in PR titles / branch names
    if prs is None:
        notes.append("%s: considered origin/main and local worktrees only, NOT open PRs" % why)
    else:
        for pr in prs:
            label = "PR #%d (%s)" % (pr["number"], pr["headRefName"])
            ref = "origin/" + pr["headRefName"]
            if not ref_exists(ref):
                git("fetch", "--quiet", "origin", "pull/%d/head:refs/bd-ids/pr-%d" % (pr["number"], pr["number"]))
                ref = "refs/bd-ids/pr-%d" % pr["number"]
            if ref_exists(ref):
                jobs.append((label, lambda r=ref: scan(r)))
            else:
                notes.append("could not fetch " + label)
            if kind == "bd":
                text = pr["title"] + " " + pr["headRefName"]
                nums = {int(m) for m in BD.findall(pr["title"])} | {int(m) for m in BRANCH_BD.findall(text)}
                if nums:
                    extra[label] = nums
    for wt in live_worktrees():
        jobs.append(("worktree " + str(wt), lambda w=wt: scan_worktree(w, kind)))
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs = [(label, ex.submit(fn)) for label, fn in jobs]
        for label, f in futs:
            results.append((label, f.result()))
    for label, nums in extra.items():
        results.append((label + " title/branch", nums))
    used, top = set(), (0, "-")
    for label, nums in results:
        used |= nums
        if nums and max(nums) > top[0]:
            top = (max(nums), label)
    return used, top, len(results)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reserve", type=int, default=1, metavar="N", help="how many consecutive free ids (default 1)")
    ap.add_argument("--peek", action="store_true", help="do not record a reservation")
    ap.add_argument("--doc", action="store_true", help="next docs/NN number instead of a BD id")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    if a.reserve < 1:
        ap.error("--reserve must be at least 1")
    notes = []
    kind = "doc" if a.doc else "bd"
    used, top, nsrc = collect(kind, notes)
    path = reservation_file()
    key = (lambda n: "BD-%d" % n) if kind == "bd" else (lambda n: "DOC-%d" % n)
    with Lock(path):
        res = load_reservations(path)
        held = {int(k.split("-")[1]) for k in res if k.startswith(key(0)[:-1])}
        base = max(used | held | {0})
        picked = list(range(base + 1, base + 1 + a.reserve))
        if not a.peek:
            now = time.time()
            res.update({key(n): now for n in picked})
            path.write_text(json.dumps(res, indent=1), encoding="utf-8")
    for n in picked:
        print(key(n) if kind == "bd" else n)
    for n in notes:
        print("next_bd_id: WARNING: " + n, file=sys.stderr)
    if a.verbose or notes:
        print("next_bd_id: scanned %d sources; highest in use %s (%s)%s" % (
            nsrc, top[0], top[1], "; reserved on this machine" if not a.peek else ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
