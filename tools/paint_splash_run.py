#!/usr/bin/env python3
"""Run tools/blender/paint_splash_test.py in headless Blender at BELOW-NORMAL priority (heavy CPU job, owner OK 2026-11-16) with a time cap,
then make a looping GIF of the frames over a soft sky backdrop. Output in build/paint-test/ (ignored).

    python tools/paint_splash_run.py [--res 72] [--frames 56] [--cap 1800]
"""
import argparse
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import blender_headless  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, default=72)
    ap.add_argument("--frames", type=int, default=56)
    ap.add_argument("--cap", type=int, default=1800)
    ap.add_argument("--out", default="build/paint-test")
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    blender = blender_headless.find_blender()
    start = time.time()
    flags = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
    log = open(out / "blender.log", "w", encoding="utf-8")
    proc = subprocess.Popen([blender, "-b", "--factory-startup", "-P", str(ROOT / "tools/blender/paint_splash_test.py"), "--",
                             str(out), str(a.res), str(a.frames)], stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
    try:
        proc.wait(timeout=a.cap)
    except subprocess.TimeoutExpired:
        proc.kill()
        sys.exit(f"stopped after the {a.cap} s cap")
    log.close()
    print(f"blender exit {proc.returncode} after {time.time() - start:.0f} s")
    frames = sorted(out.glob("frame_*.png"))
    if not frames:
        print((out / "blender.log").read_text(encoding="utf-8")[-2500:])
        sys.exit(1)
    from PIL import Image
    shots = []
    for f in frames:
        im = Image.open(f).convert("RGBA")
        bg = Image.new("RGBA", im.size, (150, 196, 228, 255))
        bg.alpha_composite(im)
        shots.append(bg.convert("RGB").resize((384, 384)))
    gif = out / "paint-test.gif"
    shots[0].save(gif, save_all=True, append_images=shots[1:] + [shots[-1]] * 15, duration=33, loop=0)
    sheet = Image.new("RGB", (192 * 8, 192 * ((len(shots) + 7) // 8)), (40, 60, 40))
    for i, s in enumerate(shots):
        sheet.paste(s.resize((192, 192)), ((i % 8) * 192, (i // 8) * 192))
    sheet.save(out / "paint-test-sheet.jpg", quality=85)
    print("clip", gif, "sheet", out / "paint-test-sheet.jpg", len(frames), "frames")


if __name__ == "__main__":
    main()
