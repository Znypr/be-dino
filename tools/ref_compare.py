#!/usr/bin/env python3
"""BD-1279: compare a reference picture (ChatGPT mock, YouTube frame, top-game screenshot) with a game capture, layer by layer,
with numbers precise enough to change the code from (owner 2026-11-21: "several layers of comparison to not miss out, really
precise changes like padding, size, layout, colors"; "looks flat, black outline is off, spacing is off, be more concrete").

    python tools/ref_compare.py REF.png GAME.jpg                       # report in build/ref-compare/<game name>/report.html
    python tools/ref_compare.py REF.png GAME.jpg --crop-game 0,34,1274,481 --boxes boxes.json --out build/ref-compare/hud

Every number is in % of the picture HEIGHT ("% h"), the unit src/shared/PhoneHudLayout.luau uses, so a difference maps 1:1 to a
spec value. Pictures of different widths line up because a piece is measured from ITS OWN edge: a left piece from the left edge,
a right piece from the right edge, a centre piece from the centre line.

Layers (all in report.html, numbers also in report.json):
  1. whole      both pictures side by side at the same height, and both edge maps (ref magenta, game cyan) on one canvas;
  2. zones      nine zones (top/middle/bottom x left/centre/right, edge anchored): ref | game | onion (50 %) | edges, ruled every 5 % h;
  3. elements   HUD pieces found automatically (dark-outlined or saturated plates) plus exact named boxes from --boxes, matched ref to game.
                Per piece: edge padding, top, width, height, gap to the piece above (all % h); outline thickness (% h and px at 720 h);
                fill colour (hex) and ΔE; shading = brightness top band minus bottom band (0 = flat, a gloss button is about 15-35);
                text/edge contrast. Each pair is cropped side by side with an onion overlay;
  4. changes    a plain list "shop: height 15.2 -> 13.9 % h (+1.3 % h)" sorted by size of the miss, with a tolerance (--tol, % h).

--boxes json (pixels of the ORIGINAL picture, before --crop; or fractions 0-1 with "unit": "frac"):
    {"unit": "px", "ref": {"shop": [x, y, w, h]}, "game": {"shop": [x, y, w, h]}}
A named box wins over an automatic one at the same spot. Uses Pillow and numpy only (the CI install); never goes on the internet.
Exit code 0 (report written), 2 bad usage / missing file.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
NORM_H = 720  # both pictures are scaled to this height first, so pixel rules mean the same on both
ZONE_ROWS = (("top", 0.0, 0.30), ("middle", 0.30, 0.72), ("bottom", 0.72, 1.0))
ZONE_EDGE_W = 0.75  # width of a left/right zone in heights (from its own edge); the centre zone is the centre +-0.45 h


# ---------- loading ----------

def parse_rect(text: str | None):
    if not text:
        return None
    parts = [float(v) for v in text.split(",")]
    if len(parts) != 4:
        raise ValueError("a rect is x,y,w,h")
    return parts


def load(path: Path, crop) -> tuple[Image.Image, float, tuple[float, float]]:
    img = Image.open(path).convert("RGB")
    offset = (0.0, 0.0)
    if crop:
        x, y, w, h = crop
        img = img.crop((int(x), int(y), int(x + w), int(y + h)))
        offset = (x, y)
    scale = NORM_H / img.height
    img = img.resize((max(1, round(img.width * scale)), NORM_H), Image.LANCZOS)
    return img, scale, offset


# ---------- geometry in % h, edge anchored ----------

def column_of(cx: float, W: float) -> str:
    if cx < W / 3:
        return "left"
    if cx > 2 * W / 3:
        return "right"
    return "centre"


def measure_box(box, W: float, H: float = NORM_H) -> dict:
    x, y, w, h = box
    col = column_of(x + w / 2, W)
    if col == "left":
        edge = x
    elif col == "right":
        edge = W - (x + w)
    else:
        edge = (x + w / 2) - W / 2  # signed offset of the centre from the centre line
    row = "top" if y + h / 2 < 0.30 * H else ("bottom" if y + h / 2 > 0.72 * H else "middle")
    pct = 100.0 / H
    return {"col": col, "row": row, "edge": edge * pct, "top": y * pct, "bottom": (H - y - h) * pct, "w": w * pct, "h": h * pct}


# ---------- pixel measures inside one box ----------

def to_arr(img: Image.Image) -> np.ndarray:
    return np.asarray(img, dtype=np.float32)


def luma(a: np.ndarray) -> np.ndarray:
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def outline_px(a: np.ndarray, dark: float = 60.0, lead: int = 10) -> float:
    """Median run of dark pixels met within the first `lead` px from each side, along three rows and three columns
    (0 = no dark outline). The crop is taken a little OUTSIDE the box, because an automatic box can hug the coloured
    plate inside its black stroke."""
    L = luma(a)
    h, w = L.shape
    runs = []
    for line in (L[h // 2, :], L[h // 3, :], L[2 * h // 3, :], L[:, w // 2], L[:, w // 3], L[:, 2 * w // 3]):
        for seq in (line, line[::-1]):
            dark_at = np.nonzero(seq[:lead] < dark)[0]
            if len(dark_at) == 0:
                runs.append(0)
                continue
            n = 0
            for v in seq[int(dark_at[0]):]:
                if v < dark:
                    n += 1
                else:
                    break
            runs.append(n)
    return float(np.median(runs)) if runs else 0.0


def lab(rgb) -> np.ndarray:
    c = np.asarray(rgb, dtype=np.float64) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def delta_e(a, b) -> float:
    return float(np.linalg.norm(lab(a) - lab(b)))


def box_stats(img: Image.Image, box) -> dict:
    x, y, w, h = [int(round(v)) for v in box]
    a = to_arr(img.crop((x, y, x + max(w, 1), y + max(h, 1))))
    if a.size == 0:
        return {}
    g = 6  # look a little outside the box for the outline
    o = outline_px(to_arr(img.crop((max(0, x - g), max(0, y - g), min(img.width, x + w + g), min(img.height, y + h + g)))))
    m = int(min(max(o + 2, 3), min(a.shape[0], a.shape[1]) // 3))
    inner = a[m:a.shape[0] - m, m:a.shape[1] - m] if a.shape[0] > 2 * m + 2 and a.shape[1] > 2 * m + 2 else a
    L = luma(inner)
    # fill = the median of the mid-bright pixels (text and outline excluded)
    keep = (L > 50) & (L < 245)
    fill = np.median(inner[keep], axis=0) if keep.sum() > 10 else np.median(inner.reshape(-1, 3), axis=0)
    band = max(1, inner.shape[0] // 5)
    shade = float(luma(inner[:band]).mean() - luma(inner[-band:]).mean())
    lo, hi = np.percentile(L, 5), np.percentile(L, 95)
    return {"outline_px": o, "outline_pct": o * 100.0 / NORM_H, "fill": [int(v) for v in fill],
            "fill_hex": "#%02x%02x%02x" % tuple(int(v) for v in fill), "shade": shade, "contrast": float(hi - lo)}


# ---------- automatic HUD pieces ----------

def _morph(mask: np.ndarray, size: int, close: bool) -> np.ndarray:
    """Binary closing (dilate then erode) or opening (erode then dilate) with a size x size square, via Pillow's Max/MinFilter."""
    im = Image.fromarray(mask.astype(np.uint8) * 255)
    first, second = (ImageFilter.MaxFilter(size), ImageFilter.MinFilter(size)) if close else (ImageFilter.MinFilter(size), ImageFilter.MaxFilter(size))
    return np.asarray(im.filter(first).filter(second)) > 127


