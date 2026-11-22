#!/usr/bin/env python3
"""Run the CI's Luau check list in parallel shards, and decide whether a pull request needs that list at all (BD-1302).

The list lives in .github/workflows/build-generated-place.yml as the `CI_LUAU_CHECKS: |` block (one command per line, comments
allowed). The verifiers and tools/release_playtest.py read their own lines from that file, so the lines stay there verbatim.

    python tools/ci_shard.py --shard 2/4            # run shard 2 of 4; report all failures
    python tools/ci_shard.py --list --shard 2/4     # print the commands of that shard, run nothing
    python tools/ci_shard.py --estimate --shards 4  # expected seconds per shard from tools/ci_shard_times.json
    python tools/ci_shard.py --update-times LOG...  # refresh the times from CI shard logs ("[i/n]  12.3s ok: <command>" lines)

Shards are balanced by measured time (BD-1303): tools/ci_shard_times.json holds each command's seconds from a real CI run; the
longest command goes first onto the least loaded shard. A command missing from the file counts as the median time.
    python tools/ci_shard.py --needs-luau --base origin/main --head HEAD
        # prints "luau=true" or "luau=false" (also appended to $GITHUB_OUTPUT when set): false only when no changed file is
        # game input (src, resources, assets, place file, workflow) and none is mentioned by any script on the list

Commands run through bash from the repo root, exactly as CI wrote them (the /tmp/luau paths are the CI ones; locally use
tools/run_ci_list.py, which swaps in this PC's runner).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/build-generated-place.yml"
MARKER = "CI_LUAU_CHECKS: |"
# changes under these always need the Luau checks (game input, the place file, the workflow and this script)
ALWAYS = ("src/", "resources/", "assets/", "default.project.json", ".github/", "tools/ci_shard.py")
TIMES = ROOT / "tools" / "ci_shard_times.json"


def check_lines(text: str | None = None) -> list[str]:
    """The commands of the CI_LUAU_CHECKS block, in order (comments and blank lines dropped)."""
    text = WORKFLOW.read_text(encoding="utf-8") if text is None else text
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.strip() == MARKER), None)
    if start is None:
        raise SystemExit(f"{MARKER!r} not found in {WORKFLOW.name}")
    indent = len(lines[start]) - len(lines[start].lstrip())
    out = []
    for raw in lines[start + 1:]:
        if raw.strip() and len(raw) - len(raw.lstrip()) <= indent:
            break
        line = raw.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def load_times() -> dict[str, float]:
    import json
    try:
        return {k: float(v) for k, v in json.loads(TIMES.read_text(encoding="utf-8")).items()}
    except (OSError, ValueError):
        return {}


def cost_of(lines: list[str], times: dict[str, float]) -> list[float]:
    known = sorted(times[l] for l in lines if l in times)
    default = known[len(known) // 2] if known else 1.0
    return [times.get(l, default) for l in lines]


def assign(lines: list[str], n: int, times: dict[str, float] | None = None) -> list[list[int]]:
    """Indices of each shard: longest command first onto the least loaded shard (ties: lower shard). Deterministic."""
    times = load_times() if times is None else times
    cost = cost_of(lines, times)
    loads, groups = [0.0] * n, [[] for _ in range(n)]
    for i in sorted(range(len(lines)), key=lambda i: (-cost[i], i)):
        k = min(range(n), key=lambda k: (loads[k], k))
        loads[k] += cost[i]
        groups[k].append(i)
    return [sorted(g) for g in groups]


def shard(lines: list[str], k: int, n: int, times: dict[str, float] | None = None) -> list[str]:
    """Shard k (1-based) of n, in list order, balanced by measured time."""
    if not (1 <= k <= n):
        raise SystemExit(f"bad shard {k}/{n}")
    return [lines[i] for i in assign(lines, n, times)[k - 1]]


def estimate(lines: list[str], n: int, times: dict[str, float] | None = None) -> list[float]:
    times = load_times() if times is None else times
    cost = cost_of(lines, times)
    return [round(sum(cost[i] for i in g), 1) for g in assign(lines, n, times)]


def update_times(logs: list[str]) -> int:
    import json
    times = load_times()
    found = 0
    for log in logs:
        for raw in Path(log).read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.search(r"\[\d+/\d+\]\s+([0-9.]+)s ok: (.+)$", raw.rstrip())
            if m:
                times[m.group(2).strip()] = round(float(m.group(1)), 1)
                found += 1
    current = set(check_lines())
    times = {k: v for k, v in sorted(times.items()) if k in current}
    TIMES.write_text(json.dumps(times, indent=1) + "\n", encoding="utf-8")
    print(f"{found} timings read, {len(times)} commands in {TIMES.name}")
    return 0


def scripts_of(lines: list[str]) -> list[Path]:
    paths = []
    for line in lines:
        for m in re.finditer(r"tools/[\w/]+\.py", line):
            p = ROOT / m.group(0)
            if p.is_file() and p not in paths:
                paths.append(p)
    return paths


def needs_luau(changed: list[str], lines: list[str] | None = None) -> tuple[bool, str]:
    """(needed, reason). Needed when a changed path is game input or is named (file name or module stem) by any listed script."""
    lines = check_lines() if lines is None else lines
    if not changed:
        return True, "no changed files listed: run everything"
    for path in changed:
        if path.startswith(ALWAYS):
            return True, f"{path} is game input"
    listed = scripts_of(lines)
    corpus = "\n".join(lines) + "\n" + "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in listed)
    for path in changed:
        name = Path(path).name
        stem = Path(path).stem
        if name in corpus or (path.endswith(".py") and re.search(r"\b%s\b" % re.escape(stem), corpus)):
            return True, f"{path} is used by the Luau check list"
        parts = Path(path).parts
        for n in range(len(parts) - 1, 1, -1):   # folders two levels deep or more (docs/catalog, docs/evidence/...)
            folder = "/".join(parts[:n])
            if folder in corpus:
                return True, f"{path} is in {folder}, which the Luau check list reads"
    return False, f"{len(changed)} changed file(s), none is game input or used by the {len(listed)} listed scripts"


def changed_files(base: str, head: str) -> list[str]:
    out = subprocess.run(["git", "diff", "--name-only", f"{base}...{head}"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode:
        return []
    return [l.strip() for l in out.stdout.splitlines() if l.strip()]


def run(lines: list[str]) -> int:
    failed, start = [], time.time()
    for i, line in enumerate(lines, 1):
        t0 = time.time()
        res = subprocess.run(["bash", "-c", line], cwd=ROOT)
        took = time.time() - t0
        status = "ok" if res.returncode == 0 else f"FAILED (exit {res.returncode})"
        print(f"::notice::[{i}/{len(lines)}] {took:5.1f}s {status}: {line}" if res.returncode else
              f"[{i}/{len(lines)}] {took:5.1f}s ok: {line}", flush=True)
        if res.returncode:
            failed.append(line)
    print(f"{len(lines) - len(failed)}/{len(lines)} passed in {time.time() - start:.0f} s", flush=True)
    for line in failed:
        print("FAILED:", line, flush=True)
    return 1 if failed else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shard", default="1/1", help="K/N")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--needs-luau", action="store_true")
    ap.add_argument("--base")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--shards", type=int, default=4)
    ap.add_argument("--update-times", nargs="+", metavar="LOG")
    a = ap.parse_args(argv)
    if a.update_times:
        return update_times(a.update_times)
    lines = check_lines()
    if a.estimate:
        est = estimate(lines, a.shards)
        print("expected seconds per shard:", est, " slowest:", max(est))
        return 0
    if a.needs_luau:
        needed, why = needs_luau(changed_files(a.base, a.head) if a.base else [], lines)
        print(f"luau={'true' if needed else 'false'}  ({why})")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
                fh.write(f"luau={'true' if needed else 'false'}\n")
        return 0
    k, n = (int(x) for x in a.shard.split("/"))
    mine = shard(lines, k, n)
    if a.list:
        print("\n".join(mine))
        print(f"# shard {k}/{n}: {len(mine)} of {len(lines)} commands")
        return 0
    return run(mine)


if __name__ == "__main__":
    sys.exit(main())
