#!/usr/bin/env python3
"""BD-1034: how different are the pattern tiles, at the size a player really sees?

Reads folders of square black-and-white tiles (white = colour 2, black = colour 1, as the dino pattern
masks define it), shrinks them to 16 x 16 and 32 x 32, also tiles each 3 x 3 and shrinks that, and
compares every pair. A pair is "the same" when one tile, turned or flipped (8 ways) and slid
sideways (tiles repeat, so a slide does not make a new pattern), looks like the other.

  python tools/pattern_similarity.py resources/patterns/candidates --fixed resources/patterns/candidates-fixed       --existing resources/patterns/existing --threshold 0.75 --sheet contact.png --expect-cluster a-A2,a-D3,a-D4

What it prints
  * one row per tile: white share, how grey it gets at 16 px, how busy it is, nearest other tile, similarity to
    it, distinctiveness (0 to 100, higher = more different), seam numbers (tools/tile_seam_check.py) and flags.
  * pairs above the threshold (near-duplicates) and the clusters they form, and the same-look-at-another-size
    pairs ("scale": tile A packed 2 or 3 times denser looks like tile B; size is a free setting on the dino,
    so dots that only differ in size count as one idea).
  * with --select: a greedy shortlist (best first) of tiles that are clean (no flag, seam PASS) and different
    from everything already picked (pair by pair, not by chain), existing patterns first.
  * --owner-groups FILE: tiles the owner says look alike (resources/patterns/owner-groups.json). The machine
    numbers are printed first, then the owner's groups are applied: the owner wins, one tile per group.
  * --expect-cluster A,B,C: checks that the named tiles land in ONE cluster (the owner looked at the first sheet
    and said a-A2, a-D3 and a-D4 look alike; the tool has to agree).
  * --fixed DIR: a tile that has a same-named file there (from tile_seam_check --repair) is used instead.
Flags: EMPTY/FULL (almost one colour, vanishes small), GREY (turns to grey mush at 16 px),
BUSY (as busy as random noise at 16 px), SEAM (does not repeat cleanly: not PASS in the seam test),
BLEND-FIX (the seam was only fixed by the cross-fade, which can crumble shapes; needs a better source tile).
Tile names are sheet letter + column letter + row number: a-D3 = first sheet, column D, row 3.
Needs Pillow and numpy only. Exit code 0 always (it is a report, not a gate).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tile_seam_check as tsc  # noqa: E402

SMALL = 16
MEDIUM = 32
BASE = 96  # working size before the final shrink (divisible by 2, 3, 16, 32)

# ---------------------------------------------------------------------------------------------
# loading and resampling


def load_tile(path: str) -> np.ndarray:
    """Square bool array, True = white. Anything not square is centre-cropped to a square."""
    im = Image.open(path).convert("L")
    w, h = im.size
    if w != h:
        s = min(w, h)
        im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    return np.array(im) >= 128


def load_folder(folder: str) -> List[Tuple[str, np.ndarray]]:
    out = []
    for name in sorted(os.listdir(folder)):
        if name.lower().endswith(".png"):
            out.append((os.path.splitext(name)[0], load_tile(os.path.join(folder, name))))
    return out


def shrink(arr: np.ndarray, n: int) -> np.ndarray:
    """Area-average a bool/float array to n x n floats in 0..1 (what a small render would show)."""
    img = Image.fromarray((arr.astype(np.float32) * 255).astype(np.uint8))
    return np.array(img.resize((n, n), Image.BOX)).astype(np.float32) / 255.0


def tiled(arr: np.ndarray, k: int) -> np.ndarray:
    return np.tile(arr, (k, k))


def d4(a: np.ndarray) -> List[np.ndarray]:
    """The 8 turns and flips of a square array."""
    out = []
    for f in (a, np.fliplr(a)):
        for r in range(4):
            out.append(np.rot90(f, r))
    return out


FEEL_SCALE = 1.4  # distance in "feel" units that counts as completely different (distance 0.35 = look-alike 0.75)


def _feel(s: np.ndarray) -> np.ndarray:
    """What a tile feels like at 32 px, wherever its shapes sit and however they are turned: how much ink,
    how much contrast is left, how busy, and how the detail is spread over fine / medium / coarse sizes.
    Waves and a zig-zag, both fine two-colour lines, come out nearly the same; dots and bands do not."""
    n = s.shape[0]
    f = np.abs(np.fft.fft2(s - s.mean())) ** 2
    yy, xx = np.indices(f.shape)
    r = np.sqrt(np.minimum(xx, n - xx) ** 2 + np.minimum(yy, n - yy) ** 2)
    edges = [0.5, 2, 4, 7, 11, 17]
    bins = np.array([f[(r >= a) & (r < b)].sum() for a, b in zip(edges[:-1], edges[1:])])
    prof = bins / (bins.sum() + 1e-9)
    b = s >= 0.5
    busy = ((b != np.roll(b, 1, 0)).mean() + (b != np.roll(b, 1, 1)).mean()) / 2
    return np.concatenate([[s.mean(), s.std() * 1.5, busy], prof])


class Features:
    """Everything the comparison needs for one tile, computed once."""

    def __init__(self, name: str, tile: np.ndarray, existing: bool = False, fixed: Optional[str] = None, raw_status: str = "", basis: Optional[np.ndarray] = None):
        self.name = name
        self.existing = existing
        self.fixed = fixed  # True when this is a repaired copy
        self.raw_status = raw_status
        self.tile = tile  # what is shown and seam-tested
        # A mirror repair is twice as big with every shape half the size; judge looks (shape, feel, grey, busy) on the
        # original tile so the repair does not count as a different, finer pattern. `basis` is that original.
        look = basis if basis is not None else tile
        base = shrink(look, BASE)
        self.base = base
        self.s16 = shrink(look, SMALL)
        self.s32 = shrink(look, MEDIUM)
        self.t3 = shrink(tiled(base, 3), 3 * SMALL)  # 3 x 3 tiling, 16 px per tile
        self.dense = {k: shrink(tiled(base, k), MEDIUM) for k in (2, 3)}
        self.white = float(look.mean())
        self.seam = None if existing else tsc.analyze(tile, context=(fixed != "mirror"))  # mirror tiles: edge test only
        b16 = self.s16 >= 0.5
        self.white16 = float(b16.mean())
        self.grey16 = float(((self.s16 > 0.25) & (self.s16 < 0.75)).mean())
        # busyness: share of neighbouring pixel pairs (wrapping, since tiles repeat) that differ
        self.busy16 = float(((b16 != np.roll(b16, 1, 0)).mean() + (b16 != np.roll(b16, 1, 1)).mean()) / 2)
        self.feel = _feel(self.s32)
        self.flags: List[str] = []
        self._ffts: Dict[Tuple[str, int], np.ndarray] = {}

    def variants_fft(self, key: str, arr: np.ndarray):
        """FFT of the 8 turned/flipped, zero-mean, unit-norm copies of arr (cached)."""
        ck = (key, arr.shape[0])
        if ck not in self._ffts:
            outs = []
            for v in d4(arr):
                z = v - v.mean()
                n = float(np.sqrt((z * z).sum()))
                outs.append(np.fft.fft2(z / n) if n > 1e-6 else None)
            self._ffts[ck] = outs
        return self._ffts[ck]


# ---------------------------------------------------------------------------------------------
# per-tile checks (the seam test itself lives in tile_seam_check.py)


def tile_flags(f: Features) -> List[str]:
    out = []
    minority = min(f.white, 1 - f.white)
    minority16 = min(f.white16, 1 - f.white16)
    if minority < 0.08 or minority16 < 0.05:
        out.append("EMPTY" if f.white < 0.5 else "FULL")
    if f.grey16 > 0.45:
        out.append("GREY")
    if f.busy16 > 0.45:
        out.append("BUSY")
    if f.seam is not None and f.seam["status"] != "PASS":
        out.append("SEAM")
    if f.fixed == "blend":  # the cross-fade repair crumbles shapes: look at it by eye before trusting it
        out.append("BLEND-FIX")
    return out


# ---------------------------------------------------------------------------------------------
# similarity


def _best(a: np.ndarray, b: Features, key: str, inverse: bool = False) -> float:
    """Best normalised correlation of a against any turn/flip/slide of b's array `key`."""
    z = a - a.mean()
    n = float(np.sqrt((z * z).sum()))
    if n < 1e-6:
        return 0.0
    fa = np.fft.fft2(z / n)
    best = -1.0
    for fb in b.variants_fft(key, getattr(b, key) if key != "dense" else None):
        if fb is None:
            continue
        corr = np.fft.ifft2(fa * np.conj(fb)).real
        v = float((-corr).max()) if inverse else float(corr.max())
        best = max(best, v)
    return best


