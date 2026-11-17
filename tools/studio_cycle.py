#!/usr/bin/env python3
"""Lead's Studio test loop in one plain command (no shell variables, so the app's allow list can match it):
compile every Luau source, build the playtest place to build/BeDino-WorldV3-test.rbxlx, close ONLY a Studio window that shows that
test file (never the owner's Place1 or any other window), open the new build on the virtual monitor (tools/monitor4.py, owner rule
2026-11-16: Studio only there or hidden) and wait until it is loaded.

    python tools/studio_cycle.py            # compile + build + restart the test Studio
    python tools/studio_cycle.py --no-studio  # compile + build only
    python tools/studio_cycle.py --name life   # a session's own test window: build/BeDino-life-test.rbxlx (one per session, docs owner rule)
"""
import argparse
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
LUAU = pathlib.Path.home() / ".cache/be-dino/luau-0.741"
TEST = ROOT / "build/BeDino-WorldV3-test.rbxlx"


def run(cmd):
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    last = (out.stdout.strip().splitlines() or [""])[-1]
    print(last)
    if out.returncode != 0:
        print(out.stderr[-1500:])
        sys.exit(out.returncode)


def powershell(script):
    return subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-studio", action="store_true")
    ap.add_argument("--wait", type=int, default=55)
    ap.add_argument("--name", default="", help="own test file build/BeDino-<name>-test.rbxlx instead of the lead's WorldV3 one")
    a = ap.parse_args()
    global TEST
    if a.name:
        if not a.name.replace("-", "").isalnum():
            sys.exit("--name: letters, digits and dashes only")
        TEST = ROOT / ("build/BeDino-" + a.name + "-test.rbxlx")
    run([sys.executable, "tools/verify_sources.py", "--compiler", str(LUAU / "luau-compile.exe")])
    run([sys.executable, "tools/build.py", "--profile", "playtest", "--output", str(TEST.relative_to(ROOT))])
    if a.no_studio:
        return
    # close only the test window (its title names the test file); any other Studio window is left alone
    closed = powershell("Get-Process RobloxStudioBeta -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like '*" + TEST.name +
                        "*' } | ForEach-Object { $_.Id; Stop-Process -Id $_.Id -Force }")
    print("closed test Studio:", closed or "none")
    time.sleep(3)
    # owner 2026-11-16: test Studio windows only on the virtual monitor (or hidden); monitor4 launches, places and maximises it there
    out = subprocess.run([sys.executable, "tools/monitor4.py", "launch", "studio", str(TEST)], cwd=ROOT, capture_output=True, text=True)
    print((out.stdout.strip().splitlines() or [""])[-1])
    if out.returncode != 0:
        print(out.stderr[-800:])
        sys.exit(out.returncode)
    time.sleep(a.wait)
    subprocess.run([sys.executable, "tools/monitor4.py", "place"], cwd=ROOT, capture_output=True, text=True)  # in case Studio moved itself while loading
    print("Studio opened on the virtual monitor:", TEST.name)


if __name__ == "__main__":
    main()
