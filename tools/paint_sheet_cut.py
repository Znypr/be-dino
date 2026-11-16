#!/usr/bin/env python3
"""BD-1212 paint beat (owner picked option B 2026-11-16: ChatGPT cartoon frames): turn a 4 x 2 sprite sheet on chroma green into game layers.

  * cuts the 8 cells (equal grid), keys out the green background (soft edges, despill);
  * splits every frame into tint layers by hue (--layer name:minHue-maxHue, saturated pixels only): each becomes WHITE with its own shading
    kept as brightness, so the game tints it with the egg's real colour (ImageColor3); everything else (egg shell, white highlights) is the
    "egg" layer, drawn as it is;
  * writes 4 x 2 flipbooks of 256 px cells (1024 x 512, RGBA, not palette) per layer, and a preview with three colour pairs.

    python tools/paint_sheet_cut.py build/received/pour-sheet.png build/paint-frames --name pour --layer paint1:5-50
    python tools/paint_sheet_cut.py build/received/spots-sheet.png build/paint-frames --name spots --layer paint1:5-50 --layer paint2:190-250
"""
import argparse
import colorsys
import pathlib

from PIL import Image

CELL = 256


def split(cell: Image.Image, ranges):
    cell = cell.convert("RGB").resize((CELL, CELL), Image.LANCZOS)
    layers = {name: Image.new("RGBA", cell.size) for name in ["egg"] + [r[0] for r in ranges]}
    pix = {k: v.load() for k, v in layers.items()}
    src = cell.load()
    for y in range(CELL):
        for x in range(CELL):
            r, g, b = src[x, y]
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            green = g - max(r, b)
            if green > 60 and .22 < h < .45:
                continue
            a = 255 if green < 20 else max(0, 255 - (green - 20) * 6)
            if green > 0:
                g = max(r, b) + min(green, 10)
            hue = h * 360
            target = "egg"
            if s > .42:
                for name, lo, hi in ranges:
                    if lo <= hue <= hi:
                        target = name
            if target == "egg":
                pix["egg"][x, y] = (r, g, b, a)
            else:
                lum = int(255 * min(1, v * 1.05))
                pix[target][x, y] = (lum, lum, lum, a)
    return layers


def tint(img, rgb):
    out = Image.new("RGBA", img.size)
    src, dst = img.load(), out.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = src[x, y]
            if a:
                dst[x, y] = (r * rgb[0] // 255, g * rgb[1] // 255, b * rgb[2] // 255, a)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet")
    ap.add_argument("out")
    ap.add_argument("--name", default="splash")
    ap.add_argument("--layer", action="append", default=[], help="name:minHue-maxHue")
    a = ap.parse_args()
    ranges = []
    for spec in a.layer or ["paint1:5-50"]:
        name, span = spec.split(":")
        lo, hi = span.split("-")
        ranges.append((name, float(lo), float(hi)))
    sheet = Image.open(a.sheet).convert("RGB")
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cw, ch = sheet.width / 4, sheet.height / 2
    books = {name: Image.new("RGBA", (CELL * 4, CELL * 2)) for name in ["egg"] + [r[0] for r in ranges]}
    for i in range(8):
        cx, cy = i % 4, i // 4
        cell = sheet.crop((round(cx * cw), round(cy * ch), round((cx + 1) * cw), round((cy + 1) * ch)))
        for name, layer in split(cell, ranges).items():
            books[name].paste(layer, (cx * CELL, cy * CELL))
    for name, book in books.items():
        book.save(out / f"{a.name}-{name}.png")
    pairs = [((79, 191, 90), (255, 214, 79)), ((61, 139, 253), (255, 255, 255)), ((186, 104, 200), (79, 195, 247))]
    prev = Image.new("RGBA", (CELL * 4, CELL * 2 * len(pairs)), (40, 52, 70, 255))
    for row, pair in enumerate(pairs):
        layer = Image.new("RGBA", books["egg"].size)
        for k, (name, _, _) in enumerate(ranges):
            layer.alpha_composite(tint(books[name], pair[k % 2]))
        layer.alpha_composite(books["egg"])  # highlights and shell over the tinted paint
        prev.alpha_composite(layer, (0, row * CELL * 2))
    prev.convert("RGB").save(out / f"{a.name}-preview.jpg", quality=85)
    print("wrote", ", ".join(f"{a.name}-{n}.png" for n in books), f"and {a.name}-preview.jpg in", out)


if __name__ == "__main__":
    main()
