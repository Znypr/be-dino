#!/usr/bin/env python3
"""Art batch 1: cut a ChatGPT sheet of colour icons into single cells, make them transparent, flag problems.

Usage:
  python tools/cut_icon_sheet.py SHEET.png OUT_DIR --prefix food --cols 4 --rows 4 [--size 512]
         [--ids berry,fruit,egg,amber]   # optional: row names, so cells become food-berry-A ... (default: A1 ... D4)

What it does for every cell (objects are found where they are drawn, because the sheet grid is not always equal):
  1. Finds the flat background colour of the whole sheet (median of its border) and flood-fills it from the
     edges to transparent; holes inside an object (a handle gap) that are exactly the background colour go too.
     If the sheet border is not one flat colour, cells keep their background and are flagged BG-NOT-CLEAN.
  2. Crops to the object, pads to a square with a small margin, resizes to --size and saves OUT_DIR/<id>.png.
  3. Prints and returns simple quality flags:
       EMPTY      nearly nothing drawn
       MUDDY      low colour (average saturation of the object is very low: grey mush)
       CLIPPED    the object touches the edge of the sheet (cut off)
       BG-NOT-CLEAN  the sheet background is not one flat colour (cells then keep their background)
       GAP-CLEARED   a hole inside the object (handle) was made transparent: look at it
Needs Pillow and numpy only. Import `process_sheet` from other tools.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import deque
from typing import Dict, List, Optional

import numpy as np
from PIL import Image


def cell_id(prefix: str, col: int, row: int, ids: Optional[List[str]]) -> str:
    letter = "ABCDEFGH"[col]
    if ids:
        return "%s-%s-%s" % (prefix, ids[row], letter)
    return "%s-%s%d" % (prefix, letter, row + 1)


def flood_background(rgb: np.ndarray, tol: float = 14.0):
    """Return (bg_mask, info). bg_mask True = background reached from the cell edges."""
    h, w, _ = rgb.shape
    ring = np.concatenate([rgb[0, :], rgb[-1, :], rgb[:, 0], rgb[:, -1]]).astype(np.float32)
    bg = np.median(ring, axis=0)
    spread = float(np.percentile(np.abs(ring - bg).max(axis=1), 90))
    diff = np.abs(rgb.astype(np.float32) - bg).max(axis=2)
    like = diff <= tol
    seen = np.zeros((h, w), bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if like[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if like[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and like[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                dq.append((ny, nx))
    return seen, {"bg": [int(v) for v in bg], "ring_spread": round(spread, 1)}


def soften_edge(alpha: np.ndarray) -> np.ndarray:
    """One pixel of anti-alias: average alpha with its neighbours so the cut-out is not jagged."""
    a = alpha.astype(np.float32)
    p = np.pad(a, 1, mode="edge")
    out = (p[1:-1, 1:-1] * 4 + p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 8.0
    return np.clip(out, 0, 255).astype(np.uint8)


def _label(mask: np.ndarray):
    """Connected components (4-neighbour) of a boolean mask -> (labels, count). Pure numpy/stdlib."""
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    n = 0
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not lab[y, x]:
                n += 1
                lab[y, x] = n
                dq = deque([(y, x)])
                while dq:
                    cy, cx = dq.popleft()
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not lab[ny, nx]:
                            lab[ny, nx] = n
                            dq.append((ny, nx))
    return lab, n


def _dilate(mask: np.ndarray, r: int) -> np.ndarray:
    out = mask.copy()
    for _ in range(r):
        p = np.pad(out, 1)
        out = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return out


def find_objects(fg: np.ndarray, cols: int, rows: int, min_area: int = 6000, absorb: int = 140):
    """Find one bounding box per object on the whole sheet. The ChatGPT grid is not always exactly equal
    (objects can sit a few pixels from the next row), so objects are found where they are drawn.
    Tries small merge radii first, takes the first one that gives exactly cols*rows big pieces, and then
    attaches small loose pieces (egg shards, paint drops) to the nearest big piece within `absorb` px.
    Returns (boxes in grid order or None, note)."""
    small = fg[::2, ::2]  # half resolution: 4x faster, boxes are scaled back
    want = cols * rows
    for merge in (2, 4, 6, 8, 10, 12, 14):
        lab, n = _label(_dilate(small, max(1, merge // 2)))
        comps = []
        for k in range(1, n + 1):
            ys, xs = np.where((lab == k) & small)
            comps.append([len(ys) * 4, int(xs.min()) * 2, int(ys.min()) * 2, int(xs.max()) * 2 + 1, int(ys.max()) * 2 + 1])
        big = [c for c in comps if c[0] >= min_area]
        if len(big) == want:
            break
    else:
        return None, "found %d objects, expected %d" % (len(big), want)
    for c in comps:
        if c[0] >= min_area or c[0] < 150:
            continue
        cx, cy = (c[1] + c[3]) / 2, (c[2] + c[4]) / 2
        best = min(big, key=lambda b: ((b[1] + b[3]) / 2 - cx) ** 2 + ((b[2] + b[4]) / 2 - cy) ** 2)
        gap_x = max(best[1] - c[3], c[1] - best[3], 0)
        gap_y = max(best[2] - c[4], c[2] - best[4], 0)
        if max(gap_x, gap_y) <= absorb:
            best[1], best[2], best[3], best[4] = min(best[1], c[1]), min(best[2], c[2]), max(best[3], c[3]), max(best[4], c[4])
    boxes = sorted([tuple(b[1:]) for b in big], key=lambda b: (b[1] + b[3]) / 2)
    ordered = []
    for r in range(rows):
        ordered.extend(sorted(boxes[r * cols:(r + 1) * cols], key=lambda b: (b[0] + b[2]) / 2))
    return ordered, ""


def process_sheet(sheet: str, out_dir: str, prefix: str, cols: int, rows: int, size: int = 512,
                  ids: Optional[List[str]] = None, edge: int = 3) -> Dict[str, dict]:
    os.makedirs(out_dir, exist_ok=True)
    img = Image.open(sheet).convert("RGB")
    rgb = np.array(img)
    H, W, _ = rgb.shape
    bgmask, binfo = flood_background(rgb)
    # enclosed gaps (the hole inside a handle): pixels almost exactly the background colour that the flood
    # fill could not reach. They are made transparent too; white paint (clearly lighter) is left alone.
    gap_flag: Dict[tuple, int] = {}
    near = (np.abs(rgb.astype(np.float32) - np.array(binfo["bg"], np.float32)).max(axis=2) <= 3) & ~bgmask
    glab, gn = _label(near[::2, ::2]) if near.any() else (None, 0)
    for k in range(1, gn + 1):
        ys, xs = np.where(glab == k)
        if len(ys) * 4 >= 250:
            for dy in (0, 1):
                for dx in (0, 1):
                    bgmask[np.minimum(ys * 2 + dy, rgb.shape[0] - 1), np.minimum(xs * 2 + dx, rgb.shape[1] - 1)] = True
            gap_flag[(int(xs.mean() * 2), int(ys.mean() * 2))] = len(ys) * 4
    sheet_clean = binfo["ring_spread"] <= 30 and bgmask.mean() > 0.3
    boxes, note = find_objects(~bgmask, cols, rows) if sheet_clean else (None, "sheet background not flat")
    cell_masks = None
    if boxes is None and sheet_clean:
        # art batch 2: swooshes, sparkles and glows split or touch, so the object count is not exact. Fall back to
        # the equal grid: every drawn piece goes to the grid cell holding its centre, and a cell keeps ONLY its own
        # pieces (no bleed from the neighbour next to it). Boxes are the pieces' bounds.
        fg_all = ~bgmask
        small = fg_all[::2, ::2]
        # objects that touch their neighbour (coins stacked with a 3 px gap): cut the labelling at the quietest
        # line near every grid line, then give those cut pixels back to the piece above / left of them.
        cut = fg_all.copy()
        cuts_y = [int(round(r * H / rows)) for r in range(1, rows)]
        cuts_x = [int(round(c * W / cols)) for c in range(1, cols)]
        ys_cut, xs_cut = [], []
        for yb in cuts_y:
            lo, hi = max(1, yb - 45), min(H - 2, yb + 45)
            ys_cut.append(lo + int(np.argmin([fg_all[y].sum() for y in range(lo, hi)])))
        for xb in cuts_x:
            lo, hi = max(1, xb - 45), min(W - 2, xb + 45)
            xs_cut.append(lo + int(np.argmin([fg_all[:, x].sum() for x in range(lo, hi)])))
        for y in ys_cut:
            cut[y - 1:y + 2, :] = False
        for x in xs_cut:
            cut[:, x - 1:x + 2] = False
        small = cut[::2, ::2]
        lab, n = _label(small)
        cw, ch = W / cols, H / rows
        cell_masks = {}
        boxes = [None] * (rows * cols)
        comps = []  # (label, area, bbox, centre)
        for k in range(1, n + 1):
            ys, xs = np.where((lab == k) & small)
            if len(ys):
                comps.append((k, len(ys) * 4, (xs.min() * 2, ys.min() * 2, xs.max() * 2, ys.max() * 2), (xs.mean() * 2, ys.mean() * 2)))
        bigc = [c for c in comps if c[1] >= 6000]
        for k, area, bb, (cx, cy) in comps:
            if area < 6000 and bigc:  # a spark or leaf piece: goes with the nearest big piece
                def dist(o):
                    gx = max(o[2][0] - bb[2], bb[0] - o[2][2], 0)
                    gy = max(o[2][1] - bb[3], bb[1] - o[2][3], 0)
                    return gx * gx + gy * gy
                cx, cy = min(bigc, key=dist)[3]
            idx = min(rows - 1, int(cy // ch)) * cols + min(cols - 1, int(cx // cw))
            cell_masks.setdefault(idx, []).append(k)
        full_lab = np.kron(lab, np.ones((2, 2), np.int32))[:H, :W]
        if full_lab.shape != (H, W):
            full_lab = np.pad(full_lab, ((0, H - full_lab.shape[0]), (0, W - full_lab.shape[1])), mode="edge")
        for idx in range(rows * cols):
            ks = cell_masks.get(idx, [])
            m = np.isin(full_lab, ks) & fg_all if ks else np.zeros((H, W), bool)
            cell_masks[idx] = m
            ys, xs = np.where(m)
            r, c = divmod(idx, cols)
            boxes[idx] = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(ys) else (int(c * cw), int(r * ch), int((c + 1) * cw) - 1, int((r + 1) * ch) - 1)
        note += " (equal-grid fallback)"
    rgba_full = np.dstack([rgb, np.full((H, W), 255, np.uint8)])
    hsv = np.array(img.convert("HSV")).astype(np.float32)
    results: Dict[str, dict] = {}
    for r in range(rows):
        for c in range(cols):
            cid = cell_id(prefix, c, r, ids)
            flags: List[str] = []
            if boxes is None:  # fall back to equal parts, background kept, flagged
                cw, ch = W / cols, H / rows
                x0, y0, x1, y1 = int(c * cw), int(r * ch), int((c + 1) * cw) - 1, int((r + 1) * ch) - 1
                flags += ["BG-NOT-CLEAN"]
                transparent = False
            else:
                x0, y0, x1, y1 = boxes[r * cols + c]
                transparent = True
            pad = 8
            X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(W - 1, x1 + pad), min(H - 1, y1 + pad)
            cell = rgba_full[Y0:Y1 + 1, X0:X1 + 1].copy()
            fgc = ~bgmask[Y0:Y1 + 1, X0:X1 + 1]
            if transparent:
                # neighbouring objects inside this box: keep only this object's own pixels (inside its tight box)
                if cell_masks is not None:
                    keep = cell_masks[r * cols + c][Y0:Y1 + 1, X0:X1 + 1]
                else:
                    keep = np.zeros_like(fgc)
                    keep[y0 - Y0:y1 - Y0 + 1, x0 - X0:x1 - X0 + 1] = True
                solid = fgc & keep
                pp = np.pad(solid, 1)  # shave 1 px: the edge pixels are part grey background (a light fringe)
                solid = solid & pp[:-2, 1:-1] & pp[2:, 1:-1] & pp[1:-1, :-2] & pp[1:-1, 2:]
                alpha = np.where(solid, 255, 0).astype(np.uint8)
                cell[..., 3] = soften_edge(alpha)
                obj = fgc & keep
            else:
                obj = fgc
            if transparent and any(x0 <= gx <= x1 and y0 <= gy <= y1 for (gx, gy) in gap_flag):
                flags.append("GAP-CLEARED")  # a hole inside the object (handle) was made transparent: check it
            share = float(obj.sum()) / max(1, obj.size)
            if obj.sum() < 800:
                flags.append("EMPTY")
            if x0 <= edge or y0 <= edge or x1 >= W - 1 - edge or y1 >= H - 1 - edge:
                flags.append("CLIPPED")
            hh = hsv[Y0:Y1 + 1, X0:X1 + 1]
            sat = float(hh[..., 1][obj].mean() / 255.0) if obj.any() else 0.0
            val = float(hh[..., 2][obj].mean() / 255.0) if obj.any() else 0.0
            if sat < 0.12 and 0.2 < val < 0.9:
                flags.append("MUDDY")
            crop = Image.fromarray(cell)
            side = int(max(crop.size) * 1.12)
            sq = Image.new("RGBA", (side, side), (0, 0, 0, 0) if transparent else (232, 232, 232, 255))
            sq.alpha_composite(crop, ((side - crop.size[0]) // 2, (side - crop.size[1]) // 2))
            sq.resize((size, size), Image.LANCZOS).save(os.path.join(out_dir, cid + ".png"))
            results[cid] = {"flags": sorted(set(flags)), "object_share": round(share, 3), "saturation": round(sat, 2),
                            "bbox": [int(x0), int(y0), int(x1), int(y1)], "transparent": transparent,
                            "bg": binfo["bg"], "note": note}
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sheet")
    ap.add_argument("out_dir")
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--rows", type=int, default=4)
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--ids", default="", help="comma list of row names")
    ap.add_argument("--json", default="", help="write the flags to this json file")
    a = ap.parse_args(argv)
    ids = [s for s in a.ids.split(",") if s] or None
    if ids and len(ids) != a.rows:
        print("--ids needs exactly one name per row")
        return 2
    res = process_sheet(a.sheet, a.out_dir, a.prefix, a.cols, a.rows, a.size, ids)
    for cid, info in res.items():
        print("%-18s %-22s object %.0f%% sat %.2f %s" % (cid, ",".join(info["flags"]) or "ok", info["object_share"] * 100,
                                                          info["saturation"], "transparent" if info["transparent"] else "kept background"))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
