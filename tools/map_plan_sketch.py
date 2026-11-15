#!/usr/bin/env python3
"""Top-down map plan sketch for the world redesign proposal (BD-1208, docs/241). A planning diagram, not game art.

    python tools/map_plan_sketch.py [out.png]
"""
import math
import random
import sys

from PIL import Image, ImageDraw, ImageFont


def font(size):
    for f in ("C:/Windows/Fonts/seguibl.ttf", "C:/Windows/Fonts/arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main(out="docs/evidence/2026-11-15-world/map-plan-v1.png"):
    W = H = 1100
    S = Image.new('RGB', (W, H), (70, 150, 200))
    d = ImageDraw.Draw(S)
    f, fs, fb = font(26), font(18), font(34)
    cx, cy, R = 550, 560, 430
    pol = lambda a, r: (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
    d.polygon([pol(a, R + 28 * math.sin(math.radians(a * 3)) + 18 * math.cos(math.radians(a * 5))) for a in range(0, 360, 4)], fill=(232, 214, 160))
    zones = [("Flower meadow", -60, 30, (168, 214, 96)), ("Broadleaf forest", 30, 110, (92, 160, 70)), ("Pine hill", 110, 180, (74, 128, 92)),
             ("Palm beach", 180, 250, (196, 214, 120)), ("Volcano corner", 250, 300, (150, 110, 90))]
    for name, a0, a1, col in zones:
        d.polygon([(cx, cy)] + [pol(a, R * 0.92) for a in range(a0, a1 + 1, 2)], fill=col)
    d.ellipse((cx - 330, cy - 60, cx - 220, cy + 70), fill=(90, 175, 215))
    random.seed(4)
    for name, a0, a1, col in zones:
        for _ in range(10 if ('forest' in name or 'Pine' in name) else 4):
            x, y = pol(random.uniform(a0 + 6, a1 - 6), random.uniform(170, 360))
            s = random.uniform(14, 26)
            dark = tuple(max(0, c - 45) for c in col)
            for _ in range(5):
                ox, oy = x + random.uniform(-s, s), y + random.uniform(-s, s)
                d.ellipse((ox - 12, oy - 12, ox + 12, oy + 12), fill=dark)
    for a in (-15, 70, 145, 215, 275):
        d.line((cx, cy) + pol(a, 380), fill=(240, 226, 180), width=22)
    d.ellipse((cx - 250, cy - 250, cx + 250, cy + 250), outline=(240, 226, 180), width=16)
    d.ellipse((cx - 90, cy - 90, cx + 90, cy + 90), fill=(240, 226, 180), outline=(60, 50, 40), width=4)
    d.text((cx, cy - 14), "Spawn plaza", font=fs, fill=(40, 30, 20), anchor='mm')
    d.text((cx, cy + 12), "hatchery + shops", font=fs, fill=(40, 30, 20), anchor='mm')
    for n, (x, y), dy in [("Giant tree", pol(70, 300), 32), ("Waterfall", pol(150, 330), 32), ("Lagoon", (cx - 275, cy + 5), 32),
                          ("Volcano", pol(275, 360), 32), ("Fossil arch", pol(-35, 345), -32)]:
        d.regular_polygon((x, y, 20), 5, fill=(255, 210, 60), outline=(40, 30, 20))
        d.text((x, y + dy), n, font=fs, fill=(20, 20, 20), anchor='mm', stroke_width=3, stroke_fill=(255, 255, 255))
    for a in (-15, 70, 145, 215, 275):
        for r in (140, 210, 300):
            x, y = pol(a + 9, r)
            for j in range(4):
                d.ellipse((x - 15 + j * 8, y - 5, x - 5 + j * 8, y + 5), fill=(220, 40, 60) if r < 300 else (255, 170, 40), outline=(40, 20, 20))
    for name, a0, a1, col in zones:
        r = 240 if name != "Palm beach" else 300
        a = (a0 + a1) / 2 + (8 if name == "Flower meadow" else 0)
        d.text(pol(a, r), name, font=f, fill=(255, 255, 255), anchor='mm', stroke_width=5, stroke_fill=(30, 30, 30))
    for i in range(0, W, 55):
        d.line((i, 0, i, H), fill=(225, 240, 250), width=1)
        d.line((0, i, W, i), fill=(225, 240, 250), width=1)
    d.rounded_rectangle((20, 20, 580, 150), radius=14, fill=(255, 247, 227), outline=(30, 30, 30), width=3)
    d.text((36, 30), "Map plan v1 (proposal)", font=fb, fill=(30, 30, 30))
    d.text((36, 76), "sand = paths and the ring road   stars = landmarks", font=fs, fill=(60, 50, 40))
    d.text((36, 102), "red dots = berry patches   orange = rarer food near landmarks", font=fs, fill=(60, 50, 40))
    d.text((36, 126), "grid = WorldLayer cells the food and tree maps use", font=fs, fill=(60, 50, 40))
    S.save(out)
    print(out)


if __name__ == '__main__':
    main(*sys.argv[1:])
