#!/usr/bin/env python3
"""Keep agent windows (Roblox Studio, Blender, the Edge window the browser tools drive) on the virtual monitor (docs/158, BD-1059).

Owner request 2026-10-18: "always open Studio, Blender and Edge on monitor 4, so I can edit my videos on the other screens."

  python tools/monitor4.py list                    # monitors and the windows this tool would care about (changes nothing)
  python tools/monitor4.py place                   # move matching windows that are NOT on the virtual monitor onto it
  python tools/monitor4.py place --dry-run         # say what it would move
  python tools/monitor4.py launch studio build/BeDino-Build020-playtest.rbxlx   # start Studio, then place its new window
  python tools/monitor4.py launch blender [file.blend]
  python tools/monitor4.py watch                   # keep placing new windows every few seconds until Ctrl+C

SAFETY RULES (memory: owner-place1-window, studio-focus):
  * Never touches a window whose title contains "Place1" (the owner's own Studio window), never minimises, never makes a window
    topmost, never closes anything, never takes focus (SWP_NOACTIVATE | SWP_NOZORDER).
  * Skips the window that has keyboard focus right now (the owner is using it) and any maximised/fullscreen window on another
    monitor unless --force-foreground is given.
  * Edge: the owner's own Edge windows are NOT moved. Only an Edge window whose title contains the marker given with
    --edge-title (default "Claude") is moved; `--edge-title "*"` moves every Edge window (use only when the owner says so),
    and a window started with `launch edge` is placed as well.
  * Windows only (ctypes, no extra packages). Does nothing on other systems.
The virtual monitor is the display whose size is 1280 x 720 (override with --size 1920x1080 or --index N).
"""
from __future__ import annotations

import argparse
import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

PROTECTED_TITLES = ("Place1",)
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SW_SHOWMAXIMIZED = 3
SW_SHOWNORMAL = 1
VIRTUAL_SIZE = (1280, 720)
STUDIO_EXE_GLOB = "C:/Users/{user}/AppData/Local/Roblox/Versions"


def is_protected(title: str) -> bool:
    return any(p.lower() in title.lower() for p in PROTECTED_TITLES)


def classify(title: str, exe: str, edge_title: str = "Claude") -> str | None:
    """Which kind of agent window is this? None = not ours (leave alone). Pure, tested."""
    low = exe.lower()
    if is_protected(title):
        return None
    if low.startswith("robloxstudiobeta"):
        return "studio"
    if low.startswith("blender"):
        return "blender"
    if low.startswith("msedge") and edge_title is not None and (edge_title == "*" or (edge_title and edge_title.lower() in title.lower())):
        return "edge"
    return None


def contains(outer: tuple, x: int, y: int) -> bool:
    return outer[0] <= x < outer[2] and outer[1] <= y < outer[3]


def target_rect(mon: tuple, win: tuple) -> tuple:
    """New (x, y, w, h) for a window on the monitor: keep its size if it fits, else fit to the monitor; centred in the work area."""
    mw, mh = mon[2] - mon[0], mon[3] - mon[1]
    w = min(win[2] - win[0], mw)
    h = min(win[3] - win[1], mh)
    if w < 400 or h < 300:  # a tiny window is made usable
        w, h = mw, mh
    return mon[0] + (mw - w) // 2, mon[1] + (mh - h) // 2, w, h


# ----------------------------------------------------------------------------------------------- Windows glue
def _windows():
    return ctypes.windll.user32, ctypes.windll.kernel32


def monitors() -> list[dict]:
    user32, _ = _windows()
    found: list[dict] = []
    MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

    def cb(h, dc, rect, data):
        r = rect.contents
        found.append({"index": len(found) + 1, "rect": (r.left, r.top, r.right, r.bottom), "size": (r.right - r.left, r.bottom - r.top)})
        return 1

    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), 0)
    return found


def pick_virtual(mons: list[dict], size=VIRTUAL_SIZE, index: int | None = None) -> dict | None:
    if index:
        return next((m for m in mons if m["index"] == index), None)
    hits = [m for m in mons if tuple(m["size"]) == tuple(size)]
    return hits[0] if hits else None


def exe_of(pid: int) -> str:
    _, k32 = _windows()
    h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return os.path.basename(buf.value)
        return ""
    finally:
        k32.CloseHandle(h)