def _best_arr(a: np.ndarray, b_arr: np.ndarray, cache_owner: Features, cache_key: str, inverse: bool = False) -> float:
    z = a - a.mean()
    n = float(np.sqrt((z * z).sum()))
    if n < 1e-6:
        return 0.0
    fa = np.fft.fft2(z / n)
    best = -1.0
    for fb in cache_owner.variants_fft(cache_key, b_arr):
        if fb is None:
            continue
        corr = np.fft.ifft2(fa * np.conj(fb)).real
        v = float((-corr).max()) if inverse else float(corr.max())
        best = max(best, v)
    return best


def pair_scores(a: Features, b: Features) -> Dict[str, float]:
    s16 = _best_arr(a.s16, b.s16, b, "s16")
    s32 = _best_arr(a.s32, b.s32, b, "s32")
    s3 = _best_arr(a.t3, b.t3, b, "t3")
    feel = max(0.0, 1.0 - float(np.abs(a.feel - b.feel).sum()) / FEEL_SCALE)
    sim = max(s16, s32, s3, feel)
    scale = -1.0
    for k in (2, 3):
        scale = max(scale, _best_arr(a.dense[k], b.s32, b, "s32"))  # A packed denser vs B
        scale = max(scale, _best_arr(a.s32, b.dense[k], b, "d%d" % k))  # A vs B packed denser
    inv = max(_best_arr(a.s32, b.s32, b, "s32", inverse=True), _best_arr(a.s16, b.s16, b, "s16", inverse=True))
    return {"s16": s16, "s32": s32, "s3": s3, "feel": feel, "sim": sim, "scale": scale, "inv": inv}


