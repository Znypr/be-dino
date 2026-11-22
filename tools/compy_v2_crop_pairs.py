#!/usr/bin/env python3
"""Same-height crop pairs: Compy V2 Blender render (left) vs the approved ChatGPT sheet view (right) (BD-1291 step 3 self-gate).

  python tools/compy_v2_crop_pairs.py
  python tools/compy_v2_crop_pairs.py --evid docs/evidence/2026-11-22-compy-v3 --label "Blender V3 render"   # V3 (Hunyuan route)
Reads docs/evidence/2026-11-22-compy-v2/render-<view>.png (tools/blender/build_compy_v2.py) and the sheet
docs/evidence/2026-11-22-dino-ranking/compy-sheet-v1.jpg; writes pair-<view>.png and pairs-all.png into the evidence folder and
prints per-view numbers (silhouette width/height ratio, lime/cream/dark share of the silhouette) for both sides.
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "docs" / "evidence" / "2026-11-22-compy-v2"
SHEET = ROOT / "docs" / "evidence" / "2026-11-22-dino-ranking" / "compy-sheet-v1.jpg"
PANELS = {"front": (100, 30, 340, 440), "q34": (370, 30, 670, 440), "side": (740, 30, 1180, 440), "back": (1220, 30, 1440, 440)}
H = 360


def silhouette_crop(im):
    a = np.asarray(im.convert("RGB")).astype(int)
    bg = a[2, 2]
    m = np.abs(a - bg).sum(2) > 45
    ys, xs = np.nonzero(m)
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    return im.crop(box), m[box[1]:box[3], box[0]:box[2]]


def shares(im, mask):
    a = np.asarray(im.convert("RGB")).astype(float) / 255
    mx, mn = a.max(2), a.min(2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    lime = (sat > 0.4) & (mx > 0.3) & (a[..., 1] >= a[..., 0])
    cream = (sat < 0.3) & (mx > 0.75)
    dark = mx < 0.3
    n = max(mask.sum(), 1)
    return {k: round(float((v & mask).sum()) / n, 3) for k, v in (("lime", lime), ("cream", cream), ("dark", dark))}


def main():
    global EVID
    ap = argparse.ArgumentParser()
    ap.add_argument("--evid", default=str(EVID), help="folder with render-<view>.png; the pairs are written there")
    ap.add_argument("--label", default="Blender V2 render")
    args = ap.parse_args()
    EVID = Path(args.evid) if Path(args.evid).is_absolute() else ROOT / args.evid
    sheet = Image.open(SHEET).convert("RGB")
    tiles = []
    for view, box in PANELS.items():
        rp = EVID / ("render-%s.png" % view)
        if not rp.is_file():
            print("missing", rp)
            continue
        rgba = Image.open(rp).convert("RGBA")
        flat = Image.new("RGBA", rgba.size, (172, 172, 172, 255))
        flat.alpha_composite(rgba)
        left, lm = silhouette_crop(flat.convert("RGB"))
        right, rm = silhouette_crop(sheet.crop(box))
        ls, rs = shares(left, lm), shares(right, rm)
        print("%-5s aspect render %.2f sheet %.2f | render %s | sheet %s" % (view, left.width / left.height, right.width / right.height,
              {k: float(v) for k, v in ls.items()}, {k: float(v) for k, v in rs.items()}))
        left = left.resize((max(1, round(left.width * H / left.height)), H), Image.LANCZOS)
        right = right.resize((max(1, round(right.width * H / right.height)), H), Image.LANCZOS)
        pad = 16
        out = Image.new("RGB", (left.width + right.width + pad * 3, H + pad * 2 + 18), (172, 172, 172))
        out.paste(left, (pad, pad + 18))
        out.paste(right, (left.width + pad * 2, pad + 18))
        d = ImageDraw.Draw(out)
        d.text((pad, 4), args.label, fill=(0, 0, 0))
        d.text((left.width + pad * 2, 4), "approved sheet", fill=(0, 0, 0))
        # height guides at 25/50/75 %
        for f in (0.25, 0.5, 0.75):
            y = pad + 18 + round(H * f)
            d.line((0, y, out.width, y), fill=(120, 120, 220), width=1)
        out.save(EVID / ("pair-%s.png" % view))
        tiles.append(out)
    if tiles:
        w = sum(t.width for t in tiles)
        allimg = Image.new("RGB", (w, tiles[0].height), (172, 172, 172))
        x = 0
        for t in tiles:
            allimg.paste(t, (x, 0))
            x += t.width
        allimg.save(EVID / "pairs-all.png")
        print("wrote", EVID / "pairs-all.png")


if __name__ == "__main__":
    main()
