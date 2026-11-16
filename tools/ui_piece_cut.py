#!/usr/bin/env python3
"""BD-1212 reveal art (owner approved the ChatGPT reveal target 2026-11-16): cut a cols x rows sheet of UI pieces on chroma green into separate
transparent PNGs (RGBA, not palette), each trimmed to its content with a small margin and fitted into --max px.

    python tools/ui_piece_cut.py <sheet.png> <out_dir> --names ribbon,plate,new,pedestal [--cols 2 --rows 2 --max 512]
"""
import argparse
import colorsys
import pathlib

from PIL import Image


def key(cell: Image.Image) -> Image.Image:
    cell = cell.convert("RGB")
    out = Image.new("RGBA", cell.size)
    src, dst = cell.load(), out.load()
    for y in range(cell.height):
        for x in range(cell.width):
            r, g, b = src[x, y]
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            green = g - max(r, b)
            if green > 60 and .22 < h < .45:
                continue
            a = 255 if green < 20 else max(0, 255 - (green - 20) * 6)
            if green > 0:
                g = max(r, b) + min(green, 10)
            dst[x, y] = (r, g, b, a)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet")
    ap.add_argument("out")
    ap.add_argument("--names", required=True)
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--rows", type=int, default=2)
    ap.add_argument("--max", type=int, default=512)
    a = ap.parse_args()
    names = a.names.split(",")
    sheet = Image.open(a.sheet)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cw, ch = sheet.width / a.cols, sheet.height / a.rows
    preview = Image.new("RGBA", (a.max * len(names), a.max), (40, 52, 70, 255))
    for i, name in enumerate(names):
        cx, cy = i % a.cols, i // a.cols
        piece = key(sheet.crop((round(cx * cw), round(cy * ch), round((cx + 1) * cw), round((cy + 1) * ch))))
        box = piece.getbbox()
        if box:
            pad = 6
            piece = piece.crop((max(0, box[0] - pad), max(0, box[1] - pad), min(piece.width, box[2] + pad), min(piece.height, box[3] + pad)))
        piece.thumbnail((a.max, a.max), Image.LANCZOS)
        piece.save(out / f"{name}.png")
        preview.alpha_composite(piece, (i * a.max + (a.max - piece.width) // 2, (a.max - piece.height) // 2))
        print(name, piece.size)
    preview.convert("RGB").save(out / "pieces-preview.jpg", quality=85)


if __name__ == "__main__":
    main()
