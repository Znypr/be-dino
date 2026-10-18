#!/usr/bin/env python3
"""BD-1034: put a ruler on a sheet of tiles so the owner can say exactly which tile he means.

Columns get letters (A, B, C ...) along the top, rows get numbers (1, 2, 3 ...) down the left side,
so the tile in column D, row 3 is "D3". The art is never touched: the sheet is pasted unchanged onto
a larger plain margin canvas and the letters and numbers are drawn only in that margin, with thin
light separator ticks in the margin too. The original file is not changed; the result goes to --out.

  python tools/label_grid_sheet.py docs/reference/pattern-tiles-chatgpt-v1-a.png --cols 4 --rows 4
      -> docs/reference/pattern-tiles-chatgpt-v1-a-labelled.png

Cells are the sheet cut into equal parts (--cols x --rows), which is how the sheets are laid out.
Options: --margin PIXELS (default: 8% of the longer side), --out PATH, --bg / --fg colours.
Needs Pillow only. Use `label_sheet(image, cols, rows, margin=None)` from other tools.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

FONT_FILES = ("arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf")


def _font(size: int):
    for name in FONT_FILES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow: fixed small font
        return ImageFont.load_default()


def column_name(i: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA."""
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def tile_id(col: int, row: int) -> str:
    return "%s%d" % (column_name(col), row + 1)


def label_sheet(img: Image.Image, cols: int, rows: int, margin: Optional[int] = None,
                bg: Tuple[int, int, int] = (24, 26, 32), fg: Tuple[int, int, int] = (255, 255, 255),
                line: Tuple[int, int, int] = (110, 116, 130)) -> Image.Image:
    """Return a new image: `img` unchanged in the lower right, ruler in the top and left margin."""
    if cols < 1 or rows < 1:
        raise ValueError("cols and rows must be at least 1")
    img = img.convert("RGB")
    w, h = img.size
    m = margin if margin is not None else max(40, int(max(w, h) * 0.08))
    out = Image.new("RGB", (w + m, h + m), bg)
    out.paste(img, (m, m))
    d = ImageDraw.Draw(out)
    cell_w, cell_h = w / cols, h / rows
    size = max(14, int(min(m * 0.62, min(cell_w, cell_h) * 0.5)))
    font = _font(size)
    for c in range(cols):
        x0 = m + c * cell_w
        label = column_name(c)
        l, t, r, b = d.textbbox((0, 0), label, font=font)
        d.text((x0 + cell_w / 2 - (r - l) / 2 - l, m / 2 - (b - t) / 2 - t), label, fill=fg, font=font)
        d.line([(x0, m - 6), (x0, m - 1)], fill=line, width=1)  # tick in the margin only
    d.line([(m + w, m - 6), (m + w, m - 1)], fill=line, width=1)
    for r_ in range(rows):
        y0 = m + r_ * cell_h
        label = str(r_ + 1)
        l, t, r, b = d.textbbox((0, 0), label, font=font)
        d.text((m / 2 - (r - l) / 2 - l, y0 + cell_h / 2 - (b - t) / 2 - t), label, fill=fg, font=font)
        d.line([(m - 6, y0), (m - 1, y0)], fill=line, width=1)
    d.line([(m - 6, m + h), (m - 1, m + h)], fill=line, width=1)
    return out


def default_out(path: str) -> str:
    base, ext = os.path.splitext(path)
    return base + "-labelled" + (ext or ".png")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--cols", type=int, required=True)
    ap.add_argument("--rows", type=int, required=True)
    ap.add_argument("--margin", type=int, default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    out = a.out or default_out(a.image)
    if os.path.abspath(out) == os.path.abspath(a.image):
        print("refusing to overwrite the original: pick another --out")
        return 2
    res = label_sheet(Image.open(a.image), a.cols, a.rows, a.margin)
    res.save(out)
    print("wrote", out, res.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