def compare_all(feats: List[Features]) -> Dict[Tuple[int, int], Dict[str, float]]:
    out = {}
    for i in range(len(feats)):
        for j in range(i + 1, len(feats)):
            out[(i, j)] = pair_scores(feats[i], feats[j])
    return out


def build(folders: List[str], existing_folders: List[str], fixed_folders: Optional[List[str]] = None) -> List[Features]:
    feats = []
    for folder in existing_folders:
        for name, t in load_folder(folder):
            feats.append(Features("E:" + name, t, existing=True))
    fixed, methods = {}, {}
    for folder in fixed_folders or []:
        for name, t in load_folder(folder):
            fixed[name] = t
        rp = os.path.join(folder, "repairs.json")
        if os.path.exists(rp):
            with open(rp) as fh:
                methods.update({k: v["method"] for k, v in json.load(fh).items()})
    for folder in folders:
        for name, t in load_folder(folder):
            if name in fixed:
                m = methods.get(name, "repaired")
                feats.append(Features(name, fixed[name], fixed=m, raw_status=tsc.analyze(t)["status"], basis=t if m == "mirror" else None))
            else:
                feats.append(Features(name, t))
    for f in feats:
        f.flags = tile_flags(f)
    return feats


def distinct_scores(feats: List[Features], pairs: Dict[Tuple[int, int], Dict[str, float]]) -> List[Tuple[float, int]]:
    """For every tile: (highest look-alike score against any other tile, index of that tile)."""
    worst = [(-1.0, -1)] * len(feats)
    for (i, j), s in pairs.items():
        v = max(s["sim"], s["scale"])
        if v > worst[i][0]:
            worst[i] = (v, j)
        if v > worst[j][0]:
            worst[j] = (v, i)
    return worst


