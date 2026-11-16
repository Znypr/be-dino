#!/usr/bin/env python3
"""Run every `python tools/verify_*.py` line of the CI workflow locally (Luau runner paths swapped for this PC's) from the repo root and
report only the failures. One plain command, so the app's allow list can match it.

    python tools/run_ci_list.py [--timeout 300] [--only word]
"""
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
LUAU = (pathlib.Path.home() / ".cache/be-dino/luau-0.741").as_posix()
WORKFLOW = ROOT / ".github/workflows/build-generated-place.yml"


def commands():
    out = []
    for raw in WORKFLOW.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("- run:"):
            line = line[len("- run:"):].strip()
        if not re.match(r"python3? tools/verify_\w+\.py", line):
            continue
        line = line.replace("/tmp/luau/luau-compile", LUAU + "/luau-compile.exe").replace("/tmp/luau/luau", LUAU + "/luau.exe")
        out.append(line)
    return out


def main():
    timeout = int(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 300
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else ""
    lines = [l for l in commands() if only in l]
    failed, start = [], time.time()
    for line in lines:
        try:
            out = subprocess.run(["bash", "-c", line], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
            ok, tail = out.returncode == 0, (out.stdout + out.stderr).strip().splitlines()[-6:]
        except subprocess.TimeoutExpired:
            ok, tail = False, ["TIMEOUT"]
        if not ok:
            failed.append(line)
            print("FAIL", line, *("    " + t[:240] for t in tail), sep="\n", flush=True)
    print(f"{len(lines) - len(failed)}/{len(lines)} passed in {time.time() - start:.0f} s")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