def _fill_holes(mask: np.ndarray) -> np.ndarray:
    """Everything not reachable from the border through background counts as inside."""
    h, w = mask.shape
    im = Image.new("L", (w + 2, h + 2), 0)
    im.paste(Image.fromarray(mask.astype(np.uint8) * 255), (1, 1))
    ImageDraw.floodfill(im, (0, 0), 128)
    return np.asarray(im)[1:-1, 1:-1] != 128


def _components(mask: np.ndarray):
    """Bounding boxes (y0, x0, y1, x1) and fill ratio of 4-connected components (iterative flood, small masks only)."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    ys, xs = np.nonzero(mask)
    for sy, sx in zip(ys.tolist(), xs.tolist()):
        if seen[sy, sx]:
            continue
        stack = [(sy, sx)]
        seen[sy, sx] = True
        y0 = y1 = sy
        x0 = x1 = sx
        n = 0
        while stack:
            y, x = stack.pop()
            n += 1
            y0, y1, x0, x1 = min(y0, y), max(y1, y), min(x0, x), max(x1, x)
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        out.append((y0, x0, y1 + 1, x1 + 1, n))
    return out


def auto_boxes(img: Image.Image) -> list[list[float]]:
    k = 2  # work on a half-size picture (360 rows): fast enough without scipy, still finds the 5 % h pieces
    small = img.resize((max(1, img.width // k), max(1, img.height // k)), Image.BILINEAR)
    a = to_arr(small)
    H, W = a.shape[:2]
    L = luma(a)
    hsv = np.asarray(small.convert("HSV"), dtype=np.float32)
    masks = [_fill_holes(_morph(L < 55, 3, close=True)),
             _morph((hsv[..., 1] > 120) & (hsv[..., 2] > 110), 3, close=False)]
    found = []
    for mask in masks:
        for y0, x0, y1, x1, n in _components(mask):
            h, w = y1 - y0, x1 - x0
            if not (0.05 * H <= h <= 0.32 * H and 0.05 * H <= w <= 0.7 * H):
                continue
            if n / float(h * w) < 0.72:  # HUD plates are near-rectangles; terrain blobs are not
                continue
            cx, cy = x0 + w / 2, y0 + h / 2
            if W * 0.33 < cx < W * 0.67 and H * 0.25 < cy < H * 0.72:
                continue  # the middle box is the world, not HUD
            found.append([float(x0 * k), float(y0 * k), float(w * k), float(h * k)])
    return nms(found)


def iou(a, b) -> float:
    ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw, ih = max(0, min(ax2, bx2) - max(a[0], b[0])), max(0, min(ay2, by2) - max(a[1], b[1]))
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union else 0.0


def nms(boxes):
    keep = []
    for b in sorted(boxes, key=lambda r: -r[2] * r[3]):
        if all(iou(b, k) < 0.4 and not inside(b, k) for k in keep):
            keep.append(b)
    return keep


def inside(a, b) -> bool:
    return a[0] >= b[0] - 2 and a[1] >= b[1] - 2 and a[0] + a[2] <= b[0] + b[2] + 2 and a[1] + a[3] <= b[1] + b[3] + 2


# ---------- matching ----------

def match(ref: list[dict], game: list[dict], limit: float = 18.0):
    pairs, used = [], set()
    cand = []
    for i, r in enumerate(ref):
        for j, g in enumerate(game):
            if r["m"]["col"] != g["m"]["col"]:
                continue
            if r.get("name") and g.get("name") and r["name"] != g["name"]:
                continue
            d = math.dist((r["m"]["edge"], r["m"]["top"], r["m"]["w"] * 0.5, r["m"]["h"]),
                          (g["m"]["edge"], g["m"]["top"], g["m"]["w"] * 0.5, g["m"]["h"]))
            if r.get("name") and r.get("name") == g.get("name"):
                d = -1.0
            cand.append((d, i, j))
    taken_r = set()
    for d, i, j in sorted(cand):
        if i in taken_r or j in used or d > limit:
            continue
        taken_r.add(i)
        used.add(j)
        pairs.append((ref[i], game[j]))
    return pairs, [r for i, r in enumerate(ref) if i not in taken_r], [g for j, g in enumerate(game) if j not in used]


def gap_above(item: dict, items: list[dict]):
    """Vertical gap (% h) to the nearest piece above in the same column that overlaps it sideways."""
    x, y, w, h = item["box"]
    best = None
    for o in items:
        if o is item or o["m"]["col"] != item["m"]["col"]:
            continue
        ox, oy, ow, oh = o["box"]
        if ox < x + w and x < ox + ow and oy + oh <= y + 1:
            g = (y - (oy + oh)) * 100.0 / NORM_H
            best = g if best is None else min(best, g)
    return best


# ---------- pictures ----------

def edges(img: Image.Image) -> Image.Image:
    return img.convert("L").filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 40 else 0)


def tint_edges(e: Image.Image, color) -> Image.Image:
    base = Image.new("RGBA", e.size, color + (0,))
    base.putalpha(e)
    return base


def ruler(img: Image.Image, step_pct: float = 5.0) -> Image.Image:
    """Yellow lines every step_pct % h (crops are at the normalised scale, so 1 % h = NORM_H / 100 px); every 10 % brighter."""
    out = img.convert("RGB").copy()
    d = ImageDraw.Draw(out)
    s = NORM_H / 100.0 * step_pct
    for k in range(int(img.height / s) + 1):
        d.line([(0, k * s), (img.width, k * s)], fill=(255, 255, 0) if k % 2 == 0 else (120, 120, 0), width=1)
    for k in range(int(img.width / s) + 1):
        d.line([(k * s, 0), (k * s, img.height)], fill=(255, 255, 0) if k % 2 == 0 else (120, 120, 0), width=1)
    return out


def zone_rect(col: str, y0: float, y1: float, W: int) -> tuple[int, int, int, int]:
    H = NORM_H
    ew = int(ZONE_EDGE_W * H)
    if col == "left":
        x0, x1 = 0, min(W, ew)
    elif col == "right":
        x0, x1 = max(0, W - ew), W
    else:
        x0, x1 = max(0, int(W / 2 - 0.45 * H)), min(W, int(W / 2 + 0.45 * H))
    return x0, int(y0 * H), x1, int(y1 * H)


def anchored_pair(a: Image.Image, b: Image.Image, col: str) -> tuple[Image.Image, Image.Image]:
    """Pad two crops to one size, aligned at their anchor (left / right edge / centre) and top."""
    W, H = max(a.width, b.width), max(a.height, b.height)
    out = []
    for im in (a, b):
        canvas = Image.new("RGB", (W, H), (20, 20, 20))
        x = 0 if col == "left" else (W - im.width if col == "right" else (W - im.width) // 2)
        canvas.paste(im, (x, 0))
        out.append(canvas)
    return out[0], out[1]


def layer_row(ref_crop: Image.Image, game_crop: Image.Image, col: str, scale: float = 1.0) -> Image.Image:
    r, g = anchored_pair(ref_crop, game_crop, col)
    onion = Image.blend(r, g, 0.5)
    edge = Image.new("RGB", r.size, (0, 0, 0))
    edge.paste(tint_edges(edges(r), (255, 0, 255)), (0, 0), tint_edges(edges(r), (255, 0, 255)))
    edge.paste(tint_edges(edges(g), (0, 255, 255)), (0, 0), tint_edges(edges(g), (0, 255, 255)))
    tiles = [ruler(r), ruler(g), ruler(onion), edge]
    gap = 8
    sheet = Image.new("RGB", (sum(t.width for t in tiles) + gap * 3, r.height), (40, 40, 40))
    x = 0
    for t in tiles:
        sheet.paste(t, (x, 0))
        x += t.width + gap
    if scale != 1.0:
        sheet = sheet.resize((max(1, int(sheet.width * scale)), max(1, int(sheet.height * scale))), Image.LANCZOS)
    return sheet


# ---------- report ----------

FIELDS = (("edge", "edge padding"), ("top", "top"), ("w", "width"), ("h", "height"))


def compare(ref_path: Path, game_path: Path, out: Path, crop_ref=None, crop_game=None, boxes=None, tol: float = 0.8) -> dict:
    ref, rs, roff = load(ref_path, crop_ref)
    game, gs, goff = load(game_path, crop_game)
    out.mkdir(parents=True, exist_ok=True)
    report = {"ref": str(ref_path), "game": str(game_path), "unit": "% of picture height",
              "ref_aspect": round(ref.width / NORM_H, 3), "game_aspect": round(game.width / NORM_H, 3),
              "elements": [], "missing_in_game": [], "extra_in_game": [], "changes": []}

    def named(side: str, scale: float, off, img: Image.Image):
        items = []
        spec = (boxes or {}).get(side, {})
        frac = (boxes or {}).get("unit") == "frac"
        for name, b in spec.items():
            if frac:
                bx = [b[0] * img.width, b[1] * img.height, b[2] * img.width, b[3] * img.height]
            else:
                bx = [(b[0] - off[0]) * scale, (b[1] - off[1]) * scale, b[2] * scale, b[3] * scale]
            items.append({"name": name, "box": bx})
        return items

    sides = {}
    for side, img, sc, off in (("ref", ref, rs, roff), ("game", game, gs, goff)):
        items = named(side, sc, off, img)
        for b in auto_boxes(img):
            if all(iou(b, it["box"]) < 0.3 for it in items):
                items.append({"name": None, "box": b})
        for it in items:
            it["m"] = measure_box(it["box"], img.width)
            it["s"] = box_stats(img, it["box"])
        for it in items:
            it["m"]["gap_above"] = gap_above(it, items)
        sides[side] = items

    pairs, miss, extra = match(sides["ref"], sides["game"])
    auto_n = 0
    for r, g in sorted(pairs, key=lambda p: (p[0]["m"]["col"], p[0]["m"]["top"])):
        name = r.get("name") or g.get("name")
        if not name:
            auto_n += 1
            name = f"{r['m']['row']}-{r['m']['col']}-{auto_n}"
        row = {"name": name, "col": r["m"]["col"], "ref": {**r["m"], **r["s"]}, "game": {**g["m"], **g["s"]}}
        row["delta_e"] = delta_e(r["s"]["fill"], g["s"]["fill"]) if r["s"] and g["s"] else None
        report["elements"].append(row)
        for key, label in FIELDS + (("gap_above", "gap to the piece above"), ("outline_pct", "outline")):
            a, b = r["m"].get(key, r["s"].get(key)), g["m"].get(key, g["s"].get(key))
            if a is None or b is None:
                continue
            if abs(a - b) > (tol if key != "outline_pct" else 0.15):
                report["changes"].append({"name": name, "what": label, "ref": round(a, 2), "game": round(b, 2),
                                          "change": round(a - b, 2), "unit": "% h",
                                          "text": f"{name}: {label} {b:.1f} -> {a:.1f} % h ({a - b:+.1f} % h)"})
        if r["s"] and g["s"]:
            if row["delta_e"] is not None and row["delta_e"] > 10:
                report["changes"].append({"name": name, "what": "fill colour", "ref": r["s"]["fill_hex"], "game": g["s"]["fill_hex"],
                                          "change": round(row["delta_e"], 1), "unit": "ΔE",
                                          "text": f"{name}: fill {g['s']['fill_hex']} -> {r['s']['fill_hex']} (dE {row["delta_e"]:.0f})"})
            if abs(r["s"]["shade"] - g["s"]["shade"]) > 8:
                report["changes"].append({"name": name, "what": "shading (top minus bottom brightness)", "ref": round(r["s"]["shade"], 1),
                                          "game": round(g["s"]["shade"], 1), "change": round(r["s"]["shade"] - g["s"]["shade"], 1), "unit": "luma",
                                          "text": f"{name}: shading {g['s']['shade']:.0f} -> {r['s']['shade']:.0f} (0 = flat; gloss is lighter on top)"})
        sheet = layer_row(ref.crop(tuple(int(v) for v in pad(r["box"], ref))), game.crop(tuple(int(v) for v in pad(g["box"], game))), row["col"], 1.5)
        fname = f"el-{safe(name)}.png"
        sheet.save(out / fname)
        row["picture"] = fname
    report["missing_in_game"] = [{"name": r.get("name"), **r["m"]} for r in miss]
    report["extra_in_game"] = [{"name": g.get("name"), **g["m"]} for g in extra]
    report["changes"].sort(key=lambda c: -abs(c["change"]) if isinstance(c["change"], (int, float)) else 0)

    # layer 1: whole
    h = 480
    a = ref.resize((round(ref.width * h / NORM_H), h))
    b = game.resize((round(game.width * h / NORM_H), h))
    whole = Image.new("RGB", (a.width + b.width + 12, h), (30, 30, 30))
    whole.paste(a, (0, 0))
    whole.paste(b, (a.width + 12, 0))
    draw_boxes(whole, sides["ref"], NORM_H / h, (0, 0), (255, 0, 255))
    draw_boxes(whole, sides["game"], NORM_H / h, (a.width + 12, 0), (0, 255, 255))
    whole.save(out / "1-whole.png")
    # layer 2: zones
    zone_files = []
    for rowname, y0, y1 in ZONE_ROWS:
        for col in ("left", "centre", "right"):
            rz = ref.crop(zone_rect(col, y0, y1, ref.width))
            gz = game.crop(zone_rect(col, y0, y1, game.width))
            f = f"2-zone-{rowname}-{col}.png"
            layer_row(rz, gz, col, 0.75).save(out / f)
            zone_files.append((f"{rowname} {col}", f))
    write_html(out, report, zone_files)
    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def pad(box, img, m: float = 6):
    x, y, w, h = box
    return (max(0, x - m), max(0, y - m), min(img.width, x + w + m), min(img.height, y + h + m))


def safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in name)


def draw_boxes(img: Image.Image, items, div: float, off, color):
    d = ImageDraw.Draw(img)
    for it in items:
        x, y, w, h = [v / div for v in it["box"]]
        d.rectangle([off[0] + x, off[1] + y, off[0] + x + w, off[1] + y + h], outline=color, width=2)


def write_html(out: Path, rep: dict, zones):
    e = html.escape
    rows = "".join(f"<tr><td>{e(c['text'])}</td></tr>" for c in rep["changes"]) or "<tr><td>No difference above the tolerance.</td></tr>"
    def cell(m, s):
        return (f"edge {m['edge']:.1f} · top {m['top']:.1f} · {m['w']:.1f} × {m['h']:.1f}"
                + (f" · gap↑ {m['gap_above']:.1f}" if m.get('gap_above') is not None else "")
                + (f"<br>outline {s.get('outline_px', 0):.0f} px · fill <span class=sw style='background:{s.get('fill_hex', '#000')}'></span>"
                   f"{s.get('fill_hex', '')} · shade {s.get('shade', 0):.0f} · contrast {s.get('contrast', 0):.0f}" if s.get('fill_hex') else ""))
    def de(r):
        return "" if r["delta_e"] is None else f" · ΔE {r['delta_e']:.0f}"
    els = "".join(
        f"<section><h3>{e(r['name'])} ({r['col']})</h3><p><b>ref</b> {cell(r['ref'], r['ref'])}<br><b>game</b> {cell(r['game'], r['game'])}"
        f"{de(r)}</p>"
        f"<img src='{r['picture']}'></section>" for r in rep["elements"])
    miss = "".join(f"<li>{e(str(m.get('name') or ''))} {m['row']} {m['col']}: {m['w']:.1f} × {m['h']:.1f} % h at edge {m['edge']:.1f}, top {m['top']:.1f}</li>"
                   for m in rep["missing_in_game"])
    extra = "".join(f"<li>{e(str(m.get('name') or ''))} {m['row']} {m['col']}: {m['w']:.1f} × {m['h']:.1f} % h at edge {m['edge']:.1f}, top {m['top']:.1f}</li>"
                    for m in rep["extra_in_game"])
    zs = "".join(f"<h3>{e(n)}</h3><img src='{f}'>" for n, f in zones)
    page = f"""<!doctype html><meta charset=utf-8><title>Reference vs game</title>
