"""Record the Roblox Studio window to MP4 with ffmpeg gdigrab (docs/133). Windows only; dev tool, nothing here ships in the game.

    python tools/demo/record.py --out clip.mp4 --duration 30
    python tools/demo/record.py --list-windows
    python tools/demo/record.py --selftest

gdigrab matches the EXACT window title, so the script first looks up the full title of the first visible window whose title
contains --title (default "Roblox Studio"; use e.g. --title DemoTrailer when several Studios are open) and records that. Studio must
not be minimised. By default the clip is cropped to the 3D viewport (child window found with Win32, so no toolbars, Explorer or
Output are in the video); --crop x,y,w,h (pixels inside the window capture) overrides, --no-crop records the whole window.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_FFMPEG = "C:/ffmpeg/bin/ffmpeg"


def find_ffmpeg() -> str:
    env = os.environ.get("FFMPEG")
    if env:
        return env
    if Path(DEFAULT_FFMPEG + ".exe").exists():
        return DEFAULT_FFMPEG
    return shutil.which("ffmpeg") or "ffmpeg"


def list_windows() -> list[str]:
    """Titles of visible top-level windows (Windows only)."""
    if sys.platform != "win32":
        return []
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    titles: list[str] = []
    proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                titles.append(buf.value)
        return True

    user32.EnumWindows(proc_type(callback), 0)
    return titles


def window_geometry(title: str):
    """(window rect, viewport rect) in screen pixels for the visible top-level window with exactly this title, or None.

    The viewport is the smallest visible child window that covers at least 40 percent of the window: Studio nests the 3D view
    inside several same-size containers, and docked panes (Explorer, Properties, Output) are separate smaller siblings.
    """
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def rect_of(hwnd):
        r = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        return (r.left, r.top, r.right, r.bottom)

    def text_of(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value

    found = []

    def top(hwnd, _):
        if user32.IsWindowVisible(hwnd) and text_of(hwnd) == title:
            found.append(hwnd)
        return True

    user32.EnumWindows(proc_type(top), 0)
    if not found:
        return None
    if user32.IsIconic(found[0]):  # a minimised window has no pixels to grab: restore it first
        user32.ShowWindow(found[0], 9)
        time.sleep(1.5)
    win = rect_of(found[0])
    rects = []

    def child(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            rects.append(rect_of(hwnd))
        return True

    user32.EnumChildWindows(found[0], proc_type(child), 0)
    return win, pick_viewport(win, rects)


def pick_viewport(win, rects):
    """Pure helper (selftested): smallest child rect covering >= 40% of the window area, else None."""
    area = lambda r: max(0, r[2] - r[0]) * max(0, r[3] - r[1])
    best = None
    for r in rects:
        if area(r) >= 0.4 * area(win) and (best is None or area(r) < area(best)):
            best = r
    return best


def crop_filter(win, view, margin: int = 2):
    """ffmpeg crop expression for the viewport relative to the window capture, with a few px trimmed off each edge."""
    x, y = view[0] - win[0] + margin, view[1] - win[1] + margin
    w, h = (view[2] - view[0] - 2 * margin) // 2 * 2, (view[3] - view[1] - 2 * margin) // 2 * 2
    return f"crop={w}:{h}:{x}:{y}"


def is_focus_blue(px) -> bool:
    return px[2] > 170 and px[0] < 110 and px[2] - px[1] > 60


def border_trims(rgb: bytes, w: int, h: int, limit: int = 60):
    """Pure helper: how many pixels to trim (left, top, right, bottom) so Studio's blue focus border and the command bar are
    outside the crop. The focus border is a thin bluish line along the viewport edge; everything beyond it is Studio chrome."""
    def px(x, y):
        i = (y * w + x) * 3
        return rgb[i], rgb[i + 1], rgb[i + 2]

    def row_blue(y):
        xs = range(8, w - 8, 8)
        return sum(is_focus_blue(px(x, y)) for x in xs) >= 0.8 * len(xs)

    def col_blue(x):
        ys = range(8, h - 8, 8)
        return sum(is_focus_blue(px(x, y)) for y in ys) >= 0.8 * len(ys)

    top = next((y + 1 for y in range(0, min(limit, h)) if row_blue(y)), 0)
    bottom = next((h - y for y in range(h - 1, max(h - 1 - limit, 0), -1) if row_blue(y)), 0)
    left = next((x + 1 for x in range(0, min(limit, w)) if col_blue(x)), 0)
    right = next((w - x for x in range(w - 1, max(w - 1 - limit, 0), -1) if col_blue(x)), 0)
    return left, top, right, bottom


def refine_crop(ffmpeg: str, title: str, crop: str) -> str:
    """Grab one frame with the coarse crop, find the blue focus border, and return a tighter crop filter."""
    w, h, x, y = (int(v) for v in crop.split("=")[1].split(":"))
    cmd = [ffmpeg, "-loglevel", "error", "-f", "gdigrab", "-framerate", "5", "-i", f"title={title}", "-frames:v", "1",
           "-vf", crop, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    if len(raw) != w * h * 3:
        return crop
    l, t, r, b = border_trims(raw, w, h)
    if not (l or t or r or b):
        return crop
    nw, nh = (w - l - r - 2) // 2 * 2, (h - t - b - 2) // 2 * 2
    return f"crop={nw}:{nh}:{x + l + 1}:{y + t + 1}"


def resolve_title(fragment: str, titles: list[str] | None = None) -> str | None:
    for title in (list_windows() if titles is None else titles):
        if fragment.lower() in title.lower():
            return title
    return None


def build_command(ffmpeg: str, title: str, out: str, duration: float, fps: int = 60, crf: int = 18, draw_mouse: bool = False, crop: str | None = None) -> list[str]:
    if duration <= 0:
        raise ValueError("duration must be positive")
    return [
        ffmpeg, "-y", "-f", "gdigrab", "-framerate", str(fps), "-draw_mouse", "1" if draw_mouse else "0",
        "-i", f"title={title}", "-t", f"{duration:g}",
        # libx264 needs even dimensions; window sizes are often odd.
        "-vf", (crop + "," if crop else "") + "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-r", str(fps), out,
    ]


def selftest() -> int:
    cmd = build_command("ffmpeg", "Roblox Studio - X", "o.mp4", 12.5, 60)
    assert cmd[cmd.index("-framerate") + 1] == "60" and "title=Roblox Studio - X" in cmd and cmd[cmd.index("-t") + 1] == "12.5"
    assert cmd[-1] == "o.mp4" and "libx264" in cmd
    try:
        build_command("ffmpeg", "t", "o", 0)
    except ValueError:
        pass
    else:
        raise AssertionError("zero duration accepted")
    assert resolve_title("studio", ["Chrome", "Roblox Studio - Place1"]) == "Roblox Studio - Place1"
    assert resolve_title("nothing", ["Chrome"]) is None
    win = (-8, -8, 1928, 1040)
    assert pick_viewport(win, [(0, 138, 1920, 963), (106, 167, 1551, 960), (1557, 138, 1920, 963), (104, 165, 1553, 962)]) == (106, 167, 1551, 960)
    assert pick_viewport(win, [(0, 0, 10, 10)]) is None
    assert crop_filter(win, (106, 167, 1551, 960), 2) == "crop=1440:788:116:177"
    assert "crop=10:10:1:2,scale" in " ".join(build_command("ffmpeg", "t", "o", 1, crop="crop=10:10:1:2"))
    blue, other = bytes((40, 80, 230)), bytes((120, 90, 60))
    w, h = 200, 200
    img = bytearray(other * (w * h))
    for x in range(w):
        img[(197 * w + x) * 3:(197 * w + x) * 3 + 3] = blue
    assert border_trims(bytes(img), w, h) == (0, 0, 0, 3)
    print("record.py selftest OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="output .mp4")
    ap.add_argument("--duration", type=float, help="seconds to record")
    ap.add_argument("--title", default="Roblox Studio", help="part of the window title (default: Roblox Studio)")
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--mouse", action="store_true", help="draw the mouse cursor (off by default)")
    ap.add_argument("--crop", help="x,y,w,h in pixels inside the window capture (overrides viewport detection)")
    ap.add_argument("--no-crop", action="store_true", help="record the whole Studio window")
    ap.add_argument("--list-windows", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.list_windows:
        print("\n".join(list_windows()))
        return 0
    if not args.out or not args.duration:
        ap.error("--out and --duration are required")
    title = resolve_title(args.title)
    if not title:
        print(f"No visible window title contains {args.title!r}. Use --list-windows.", file=sys.stderr)
        return 2
    crop = None
    if args.crop:
        x, y, w, h = (int(v) for v in args.crop.split(","))
        crop = f"crop={w // 2 * 2}:{h // 2 * 2}:{x}:{y}"
    elif not args.no_crop:
        geo = window_geometry(title)
        if geo and geo[1]:
            crop = refine_crop(find_ffmpeg(), title, crop_filter(*geo))
        else:
            print("Could not find the 3D viewport; pass --crop x,y,w,h or --no-crop.", file=sys.stderr)
            return 3
    print(f"Recording window: {ascii(title)} for {args.duration:g}s at {args.fps} fps, {crop or 'no crop'}")
    return subprocess.call(build_command(find_ffmpeg(), title, args.out, args.duration, args.fps, args.crf, args.mouse, crop))


if __name__ == "__main__":
    sys.exit(main())
