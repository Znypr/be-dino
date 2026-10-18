#!/usr/bin/env python3
"""BD-1034: cut a ChatGPT sheet of square black-and-white pattern tiles into single tiles.

Usage:
  python tools/cut_pattern_sheet.py SHEET.png OUT_DIR --prefix a [--grid 4] [--size 256]

Finds the white gaps between tiles (runs of all-white rows / columns at least `--min-gap` wide),
crops each tile with a small inset, resizes to size x size, and thresholds to pure black (0) and
white (255). Writes OUT_DIR/<prefix>A1.png ... <prefix>D4.png (column letter + row number, left to right,
top to bottom, so --prefix a- gives a-A1 ... a-D4) and prints each tile's white share and a quick seam test
(tools/tile_seam_check.py gives the full seam report and repairs).
Only the standard library, Pillow and numpy are needed.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def runs(mask, min_len):
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        if not v and start is not None:
            if i - start >= min_len:
                out.append((start, i - 1))
            start = None
    if start is not None and len(mask) - start >= min_len:
        out.append((start, len(mask) - 1))
    return out


def tile_spans(gaps, length, grid):
    """Turn gap runs into `grid` content spans. Falls back to an equal split when detection fails."""
    edges = list(gaps)
    if not edges or edges[0][0] > 2:
        edges.insert(0, (-1, -1))
    if edges[-1][1] < length - 3:
        edges.append((length, length))
    spans = [(edges[i][1] + 1, edges[i + 1][0] - 1) for i in range(len(edges) - 1)]
    spans = [s for s in spans if s[1] - s[0] > 8]
    if len(spans) != grid:
        step = length / grid
        spans = [(int(i * step), int((i + 1) * step) - 1) for i in range(grid)]
    return spans


def cut(path, grid=4, min_gap=4):
    gray = np.array(Image.open(path).convert("L"))
    white = gray > 235
    ys = tile_spans(runs(white.all(axis=1), min_gap), gray.shape[0], grid)
    xs = tile_spans(runs(white.all(axis=0), min_gap), gray.shape[1], grid)
    tiles = []
    for (y0, y1) in ys:
        for (x0, x1) in xs:
            tiles.append(gray[y0:y1 + 1, x0:x1 + 1])
    return tiles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet")
    ap.add_argument("out_dir")
    ap.add_argument("--prefix", default="t")
    ap.add_argument("--grid", type=int, default=4)
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--inset", type=int, default=2, help="pixels trimmed from each side of the crop")
    ap.add_argument("--min-gap", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    from tile_seam_check import analyze
    for i, t in enumerate(cut(a.sheet, a.grid, a.min_gap), 1):
        if a.inset:
            t = t[a.inset:-a.inset, a.inset:-a.inset]
        im = Image.fromarray(t).resize((a.size, a.size), Image.LANCZOS)
        bw = (np.array(im) >= 128).astype(np.uint8) * 255
        r, c = divmod(i - 1, a.grid)
        name = "%s%s%d.png" % (a.prefix, "ABCDEFGH"[c], r + 1)  # column letter + row number, e.g. a-D3
        Image.fromarray(bw).save(os.path.join(a.out_dir, name))
        sm = analyze(bw > 127)
        print("%s white=%.2f H%.1f V%.1f %s" % (name, bw.mean() / 255, sm["H"], sm["V"], sm["status"]))


if __name__ == "__main__":
    main()