def select(feats: List[Features], pairs: Dict[Tuple[int, int], Dict[str, float]], thr: float) -> List[int]:
    """Greedy shortlist: existing tiles first, then candidates without bad flags, most distinctive first,
    each only if it differs (below thr, shape and scale) from every tile already picked."""
    def look(i, j):
        s = pairs[(min(i, j), max(i, j))]
        return max(s["sim"], s["scale"])

    picked = [i for i, f in enumerate(feats) if f.existing]
    worst = distinct_scores(feats, pairs)
    order = sorted([i for i, f in enumerate(feats) if not f.existing and not f.flags], key=lambda i: worst[i][0])
    for i in order:
        if all(look(i, j) < thr for j in picked):
            picked.append(i)
    return [i for i in picked if not feats[i].existing]


# ---------------------------------------------------------------------------------------------
# reports


def seam_text(f: Features) -> str:
    if f.seam is None:
        return "in game"
    t = "H%.1f V%.1f %s" % (f.seam["H"], f.seam["V"], f.seam["status"])
    if f.fixed:
        t += " (%s fix, was %s)" % (f.fixed, f.raw_status)
    return t


def table(feats, pairs):
    worst = distinct_scores(feats, pairs)
    print("%-16s %5s %5s %5s %5s  %-16s %5s %6s  %-34s %s" % (
        "tile", "white", "grey", "busy", "inv", "nearest", "alike", "DISTIN", "seam", "flags"))
    for i, f in enumerate(feats):
        w, j = worst[i]
        inv = max([s["inv"] for (a, b), s in pairs.items() if i in (a, b)] or [0])
        near = feats[j].name if j >= 0 else "-"
        print("%-16s %5.2f %5.2f %5.2f %5.2f  %-16s %5.2f %6.0f  %-34s %s" % (
            f.name, f.white, f.grey16, f.busy16, inv, near, w, max(0.0, 100 * (1 - w)), seam_text(f), " ".join(f.flags)))
    print()


def flagged_pairs(feats, pairs, thr):
    out = []
    for (i, j), s in pairs.items():
        v = max(s["sim"], s["scale"])
        if v >= thr:
            out.append((v, i, j, "owner" if s.get("owner") else ("feel" if s["feel"] >= thr and max(s["s16"], s["s32"], s["s3"]) < thr else "shape") if s["sim"] >= thr else "scale"))
    out.sort(reverse=True)
    return out


