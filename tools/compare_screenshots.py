#!/usr/bin/env python3
"""Screenshot diff for UI checks (BD-656, docs/162): what changed between two pictures?

  python tools/compare_screenshots.py before.png after.png
  python tools/compare_screenshots.py before_folder after_folder --out diffs

For every pair it works out:
  * how many pixels changed (a pixel counts when any colour channel differs by more than --threshold),
  * the changed area as a percent of the picture,
  * boxes around each changed spot (nearby specks are joined into one box),
  * a picture saved as  before | after | changed  (changed pixels red, boxes drawn),
  * a plain-words verdict.

Parts that always move (a clock, a spinning icon) go in --ignore X,Y,W,H (repeat it) or in an
--ignore-file json: {"*": [[x,y,w,h]], "menu.png": [[x,y,w,h]]}.

Exit code: 0 = every picture is the same or changed by no more than --max-changed-percent,
1 = something changed too much, a size is different, or a file is missing,
2 = bad usage. Uses Pillow only (already used in tools/).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
except ImportError:   # pragma: no cover
    print("Pillow is missing: python -m pip install Pillow", file=sys.stderr)
    raise SystemExit(2)

DEFAULT_THRESHOLD = 16          # per colour channel, 0 to 255
DEFAULT_MAX_PERCENT = 0.5       # changed area allowed, percent of the picture
CELL = 8                        # pixels per cell when joining nearby changed spots
MERGE_CELLS = 2                 # spots closer than this many cells become one box
MAX_BOXES_SHOWN = 10
RED = (255, 40, 40)
BLUE = (60, 120, 255)
GAP = 10
LABEL_H = 18


def parse_rect(text: str):
    try:
        x, y, w, h = (int(float(p)) for p in text.replace(" ", "").split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' is not X,Y,W,H")
    if w <= 0 or h <= 0:
        raise argparse.ArgumentTypeError(f"'{text}' needs a width and height above 0")
    return (x, y, w, h)


def load_ignore_file(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for name, rects in data.items():
        out[name] = [parse_rect(",".join(str(v) for v in r)) for r in rects]
    return out


def _flat(img: Image.Image) -> Image.Image:
    """RGB copy; see-through pixels are shown over black so they compare the same on both sides."""
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        base = Image.new("RGBA", img.size, (0, 0, 0, 255))
        base.alpha_composite(img)
        return base.convert("RGB")
    return img.convert("RGB")


def _mask_for(rects, size):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for x, y, w, h in rects:
        d.rectangle([x, y, x + w - 1, y + h - 1], fill=255)
    return m


def _regions(mask: Image.Image, min_pixels: int):
    """Join nearby changed pixels into boxes. Returns [(x0, y0, x1, y1, pixels)] biggest first."""
    w, h = mask.size
    gw, gh = max(1, (w + CELL - 1) // CELL), max(1, (h + CELL - 1) // CELL)
    cells = mask.resize((gw, gh), Image.BOX).point(lambda v: 255 if v > 0 else 0)
    size = 2 * MERGE_CELLS + 1
    joined = cells.filter(ImageFilter.MaxFilter(size)) if size > 1 else cells
    px = joined.load()
    seen = [[False] * gw for _ in range(gh)]
    boxes = []
    for sy in range(gh):
        for sx in range(gw):
            if px[sx, sy] == 0 or seen[sy][sx]:
                continue
            stack = [(sx, sy)]
            seen[sy][sx] = True
            minx = maxx = sx
            miny = maxy = sy
            while stack:
                cx, cy = stack.pop()
                minx, maxx, miny, maxy = min(minx, cx), max(maxx, cx), min(miny, cy), max(maxy, cy)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < gw and 0 <= ny < gh and not seen[ny][nx] and px[nx, ny]:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            region = (minx * CELL, miny * CELL, min(w, (maxx + 1) * CELL), min(h, (maxy + 1) * CELL))
            crop = mask.crop(region)
            tight = crop.getbbox()
            if not tight:
                continue
            x0, y0 = region[0] + tight[0], region[1] + tight[1]
            x1, y1 = region[0] + tight[2], region[1] + tight[3]
            count = crop.histogram()[255]
            if count >= min_pixels:
                boxes.append((x0, y0, x1, y1, count))
    boxes.sort(key=lambda b: -b[4])
    return boxes


def compare_images(before: Image.Image, after: Image.Image, threshold=DEFAULT_THRESHOLD, ignore=(), min_pixels=1):
    """Pure comparison. Returns a dict (no files written)."""
    a, b = _flat(before), _flat(after)
    res = {"size_before": a.size, "size_after": b.size, "size_changed": a.size != b.size}
    if a.size != b.size:
        res.update(changed_pixels=None, changed_percent=100.0, regions=[], compared_pixels=None)
        return res
    w, h = a.size
    diff = ImageChops.difference(a, b)
    r, g, bl = diff.split()
    strongest = ImageChops.lighter(ImageChops.lighter(r, g), bl)
    changed = strongest.point(lambda v: 255 if v > threshold else 0)
    ignore_mask = _mask_for(ignore, a.size) if ignore else None
    if ignore_mask is not None:
        changed = ImageChops.subtract(changed, ignore_mask)
    total = w * h
    if ignore_mask is not None:
        total -= ignore_mask.histogram()[255]
    n = changed.histogram()[255]
    pct = (100.0 * n / total) if total > 0 else 0.0
    regions = _regions(changed, min_pixels) if n else []
    res.update(changed_pixels=n, changed_percent=pct, regions=regions, compared_pixels=total,
               _mask=changed, _a=a, _b=b, _ignore=list(ignore))
    return res


def verdict_words(res, max_percent):
    if res["size_changed"]:
        return (f"BAD: the pictures are not the same size ({res['size_before'][0]}x{res['size_before'][1]} before, "
                f"{res['size_after'][0]}x{res['size_after'][1]} after).")
    n, pct, regs = res["changed_pixels"], res["changed_percent"], res["regions"]
    if n == 0:
        return "Same: nothing changed."
    where = ""
    if regs:
        x0, y0, x1, y1, _ = regs[0]
        where = f" Biggest spot: {x1 - x0}x{y1 - y0} at ({x0},{y0})."
    spots = f"{len(regs)} spot" + ("" if len(regs) == 1 else "s")
    if pct <= max_percent:
        return f"Small change, allowed: {pct:.2f}% of the picture changed in {spots}.{where}"
    return f"TOO MUCH CHANGE: {pct:.2f}% of the picture changed in {spots} (allowed {max_percent:g}%).{where}"


def passes(res, max_percent):
    if res["size_changed"]:
        return False
    return res["changed_percent"] <= max_percent


def _label(draw, x, text):
    draw.text((x + 4, 3), text, fill=(235, 235, 235))


def make_diff_picture(res, label_a="before", label_b="after"):
    a, b = res["_a"], res["_b"]
    w, h = a.size
    mask = res["_mask"]
    dim = Image.blend(b, Image.new("RGB", (w, h), (90, 90, 90)), 0.55)
    red = Image.new("RGB", (w, h), RED)
    hi = Image.composite(red, dim, mask)
    d = ImageDraw.Draw(hi)
    for x0, y0, x1, y1, _ in res["regions"][:MAX_BOXES_SHOWN * 3]:
        d.rectangle([x0 - 2, y0 - 2, x1 + 1, y1 + 1], outline=(255, 235, 60), width=2)
    for x, y, rw, rh in res["_ignore"]:
        d.rectangle([x, y, x + rw - 1, y + rh - 1], outline=BLUE, width=2)
    sheet = Image.new("RGB", (w * 3 + GAP * 2, h + LABEL_H), (30, 30, 30))
    for i, im in enumerate((a, b, hi)):
        sheet.paste(im, (i * (w + GAP), LABEL_H))
    dr = ImageDraw.Draw(sheet)
    _label(dr, 0, label_a)
    _label(dr, w + GAP, label_b)
    _label(dr, 2 * (w + GAP), "changed (red), ignored (blue)")
    return sheet


def make_size_picture(before, after):
    a, b = _flat(before), _flat(after)
    h = max(a.height, b.height)
    sheet = Image.new("RGB", (a.width + b.width + GAP, h + LABEL_H), (30, 30, 30))
    sheet.paste(a, (0, LABEL_H))
    sheet.paste(b, (a.width + GAP, LABEL_H))
    dr = ImageDraw.Draw(sheet)
    _label(dr, 0, "before")
    _label(dr, a.width + GAP, "after (different size)")
    return sheet


def compare_files(before: Path, after: Path, out_png, threshold, max_percent, ignore, min_pixels, write_image=True):
    with Image.open(before) as ia, Image.open(after) as ib:
        ia.load()
        ib.load()
        res = compare_images(ia, ib, threshold, ignore, min_pixels)
        res["verdict"] = verdict_words(res, max_percent)
        res["ok"] = passes(res, max_percent)
        if write_image and out_png is not None and (res["size_changed"] or res["changed_pixels"]):
            out_png.parent.mkdir(parents=True, exist_ok=True)
            pic = make_size_picture(ia, ib) if res["size_changed"] else make_diff_picture(res, before.name, after.name)
            pic.save(out_png)
            res["diff_png"] = str(out_png)
    for k in ("_mask", "_a", "_b", "_ignore"):
        res.pop(k, None)
    return res


def _jsonable(res):
    out = dict(res)
    out["regions"] = [list(r) for r in res["regions"]]
    out["size_before"] = list(res["size_before"])
    out["size_after"] = list(res["size_after"])
    return out


def run(args):
    before, after = Path(args.before), Path(args.after)
    ignore_all = list(args.ignore or [])
    per_file = load_ignore_file(Path(args.ignore_file)) if args.ignore_file else {}
    results = {}
    if before.is_dir() != after.is_dir():
        print("Give two files or two folders, not one of each.", file=sys.stderr)
        return 2, results
    if before.is_dir():
        names_b = {p.name.lower(): p.name for p in before.iterdir() if p.suffix.lower() == ".png"}
        names_a = {p.name.lower(): p.name for p in after.iterdir() if p.suffix.lower() == ".png"}
        out_dir = Path(args.out) if args.out else Path("screenshot_diff")
        for key in sorted(set(names_a) | set(names_b)):
            if key not in names_a:
                results[names_b[key]] = {"ok": args.allow_missing, "verdict": "Missing: this picture is in 'before' but not in 'after'."}
                continue
            if key not in names_b:
                results[names_a[key]] = {"ok": args.allow_new, "verdict": "New: this picture is only in 'after'."}
                continue
            name = names_a[key]
            rects = ignore_all + per_file.get("*", []) + per_file.get(name, [])
            png = None if args.no_image else out_dir / f"{Path(name).stem}_diff.png"
            results[name] = compare_files(before / names_b[key], after / name, png, args.threshold, args.max_changed_percent,
                                          rects, args.min_pixels, not args.no_image)
        if not results:
            print("No PNG files found.", file=sys.stderr)
            return 2, results
    else:
        for p in (before, after):
            if not p.is_file():
                print(f"Cannot find {p}", file=sys.stderr)
                return 2, results
        rects = ignore_all + per_file.get("*", []) + per_file.get(after.name, [])
        png = None
        if not args.no_image:
            png = Path(args.out) if args.out else Path(f"{after.stem}_diff.png")
            if png.suffix.lower() != ".png":
                png = png / f"{after.stem}_diff.png"
        results[after.name] = compare_files(before, after, png, args.threshold, args.max_changed_percent, rects,
                                            args.min_pixels, not args.no_image)
    bad = [n for n, r in results.items() if not r["ok"]]
    return (1 if bad else 0), results


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compare two screenshots (or two folders of same-named PNGs).")
    ap.add_argument("before", help="old PNG or folder")
    ap.add_argument("after", help="new PNG or folder")
    ap.add_argument("--out", help="diff PNG (file mode) or folder for diff PNGs (folder mode)")
    ap.add_argument("--no-image", action="store_true", help="do not write diff pictures")
    ap.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD, help="colour difference per channel that counts as changed (default %(default)s)")
    ap.add_argument("--max-changed-percent", type=float, default=DEFAULT_MAX_PERCENT, help="exit 1 above this changed area (default %(default)s)")
    ap.add_argument("--min-pixels", type=int, default=1, help="ignore spots smaller than this many pixels in the list of boxes")
    ap.add_argument("--ignore", action="append", type=parse_rect, metavar="X,Y,W,H", help="rectangle to skip (repeat for more)")
    ap.add_argument("--ignore-file", help="json with ignore rectangles per file name ('*' = all)")
    ap.add_argument("--allow-missing", action="store_true", help="folder mode: a picture missing in 'after' is not an error")
    ap.add_argument("--allow-new", action="store_true", help="folder mode: a picture only in 'after' is not an error")
    ap.add_argument("--json", action="store_true", help="print the result as json")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    code, results = run(args)
    if code == 2:
        return 2
    if args.json:
        print(json.dumps({n: _jsonable(r) if "size_before" in r else r for n, r in results.items()}, indent=1))
    else:
        for name, r in results.items():
            mark = "ok  " if r["ok"] else "FAIL"
            print(f"{mark} {name}: {r['verdict']}")
            for x0, y0, x1, y1, n in (r.get("regions") or [])[:MAX_BOXES_SHOWN]:
                print(f"       spot x={x0} y={y0} w={x1 - x0} h={y1 - y0} ({n} pixels)")
            if r.get("diff_png"):
                print(f"       picture: {r['diff_png']}")
        bad = sum(1 for r in results.values() if not r["ok"])
        print(f"{len(results)} picture(s): {len(results) - bad} fine, {bad} to look at.")
    return code


if __name__ == "__main__":
    sys.exit(main())
