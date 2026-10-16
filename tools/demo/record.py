"""Record the Roblox Studio window to MP4 with ffmpeg gdigrab (docs/133). Windows only; dev tool, nothing here ships in the game.

    python tools/demo/record.py --out clip.mp4 --duration 30
    python tools/demo/record.py --list-windows
    python tools/demo/record.py --selftest

gdigrab matches the EXACT window title, so the script first looks up the full title of the first visible window whose title
contains --title (default "Roblox Studio") and records that. Studio must not be minimised.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
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


def resolve_title(fragment: str, titles: list[str] | None = None) -> str | None:
    for title in (list_windows() if titles is None else titles):
        if fragment.lower() in title.lower():
            return title
    return None


def build_command(ffmpeg: str, title: str, out: str, duration: float, fps: int = 60, crf: int = 18, draw_mouse: bool = False) -> list[str]:
    if duration <= 0:
        raise ValueError("duration must be positive")
    return [
        ffmpeg, "-y", "-f", "gdigrab", "-framerate", str(fps), "-draw_mouse", "1" if draw_mouse else "0",
        "-i", f"title={title}", "-t", f"{duration:g}",
        # libx264 needs even dimensions; window sizes are often odd.
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
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
    print(f"Recording window: {title!r} for {args.duration:g}s at {args.fps} fps")
    return subprocess.call(build_command(find_ffmpeg(), title, args.out, args.duration, args.fps, args.crf, args.mouse))


if __name__ == "__main__":
    sys.exit(main())
