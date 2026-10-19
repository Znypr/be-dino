#!/usr/bin/env python3
"""BD-1034 part 1b: cut a ChatGPT sheet into tiles by looking for the window that really repeats.

tools/cut_pattern_sheet.py cuts every cell whole. A ChatGPT cell is not a perfect period: it has a white frame
ring, rounded corners, and the pattern inside rarely wraps at exactly the cell size. This tool keeps a plain
crop (no blending, no mirroring) of each cell, chosen so that the wrap line (last column next to the first
column, bottom row next to the top row) looks like any ordinary neighbouring columns.

  python tools/tile_window_cut.py SHEET.png OUT_DIR PREFIX [--grid 4] [--checks A2,B2]

Two modes, per cell:
  * default (any pattern): for every window width/height at least 55 % of the cell (never touching the outer 4 px,
    which holds the frame), score the wrap with a column-difference matrix: the pair (last column, first column)
    and the pairs one column further in must differ about as much as ordinary neighbours do. For patterns whose
    shapes stand in rows with empty gaps between them (dots, plus signs, stars, hearts: "margin patterns") the
    empty run across the wrap must also be as wide as an ordinary gap (taken from the middle rows only, because the
    sheet leaves white nibbles in the corners). The window must be nearly square (6 % aspect). Big windows win ties.
  * --checks CELLS (checkerboards): finds the square edges (lines that flip in most places) and keeps an EVEN
    number of whole squares in each direction.
The window is resized to 256 px and set to pure black and white (white = colour 2). Each result is then run through
tools/tile_seam_check.analyze, and the line says PASS / PASS-SHIFT / FAIL. This tool only proposes; run
tools/tile_seam_strict.py (shape test) and LOOK at a 3 x 3 repeat before trusting a tile.
Pillow and numpy only.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_pattern_sheet import cut  # noqa: E402
from tile_seam_check import analyze  # noqa: E402

SZ = 256
MARGIN = 4
MINFRAC = 0.55
ASPECT = 0.06


def axis_costs(white):
    """white: bool h x w. For every window width, (cost, x0) of the best window. Small cost = the wrap looks ordinary."""
    a = white.astype(np.float32)
    h, w = a.shape
    d = a.T @ (1 - a) + (1 - a).T @ a  # d[i, j] = rows in which columns i and j differ
    o1 = np.median([d[i, i + 1] for i in range(w - 1)]) + 1.0
    o2 = np.median([d[i, i + 2] for i in range(w - 2)]) + 1.0
    occ = white[int(0.12 * h):int(0.88 * h)].any(axis=0)
    runs, i = [], 0
    while i < w:
        if not occ[i]:
            j = i
            while j < w and not occ[j]:
                j += 1
            if i > 0 and j < w:
                runs.append(j - i)
            i = j
        else:
            i += 1
    gapmed = float(np.median(runs)) if len(runs) >= 2 else None
    out = {}
    for wd in range(int(MINFRAC * w), w - 2 * MARGIN + 1):
        best = None
        for x0 in range(MARGIN, w - MARGIN - wd + 1):
            x1 = x0 + wd
            c = d[x1 - 1, x0] / o1 + 0.5 * (d[x1 - 2, x0] + d[x1 - 1, x0 + 1]) / (2 * o2)
            if gapmed:
                lead = 0
                while x0 + lead < x1 and not occ[x0 + lead]:
                    lead += 1
                trail = 0
                while x1 - 1 - trail >= x0 and not occ[x1 - 1 - trail]:
                    trail += 1
                c += 4.0 * abs(lead + trail - gapmed) / gapmed
            if best is None or c < best[0]:
                best = (c, x0)
        out[wd] = best
    return out


def best_window(cell):
    white = cell >= 128
    cx, cy = axis_costs(white), axis_costs(white.T)
    best = None
    for wd, (c1, x0) in cx.items():
        for ht, (c2, y0) in cy.items():
            if abs(wd - ht) / max(wd, ht) > ASPECT:
                continue
            s = c1 + c2 + 0.3 * (1 - (wd * ht) / (cell.shape[0] * cell.shape[1]))
            if best is None or s < best[0]:
                best = (s, x0, wd, y0, ht)
    return best[1:]


def square_edges(white, axis):
    """Positions where the whole line flips (the edge between two squares of a checkerboard), merged within 3 px."""
    a = white if axis == 0 else white.T
    w = a.shape[1]
    diff = np.array([(a[:, i] != a[:, i + 1]).mean() for i in range(w - 1)])
    groups = []
    for i in (i for i in range(4, w - 5) if diff[i] > 0.5):
        if groups and i - groups[-1][-1] <= 3:
            groups[-1].append(i)
        else:
            groups.append([i])
    return [int(round(np.mean(g))) for g in groups]


def checks_window(cell):
    white = cell >= 128
    out = []
    for axis in (0, 1):
        bs = square_edges(white, axis)
        n = len(bs) - 1
        m = n if n % 2 == 0 else n - 1
        if m < 2:
            return None
        start = (n - m) // 2
        out.append((bs[start] + 1, bs[start + m] + 1))
    (x0, x1), (y0, y1) = out
    return x0, x1 - x0, y0, y1 - y0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sheet")
    ap.add_argument("out_dir")
    ap.add_argument("prefix")
    ap.add_argument("--grid", type=int, default=4)
    ap.add_argument("--checks", default="", help="comma separated cells that are checkerboards, e.g. B2,C2")
    a = ap.parse_args()
    checks = {c.strip().upper() for c in a.checks.split(",") if c.strip()}
    os.makedirs(a.out_dir, exist_ok=True)
    for i, cell in enumerate(cut(a.sheet, a.grid, 4)):
        r, c = divmod(i, a.grid)
        cellname = "%s%d" % ("ABCDEFGH"[c], r + 1)
        win = checks_window(cell) if cellname in checks else best_window(cell)
        if win is None:
            print("%s%s no window found" % (a.prefix, cellname))
            continue
        x0, wd, y0, ht = win
        im = Image.fromarray(cell[y0:y0 + ht, x0:x0 + wd]).resize((SZ, SZ), Image.LANCZOS)
        m = np.array(im) >= 128
        res = analyze(m)
        Image.fromarray(m.astype(np.uint8) * 255).save(os.path.join(a.out_dir, a.prefix + cellname + ".png"))
        print("%s%s H%.2f V%.2f %s window x%d y%d %dx%d of %s" % (
            a.prefix, cellname, res["H"], res["V"], res["status"], x0, y0, wd, ht, cell.shape))


if __name__ == "__main__":
    main()
