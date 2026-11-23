#!/usr/bin/env python3
"""Sheet -> Hunyuan3D -> game dino, one command per step (BD-1304; route proven on Pachy V5 and Anky V5, docs/169 section 8).

    python tools/hy_dino.py sheet  <sheet.jpg> --dir build/hy-<name>     # find the 4 views, write proj-*.png and the 3/4 input q34.png
    python tools/hy_dino.py gen    --dir build/hy-<name>                 # Hunyuan3D-2 shape from q34.png (local GPU, low priority, ~1 min)
    python tools/hy_dino.py config --dir build/hy-<name> --name Anky_V5 --plan quadruped|biped|flyer
                                                                        # measure the shape, write cfg.py from the plan template
    python tools/hy_dino.py parts  --dir build/hy-<name>                 # cut, cap, decimate -> parts.blend (+ spike candidates)
    python tools/hy_dino.py colour --dir build/hy-<name> [--final]       # project + bake colours, pivots, renders (EEVEE preview by default)
    python tools/hy_dino.py anim   --dir build/hy-<name>                 # rig + the game's 8 clips -> frames -> gifs/*.gif
    python tools/hy_dino.py all    <sheet.jpg> --dir ... --name ... --plan ...   # every step in order (config only when cfg.py is missing)

A colour tweak = edit <dir>/cfg.py and rerun `colour` only (about 20 s). Rerun `parts` only after changing cuts or budgets.
Then export: python tools/blender_export_roblox.py <dir>/<NAME>.blend --out <dir>/<NAME>.fbx --embed-textures

Sheets that cut cleanly (ask ChatGPT for exactly this): one row of four views FRONT, 3/4, SIDE (snout to the right), BACK, same scale and
same neutral pose in every view, a plain light-grey background, at least 20 px of empty space between figures and above the labels, and
NO black outline on the figures (outlines bleed dark onto edges when projected). Extra poses go in a second row below.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hy_dino_lib as lib  # noqa: E402

BLENDER = os.environ.get("BLENDER_EXE", "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe")
HUNYUAN = Path(os.environ.get("HUNYUAN_DIR", str(Path.home() / "Hunyuan3D-2")))
VIEWS = ("front", "q34", "side", "back")


def blender(stage: str, d: Path, *extra: str) -> int:
    cmd = [BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", str(ROOT / "tools/blender/hy_dino_blender.py"), "--", "--stage", stage, "--dir", str(d), *extra]
    flags = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags)
    for line in (res.stdout or "").splitlines():
        if line.startswith("HY") or "Error" in line or "Traceback" in line or line.startswith("  File"):
            print(line)
    print(f"[{stage}] {time.time() - t0:.0f} s, exit {res.returncode}")
    if res.returncode:
        print((res.stderr or "")[-1500:])
    return res.returncode


def cmd_sheet(sheet: Path, d: Path) -> int:
    import numpy as np
    from PIL import Image
    d.mkdir(parents=True, exist_ok=True)
    im = Image.open(sheet).convert("RGB")
    a = np.asarray(im).astype(int)
    h, w = a.shape[:2]
    band = a[: int(h * 0.45)]
    bg = np.median(band[:4].reshape(-1, 3), axis=0)
    fg = np.abs(band - bg).sum(axis=2) > 40
    cols = lib.panels_from_columns(list(fg[: int(h * 0.30)].sum(axis=0)), want=4)
    if len(cols) != 4:
        print(f"found {len(cols)} figures in the top row, expected 4 (front, 3/4, side, back): {cols}; see the sheet rules in --help")
        return 2
    boxes = {}
    for view, (x0, x1) in zip(VIEWS, cols):
        y0, y1 = lib.figure_rows(list(fg[:, x0:x1].sum(axis=1)))
        sub = fg[y0:y1, x0:x1]
        ys, xs = np.where(sub)
        boxes[view] = (int(x0 + xs.min()), int(y0 + ys.min()), int(x0 + xs.max() + 1), int(y0 + ys.max() + 1))
        crop = im.crop(boxes[view])
        if view == "q34":
            side = max(crop.size) + 40
            sq = Image.new("RGB", (side, side), tuple(int(v) for v in bg))
            sq.paste(crop, ((side - crop.width) // 2, (side - crop.height) // 2))
            sq.resize((1100, 1100), Image.LANCZOS).save(d / "q34.png")
        else:
            crop.save(d / f"proj-{view}.png")
    json.dump({"sheet": str(sheet), "boxes": boxes}, open(d / "sheet.json", "w"), indent=1)
    strip = Image.new("RGB", (1200, 300), (230, 230, 230))
    for i, view in enumerate(VIEWS):
        c = im.crop(boxes[view])
        c.thumbnail((290, 290))
        strip.paste(c, (i * 300 + 5, 5))
    strip.save(d / "sheet-views.png")
    print("views", boxes, "->", d / "sheet-views.png")
    return 0


def cmd_gen(d: Path) -> int:
    py = HUNYUAN / ".venv/Scripts/python.exe"
    flags = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
    t0 = time.time()
    res = subprocess.run([str(py), "bedino_gen.py", str(d / "q34.png"), str(d / "out"), "--no-texture"], cwd=HUNYUAN,
                         capture_output=True, text=True, creationflags=flags)
    ok = (d / "out/q34_shape.glb").exists()
    print(f"[gen] {time.time() - t0:.0f} s, shape {'ok' if ok else 'MISSING'}")
    if not ok:
        print((res.stdout + res.stderr)[-1500:])
    return 0 if ok else 1


def cmd_config(d: Path, name: str, plan: str) -> int:
    if blender("measure", d, "--src", str(d / "out/q34_shape.glb")):
        return 1
    a = json.load(open(d / "anatomy.json"))
    (d / "cfg.py").write_text(lib.species_config(name, plan, a), encoding="utf-8")
    print("wrote", d / "cfg.py")
    return 0


def cmd_gifs(d: Path, title: str) -> int:
    from PIL import Image, ImageDraw, ImageFont
    order = ["idle", "walk", "run", "eat", "happy", "look", "jump", "land"]
    desc = {"idle": "idle (loop)", "walk": "walk (loop)", "run": "run (loop)", "eat": "eat", "happy": "happy", "look": "look around",
            "jump": "jump", "land": "land"}
    try:
        font, small = ImageFont.truetype("arialbd.ttf", 22), ImageFont.truetype("arialbd.ttf", 18)
    except OSError:
        font = small = ImageFont.load_default()
    out = d / "gifs"
    out.mkdir(exist_ok=True)
    seqs = {}
    for clip in order:
        frames = sorted((d / "frames" / clip).glob("f*.png"))
        if not frames:
            continue
        ims = [Image.open(p).convert("RGB") for p in frames]
        seqs[clip] = [i.resize((300, 300)) for i in ims]
        lab = []
        for im in ims:
            ImageDraw.Draw(im).text((12, 10), f"{title}: {desc[clip]}", fill=(255, 255, 255), font=font, stroke_width=3, stroke_fill=(30, 30, 30))
            lab.append(im.convert("P", palette=Image.ADAPTIVE, colors=128))
        dur = [83] * len(lab)
        if clip not in ("idle", "walk", "run"):
            dur[-1] = 600
        lab[0].save(out / f"{clip}.gif", save_all=True, append_images=lab[1:], duration=dur, loop=0, disposal=2)
    grid = []
    for i in range(48):
        W = Image.new("RGB", (1200, 600), (40, 40, 40))
        dr = ImageDraw.Draw(W)
        for k, c in enumerate(order):
            if c in seqs:
                x, y = (k % 4) * 300, (k // 4) * 300
                W.paste(seqs[c][i % len(seqs[c])], (x, y))
                dr.text((x + 8, y + 6), desc[c], fill=(255, 255, 255), font=small, stroke_width=3, stroke_fill=(20, 20, 20))
        grid.append(W.convert("P", palette=Image.ADAPTIVE, colors=160))
    grid[0].save(out / "all-animations.gif", save_all=True, append_images=grid[1:], duration=83, loop=0)
    print("gifs in", out)
    return 0


def cmd_strip(d: Path) -> None:
    from PIL import Image
    ims = [Image.open(d / f"render-{v}.png").convert("RGBA") for v in ("front", "q34", "side", "back") if (d / f"render-{v}.png").exists()]
    if not ims:
        return
    s = 400
    W = Image.new("RGBA", (s * len(ims), s + 300), (215, 215, 215, 255))
    for i, im in enumerate(ims):
        W.alpha_composite(im.resize((s, s)), (i * s, 0))
    if (d / "sheet-views.png").exists():
        sv = Image.open(d / "sheet-views.png").convert("RGBA").resize((s * len(ims), 300))
        W.alpha_composite(sv, (0, s))
    W.convert("RGB").save(d / "compare.png")
    print("compare:", d / "compare.png")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["sheet", "gen", "config", "parts", "colour", "anim", "gifs", "all"])
    ap.add_argument("sheet", nargs="?")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--name")
    ap.add_argument("--plan", choices=lib.PLANS, default="quadruped")
    ap.add_argument("--final", action="store_true", help="colour: Cycles renders instead of the quick EEVEE preview")
    a = ap.parse_args(argv)
    d = Path(a.dir).resolve()
    cfgp = str(d / "cfg.py")
    steps = ["sheet", "gen", "config", "parts", "colour", "anim"] if a.step == "all" else [a.step]
    t0 = time.time()
    for st in steps:
        if st == "sheet" and cmd_sheet(Path(a.sheet), d):
            return 2
        if st == "gen" and not (d / "out/q34_shape.glb").exists() and cmd_gen(d):
            return 1
        if st == "config" and (a.step == "config" or not (d / "cfg.py").exists()) and cmd_config(d, a.name, a.plan):
            return 1
        if st == "parts" and blender("parts", d, "--src", str(d / "out/q34_shape.glb"), "--config", cfgp):
            return 1
        if st == "colour":
            if blender("colour", d, "--config", cfgp, *([] if a.final else ["--preview"])):
                return 1
            cmd_strip(d)
        if st == "anim":
            if blender("anim", d, "--config", cfgp):
                return 1
            cmd_gifs(d, a.name or d.name)
        if st == "gifs":
            cmd_gifs(d, a.name or d.name)
    print(f"total {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
