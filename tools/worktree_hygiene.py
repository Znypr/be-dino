#!/usr/bin/env python3
"""Keep git worktrees tidy (docs/170, BD-660): audit them, remove the safe ones, report what prune would do.

On 2026-10-18 the owner found about 248 GB of loose project copies (git worktrees, 0.5 to 0.8 GB each) in
C:/Users/znypr/Documents, made by helper agents over several days. This is the permanent version of the two throwaway
scripts the lead used to find and remove them.

  python tools/worktree_hygiene.py audit                 # read-only table + totals (also lists unregistered folders with a .git)
  python tools/worktree_hygiene.py audit --md out.md     # same, also written as a markdown file
  python tools/worktree_hygiene.py clean                 # DRY RUN: shows what would be removed and what is kept, and why
  python tools/worktree_hygiene.py clean --go            # really removes ONLY the safe ones (see below)
  python tools/worktree_hygiene.py prune-report          # what `git worktree prune` would do (it is never run)

The rule (docs/170): worktrees live in ONE folder, <repo>/.claude/worktrees (agents), or in the session scratchpad.
Anywhere else (for example a sibling folder in Documents) is flagged LOOSE.

`clean --go` removes a worktree only if ALL of these hold (checked again right before each removal):
  * it is not the main checkout and not locked, and its folder exists
  * no unsaved files: `git status` shows nothing modified, staged or untracked
  * every commit in it exists on a remote ref (nothing unpushed)
  * its gitdir HEAD has not moved for --min-age-hours (default 6), so a running or resumable helper is left alone
  * it does not match a --keep text
It uses plain `git worktree remove <path>` WITHOUT --force. It never deletes a branch, does no delete of its own, never runs
`git worktree prune`, never changes git config and never touches the main checkout. Files that git IGNORES (build
output and similar) are not "unsaved" for git and go with the worktree; `clean` prints how many ignored entries there are.

Remote refs are as of the last fetch. Add --fetch to run a plain `git fetch origin` first (updates remote refs only).
Stale refs can only make a worktree look MORE pushed if someone deleted the remote branch by hand, so run with --fetch
before a real --go.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ---- the rules, in one place -------------------------------------------------------------------------------------
# The one allowed folder for worktrees, relative to the main checkout. Agents get theirs here.
ALLOWED_AGENT_DIR = ".claude/worktrees"
# The other allowed place: the session scratchpad (Temp/claude/<project>/<session>/scratchpad/...). A path is in it if
# its lower-case, forward-slash form contains BOTH parts.
SCRATCHPAD_PARTS = ("/temp/claude/", "/scratchpad")
# Folders that are listed (one level down) when looking for unregistered copies that have a .git. The first is the
# folder the main checkout lives in (the 2026-10-18 problem), the second is the allowed folder.
SCAN_PARENT_OF_MAIN = True
DEFAULT_MIN_AGE_HOURS = 6.0
# Never touched: the main checkout is always the first entry of `git worktree list` and is refused by name below.


# ---- small helpers -----------------------------------------------------------------------------------------------
def norm(p) -> str:
    return os.path.normcase(os.path.realpath(str(p)))


def slash(p) -> str:
    return str(p).replace("\\", "/")


def git(repo, *args, timeout=300):
    """Run git in `repo`. Returns (returncode, stdout, stderr). Never raises."""
    try:
        r = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return r.returncode, r.stdout.strip("\r\n"), r.stderr.strip()
    except Exception as e:  # noqa: BLE001 - report, do not crash an audit
        return 99, "", str(e)


def dir_size(path) -> tuple[int, int]:
    """Total bytes and file count under path. Symlinks are not followed. Read-only."""
    total = files = 0
    stack = [str(path)]
    while stack:
        p = stack.pop()
        try:
            with os.scandir(p) as it:
                for e in it:
                    try:
                        if e.is_symlink():
                            continue
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        else:
                            total += e.stat(follow_symlinks=False).st_size
                            files += 1
                    except OSError:
                        pass
        except OSError:
            pass
    return total, files


def human_size(n) -> str:
    if n is None:
        return "?"
    if n >= 1 << 30:
        return f"{n / (1 << 30):.2f} GB"
    return f"{n / (1 << 20):.0f} MB"


def human_age(hours) -> str:
    if hours is None:
        return "?"
    if hours < 1:
        return f"{int(hours * 60)}m"
    if hours < 48:
        return f"{hours:.0f}h"
    return f"{hours / 24:.0f}d"


def parse_worktrees(porcelain: str) -> list[dict]:
    out, cur = [], {}
    for line in porcelain.splitlines() + [""]:
        if not line.strip():
            if cur:
                out.append(cur)
            cur = {}
            continue
        k, _, v = line.partition(" ")
        cur[k] = v
    return out


def find_main_checkout(start) -> Path:
    rc, out, err = git(start, "worktree", "list", "--porcelain")
    if rc != 0:
        raise SystemExit(f"not a git repository (or git failed): {start}\n{err}")
    wts = parse_worktrees(out)
    if not wts:
        raise SystemExit("git lists no worktrees")
    return Path(wts[0]["worktree"])  # git always lists the main checkout first


def gitdir_of(path: Path) -> Path | None:
    g = path / ".git"
    try:
        if g.is_dir():
            return g
        if g.is_file():
            txt = g.read_text(encoding="utf-8", errors="replace")
            if "gitdir:" in txt:
                d = Path(txt.split("gitdir:", 1)[1].strip().splitlines()[0].strip())
                return d if d.is_absolute() else (path / d)
    except OSError:
        pass
    return None


def last_activity_hours(path: Path, now: float) -> float | None:
    """Hours since the gitdir HEAD file last changed (checkout, commit, switch). None if unknown."""
    gd = gitdir_of(path)
    if gd is None:
        return None
    try:
        return max(0.0, (now - (gd / "HEAD").stat().st_mtime) / 3600)
    except OSError:
        return None


def in_allowed_place(path: Path, main: Path) -> bool:
    p = norm(path)
    allowed = norm(main / ALLOWED_AGENT_DIR)
    if p == allowed or p.startswith(allowed + os.sep):
        return True
    s = slash(p).lower()
    return all(part in s for part in SCRATCHPAD_PARTS)


# ---- audit -------------------------------------------------------------------------------------------------------
def audit(repo, *, with_size=True, fetch=False, scan_dirs=None, now=None) -> dict:
    now = time.time() if now is None else now
    main = find_main_checkout(repo)
    if fetch:
        git(main, "fetch", "-q", "origin")
    rc, out, _ = git(main, "worktree", "list", "--porcelain")
    wts = parse_worktrees(out)
    main_ref = None
    for cand in ("origin/main", "main"):
        if git(main, "rev-parse", "--verify", "-q", cand)[0] == 0:
            main_ref = cand
            break
    rows = []
    for w in wts:
        path = Path(w["worktree"])
        row = {
            "path": slash(path),
            "branch": w.get("branch", "(detached)").replace("refs/heads/", ""),
            "head": w.get("HEAD", "")[:10],
            "is_main": norm(path) == norm(main),
            "exists": path.exists(),
            "locked": "locked" in w,
            "lock_reason": w.get("locked", ""),
            "prunable": "prunable" in w,
            "size_bytes": None, "files": None, "dirty": [], "ignored": 0, "unpushed": None, "in_main": None,
            "age_hours": None, "allowed": in_allowed_place(path, main),
        }
        if row["is_main"] or not row["exists"]:
            rows.append(row)
            continue
        if with_size:
            row["size_bytes"], row["files"] = dir_size(path)
        rc, st, _ = git(path, "status", "--porcelain", "--untracked-files=normal", "--ignored=traditional")
        if rc == 0:
            lines = [ln for ln in st.splitlines() if ln.strip()]
            row["dirty"] = [ln for ln in lines if not ln.startswith("!!")]
            row["ignored"] = sum(1 for ln in lines if ln.startswith("!!"))
        else:
            row["dirty"] = ["(git status failed)"]
        rc, cnt, _ = git(path, "rev-list", "--count", "HEAD", "--not", "--remotes")
        row["unpushed"] = int(cnt) if rc == 0 and cnt.isdigit() else None
        if main_ref and w.get("HEAD"):
            row["in_main"] = git(main, "merge-base", "--is-ancestor", w["HEAD"], main_ref)[0] == 0
        row["age_hours"] = last_activity_hours(path, now)
        rows.append(row)

    registered = {norm(r["path"]) for r in rows}
    scan = list(scan_dirs) if scan_dirs is not None else (
        ([main.parent] if SCAN_PARENT_OF_MAIN else []) + [main / ALLOWED_AGENT_DIR])
    unregistered = []
    for d in scan:
        try:
            kids = sorted(Path(d).iterdir())
        except OSError:
            continue
        for k in kids:
            try:
                if not k.is_dir() or norm(k) in registered or norm(k) == norm(main):
                    continue
                if (k / ".git").exists():
                    size = dir_size(k)[0] if with_size else None
                    unregistered.append({"path": slash(k), "size_bytes": size,
                                         "kind": "git folder" if (k / ".git").is_dir() else "worktree copy, not registered"})
            except OSError:
                pass
    return {"main": slash(main), "rows": rows, "unregistered": unregistered, "main_ref": main_ref, "when": now}


def blockers(row: dict, min_age_hours: float, keep=()) -> list[str]:
    """Reasons this worktree must NOT be removed. Empty list = safe to remove."""
    if row["is_main"]:
        return ["main checkout"]
    why = []
    if row["locked"]:
        why.append("locked" + (f" ({row['lock_reason']})" if row["lock_reason"] else ""))
    if not row["exists"]:
        why.append("folder missing")
        return why
    if row["dirty"]:
        why.append(f"unsaved files ({len(row['dirty'])})")
    if row["unpushed"] is None:
        why.append("cannot tell if pushed")
    elif row["unpushed"] > 0:
        why.append(f"unpushed commits ({row['unpushed']})")
    if row["age_hours"] is None:
        why.append("age unknown")
    elif row["age_hours"] < min_age_hours:
        why.append(f"recent ({human_age(row['age_hours'])})")
    p = slash(row["path"]).lower()
    for k in keep:
        if k.lower() in p:
            why.append(f"--keep {k}")
    return why


def state_of(row: dict) -> str:
    """Short plain state word for the table."""
    if row["is_main"]:
        return "main"
    if not row["exists"]:
        return "missing"
    if row["dirty"]:
        return "UNSAVED"
    if row["unpushed"]:
        return "UNPUSHED"
    return "clean"


def where(row: dict) -> str:
    if row["is_main"]:
        return "main"
    return "ok" if row["allowed"] else "LOOSE"


def render_table(rep: dict, min_age_hours: float, keep=()) -> list[str]:
    rows = rep["rows"]
    lines = []
    head = f"{'SIZE':>9}  {'STATE':<8} {'PUSHED':<7} {'LOCK':<5} {'AGE':>4}  {'WHERE':<5} {'REMOVABLE?':<22} BRANCH / PATH"
    lines.append(head)
    for r in sorted(rows, key=lambda r: -(r["size_bytes"] or 0)):
        b = blockers(r, min_age_hours, keep)
        verdict = "yes" if not b else "no: " + b[0]
        if r["is_main"]:
            pushed = "-"
        elif r["unpushed"] is None:
            pushed = "?"
        else:
            pushed = "yes" if r["unpushed"] == 0 else f"no({r['unpushed']})"
        if r["in_main"]:
            pushed += "+main"
        lines.append(f"{human_size(r['size_bytes']):>9}  {state_of(r):<8} {pushed:<7} {'yes' if r['locked'] else '-':<5} "
                     f"{human_age(r['age_hours']):>4}  {where(r):<5} {verdict[:22]:<22} {r['branch']}")
        lines.append(f"{'':>9}  {r['path']}")
        if r["dirty"] and not r["is_main"]:
            for d in r["dirty"][:3]:
                lines.append(f"{'':>9}    unsaved: {d}")
            if len(r["dirty"]) > 3:
                lines.append(f"{'':>9}    ... and {len(r['dirty']) - 3} more")
    return lines


def totals(rep: dict, min_age_hours: float, keep=()) -> dict:
    rows = [r for r in rep["rows"] if not r["is_main"]]
    safe = [r for r in rows if not blockers(r, min_age_hours, keep)]
    loose = [r for r in rows if not r["allowed"]]
    unsaved = [r for r in rows if r["exists"] and r["dirty"]]
    unpushed = [r for r in rows if r["exists"] and r["unpushed"]]
    s = lambda rs: sum(r["size_bytes"] or 0 for r in rs)  # noqa: E731
    return {
        "worktrees": len(rows), "size": s(rows),
        "safe": len(safe), "safe_size": s(safe),
        "loose": len(loose), "loose_size": s(loose),
        "unsaved": len(unsaved), "unpushed": len(unpushed),
        "locked": sum(1 for r in rows if r["locked"]),
        "missing": sum(1 for r in rows if not r["exists"]),
        "unregistered": len(rep["unregistered"]),
        "unregistered_size": sum(u["size_bytes"] or 0 for u in rep["unregistered"]),
    }


def render_totals(t: dict, min_age_hours: float) -> list[str]:
    return [
        f"worktrees (not counting the main checkout): {t['worktrees']}, total {human_size(t['size'])}",
        f"safe to remove with `clean --go` (min age {min_age_hours:g}h): {t['safe']}, {human_size(t['safe_size'])}",
        f"with unsaved files: {t['unsaved']}; with unpushed commits: {t['unpushed']}; locked: {t['locked']}; folder missing: {t['missing']}",
        f"LOOSE (outside {ALLOWED_AGENT_DIR} and the scratchpad): {t['loose']}, {human_size(t['loose_size'])}",
        f"unregistered folders with a .git: {t['unregistered']}, {human_size(t['unregistered_size'])}",
    ]


def cmd_audit(args) -> int:
    rep = audit(args.repo, with_size=not args.no_size, fetch=args.fetch)
    keep = args.keep or []
    t = totals(rep, args.min_age_hours, keep)
    print(f"Worktree audit {time.strftime('%Y-%m-%d %H:%M', time.localtime(rep['when']))} (read-only)")
    print(f"main checkout: {rep['main']}")
    print(f"allowed folders: {rep['main']}/{ALLOWED_AGENT_DIR} and the session scratchpad")
    print()
    table = render_table(rep, args.min_age_hours, keep)
    print("\n".join(table))
    print()
    if rep["unregistered"]:
        print("Unregistered folders that contain a .git (check by hand, this tool never removes them):")
        for u in rep["unregistered"]:
            print(f"  {human_size(u['size_bytes']):>9}  {u['path']}  ({u['kind']})")
        print()
    print("\n".join(render_totals(t, args.min_age_hours)))
    if args.md:
        md = [f"# Worktree audit {time.strftime('%Y-%m-%d %H:%M', time.localtime(rep['when']))}", "",
              "Read-only output of `python tools/worktree_hygiene.py audit` (docs/170). Nothing was removed or moved.", "",
              "```text", *table, "```", ""]
        if rep["unregistered"]:
            md += ["Unregistered folders that contain a .git:", "", "```text",
                   *[f"{human_size(u['size_bytes']):>9}  {u['path']}  ({u['kind']})" for u in rep["unregistered"]], "```", ""]
        md += ["Totals:", "", *[f"- {ln}" for ln in render_totals(t, args.min_age_hours)], ""]
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text("\n".join(md), encoding="utf-8")
        print(f"\nwritten: {args.md}")
    if args.json:
        Path(args.json).write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return 0


# ---- clean -------------------------------------------------------------------------------------------------------
def clean(repo, *, go=False, min_age_hours=DEFAULT_MIN_AGE_HOURS, keep=(), fetch=False, with_size=True,
          log=print, now=None) -> dict:
    """Dry run unless go=True. Returns {"candidates": [...], "removed": [...], "skipped": {path: reasons}, "failed": [...]}."""
    rep = audit(repo, with_size=with_size, fetch=fetch, scan_dirs=[], now=now)
    main = rep["main"]
    cands, skipped = [], {}
    for r in rep["rows"]:
        b = blockers(r, min_age_hours, keep)
        if r["is_main"]:
            continue
        if b:
            skipped[r["path"]] = b
        else:
            cands.append(r)
    log(f"{'REAL RUN' if go else 'DRY RUN'}: {len(cands)} worktree(s) can be removed "
        f"({human_size(sum(r['size_bytes'] or 0 for r in cands))}), {len(skipped)} kept")
    for p, b in skipped.items():
        log(f"  keep    {p}  [{'; '.join(b)}]")
    result = {"candidates": [r["path"] for r in cands], "removed": [], "skipped": skipped, "failed": [], "freed": 0}
    for r in cands:
        note = f", {r['ignored']} ignored entr{'y' if r['ignored'] == 1 else 'ies'} go with it" if r["ignored"] else ""
        if not go:
            log(f"  remove  {r['path']}  ({human_size(r['size_bytes'])}{note})   <- dry run, nothing done")
            continue
        # Re-check right before removing: it may have changed since the audit.
        rc, st, _ = git(r["path"], "status", "--porcelain", "--untracked-files=normal")
        if rc != 0 or st.strip():
            log(f"  SKIP (became unsaved or unreadable): {r['path']}")
            result["skipped"][r["path"]] = ["became unsaved"]
            continue
        # Plain remove, no --force: git itself also refuses a dirty or locked worktree.
        rc, out, err = git(main, "worktree", "remove", r["path"])
        if rc == 0 and not Path(r["path"]).exists():
            result["removed"].append(r["path"])
            result["freed"] += r["size_bytes"] or 0
            log(f"  removed {r['path']}")
        else:
            result["failed"].append(r["path"])
            log(f"  FAILED  {r['path']}: {(err or out)[:200]}")
    if go:
        log(f"DONE: removed {len(result['removed'])}, failed {len(result['failed'])}, freed {human_size(result['freed'])}")
    else:
        log("Nothing was removed. Add --go to remove the list above.")
    return result


def cmd_clean(args) -> int:
    res = clean(args.repo, go=args.go, min_age_hours=args.min_age_hours, keep=args.keep or [], fetch=args.fetch,
                with_size=not args.no_size)
    return 1 if res["failed"] else 0


# ---- prune-report ------------------------------------------------------------------------------------------------
def prune_report(repo) -> list[str]:
    main = find_main_checkout(repo)
    rc, out, err = git(main, "worktree", "prune", "--dry-run", "--verbose")
    lines = [ln for ln in (out + "\n" + err).splitlines() if ln.strip()]
    return lines


def cmd_prune_report(args) -> int:
    lines = prune_report(args.repo)
    if not lines:
        print("Nothing to prune: every registered worktree folder exists.")
    else:
        print("`git worktree prune` WOULD remove these records (dry run, nothing was changed):")
        for ln in lines:
            print("  " + ln)
        print(f"{len(lines)} record(s). To do it for real, run `git worktree prune` yourself.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=".", help="any folder inside the repository (default: current folder)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, fetch=True):
        p.add_argument("--min-age-hours", type=float, default=DEFAULT_MIN_AGE_HOURS,
                       help=f"leave worktrees whose HEAD moved more recently than this (default {DEFAULT_MIN_AGE_HOURS:g})")
        p.add_argument("--keep", action="append", help="never remove a worktree whose path contains this text (repeatable)")
        p.add_argument("--no-size", action="store_true", help="skip the (slow) size count")
        if fetch:
            p.add_argument("--fetch", action="store_true", help="run `git fetch origin` first (updates remote refs only)")

    a = sub.add_parser("audit", help="read-only table of every worktree")
    common(a)
    a.add_argument("--md", help="also write the output as a markdown file")
    a.add_argument("--json", help="also write the raw data as JSON")
    a.set_defaults(fn=cmd_audit)
    c = sub.add_parser("clean", help="remove safe worktrees (dry run unless --go)")
    common(c)
    c.add_argument("--go", action="store_true", help="really remove (default is a dry run)")
    c.set_defaults(fn=cmd_clean)
    p = sub.add_parser("prune-report", help="what `git worktree prune` would do")
    p.set_defaults(fn=cmd_prune_report)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
