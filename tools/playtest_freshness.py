#!/usr/bin/env python3
"""BD-1043: is this built playtest file the newest one?

    python tools/playtest_freshness.py build/BeDino-Build020-playtest.rbxlx
    python tools/playtest_freshness.py build/BeDino-Build020-playtest.manifest.json --warn-only
    python tools/playtest_freshness.py FILE --fetch        # run `git fetch origin` first

It finds the commit the file was built from (the manifest next to it, or the "BUILD redesign-NNN <id>" stamp inside the
.rbxlx) and counts the commits on origin/main since then. Prints "up to date" or "N commits behind origin/main" plus the
newest merged feature rows (git log subjects that name a BD- row).

Exit code: 0 up to date, 1 behind, 2 cannot tell (no stamp, unknown commit, no git). --warn-only turns 1 and 2 into 0.
Read-only: it never changes the repository (only --fetch talks to the network).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAMP_IN_PLACE = re.compile(r'Build = "redesign-(\d+) ([0-9a-f]{7,40})(\*?)"')
HEX = re.compile(r"[0-9a-f]{7,40}")
FEATURE_ROW = re.compile(r"\bBD-\d+")


class Unknown(Exception):
    """The built file does not say which commit it came from."""


def stamp_from_place_text(text: str):
    """(short id, dirty) from the Config source inside a .rbxlx, or None. Default-profile places carry no id."""
    match = STAMP_IN_PLACE.search(text)
    return (match.group(2), bool(match.group(3))) if match else None


def read_stamp(path: Path):
    """(commit id, dirty or None, how it was found) for a .rbxlx or a .manifest.json."""
    path = Path(path)
    if not path.exists():
        raise Unknown(f"{path} does not exist")
    manifest_path = path if path.name.endswith(".manifest.json") else path.with_suffix(".manifest.json")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        commit = manifest.get("git_commit")
        if commit and HEX.fullmatch(commit):
            return commit, manifest.get("git_dirty"), manifest_path.name
    if path.name.endswith(".manifest.json"):
        raise Unknown(f"{path.name} has no git_commit (built outside a git checkout)")
    found = stamp_from_place_text(path.read_text(encoding="utf-8", errors="replace"))
    if found:
        return found[0], found[1], path.name
    raise Unknown(f"{path.name} has no commit stamp (a default-profile place, or built before BD-1043); rebuild with: python tools/build.py --profile playtest")


def _git(*args: str, root: Path = ROOT) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout


def behind(commit: str, ref: str = "origin/main", root: Path = ROOT):
    """(number of commits on ref that `commit` does not have, subjects of the merged ones, newest first)."""
    try:
        _git("cat-file", "-e", commit + "^{commit}", root=root)
    except subprocess.CalledProcessError:
        raise Unknown(f"commit {commit} is not in this repository (try --fetch, or the file came from another clone)")
    try:
        count = int(_git("rev-list", "--count", f"{commit}..{ref}", root=root).strip())
        subjects = _git("log", "--first-parent", "--format=%s", f"{commit}..{ref}", root=root).splitlines()
    except subprocess.CalledProcessError as error:
        raise Unknown(f"cannot read {ref}: {error.stderr.strip() or error}")
    return count, [s for s in subjects if s.strip()]


def feature_rows(subjects: list[str], limit: int = 8) -> list[str]:
    """Newest merged subjects that name a kanban row (BD-NNN), at most `limit`."""
    return [s for s in subjects if FEATURE_ROW.search(s)][:limit]


def report(count: int, subjects: list[str], dirty, limit: int = 8, ref: str = "origin/main") -> list[str]:
    lines = []
    if count == 0:
        lines.append("up to date")
    else:
        lines.append(f"{count} commit{'s' if count != 1 else ''} behind {ref}")
        rows = feature_rows(subjects, limit)
        if rows:
            lines.append(f"newest merged feature rows since this build ({len(rows)} shown):")
            lines.extend(f"  - {row}" for row in rows)
        else:
            lines.append("no merged feature rows since this build (only housekeeping)")
        lines.append("rebuild: git fetch origin && python tools/build.py --profile playtest")
    if dirty:
        lines.append("note: this build had uncommitted changes (stamp ends with *)")
    return lines


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("built", type=Path, help="a built playtest .rbxlx or its .manifest.json")
    parser.add_argument("--ref", default="origin/main", help="what to compare with (default origin/main)")
    parser.add_argument("--fetch", action="store_true", help="run `git fetch origin` first")
    parser.add_argument("--limit", type=int, default=8, help="how many feature rows to list")
    parser.add_argument("--warn-only", action="store_true", help="always exit 0 (print only)")
    args = parser.parse_args(argv)
    try:
        if args.fetch:
            subprocess.run(["git", "fetch", "origin"], cwd=ROOT, check=True, capture_output=True)
        commit, dirty, source = read_stamp(args.built)
        count, subjects = behind(commit, args.ref)
    except (Unknown, subprocess.CalledProcessError, OSError, json.JSONDecodeError) as error:
        print(f"cannot tell: {error}")
        return 0 if args.warn_only else 2
    print(f"built from {commit[:8]} ({source})")
    for line in report(count, subjects, dirty, args.limit, args.ref):
        print(line)
    return 0 if count == 0 or args.warn_only else 1


if __name__ == "__main__":
    sys.exit(main())
