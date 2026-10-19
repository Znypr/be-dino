#!/usr/bin/env python3
"""BD-1034 part 1b: a second, stricter seam test for pattern tiles (shapes, not columns).

tools/tile_seam_check.py compares columns and rows across the wrap line. It has two blind spots that showed up
with the v2 ChatGPT sheets: (1) a white frame ring (1 px of white round the whole tile, left over from the sheet's
white gaps) looks like a perfect match to itself, but it draws a white cross of lines between copies; (2) a shape cut at
the seam and glued to its neighbour can still look like "an ordinary strip" to the column test.

This test looks at SHAPES. The tile is shrunk to 128 px, tiled 3 x 3, and white and black blobs are labelled
(4-connected). A blob that touches the outer edge of the 3 x 3 picture is ignored. Blobs that cross one of the
four inner wrap lines are "seam blobs"; blobs that do not are "inner blobs". For each colour:
  * with at least 3 inner blobs: a seam blob smaller than 0.8 x the smallest inner blob (a fragment) or bigger than
    1.25 x the biggest inner blob (two shapes glued together) is a CUT shape;
  * with fewer inner blobs: the same with 0.55 x and 1.7 x the median of all blobs (not touching the edge);
  * a single huge background blob (black or white sea) never counts.
FRAME: the outer 1 or 2 rows / columns of the tile are one flat colour while the row next to them is not (a frame ring).
Verdict: OK (no frame, 0 cut shapes), CUT (cut shapes found), FRAME.

  python tools/tile_seam_strict.py resources/patterns/seamless
Pillow and numpy only. Exit code 0 always (a report).
"""
import argparse
import os
import sys
from collections import deque

import numpy as np
from PIL import Image

SZ = 128


def label(mask):
    """4-connected labelling of a bool array. Returns (labels, count); background (False) is 0."""
    h, w = mask.shape
    lab = np.zeros((h, w), dtype=np.int32)
    n = 0
    m = mask.tolist()
    lb = lab.tolist()
    for y in range(h):
        row = m[y]
        for x in range(w):
            if row[x] and lb[y][x] == 0:
                n += 1
                lb[y][x] = n
                dq = deque([(y, x)])
                while dq:
                    cy, cx = dq.popleft()
                    for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                        if 0 <= ny < h and 0 <= nx < w and m[ny][nx] and lb[ny][nx] == 0:
                            lb[ny][nx] = n
                            dq.append((ny, nx))
    return np.array(lb, dtype=np.int32), n


def frame_ring(white):
    """True when the outer 1-2 rows/columns are flat but the next one is not (a leftover frame)."""
    for k in (1, 2):
        edges = [white[:k], white[-k:], white[:, :k], white[:, -k:]]
        nxt = [white[k], white[-k - 1], white[:, k], white[:, -k - 1]]
        flat = all(e.min() == e.max() for e in edges) and all(e.min() == edges[0].min() for e in edges)
        if flat and all(not (n.min() == n.max() == edges[0].min()) for n in nxt):
            # the ring colour must differ from what is next to it in most places
            if np.mean([np.mean(n != edges[0].flat[0]) for n in nxt]) > 0.3:
                return True
    return False


def cut_shapes(white, size=SZ):
    img = Image.fromarray((white.astype(np.uint8)) * 255).resize((size, size), Image.BOX)
    w = np.array(img) >= 128
    T = np.tile(w, (3, 3))
    res = {}
    for colour, name in ((True, "white"), (False, "black")):
        lab, n = label(T == colour)
        if n == 0:
            res[name] = 0
            continue
        border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist())
        cross = set()
        for line in (size, 2 * size):
            a, b = lab[:, line - 1], lab[:, line]
            cross |= set(a[(a == b) & (a > 0)].tolist())
            a, b = lab[line - 1, :], lab[line, :]
            cross |= set(a[(a == b) & (a > 0)].tolist())
        areas = np.bincount(lab.ravel(), minlength=n + 1)
        inner = [areas[i] for i in range(1, n + 1) if i not in border and i not in cross]
        seam = [i for i in range(1, n + 1) if i not in border and i in cross]
        allb = [areas[i] for i in range(1, n + 1) if i not in border]
        if not allb:
            res[name] = 0
            continue
        # a sea (one blob far bigger than a tile quarter) is not a shape
        big = size * size * 0.25
        if len(inner) >= 3:
            lo, hi = 0.8 * min(inner), 1.25 * max(inner)
        else:
            med = float(np.median(allb))
            lo, hi = 0.55 * med, 1.7 * med
        bad = 0
        centre = set(np.unique(lab[size:2 * size, size:2 * size]).tolist())
        for i in seam:
            if i in centre and areas[i] < big and (areas[i] < lo or areas[i] > hi):
                bad += 1
        res[name] = bad
    return res


def check_file(path):
    white = np.array(Image.open(path).convert("L")) >= 128
    fr = frame_ring(white)
    cs = cut_shapes(white)
    bad = cs["white"] + cs["black"]
    verdict = "FRAME" if fr else ("CUT" if bad else "OK")
    return dict(frame=fr, cut_white=cs["white"], cut_black=cs["black"], cut=bad, verdict=verdict)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folders", nargs="+")
    a = ap.parse_args()
    for folder in a.folders:
        files = [folder] if os.path.isfile(folder) else sorted(
            os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".png"))
        for f in files:
            r = check_file(f)
            print("%-22s %-5s frame=%s cut(white)=%d cut(black)=%d" % (
                os.path.basename(f)[:-4], r["verdict"], "yes" if r["frame"] else "no", r["cut_white"], r["cut_black"]))


if __name__ == "__main__":
    sys.exit(main())
