#!/usr/bin/env python3
"""BD-1034: does a pattern tile really repeat without a visible seam? Do not trust the generator.

  python tools/tile_seam_check.py resources/patterns/candidates
  python tools/tile_seam_check.py resources/patterns/candidates --repair resources/patterns/candidates-fixed \
        --fail-sheet fails.png --json seams.json

1. SEAM NUMBERS (per tile, per direction, after a threshold to pure black and white). Put the tile next
   to a copy of itself: the last column then touches the first column (and the bottom row the top row).
   EDGE test: pixels that differ across that wrap line, divided by the pixels that differ across the
   roughest ordinary pair of neighbouring columns (rows) inside the tile; (x + 0.01) on both sides so
   a blank tile gives 1. Stripes have full-height edges every few pixels, so a wrap that lands on a
   stripe edge is fine (ratio 1); a dot or blob cut in two is not (ratio 3 and up).
   CONTEXT test: the strip that crosses the seam (W/2 columns from each side, W = width/4) is matched
   against every other strip of the tile; ordinary strips get the same treatment; ratio = best match
   over the median ordinary best match. Catches what one column cannot: a stripe that comes out too
   wide, a pattern that repeats with the wrong spacing.
   Reported as H (left/right) and V (top/bottom) = the worse of the edge ratio and the context ratio
   divided by 2 (the details are kept in the json: edge_H, ctx_H ...). 1.0 = the seam looks like any
   other place in the tile. PASS when both H and V are at most THRESHOLD (1.25).
   CROP SHIFT: cutting a sheet can leave one or two stray pixels at an edge. The test is repeated after
   trimming 0 to 2 pixels off each side and the best trim is reported ("H0.9@1,2" = ratio 0.9 after
   removing 1 px left and 2 px right). A tile that only passes after a trim is PASS-SHIFT (fixable).
   Everything else is FAIL.
2. PICTURE TEST (--fail-sheet): a 3 x 3 repeat of every FAILED tile with the wrap lines drawn faintly,
   on one sheet with a letter and number ruler (tools/label_grid_sheet.py), so a person can see the seam.
3. REPAIR (--repair OUTDIR): for PASS-SHIFT and FAIL tiles it tries, in this order of trust: trim the
   stray pixels; crop to the largest window that repeats cleanly (period crop); mirror the tile 2 x 2
   (always seamless, twice as big, flips the shapes, so directional patterns change); last resort slide
   by half a tile and cross-fade the new centre (blend, can crumble shapes). The first method whose result
   still looks like the same kind of pattern wins; a result that adds or removes more than about a third
   of the outline is rejected. The repaired copy is written to OUTDIR with the same name (the original is
   never touched), the test is run on it again, and two numbers say how close it still is to the original:
   "kind" (same size of shapes and amount of ink, 0..1) and "layout" (shapes in the same places, -1..1).
   Words: SAME (kind 0.90+ and layout 0.70+), SAME-KIND (new layout) (kind 0.90+, shapes moved: mirror and
   blend always do that), SIMILAR (kind 0.75+), CHANGED. --repair-sheet shows before | after, judge by eye.
WHAT THIS CANNOT SEE: how the tile lands on the dino's UV islands. A perfect tile still shows seams where
two UV islands meet; that is checked in Studio (BD-1034 part 2).
Needs Pillow and numpy only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

THRESHOLD = 1.25
CTX_SCALE = 2.0  # a context ratio of THRESHOLD * CTX_SCALE counts as much as an edge ratio of THRESHOLD
EPS = 0.01
MAX_SHIFT = 2


# --------------------------------------------------------------------------------------------
# edge test and context test (horizontal direction; the vertical one is the same on the turned tile)


def _ratio(wrap: float, inner: float) -> float:
    return (wrap + EPS) / (inner + EPS)


def edge_ratio_x(t: np.ndarray) -> float:
    """Left/right wrap: mismatch of the last column against the first, over the mismatch of the roughest
    ordinary pair of neighbouring columns inside the tile. 1.0 or less = the wrap line is no rougher than
    any line the tile has anyway (stripes have a full-height edge every few pixels, so the wrap may too)."""
    a = t.astype(np.int8)
    inner = float(np.abs(np.diff(a, axis=1)).mean(axis=0).max())
    wrap = float(np.abs(a[:, 0] - a[:, -1]).mean())
    return _ratio(wrap, inner)


def context_ratio_x(t: np.ndarray) -> float:
    """Left/right wrap, looking further than one column. The strip that crosses the seam (the right
    W/2 columns followed by the left W/2 columns, W = 1/4 of the width) is compared with every other
    strip of the tile that does not overlap it; the best match is its distance d. Every ordinary strip
    gets the same treatment; ratio = d over the median ordinary distance. A tile that repeats has a
    crossing strip that matches somewhere (stripes, dots, bricks); a stripe that comes out too wide
    or a dot cut in two does not. Catches what the one-column test cannot see."""
    n = t.shape[1]
    w = max(8, (n // 4) // 2 * 2)
    if n < 3 * w:
        return 1.0
    f = t.astype(np.float32)
    strips = np.stack([f[:, p:p + w].ravel() for p in range(n - w + 1)])
    size = strips.shape[1]
    mism = (strips @ (1 - strips).T + (1 - strips) @ strips.T) / size
    pos = np.arange(n - w + 1)
    mism[np.abs(pos[:, None] - pos[None, :]) < w] = np.inf
    base = float(np.median(mism.min(axis=1)))
    cross = np.hstack([f[:, n - w // 2:], f[:, :w // 2]]).ravel()
    ok = (pos >= w // 2) & (pos + w <= n - w // 2)
    d = float(((cross @ (1 - strips[ok]).T + (1 - cross) @ strips[ok].T) / size).min())
    return _ratio(d, base)


def seam_x(t: np.ndarray, context: bool = True) -> Tuple[float, float, float]:
    """(combined, edge, context): combined is the worse of the edge ratio and the context ratio / CTX_SCALE.
    context=False (edge test only) is for mirror tiles, which are seamless by construction: their wrap line is
    a mirror line, which the strip matching would wrongly read as a seam (the two mirror lines differ)."""
    e = edge_ratio_x(t)
    c = context_ratio_x(t) if context else 1.0
    return max(e, c / CTX_SCALE), e, c


def edge_ratios(t: np.ndarray) -> Tuple[float, float]:
    """(H, V) combined ratio for a bool tile exactly as given (no trim)."""
    return seam_x(t)[0], seam_x(t.T)[0]


def _best_trim(t: np.ndarray, max_shift: int, context: bool = True) -> Tuple[float, Tuple[int, int]]:
    """Best combined ratio over trims of 0..max_shift pixels off the left and right (cheap edge test first,
    the context test only where the edge test already passes)."""
    n = t.shape[1]
    best = (seam_x(t, context)[0], (0, 0))
    for p in range(max_shift + 1):
        for q in range(max_shift + 1):
            if (p, q) == (0, 0) or n - p - q < 16:
                continue
            sub = t[:, p:n - q]
            if edge_ratio_x(sub) > best[0] and edge_ratio_x(sub) > THRESHOLD:
                continue
            c = seam_x(sub, context)[0]
            if c < best[0] - 1e-9:
                best = (c, (p, q))
    return best


def analyze(tile: np.ndarray, threshold: float = THRESHOLD, max_shift: int = MAX_SHIFT, context: bool = True) -> Dict:
    """Seam numbers for one tile (bool array, True = white). H = left/right, V = top/bottom."""
    h0, eh, ch = seam_x(tile, context)
    v0, ev, cv = seam_x(tile.T, context)
    best_h = _best_trim(tile, max_shift, context) if max_shift else (h0, (0, 0))
    best_v = _best_trim(tile.T, max_shift, context) if max_shift else (v0, (0, 0))
    ok0 = h0 <= threshold and v0 <= threshold
    ok_shift = best_h[0] <= threshold and best_v[0] <= threshold
    status = "PASS" if ok0 else ("PASS-SHIFT" if ok_shift else "FAIL")
    return {
        "H": round(h0, 2), "V": round(v0, 2),
        "edge_H": round(eh, 2), "edge_V": round(ev, 2), "ctx_H": round(ch, 2), "ctx_V": round(cv, 2),
        "H_best": round(best_h[0], 2), "H_trim": best_h[1],
        "V_best": round(best_v[0], 2), "V_trim": best_v[1],
        "status": status,
    }


def label(a: Dict) -> str:
    """Short text for a contact sheet: 'H0.9 V1.1 PASS'."""
    return "H%.1f V%.1f %s" % (a["H"], a["V"], a["status"])


# --------------------------------------------------------------------------------------------
# helpers shared with the repair step


def to_bool(img: Image.Image) -> np.ndarray:
    return np.array(img.convert("L")) >= 128


def resize_bool(t: np.ndarray, n: int) -> np.ndarray:
    im = Image.fromarray(t.astype(np.uint8) * 255).resize((n, n), Image.LANCZOS)
    return np.array(im) >= 128


def _small(t: np.ndarray, n: int = 16) -> np.ndarray:
    im = Image.fromarray(t.astype(np.uint8) * 255).resize((n, n), Image.BOX)
    return np.array(im).astype(np.float32) / 255.0


def layout_alike(a: np.ndarray, b: np.ndarray) -> float:
    """Do the shapes sit in the same places? Correlation of the two tiles at 16 px, allowing a slide
    (tiles repeat): -1..1. Low after a blend or mirror repair, by design: the layout is new."""
    x, y = _small(a), _small(b)
    x, y = x - x.mean(), y - y.mean()
    nx, ny = float(np.sqrt((x * x).sum())), float(np.sqrt((y * y).sum()))
    if nx < 1e-6 or ny < 1e-6:
        return 1.0 if nx < 1e-6 and ny < 1e-6 else 0.0
    corr = np.fft.ifft2(np.fft.fft2(x / nx) * np.conj(np.fft.fft2(y / ny))).real
    return float(corr.max())


def _radial(t: np.ndarray) -> np.ndarray:
    n = 64
    f = _small(t, n)
    f = (f - f.mean()) * np.outer(np.hanning(n), np.hanning(n))  # window: tile edges must not add fake lines
    p = np.abs(np.fft.fftshift(np.fft.fft2(f))) ** 2
    yy, xx = np.indices(p.shape)
    r = np.sqrt((yy - n // 2) ** 2 + (xx - n // 2) ** 2).astype(int)
    prof = np.bincount(r.ravel(), p.ravel(), minlength=n // 2 + 1)[1:n // 2]
    tot = prof.sum()
    return prof / tot if tot > 1e-9 else prof


def texture_alike(a: np.ndarray, b: np.ndarray) -> float:
    """Same KIND of pattern (same size of shapes, same amount of ink) wherever the shapes sit: 0..1.
    A 9 percent rescale from a crop barely moves it; a different pattern family does."""
    ra, rb = _radial(a), _radial(b)
    na, nb = float(np.linalg.norm(ra)), float(np.linalg.norm(rb))
    cos = float(ra @ rb / (na * nb)) if na > 1e-9 and nb > 1e-9 else 0.0
    return max(0.0, cos * (1 - min(1.0, 2 * abs(float(a.mean()) - float(b.mean())))))


def look_word(texture: float, layout: float) -> str:
    if texture >= 0.90 and layout >= 0.70:
        return "SAME"
    if texture >= 0.90:
        return "SAME-KIND (new layout)"
    if texture >= 0.75:
        return "SIMILAR"
    return "CHANGED"


# --------------------------------------------------------------------------------------------
# repair


def _trim(t: np.ndarray, a: Dict) -> np.ndarray:
    (hp, hq), (vp, vq) = a["H_trim"], a["V_trim"]
    return t[vp:t.shape[0] - vq, hp:t.shape[1] - hq]


def _period_crop(t: np.ndarray) -> Optional[np.ndarray]:
    """Largest square window whose left edge continues into its right edge and top into bottom."""
    n = t.shape[0]
    f = t.astype(np.float32)
    dx = np.abs(f.T[:, None, :] - f.T[None, :, :]).mean(axis=2)
    dy = np.abs(f[:, None, :] - f[None, :, :]).mean(axis=2)
    for size in range(n, int(n * 0.55), -1):
        k = size - 1
        cx = [dx[x0, x0 + k] for x0 in range(0, n - k)]
        cy = [dy[y0, y0 + k] for y0 in range(0, n - k)]
        x0, y0 = int(np.argmin(cx)), int(np.argmin(cy))
        win = t[y0:y0 + size, x0:x0 + size]
        h, v = edge_ratios(win)
        if h <= THRESHOLD and v <= THRESHOLD:
            return win
    return None


def _blend(t: np.ndarray) -> np.ndarray:
    """Slide by half a tile, so the old seam is in the middle, and cross-fade the middle with the original."""
    n = t.shape[0]
    f = t.astype(np.float32)
    w = 1 - np.abs(np.linspace(-1, 1, n))  # 0 at the borders, 1 in the middle
    out = f
    for axis in (1, 0):
        rolled = np.roll(out, n // 2, axis=axis)
        wk = w[None, :] if axis == 1 else w[:, None]
        out = wk * out + (1 - wk) * rolled
    return out >= 0.5


def _mirror(t: np.ndarray) -> np.ndarray:
    top = np.hstack([t, np.fliplr(t)])
    return np.vstack([top, np.flipud(top)])


def edge_density(t: np.ndarray) -> float:
    """Share of neighbouring pixel pairs that differ: how much outline the tile has."""
    a = t.astype(np.int8)
    return float((np.abs(np.diff(a, axis=0)).mean() + np.abs(np.diff(a, axis=1)).mean()) / 2)


def repair(tile: np.ndarray, threshold: float = THRESHOLD) -> Dict:
    """Try the repair methods; return {'tile', 'method', 'analysis', 'look'} (method None if nothing passed)."""
    n = tile.shape[0]
    a0 = analyze(tile, threshold)
    # (method, output tile, same-scale tile to compare the look with)
    cands: List[Tuple[str, np.ndarray, np.ndarray]] = []  # (method, output, same-area reference for the look test)
    if a0["status"] == "PASS-SHIFT":
        t = _trim(tile, a0)
        if t.shape[0] != t.shape[1]:
            t = resize_bool(t, n)
        cands.append(("trim", t, tile))
    pc = _period_crop(tile)
    if pc is not None:
        t = resize_bool(pc, n)
        cands.append(("period-crop", t, tile))
    t = _blend(tile)
    cands.append(("blend", t, tile))
    m = _mirror(tile)  # twice as big, so the shapes keep their size
    cands.append(("mirror", m, np.tile(tile, (2, 2))))  # same area, same scale: plain repeat vs mirror
    best = None
    for method, t, ref in cands:
        a = analyze(t, threshold, max_shift=0, context=(method != "mirror"))
        if a["status"] != "PASS":
            continue
        ratio = edge_density(t) / max(edge_density(ref), 1e-6)
        if method != "trim" and not 0.7 <= ratio <= 1.35:  # a cross-fade that cuts shapes into crumbs adds outline: reject
            continue
        tex, lay = texture_alike(ref, t), layout_alike(ref, t)
        # order of trust: trim, period-crop (same shapes), mirror (flipped shapes), blend (can crumble shapes)
        key = (tex >= 0.80, -["trim", "period-crop", "mirror", "blend"].index(method))
        if best is None or key > best["key"]:
            best = {"tile": t, "method": method, "analysis": a, "look": round(tex, 2), "layout": round(lay, 2), "key": key}
    if best:
        best.pop("key")
        return best
    return {"tile": tile, "method": None, "analysis": a0, "look": 1.0, "layout": 1.0}


# --------------------------------------------------------------------------------------------
# pictures


def _font(size: int):
    for name in ("arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def preview3(tile: np.ndarray, px: int = 96, lines: bool = True) -> Image.Image:
    """3 x 3 repeat of the tile, wrap lines drawn faintly (red, thin) between the copies."""
    one = Image.fromarray(tile.astype(np.uint8) * 255).resize((px, px), Image.LANCZOS).convert("RGB")
    out = Image.new("RGB", (3 * px, 3 * px))
    for i in range(3):
        for j in range(3):
            out.paste(one, (i * px, j * px))
    if lines:
        ov = Image.new("RGBA", out.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for k in (1, 2):
            d.line([(k * px, 0), (k * px, 3 * px)], fill=(255, 40, 40, 110), width=1)
            d.line([(0, k * px), (3 * px, k * px)], fill=(255, 40, 40, 110), width=1)
        out = Image.alpha_composite(out.convert("RGBA"), ov).convert("RGB")
    return out


def fail_sheet(items: List[Tuple[str, np.ndarray, str]], path: str, cols: int = 4, px: int = 96) -> None:
    """One labelled sheet (letters along the top, numbers down the side) of the 3 x 3 previews of failed tiles."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from label_grid_sheet import label_sheet

    rows = (len(items) + cols - 1) // cols
    cw, ch = 3 * px + 10, 3 * px + 40
    sheet = Image.new("RGB", (cols * cw, rows * ch), (40, 44, 52))
    d = ImageDraw.Draw(sheet)
    f = _font(16)
    for n, (name, tile, text) in enumerate(items):
        x, y = (n % cols) * cw + 5, (n // cols) * ch + 4
        sheet.paste(preview3(tile, px), (x, y))
        d.text((x, y + 3 * px + 6), "%s  %s" % (name, text), fill=(255, 255, 255), font=f)
    label_sheet(sheet, cols, rows).save(path)


def repair_sheet(results, path: str, cols: int = 3, px: int = 64) -> None:
    """Before | after, each as a 3 x 3 repeat, for every repaired tile, with the numbers, labelled with a ruler."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from label_grid_sheet import label_sheet

    items = [r for r in results if r["repair"] and r["repair"]["method"]]
    if not items:
        return
    rows = (len(items) + cols - 1) // cols
    cw, ch = 6 * px + 20, 3 * px + 44
    sheet = Image.new("RGB", (cols * cw, rows * ch), (40, 44, 52))
    d = ImageDraw.Draw(sheet)
    f = _font(14)
    for n, r in enumerate(items):
        x, y = (n % cols) * cw + 5, (n // cols) * ch + 4
        sheet.paste(preview3(r["tile"], px), (x, y))
        sheet.paste(preview3(r["repair"]["tile"], px), (x + 3 * px + 10, y))
        rep = r["repair"]
        d.text((x, y + 3 * px + 5), "%s  %s" % (r["name"], rep["method"]), fill=(255, 255, 255), font=f)
        d.text((x, y + 3 * px + 22), "kind %.2f layout %.2f %s" % (rep["look"], rep["layout"], look_word(rep["look"], rep["layout"])), fill=(190, 195, 205), font=f)
    label_sheet(sheet, cols, rows).save(path)


# --------------------------------------------------------------------------------------------
# folder run


def run_folder(folder: str, threshold: float = THRESHOLD, fix_dir: Optional[str] = None):
    results = []
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith(".png"):
            continue
        name = os.path.splitext(fn)[0]
        tile = to_bool(Image.open(os.path.join(folder, fn)))
        a = analyze(tile, threshold)
        rep = None
        if fix_dir and a["status"] != "PASS":
            rep = repair(tile, threshold)
            if rep["method"]:
                os.makedirs(fix_dir, exist_ok=True)
                Image.fromarray(rep["tile"].astype(np.uint8) * 255).save(os.path.join(fix_dir, fn))
        results.append({"name": name, "tile": tile, "analysis": a, "repair": rep})
    if fix_dir and os.path.isdir(fix_dir):  # which method fixed which tile; pattern_similarity.py reads this
        path = os.path.join(fix_dir, "repairs.json")
        old = {}
        if os.path.exists(path):
            with open(path) as f:
                old = json.load(f)
        for r in results:
            if r["repair"] and r["repair"]["method"]:
                old[r["name"]] = {"method": r["repair"]["method"], "kind": r["repair"]["look"], "layout": r["repair"]["layout"],
                                  "was": r["analysis"]["status"]}
        with open(path, "w") as f:
            json.dump(old, f, indent=1, sort_keys=True)
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folders", nargs="+")
    ap.add_argument("--threshold", type=float, default=THRESHOLD)
    ap.add_argument("--repair", metavar="OUTDIR", help="write repaired copies of tiles that are not PASS here")
    ap.add_argument("--fail-sheet", metavar="PNG", help="3 x 3 previews of all FAILED tiles on one labelled sheet")
    ap.add_argument("--repair-sheet", metavar="PNG", help="before | after 3 x 3 previews of every repaired tile (needs --repair)")
    ap.add_argument("--json", metavar="PATH", help="write the numbers as json")
    a = ap.parse_args(argv)
    allres = []
    for folder in a.folders:
        allres += run_folder(folder, a.threshold, a.repair)
    print("%-10s %6s %6s  %-14s %-14s %-11s  %s" % ("tile", "H", "V", "best H@trim", "best V@trim", "status", "repair"))
    for r in allres:
        x, rep = r["analysis"], r["repair"]
        txt = ""
        if rep is not None:
            if rep["method"]:
                txt = "%s -> H%.1f V%.1f %s, kind %.2f layout %.2f: %s" % (
                    rep["method"], rep["analysis"]["H"], rep["analysis"]["V"], rep["analysis"]["status"], rep["look"], rep["layout"], look_word(rep["look"], rep["layout"]))
            else:
                txt = "no repair passed"
        print("%-10s %6.2f %6.2f  %-14s %-14s %-11s  %s" % (
            r["name"], x["H"], x["V"], "%.2f@%d,%d" % (x["H_best"], *x["H_trim"]), "%.2f@%d,%d" % (x["V_best"], *x["V_trim"]), x["status"], txt))
    n = len(allres)
    cnt = {k: sum(1 for r in allres if r["analysis"]["status"] == k) for k in ("PASS", "PASS-SHIFT", "FAIL")}
    print("\n%d tiles: PASS %d, PASS-SHIFT %d, FAIL %d (threshold %.2f)" % (n, cnt["PASS"], cnt["PASS-SHIFT"], cnt["FAIL"], a.threshold))
    if a.repair:
        fixed = sum(1 for r in allres if r["repair"] and r["repair"]["method"])
        print("repaired copies written: %d of %d needing it (%s)" % (fixed, cnt["PASS-SHIFT"] + cnt["FAIL"], a.repair))
    if a.repair_sheet and a.repair:
        repair_sheet(allres, a.repair_sheet)
        print("repair before/after sheet:", a.repair_sheet)
    if a.fail_sheet:
        items = [(r["name"], r["tile"], "H%.1f V%.1f" % (r["analysis"]["H"], r["analysis"]["V"])) for r in allres if r["analysis"]["status"] == "FAIL"]
        if items:
            fail_sheet(items, a.fail_sheet)
            print("failed-tile sheet:", a.fail_sheet)
        else:
            print("no failed tiles, no sheet written")
    if a.json:
        out = {r["name"]: dict(r["analysis"], repair=(None if not r["repair"] else {
            "method": r["repair"]["method"], "look": r["repair"]["look"], "layout": r["repair"]["layout"], "status": r["repair"]["analysis"]["status"]})) for r in allres}
        with open(a.json, "w") as f:
            json.dump(out, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
