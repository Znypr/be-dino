#!/usr/bin/env python3
"""Art batch 1: ONE contact sheet that groups the cut candidates per item, with ids and quality flags.

Usage:
  python tools/art_contact_sheet.py DIR OUT.png --group "Berry=food-berry-*" --group "Fruit=food-fruit-*" ...
         [--flags flags1.json --flags flags2.json] [--tile 190] [--perrow 8]

Every group is a heading plus its tiles (transparent PNGs shown on a mid-dark card colour, so a leftover
light fringe or grey gap shows). Under each id a small line shows the flags from tools/cut_icon_sheet.py
(--json files); every tile also gets a 64 px copy next to it, because icons must read at 64 px
(docs/72, docs/87). Groups with 4 tiles or fewer share a line in pairs. Pillow only.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont

BG = (36, 34, 46)
CARD = (61, 58, 73)
FONT_FILES = ("arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf")


def font(size: int):
    for n in FONT_FILES:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("out")
    ap.add_argument("--group", action="append", required=True, help='"Title=glob", for example "Berry=food-berry-*"')
    ap.add_argument("--flags", action="append", default=[])
    ap.add_argument("--tile", type=int, default=190)
    ap.add_argument("--perrow", type=int, default=8)
    ap.add_argument("--title", default="Art batch 1: candidates")
    a = ap.parse_args(argv)

    flags: Dict[str, List[str]] = {}
    for f in a.flags:
        with open(f, encoding="utf-8") as fh:
            for k, v in json.load(fh).items():
                flags[k] = v["flags"]

    groups: List[Tuple[str, List[str]]] = []
    for g in a.group:
        title, pat = g.split("=", 1)
        names = sorted(n for n in os.listdir(a.dir) if fnmatch.fnmatch(n, pat + ".png" if not pat.endswith(".png") else pat))
        if not names:
            print("no files for", g)
            return 2
        groups.append((title, names))

    T = a.tile
    thumb = 64
    cell_w = T + 14
    cell_h = T + 14 + 72  # tile + id/flag lines and the 64 px copy
    head_h = 34
    pad = 16
    full_w = pad * 2 + cell_w * a.perrow
    # lay groups out in "lines": a line holds up to perrow tiles
    lines: List[List[Tuple[str, List[str]]]] = []
    cur: List[Tuple[str, List[str]]] = []
    used = 0
    for title, names in groups:
        n = len(names)
        if used and used + n <= a.perrow:
            cur.append((title, names))
            used += n
        else:
            if cur:
                lines.append(cur)
            if n > a.perrow:  # split a long group over several lines
                for k in range(0, n, a.perrow):
                    lines.append([(title if k == 0 else title + " (cont.)", names[k:k + a.perrow])])
                cur, used = [], 0
                continue
            cur, used = [(title, names)], n
    if cur:
        lines.append(cur)
    line_h = head_h + cell_h + 10
    top = 56
    out = Image.new("RGB", (full_w, top + line_h * len(lines) + pad), BG)
    d = ImageDraw.Draw(out)
    d.text((pad, 14), a.title, fill=(255, 255, 255), font=font(26))
    fh, fi, fs = font(22), font(15), font(13)
    y = top
    for line in lines:
        x = pad
        for title, names in line:
            d.text((x + 4, y + 4), title, fill=(255, 210, 43), font=fh)
            for i, n in enumerate(names):
                cx = x + i * cell_w
                cy = y + head_h
                d.rounded_rectangle([cx, cy, cx + T + 6, cy + T + 6], radius=10, fill=CARD)
                im = Image.open(os.path.join(a.dir, n)).convert("RGBA")
                big = im.resize((T, T), Image.LANCZOS)
                out.paste(big, (cx + 3, cy + 3), big)
                sm = im.resize((thumb, thumb), Image.LANCZOS)  # 64 px copy: icons must read this small
                d.rounded_rectangle([cx + T - thumb - 2, cy + T + 10, cx + T + 6, cy + T + 14 + thumb], radius=6, fill=CARD)
                out.paste(sm, (cx + T - thumb + 2, cy + T + 12), sm)
                cid = n[:-4]
                short = cid.split("-", 1)[1] if "-" in cid else cid
                fl = flags.get(cid, [])
                d.text((cx + 4, cy + T + 8), cid, fill=(255, 255, 255), font=fi)
                if fl:
                    d.text((cx + 4, cy + T + 25), ",".join(fl), fill=(255, 120, 100), font=fs)
            x += cell_w * len(names)
        y += line_h
    out.save(a.out)
    print("wrote", a.out, out.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
