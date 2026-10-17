#!/usr/bin/env python3
"""Golden session for the ProfileRepository split (docs/150): the stored profile must not change by one byte.

Plays ONE long scripted session (tools/profile_golden.luau) against the REAL src/server/ProfileRepository.luau and the parts it installs, on
the virtual clock, seeded Random and mocked DataStore of tools/verify_load.py: load, run settlements (replayed and bad), hatching, hatch
pages, preferences with a coalescing burst, bonus nests, equip, test grants, crystal shop (potion, aura, trail, perk, egg), objectives,
gifts, Gold mutation, identity fusion, a Robux receipt, the paid-random gate, lease renew and release, a second session, and the Studio
preview with the demo triggers. After EVERY step it prints a fingerprint of the stored profile (canonical JSON, sorted keys), of the step's
own return values and of the player's owner-only state.

    python tools/verify_profile_golden.py --runner /path/to/luau                    # compare with tools/fixtures/profile_golden.json
    python tools/verify_profile_golden.py --runner ... --compare-root ../old-tree   # run the old tree and this one, compare every byte
    python tools/verify_profile_golden.py --runner ... --record [--source-root OLD]  # rewrite the fixture (only when a PR changes stored data on purpose)

The fixture was recorded from the code BEFORE the split (origin/main at 72cfde77) and has not changed since: that is the proof that the
split is a pure move. A later PR that changes stored data on purpose records the new fixture and says so.
Limits: a mocked DataStore proves transaction behaviour, not Roblox. The hash is a 64-bit fingerprint; --compare-root compares full text.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import verify_load  # noqa: E402

FIXTURE = ROOT / "tools" / "fixtures" / "profile_golden.json"
HEAD_MARKER = "-------------------------------------------------------------------- simulated players"
EMBED_LIMIT = 150_000  # the generated art tables (ResourceGeometry, IconRaster) are never required by the repository
MIN_STEPS = 170
STEP = re.compile(r"^STEP (\d+) (.*) len=(\d+) h=([0-9a-f]{16})$")


def patch_head(head: str) -> str:
    def swap(old: str, new: str) -> None:
        nonlocal head
        if head.count(old) != 1:
            raise SystemExit(f"harness patch target changed in verify_load.py: {old!r}")
        head = head.replace(old, new)

    swap("local SCENARIOS = __SCENARIOS__", "local SCENARIOS = {}\nlocal STUDIO = false\nlocal LASTPROFILE = nil")
    swap("RunService = {IsStudio = function() return false end},", "RunService = {IsStudio = function() return STUDIO end},")
    swap("server.game = {GameId = 4242,", "server.game = {GameId = if STUDIO then 0 else 4242,")
    swap("JSONEncode = function(_, v) return deepcopy(v) end,",
         "JSONEncode = function(_, v) if type(v) == 'table' and v.schemaVersion ~= nil and v.revision ~= nil then LASTPROFILE = deepcopy(v) end return deepcopy(v) end,")
    swap('    server.Repository = load(node("src/server/ProfileRepository"))\n',
         '    server.require = load\n    server.Repository = load(node("src/server/ProfileRepository"))\n')
    return head


def harness(root: Path, dump: bool) -> str:
    marker_at = verify_load.HARNESS.index(HEAD_MARKER)
    head = patch_head(verify_load.HARNESS[:marker_at])
    entries = []
    for folder in ("src/server", "src/shared"):
        for path in sorted((root / folder).glob("*.luau")):
            if path.stat().st_size > EMBED_LIMIT:
                continue
            entries.append(f"[{json.dumps(f'{folder}/{path.stem}')}] = {verify_load.long_string(path.read_text(encoding='utf-8'))}")
    head = head.replace("__SOURCES__", "{\n" + ",\n".join(entries) + "\n}")
    body = (ROOT / "tools" / "profile_golden.luau").read_text(encoding="utf-8").replace("__DUMP__", "true" if dump else "false")
    return "local SCENARIO_FAIL_RATE = 0\n" + head + "\n" + body


def run(runner: str, root: Path, dump: bool = False) -> tuple[list[tuple[int, str, int, str]], dict[int, str], list[str]]:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "golden.luau"
        path.write_text(harness(root, dump), encoding="utf-8")
        done = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    steps, texts, problems = [], {}, []
    for line in done.stdout.splitlines():
        match = STEP.match(line)
        if match:
            steps.append((int(match[1]), match[2], int(match[3]), match[4]))
        elif line.startswith("JSON "):
            number, _, text = line[5:].partition(" ")
            texts[int(number)] = text
        elif line.startswith(("SCENARIO_ERROR", "CRASH")):
            problems.append(line)
    if done.returncode != 0:
        problems.append(f"runner exited {done.returncode}: {(done.stderr or done.stdout)[-600:]}")
    if "DONE steps=" not in done.stdout:
        problems.append("the session did not finish")
    if len(steps) < MIN_STEPS:
        problems.append(f"only {len(steps)} steps ran (expected at least {MIN_STEPS}): the session stopped early")
    return steps, texts, problems


def compare(old: list, new: list, label: str) -> list[str]:
    errors = []
    if len(old) != len(new):
        errors.append(f"{label}: {len(old)} steps expected, {len(new)} ran")
    for a, b in zip(old, new):
        if a != b:
            errors.append(f"{label}: step {a[0]} '{a[1]}' differs: expected len={a[2]} h={a[3]}, got len={b[2]} h={b[3]}" if a[0] == b[0] and a[1] == b[1]
                          else f"{label}: step {a[0]} '{a[1]}' is now step {b[0]} '{b[1]}'")
            if len(errors) >= 8:
                errors.append("... more differences follow")
                break
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runner", required=True, help="path to the pinned luau")
    parser.add_argument("--compare-root", help="another checkout (the old code): run both and compare every byte")
    parser.add_argument("--record", action="store_true", help="rewrite tools/fixtures/profile_golden.json from the source tree")
    parser.add_argument("--source-root", help="read src/ from this checkout instead of this one (used to record the fixture from the old code)")
    args = parser.parse_args()

    source = Path(args.source_root).resolve() if args.source_root else ROOT
    if args.compare_root:
        old_root = Path(args.compare_root).resolve()
        old_steps, old_texts, old_problems = run(args.runner, old_root, dump=True)
        new_steps, new_texts, new_problems = run(args.runner, source, dump=True)
        errors = [f"old tree: {p}" for p in old_problems] + [f"this tree: {p}" for p in new_problems]
        errors += compare(old_steps, new_steps, "old vs new")
        for number, text in old_texts.items():
            if new_texts.get(number) != text:
                errors.append(f"step {number}: full text differs")
                break
        if errors:
            print("\n".join(errors))
            return 1
        total = sum(len(t) for t in new_texts.values())
        print(f"Old and new code agree at all {len(new_steps)} steps: {total} bytes of canonical profile, results and owner state are identical.")
        return 0

    steps, _, problems = run(args.runner, source)
    if problems:
        print("\n".join(problems))
        return 1
    if args.record:
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(json.dumps({"steps": [list(s) for s in steps]}, indent=0) + "\n", encoding="utf-8")
        print(f"Recorded {len(steps)} steps to {FIXTURE.relative_to(ROOT)}")
        return 0
    golden = [tuple(s) for s in json.loads(FIXTURE.read_text(encoding="utf-8"))["steps"]]
    errors = compare(golden, steps, "golden")
    if errors:
        print("\n".join(errors))
        print("The stored profile changed. A pure refactor must not do that (docs/150). If a PR changes stored data on purpose, record the new fixture with --record and say so.")
        return 1
    print(f"Golden session passed: {len(steps)} steps, stored profile, results and owner state match the fixture byte for byte (fingerprints).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
