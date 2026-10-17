#!/usr/bin/env python3
"""Switch-on rehearsal runner (docs/149): run the offline verifiers against a release profile's Config values.

    python tools/run_rehearsal.py --runner C:/.../luau.exe --compiler C:/.../luau-compile.exe
    python tools/run_rehearsal.py --runner ... --profile all-on-rehearsal --only multiplayer,gifts
    python tools/run_rehearsal.py --runner ... --profile none          # baseline: the committed Config as it is
    python tools/run_rehearsal.py --list

Why a tree copy: every verifier reads `src/shared/Config.luau` relative to its own file (`Path(__file__).resolve().parents[1]`)
and most embed the file into a Luau harness. The runner therefore copies `src/`, `tools/`, `tests/` and the workflow into a
scratch directory, rewrites ONLY the scratch copy of Config with `release_profiles.apply_profile` (the same rewrite
`tools/build.py --profile` does for a place), links the big read-only folders (docs, resources, assets, build) and runs every
`python tools/...` command of the CI job there. The committed Config is never edited and nothing is written back.

The all-on-rehearsal profile is a SCRATCH profile: never built into a published place, never uploaded, not a shipped profile
(see tools/release_profiles.py and tools/release_playtest.shipped_profiles).

Many verifiers assert that a flag SHIPS false ("Config.CombatEnabled must stay false"). Those lines are expected to fail when the
flag is on; they are reported as `shipped-state` failures (a regexp over the output), not as interactions. Every other failure is
compared with the same command on the committed tree: a failure that is new only under the rehearsal is an `INTERACTION` and gets
a root-cause note in docs/149.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_profiles  # noqa: E402
import release_playtest  # noqa: E402

NL = chr(10)
OVERRIDES: dict = {}  # profile -> {key: value} applied by overlay_config (for the report)
COPIED = ["src", "tools", "tests", ".github", "default.project.json"]
LINKED = ["docs", "assets", "build"]
# default.project.json maps these resources into the place; build.py refuses a source path that resolves outside the project,
# so they are copied (a link would resolve to the real folder). Everything else under resources/ is read-only data and linked.
RESOURCES_COPIED = {"roblox", "worldkit", "world-materials.rbxmx"}
# Run explicitly by hand or meaningless against a scratch copy of the tree.
SKIP = {"build.py", "verify_release.py", "verify_kanban_merge.py", "board_summary.py", "verify_doc_ids.py", "verify_release_ids.py"}
# A verifier that checks "this flag ships false" fails when the flag is on. These phrases mark that class of failure.
SHIPPED_STATE = re.compile(
    r"ships (OFF|false)|must stay false|stay false|ships false|== ?false|is false in source|flag-off|flag off|off in the default"
    r"|PROFILE_OFF|requires False|must be false|ships OFF|ships off",
    re.I)


def link_dir(source: Path, target: Path) -> None:
    """Directory link without admin rights: symlink where allowed, a junction on Windows, else a copy."""
    try:
        os.symlink(source, target, target_is_directory=True)
        return
    except (OSError, NotImplementedError):
        pass
    if os.name == "nt":
        done = subprocess.run(["cmd", "/c", "mklink", "/J", str(target), str(source)], capture_output=True)
        if done.returncode == 0:
            return
    shutil.copytree(source, target)


def overlay_config(source: str, profile: str) -> tuple[str, list[str], dict]:
    """Config source whose RETURNED values are the profile's, while every original line stays as committed.

    Most verifiers read Config twice: embedded into a Luau harness (values matter) and as text, to prove a wiring rule such as
    "CombatEnabled = false ships in source" (the committed state matters). A rewrite of the lines would break the second kind for
    a reason that says nothing about behaviour. So the original table becomes `BaseConfig`, and a tail block clones it, overrides
    exactly the keys `release_profiles.apply_profile` changes, and returns the frozen result. Returns (source, errors, overrides).
    """
    if profile == "none":
        return source, [], {}
    rewritten, report = release_profiles.apply_profile(source, profile)
    before, after = release_profiles.config_entries(source), release_profiles.config_entries(rewritten)
    overrides = {key: after[key][-1][1] for key in after if key in before and after[key][-1][1] != before[key][-1][1]}
    head = "return table.freeze({"
    if source.count(head) != 1 or not source.rstrip().endswith("})"):
        return source, ["Config.luau no longer has the expected `return table.freeze({ ... })` shape; update overlay_config"], {}
    body = source.rstrip()
    body = body.replace(head, "local BaseConfig = table.freeze({", 1)
    lines = [body, "", "-- rehearsal overlay (tools/run_rehearsal.py): scratch tree only, never committed", "local Rehearsal: any = table.clone(BaseConfig)"]
    for key, value in overrides.items():
        lines.append(f"Rehearsal.{key} = {release_profiles.format_literal(value)}")
    lines.append("return table.freeze(Rehearsal)")
    return NL.join(lines) + NL, list(report.errors), overrides


def make_tree(profile: str, base: Path) -> Path:
    tree = base / "tree"
    tree.mkdir(parents=True)
    for name in COPIED:
        src = ROOT / name
        if src.is_dir():
            shutil.copytree(src, tree / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        elif src.is_file():
            shutil.copy2(src, tree / name)
    for name in LINKED:
        if (ROOT / name).is_dir():
            link_dir(ROOT / name, tree / name)
    (tree / "resources").mkdir()
    for entry in sorted((ROOT / "resources").iterdir()):
        if entry.name in RESOURCES_COPIED:
            shutil.copytree(entry, tree / "resources" / entry.name) if entry.is_dir() else shutil.copy2(entry, tree / "resources" / entry.name)
        elif entry.is_dir():
            link_dir(entry, tree / "resources" / entry.name)
        else:
            shutil.copy2(entry, tree / "resources" / entry.name)
    config = tree / "src/shared/Config.luau"
    rewritten, errors, overrides = overlay_config(config.read_text(encoding="utf-8"), profile)
    if errors:
        raise SystemExit("profile overlay failed:" + NL + "  " + (NL + "  ").join(errors))
    config.write_text(rewritten, encoding="utf-8", newline="")
    OVERRIDES[profile] = overrides
    return tree


def commands(luau: str, compiler: str, only: list[str]) -> list[list[str]]:
    text = (ROOT / ".github/workflows/build-generated-place.yml").read_text(encoding="utf-8")
    ast = next((str(p) for p in (Path(luau).parent / "luau-ast", Path(luau).parent / "luau-ast.exe") if p.is_file()), compiler)
    text = text.replace("/tmp/luau/luau-ast", ast)  # before ci_commands swaps "/tmp/luau/luau" for the runner
    out = []
    for cmd in release_playtest.ci_commands(text, luau, compiler):
        script = Path(cmd[1]).name
        if script in SKIP or script.startswith("generate_") or "/demo/" in cmd[1].replace("\\", "/"):
            continue
        if only and not any(token in script for token in only):
            continue
        out.append(cmd)
    # the session-1 smoke is excluded from release_playtest's CI list (it runs it by itself); the rehearsal wants it
    smoke = [sys.executable, "tools/verify_session1_smoke.py", "--runner", luau]
    if smoke not in out and (not only or any(t in "verify_session1_smoke.py" for t in only)):
        out.append(smoke)
    return out


def run_one(cmd: list[str], cwd: Path, timeout: int) -> dict:
    started = time.time()
    try:
        done = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout)
        code = done.returncode
        output = (done.stdout + b"\n" + done.stderr).decode("utf-8", "replace")
    except subprocess.TimeoutExpired as error:
        code, output = 124, f"TIMEOUT after {timeout}s\n" + ((error.stdout or b"").decode("utf-8", "replace"))
    return {"cmd": Path(cmd[1]).name, "args": cmd[2:], "code": code, "seconds": round(time.time() - started, 1), "output": output}


def run_all(cmds: list[list[str]], cwd: Path, jobs: int, timeout: int) -> list[dict]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        return list(pool.map(lambda c: run_one(c, cwd, timeout), cmds))


EXPECTED_PATH = Path(__file__).resolve().parent / "rehearsal_expected.json"


def load_expected() -> dict:
    data = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def expected_failure(result: dict, entry: dict | None) -> bool:
    """A failure is expected when its output carries the entry's signature and every FAIL line matches the entry's `only` pattern."""
    if entry is None:
        return False
    if not re.search(entry["signature"], result["output"]):
        return False
    only = entry.get("only")
    if only:
        for line in result["output"].splitlines():
            if "FAIL" in line and not re.search(only, line):
                return False
    return True


def normalise(text: str) -> list[str]:
    """Output lines with scratch paths and temp names removed, so two runs in different trees compare."""
    out = []
    for line in text.splitlines():
        line = re.sub(r"bd-rehearsal-\w+", "T", line)
        line = re.sub(r"tmp\w+", "tmp", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            out.append(line)
    return out


def last_lines(text: str, n: int = 6) -> str:
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return "\n".join(lines[-n:])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runner", help="path to the Luau runner (luau / luau.exe)")
    parser.add_argument("--compiler", help="path to luau-compile")
    parser.add_argument("--profile", default="all-on-rehearsal", help="release profile whose Config values are applied to the scratch tree; 'none' = committed Config")
    parser.add_argument("--only", default="", help="comma-separated substrings of verifier file names")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--baseline", default="none", help="profile whose scratch tree is the comparison for failing commands that are not listed in tools/rehearsal_expected.json (default none = the committed Config)")
    parser.add_argument("--no-baseline", action="store_true", help="do not re-run failing commands on a baseline tree")
    parser.add_argument("--json", type=Path, help="write the full result (with outputs) here")
    parser.add_argument("--keep", action="store_true", help="keep the scratch tree and print its path")
    parser.add_argument("--list", action="store_true", help="print the commands and the flags the profile turns on, then exit")
    args = parser.parse_args(argv)

    luau, compiler = release_playtest.find_luau(args.runner)
    if not luau:
        print("No Luau runner: pass --runner PATH")
        return 1
    compiler = args.compiler or compiler or luau
    only = [t for t in args.only.split(",") if t]
    cmds = commands(luau, compiler, only)
    if args.list:
        for cmd in cmds:
            print(" ".join(cmd[1:]))
        print(f"{len(cmds)} commands")
        return 0

    base = Path(tempfile.mkdtemp(prefix="bd-rehearsal-"))
    try:
        tree = make_tree(args.profile, base)
        base_entries = release_profiles.config_entries((ROOT / "src/shared/Config.luau").read_text(encoding="utf-8"))
        flags = {k: v[-1][1] for k, v in base_entries.items() if isinstance(v[-1][1], bool)}
        flags.update({k: v for k, v in OVERRIDES.get(args.profile, {}).items() if isinstance(v, bool)})
        print(f"profile {args.profile!r}: {sum(1 for v in flags.values() if v)} boolean flags true, {sum(1 for v in flags.values() if not v)} false")
        print("  on : " + ", ".join(sorted(k for k, v in flags.items() if v)))
        print("  off: " + ", ".join(sorted(k for k, v in flags.items() if not v)))
        print("  overridden vs committed Config: " + ", ".join(f"{k}={v}" for k, v in OVERRIDES.get(args.profile, {}).items()))
        print(f"running {len(cmds)} commands with {args.jobs} workers in {tree}")
        results = run_all(cmds, tree, args.jobs, args.timeout)
        failed = [r for r in results if r["code"] != 0]
        if args.profile != "none" and not args.no_baseline:
            print(f"running the failing commands again on the {args.baseline!r} tree for comparison")
            base_tree = make_tree(args.baseline, base / "baseline") if args.baseline != "none" else ROOT
            base_cmds = [[sys.executable, f"tools/{r['cmd']}", *r["args"]] for r in failed]
            for r, b in zip(failed, run_all(base_cmds, base_tree, args.jobs, args.timeout)):
                r["baseline_code"] = b["code"]
        expected = load_expected()
        by_name = {r["cmd"]: r for r in results}
        for r in failed:
            if args.profile == "none":
                r["class"] = "baseline-failure"
            elif expected_failure(r, expected.get(r["cmd"])):
                r["class"] = "expected (pins the committed off state)"
            elif r.get("baseline_code", 0) != 0:
                r["class"] = "also-fails-on-baseline"
            else:
                r["class"] = "INTERACTION"
        stale = [name for name in expected if name in by_name and by_name[name]["code"] == 0 and args.profile != "none"]
        print()
        for r in results:
            state = "ok  " if r["code"] == 0 else "FAIL"
            print(f"[{state}] {r['cmd']:42s} {r['seconds']:6.1f}s" + (f"  ({r['class']})" if r["code"] else ""))
        print()
        for r in failed:
            if r["class"].startswith("expected"):
                print(f"expected: {r['cmd']}: {expected[r['cmd']]['reason']}")
                continue
            print(f"--- {r['cmd']} exit {r['code']} class {r['class']}")
            for line in last_lines(r["output"], 10).splitlines():
                print("    " + line[:260])
            print()
        for name in stale:
            print(f"stale: tools/rehearsal_expected.json lists {name} but it passes under {args.profile!r}; remove the entry")
        counts: dict[str, int] = {}
        for r in failed:
            counts[r["class"]] = counts.get(r["class"], 0) + 1
        print(f"{len(results) - len(failed)} passed, {len(failed)} failed: {counts}")
        if args.json:
            args.json.write_text(json.dumps({"profile": args.profile, "flags": flags, "results": results}, indent=1), encoding="utf-8")
        if args.keep:
            print(f"scratch tree kept: {tree}")
        return 1 if any(not r["class"].startswith("expected") for r in failed) or (stale and args.profile != "none") else 0
    finally:
        if not args.keep:
            # remove the directory links first (rmdir/unlink never follow them), so rmtree cannot reach the real docs/resources
            for root in (base / "tree", base / "baseline" / "tree"):
                links = [root / n for n in LINKED] + [e for e in (root / "resources").glob("*") if e.is_dir() and e.name not in RESOURCES_COPIED]
                for link in links:
                    try:
                        os.unlink(link) if link.is_symlink() else os.rmdir(link)
                    except OSError:
                        pass
            shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