def clusters(n: int, fp) -> List[List[int]]:
    """Groups of tiles joined by look-alike pairs (single linkage)."""
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for _, i, j, _k in fp:
        parent[find(i)] = find(j)
    groups: Dict[int, List[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return [g for g in groups.values() if len(g) > 1]


def load_owner_groups(path: str) -> List[Dict]:
    with open(path) as f:
        return json.load(f)["groups"]


def apply_owner_groups(feats, pairs, groups) -> None:
    """The owner looked at the sheet and said these tiles look alike. Every pair inside a group becomes a
    look-alike pair (kind 'owner'), whatever the numbers say, so only one of them can be shortlisted."""
    idx = {f.name: i for i, f in enumerate(feats)}
    for g in groups:
        ids = [idx[n] for n in g["tiles"] if n in idx]
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                key = (min(ids[x], ids[y]), max(ids[x], ids[y]))
                pairs[key]["owner"] = True
                pairs[key]["sim"] = 1.0


def report(feats, pairs, thr):
    table(feats, pairs)
    fp = flagged_pairs(feats, pairs, thr)
    print("Pairs that look alike (>= %.2f): %d" % (thr, len(fp)))
    for v, i, j, kind in fp:
        s = pairs[(i, j)]
        print("  %.2f  %-16s %-16s  (%s; same size %.2f, other size %.2f, inverse %.2f)" % (
            v, feats[i].name, feats[j].name, kind, s["sim"], s["scale"], s["inv"]))
    cl = clusters(len(feats), fp)
    print("\nClusters (tiles joined by look-alike pairs; one tile per look-alike group is enough): %d" % len(cl))
    for g in cl:
        print("  " + ", ".join(feats[i].name for i in g))
    print()
    return fp, cl


def expect_cluster(feats, pairs, names: List[str], thr: float):
    """Print how close the named tiles are to each other and whether they sit in one cluster at thr."""
    idx = []
    for n in names:
        match = [i for i, f in enumerate(feats) if f.name == n]
        if not match:
            print("expect-cluster: no tile named", n)
            return False
        idx.append(match[0])
    print("Ground-truth check: %s must be one cluster (threshold %.2f)" % (", ".join(names), thr))
    for x in range(len(idx)):
        for y in range(x + 1, len(idx)):
            i, j = sorted((idx[x], idx[y]))
            s = pairs[(i, j)]
            print("  %-6s %-6s  shape16 %.2f  shape32 %.2f  3x3 %.2f  feel %.2f  other-size %.2f  -> look-alike %.2f" % (
                feats[i].name, feats[j].name, s["s16"], s["s32"], s["s3"], s["feel"], s["scale"], max(s["sim"], s["scale"])))
    fp = flagged_pairs(feats, pairs, thr)
    ok = any(set(idx) <= set(g) for g in clusters(len(feats), fp))
    print("  => %s" % ("ONE CLUSTER (matches the owner)" if ok else "NOT one cluster at this threshold"))
    print()
    return ok


# ---------------------------------------------------------------------------------------------
# contact sheet

CELL = 150
SMALLPX = 24
GAP = 24


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # old Pillow
        return ImageFont.load_default()


def _tile_img(f: Features, px: int) -> Image.Image:
    return Image.fromarray((f.tile.astype(np.uint8)) * 255).resize((px, px), Image.NEAREST if px <= f.tile.shape[0] else Image.LANCZOS)


def _block(group, feats, worst, picked_set, fontc, fonts, cols):
    """One grid of tiles (cells in sheet order) as an image, and its row count."""
    ch = CELL + 68
    rows = (len(group) + cols - 1) // cols
    img = Image.new("RGB", (cols * (CELL + 8), rows * ch), (40, 44, 52))
    d = ImageDraw.Draw(img)
    for n, i in enumerate(group):
        f = feats[i]
        cx, cy = (n % cols) * (CELL + 8) + 2, (n // cols) * ch + 2
        good = f.existing or i in picked_set
        d.rectangle([cx, cy, cx + CELL + 3, cy + ch - 4], outline=(90, 200, 110) if good else (220, 90, 90), width=3)
        img.paste(_tile_img(f, CELL), (cx + 2, cy + 2))
        w, j = worst[i]
        d.text((cx + 5, cy + CELL + 5), f.name.replace("E:", ""), fill=(255, 170, 60) if f.existing else (255, 255, 255), font=fontc)
        d.text((cx + 5, cy + CELL + 22), seam_text(f).split(" (")[0], fill=(190, 195, 205), font=fonts)
        d.text((cx + 5, cy + CELL + 36), "like %s %.2f" % (feats[j].name.replace("E:", "")[:12], w), fill=(190, 195, 205), font=fonts)
        if f.flags:
            d.text((cx + 5, cy + CELL + 50), " ".join(f.flags), fill=(255, 140, 120), font=fonts)
        img.paste(_tile_img(f, SMALLPX), (cx + CELL - SMALLPX - 1, cy + CELL + 4))
    return img, rows


def contact_sheet(feats, pairs, thr, picked: List[int], path: str, title: str = "Pattern tiles: candidates and the patterns already in the game"):
    from label_grid_sheet import label_sheet

    fontc, fonts, fbig = _font(15), _font(12), _font(22)
    worst = distinct_scores(feats, pairs)
    picked_set = set(picked)
    groups: Dict[str, List[int]] = {}
    for i, f in enumerate(feats):
        key = "existing" if f.existing else f.name.split("-")[0]
        groups.setdefault(key, []).append(i)
    blocks = []
    for key in sorted(groups, key=lambda k: (k != "existing", k)):
        img, rows = _block(groups[key], feats, worst, picked_set, fontc, fonts, 4)
        if key != "existing":
            img = label_sheet(img, 4, rows, margin=48)  # ruler: tile "a-D3" = sheet a, column D, row 3
        title_img = Image.new("RGB", (img.width, 34), (40, 44, 52))
        ImageDraw.Draw(title_img).text((6, 4), "patterns already in the game" if key == "existing" else "sheet %s" % key, fill=(255, 255, 255), font=fbig)
        blk = Image.new("RGB", (img.width, img.height + 34))
        blk.paste(title_img, (0, 0))
        blk.paste(img, (0, 34))
        blocks.append(blk)
    W = sum(b.width for b in blocks) + GAP * (len(blocks) + 1)
    fp = flagged_pairs(feats, pairs, thr)
    PH = CELL + 24
    pair_rows = (len(fp) + 3) // 4 if fp else 0
    H = 76 + max(b.height for b in blocks) + (50 + pair_rows * PH if fp else 0) + 20
    sheet = Image.new("RGB", (W, H), (40, 44, 52))
    d = ImageDraw.Draw(sheet)
    d.text((GAP, 10), title, fill=(255, 255, 255), font=fbig)
    d.text((GAP, 40), "Green frame = kept, red = flagged or too like another tile. Small square = the tile at 24 px, the size a player really sees. "
           "Seam text: H/V ratio, 1.0 = invisible seam, PASS at 1.6 or less. Orange = already in the game.", fill=(200, 205, 215), font=fonts)
    x = GAP
    for b in blocks:
        sheet.paste(b, (x, 76))
        x += b.width + GAP
    if fp:
        py = 76 + max(b.height for b in blocks) + 14
        d.text((GAP, py), "Pairs that look alike (%.2f or more): the second one adds little" % thr, fill=(255, 255, 255), font=fbig)
        for n, (v, i, j, kind) in enumerate(fp):
            px, pyy = GAP + (n % 4) * (2 * CELL + 90), py + 40 + (n // 4) * PH
            sheet.paste(_tile_img(feats[i], CELL), (px, pyy))
            sheet.paste(_tile_img(feats[j], CELL), (px + CELL + 6, pyy))
            d.text((px + 2 * CELL + 14, pyy + 4), "%.2f" % v, fill=(255, 120, 120), font=fontc)
            d.text((px + 2 * CELL + 14, pyy + 24), kind, fill=(200, 205, 215), font=fonts)
            d.text((px, pyy + CELL + 4), "%s + %s" % (feats[i].name.replace("E:", ""), feats[j].name.replace("E:", "")), fill=(230, 230, 230), font=fonts)
    sheet.save(path)
    print("contact sheet:", path)


# ---------------------------------------------------------------------------------------------


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folders", nargs="+", help="folders of candidate tiles (png, square, black and white)")
    ap.add_argument("--existing", action="append", default=[], help="folder of tiles already in the game (compared against, never dropped)")
    ap.add_argument("--fixed", action="append", default=[], help="folder of repaired tiles (tile_seam_check --repair); same name = used instead")
    ap.add_argument("--threshold", type=float, default=0.75, help="look-alike score from which two tiles count as near-duplicates")
    ap.add_argument("--select", action="store_true", help="print the greedy shortlist")
    ap.add_argument("--sheet", help="write a contact sheet png")
    ap.add_argument("--owner-groups", help="json file: tiles the owner says look alike (applied AFTER the machine numbers are printed)")
    ap.add_argument("--expect-cluster", help="comma separated tile names that must fall in one cluster")
    a = ap.parse_args(argv)
    feats = build(a.folders, a.existing, a.fixed)
    if len(feats) < 2:
        print("need at least two tiles")
        return 0
    pairs = compare_all(feats)
    print("=== machine numbers only ===")
    report(feats, pairs, a.threshold)
    if a.expect_cluster:
        expect_cluster(feats, pairs, a.expect_cluster.split(","), a.threshold)
    if a.owner_groups:
        apply_owner_groups(feats, pairs, load_owner_groups(a.owner_groups))
        print("=== after the owner's groups (%s) ===" % a.owner_groups)
        fp2 = flagged_pairs(feats, pairs, a.threshold)
        for g in clusters(len(feats), fp2):
            print("  cluster: " + ", ".join(feats[i].name for i in g))
        print()
    picked = select(feats, pairs, a.threshold) if (a.select or a.sheet) else []
    cands = [f for f in feats if not f.existing]
    clean = [f for f in cands if not f.flags]
    print("Candidates: %d, clean (no flag, seam PASS): %d, flagged: %d" % (len(cands), len(clean), len(cands) - len(clean)))
    if a.select or a.sheet:
        print("Shortlist (different from the existing patterns and from each other): %d" % len(picked))
        for i in picked:
            print("  ", feats[i].name)
    if a.sheet:
        contact_sheet(feats, pairs, a.threshold, picked, a.sheet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