<style>body{{font:14px system-ui;background:#16181c;color:#e8e8e8;margin:16px}}img{{max-width:100%;display:block;margin:6px 0 18px}}
td{{padding:3px 8px;border-bottom:1px solid #333}}.sw{{display:inline-block;width:12px;height:12px;border:1px solid #fff;margin:0 4px}}
h2{{border-top:1px solid #444;padding-top:12px}}</style>
<h1>Reference vs game</h1><p>Unit: % of picture height (the PhoneHudLayout unit). Ref aspect {rep['ref_aspect']}, game aspect {rep['game_aspect']}.
Left pieces are measured from the left edge, right pieces from the right edge, centre pieces from the centre line.
Layer columns: ref | game | onion 50 % | edges (ref magenta, game cyan); yellow ruler every 5 % h.</p>
<h2>4. Changes to make (largest first)</h2><table>{rows}</table>
<h2>Missing in game</h2><ul>{miss or '<li>none</li>'}</ul><h2>Only in game</h2><ul>{extra or '<li>none</li>'}</ul>
<h2>3. Elements</h2>{els or '<p>No pairs found: add --boxes.</p>'}
<h2>1. Whole</h2><img src='1-whole.png'><h2>2. Zones</h2>{zs}"""
    (out / "report.html").write_text(page, encoding="utf-8")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ref")
    ap.add_argument("game")
    ap.add_argument("--out")
    ap.add_argument("--crop-ref", help="x,y,w,h of the reference picture to use (drop a title bar)")
    ap.add_argument("--crop-game", help="x,y,w,h of the game picture to use (drop Studio's top bar)")
    ap.add_argument("--boxes", help="json with named boxes per side")
    ap.add_argument("--tol", type=float, default=0.8, help="ignore size/position misses up to this many %% h")
    a = ap.parse_args(argv)
    ref, game = Path(a.ref), Path(a.game)
    for p in (ref, game):
        if not p.exists():
            print(f"missing: {p}")
            return 2
    try:
        boxes = json.loads(Path(a.boxes).read_text(encoding="utf-8")) if a.boxes else None
        crop_ref, crop_game = parse_rect(a.crop_ref), parse_rect(a.crop_game)
    except (ValueError, OSError) as err:
        print(f"bad input: {err}")
        return 2
    out = Path(a.out) if a.out else ROOT / "build" / "ref-compare" / game.stem
    rep = compare(ref, game, out, crop_ref, crop_game, boxes, a.tol)
    print(f"{len(rep['elements'])} matched pieces, {len(rep['missing_in_game'])} missing in game, {len(rep['extra_in_game'])} only in game, "
          f"{len(rep['changes'])} changes over tolerance")
    for c in rep["changes"][:25]:
        print("  " + c["text"])
    print(f"report: {out / 'report.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