def top_windows(edge_title: str = "Claude") -> list[dict]:
    user32, _ = _windows()
    out: list[dict] = []
    fg = user32.GetForegroundWindow()
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, data):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return 1
        n = user32.GetWindowTextLengthW(hwnd)
        if n == 0:
            return 1
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        exe = exe_of(pid.value)
        kind = classify(buf.value, exe, edge_title)
        if not kind:
            return 1
        r = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        out.append({"hwnd": hwnd, "title": buf.value, "exe": exe, "kind": kind, "rect": (r.left, r.top, r.right, r.bottom),
                    "foreground": hwnd == fg, "maximised": bool(user32.IsZoomed(hwnd))})
        return 1

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def place(args) -> int:
    user32, _ = _windows()
    mons = monitors()
    virt = pick_virtual(mons, args.size, args.index)
    if not virt:
        print("STOP: no %dx%d monitor found. Monitors: %s" % (args.size[0], args.size[1], [(m["index"], m["size"]) for m in mons]))
        return 2
    moved = 0
    for w in top_windows(args.edge_title):
        cx, cy = (w["rect"][0] + w["rect"][2]) // 2, (w["rect"][1] + w["rect"][3]) // 2
        if contains(virt["rect"], cx, cy):
            continue
        if w["foreground"] and not args.force_foreground:
            print("skip (has focus, owner may be using it): %s" % w["title"][:70])
            continue
        x, y, ww, hh = target_rect(virt["rect"], w["rect"])
        print("%s %s [%s] -> monitor %d at %d,%d %dx%d" % ("would move" if args.dry_run else "moving", w["kind"], w["title"][:60], virt["index"], x, y, ww, hh))
        if args.dry_run:
            continue
        if w["maximised"]:
            user32.ShowWindow(w["hwnd"], SW_SHOWNORMAL)  # a maximised window cannot be moved to another monitor
        user32.SetWindowPos(w["hwnd"], None, x, y, ww, hh, SWP_NOZORDER | SWP_NOACTIVATE)
        moved += 1
    print("done: %d window(s) %s" % (moved, "would be moved" if args.dry_run else "moved"))
    return 0


def list_cmd(args) -> int:
    mons = monitors()
    virt = pick_virtual(mons, args.size, args.index)
    for m in mons:
        print("monitor %d: %dx%d at %s%s" % (m["index"], m["size"][0], m["size"][1], m["rect"][:2], "   <- virtual (target)" if virt and m is virt else ""))
    for w in top_windows(args.edge_title):
        on = ""
        if virt:
            cx, cy = (w["rect"][0] + w["rect"][2]) // 2, (w["rect"][1] + w["rect"][3]) // 2
            on = "on virtual" if contains(virt["rect"], cx, cy) else "ELSEWHERE"
        print("  %-8s %-10s %s%s" % (w["kind"], on, w["title"][:70], "  (focus)" if w["foreground"] else ""))
    return 0


def find_studio_exe() -> str | None:
    root = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Roblox", "Versions")
    if not os.path.isdir(root):
        return None
    best = None
    for d in sorted(os.listdir(root)):
        p = os.path.join(root, d, "RobloxStudioBeta.exe")
        if os.path.isfile(p):
            best = p
    return best


def find_blender_exe() -> str | None:
    import glob, shutil
    return os.environ.get("BLENDER_EXE") or shutil.which("blender") or (sorted(glob.glob("C:/Program Files/Blender Foundation/*/blender.exe")) or [None])[-1]


def launch(args) -> int:
    if args.what == "studio":
        exe = find_studio_exe()
        cmd = [exe] + ([args.file] if args.file else [])
    elif args.what == "blender":
        exe = find_blender_exe()
        cmd = [exe] + ([args.file] if args.file else [])
    else:
        exe = os.path.join(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"), "Microsoft/Edge/Application/msedge.exe")
        cmd = [exe, "--new-window"] + ([args.file] if args.file else [])
    if not exe or not os.path.isfile(exe):
        print("STOP: could not find %s" % args.what)
        return 2
    print("starting:", " ".join(cmd))
    subprocess.Popen(cmd)
    if args.what == "edge":
        args.edge_title = "*"  # a window we start ourselves is ours
    for _ in range(40):  # wait up to ~2 minutes for the window
        time.sleep(3)
        if any(w["kind"] == args.what for w in top_windows(args.edge_title)):
            break
    return place(args)


def watch(args) -> int:
    print("watching every %ds, Ctrl+C to stop" % args.every)
    try:
        while True:
            place(args)
            time.sleep(args.every)
    except KeyboardInterrupt:
        return 0


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(errors="replace")  # window titles hold odd characters
    except Exception:
        pass
    if sys.platform != "win32":
        print("monitor4.py works on Windows only")
        return 0
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("list", "place", "watch", "launch"):
        p = sub.add_parser(name)
        p.add_argument("--size", type=lambda s: tuple(int(x) for x in s.lower().split("x")), default=VIRTUAL_SIZE)
        p.add_argument("--index", type=int, default=None, help="monitor number instead of size matching")
        p.add_argument("--edge-title", default="Claude", help="only Edge windows whose title contains this are moved")
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--force-foreground", action="store_true")
        if name == "watch":
            p.add_argument("--every", type=int, default=5)
        if name == "launch":
            p.add_argument("what", choices=["studio", "blender", "edge"])
            p.add_argument("file", nargs="?")
    args = ap.parse_args(argv)
    return {"list": list_cmd, "place": place, "watch": watch, "launch": launch}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
