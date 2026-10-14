#!/usr/bin/env python3
"""Be Dino! condition-egg concept boards (BD-103 draft art).

Deterministic (fixed seeds, no clock). Draws the five egg conditions
(Cracked, Dirty, Normal, Rainbow, Astra) in two styles:
  A = sticker-clean (chunky outline, glossy)   B = painterly soft
Usage (repo root):
  PYTHONPATH=<Pillow+numpy site-packages> python tools/design/condition_egg_concepts.py
  ... --out docs/evidence/2026-10-14-condition-eggs
Outputs board-A.png, board-B.png, comparison.png. Concept art only.
"""
import argparse
import math
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SS = 3
NAVY = (20, 32, 53)
CONDS = ["cracked", "dirty", "normal", "rainbow", "astra"]
LABEL = {"cracked": ("Cracked", "Hatches 1 in 5"), "dirty": ("Dirty", "Speed -20%"),
         "normal": ("Normal", "Plain egg"), "rainbow": ("Rainbow", "Speed +20%"),
         "astra": ("Astra", "Speed +80%")}
BASE = {"cracked": (236, 226, 196), "dirty": (240, 230, 200), "normal": (250, 241, 214),
        "rainbow": (252, 244, 226), "astra": (46, 34, 112)}
PATC = {"cracked": (176, 200, 140), "dirty": (150, 210, 150), "normal": (120, 214, 130),
        "rainbow": (120, 214, 130), "astra": (120, 86, 214)}
FONT = "C:/Windows/Fonts/arialbd.ttf"


def font(n):
    try:
        return ImageFont.truetype(FONT, n)
    except OSError:
        return ImageFont.load_default()


def egg_mask(w, h):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    x = (xx - w / 2) / (w * 0.40)
    y = (yy - h * 0.52) / (h * 0.44)
    prof = np.sqrt(np.clip(1 - y ** 2, 0, 1)) * (1 + 0.16 * y)
    return (np.abs(x) < prof), x, y, prof


def noise(w, h, rng, scale):
    n = rng.random((h // scale + 2, w // scale + 2)).astype(np.float32)
    im = Image.fromarray((n * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im, dtype=np.float32) / 255


def blob_mask(w, h, rng, count, cx_rng, cy_rng, rr, blur):
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for _ in range(count):
        cx = rng.uniform(*cx_rng) * w
        cy = rng.uniform(*cy_rng) * h
        r = rng.uniform(*rr) * w
        pts = []
        for k in range(14):
            a = k / 14 * 2 * math.pi
            r2 = r * rng.uniform(0.6, 1.25)
            pts.append((cx + math.cos(a) * r2, cy + math.sin(a) * r2 * 0.8))
        d.polygon(pts, fill=255)
    return im.filter(ImageFilter.GaussianBlur(blur))


def star(d, cx, cy, r, fill, thin=0.22):
    d.polygon([(cx, cy - r), (cx + r * thin, cy - r * thin), (cx + r, cy), (cx + r * thin, cy + r * thin),
               (cx, cy + r), (cx - r * thin, cy + r * thin), (cx - r, cy), (cx - r * thin, cy - r * thin)], fill=fill)


def f32(img):
    return np.asarray(img, dtype=np.float32)


def u8(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def render_egg(cond, style, pattern, size=(300, 380), seed=7):
    """RGBA egg (with glow margin inside canvas), rendered at SS x then downscaled."""
    W, H = size[0] * SS, size[1] * SS
    rng = np.random.default_rng(seed + CONDS.index(cond))
    mask, x, y, prof = egg_mask(W, H)
    A = style == "A"
    nz = np.sqrt(np.clip(1 - (x / np.maximum(prof, 1e-3)) ** 2 * 0.9 - y ** 2 * 0.3, 0.05, 1))
    light = np.clip(0.62 + 0.55 * (-x * 0.45 - y * 0.55 + nz * 0.5), 0, 1.25)
    if A:  # cel shading: 3 bands
        light = np.where(light > 0.95, 1.05, np.where(light > 0.62, 0.86, 0.68))
    col = np.zeros((H, W, 3), np.float32)
    col[:] = BASE[cond]
    if cond == "astra":
        n = noise(W, H, rng, 60) * 0.6 + noise(W, H, rng, 20) * 0.4
        col = col + np.stack([n * 90, n * 30, n * 120], -1)
        col = col + (y[..., None] > 0.2) * np.array([10, 0, 30]) * (y[..., None] - 0.2)
    img = u8(col)
    d = ImageDraw.Draw(img)
    if pattern:
        pr = np.random.default_rng(99)
        for _ in range(11):
            cx, cy = pr.uniform(0.25, 0.75) * W, pr.uniform(0.2, 0.85) * H
            r = pr.uniform(0.035, 0.07) * W
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PATC[cond])
    arr = f32(img)
    if cond == "cracked":  # dull shell
        g = arr.mean(-1, keepdims=True)
        arr = (arr * 0.55 + g * 0.45) * 0.9
    elif cond == "rainbow":
        t = (x * 0.8 + y * 0.6)
        if A:
            band = np.floor((t + 2) * 3.0).astype(int) % 6
            cols = np.array([(255, 90, 100), (255, 170, 60), (255, 230, 70), (90, 220, 110), (80, 180, 255), (180, 110, 255)], np.float32)
            hues = cols[band]
        else:
            t = t * 3.2
            hues = 110 + np.stack([np.sin(t) * .5 + .5, np.sin(t + 2.09) * .5 + .5, np.sin(t + 4.19) * .5 + .5], -1) * 145
        arr = arr * 0.45 + hues * 0.55
    shade = (np.clip(light, 0, 1.3) / 1.3 * 1.3)[..., None]
    arr = arr * (0.75 + 0.25 * shade)
    if not A:  # painterly: brush noise + cool shadow shift
        brush = (noise(W, H, rng, 14) - 0.5) * 26
        arr = arr + brush[..., None] + (1 - np.minimum(shade, 1)) * np.array([-18, -8, 14])
    img = u8(arr)
    em = u8(mask * 255.0).convert("L")
    # --- condition cues
    if cond == "dirty":
        blur = 2 if A else 7
        mm = f32(blob_mask(W, H, rng, 9, (0.2, 0.8), (0.55, 0.92), (0.03, 0.075), blur)) / 255
        mm = np.maximum(mm, f32(blob_mask(W, H, rng, 5, (0.25, 0.75), (0.2, 0.5), (0.018, 0.03), blur)) / 255 * 0.9)
        if A:
            mm = (mm > 0.5).astype(np.float32)
        mudc = np.array([112, 78, 44], np.float32) * (0.85 + 0.3 * noise(W, H, rng, 18)[..., None])
        a = f32(img)
        a = a * (1 - mm[..., None]) + mudc * mm[..., None]
        sp = (noise(W, H, rng, 5) > 0.78).astype(np.float32) * np.clip((y + 0.1) * 1.5, 0, 1) * 0.55
        a = a * (1 - sp[..., None]) + np.array([150, 120, 80]) * sp[..., None]
        img = u8(a)
    if cond == "cracked":
        pts = [(0.52, 0.10), (0.46, 0.20), (0.56, 0.29), (0.47, 0.40), (0.58, 0.50), (0.50, 0.60), (0.57, 0.70)]
        br = [(0.56, 0.29), (0.68, 0.34), (0.74, 0.42)]
        br2 = [(0.47, 0.40), (0.36, 0.46), (0.30, 0.56)]
        cl = Image.new("L", (W, H), 0)
        cd = ImageDraw.Draw(cl)
        for path, wd in ((pts, 11), (br, 8), (br2, 8)):
            cd.line([(px * W, py * H) for px, py in path], fill=255, width=max(2, wd * SS // (1 if A else 2)), joint="curve")
        hl = f32(cl.filter(ImageFilter.GaussianBlur(0 if A else 3)))[..., None] / 255
        edge = f32(cl.filter(ImageFilter.MaxFilter(5 * SS | 1)))[..., None] / 255
        a = f32(img)
        a = a * (1 - edge * 0.35) + np.array([255, 250, 235]) * edge * 0.2
        a = a * (1 - hl) + np.array([52, 36, 30]) * hl
        img = u8(a)
        emd = ImageDraw.Draw(em)
        for (cx, cy, r) in ((0.223, 0.24, 0.06), (0.853, 0.78, 0.07), (0.819, 0.30, 0.045)):
            poly = []
            for k in range(10):
                aa = k / 10 * 2 * math.pi
                rad = r * W * (1.0 if k % 2 else 0.55)
                poly.append((cx * W + math.cos(aa) * rad, cy * H + math.sin(aa) * rad))
            emd.polygon(poly, fill=0)
    # --- highlights
    hl = Image.new("L", (W, H), 0)
    hd = ImageDraw.Draw(hl)
    if A:
        hd.ellipse([0.2 * W, 0.2 * H, 0.38 * W, 0.42 * H], fill=235)
        hd.ellipse([0.4 * W, 0.12 * H, 0.45 * W, 0.17 * H], fill=235)
        hl = hl.filter(ImageFilter.GaussianBlur(1))
    else:
        hd.ellipse([0.2 * W, 0.18 * H, 0.4 * W, 0.44 * H], fill=150)
        hl = hl.filter(ImageFilter.GaussianBlur(14 * SS))
    hs = 0.35 if cond == "cracked" else (0.55 if cond == "dirty" else 1.0)
    hla = f32(hl)[..., None] / 255 * hs
    a = f32(img) * (1 - hla) + 255 * hla
    if cond == "rainbow":
        sl = Image.new("L", (W, H), 0)
        sdd = ImageDraw.Draw(sl)
        for sx, sy, sr in ((0.68, 0.30, 0.07), (0.34, 0.62, 0.05), (0.62, 0.72, 0.04)):
            star(sdd, sx * W, sy * H, sr * W, 255)
        s = f32(sl)[..., None] / 255
        a = a * (1 - s) + 255 * s
    if cond == "astra":
        sl = Image.new("L", (W, H), 0)
        sdd = ImageDraw.Draw(sl)
        sr = np.random.default_rng(5)
        for _ in range(34):
            px, py = sr.uniform(0.2, 0.8) * W, sr.uniform(0.12, 0.9) * H
            r = sr.uniform(0.006, 0.014) * W
            sdd.ellipse([px - r, py - r, px + r, py + r], fill=255)
        for sx, sy, rr in ((0.66, 0.28, 0.075), (0.36, 0.5, 0.06), (0.60, 0.70, 0.05), (0.42, 0.22, 0.04)):
            star(sdd, sx * W, sy * H, rr * W, 255, 0.18)
        s = f32(sl)[..., None] / 255
        glow = f32(sl.filter(ImageFilter.GaussianBlur(7 * SS)))[..., None] / 255
        a = a + glow * np.array([120, 80, 200]) * 0.8
        a = a * (1 - s) + np.array([255, 245, 200]) * s
    img = u8(a).convert("RGBA")
    # --- outline
    ow = max(2, int((9 if A else 3) * SS * size[0] / 300))
    outl = em.filter(ImageFilter.MaxFilter(ow * 2 + 1))
    if not A:
        outl = outl.filter(ImageFilter.GaussianBlur(3 * SS)).point(lambda v: int(v * 0.75))
    ocol = (30, 22, 40) if A else (92, 70, 96)
    if cond == "astra":
        ocol = (15, 10, 45) if A else (50, 36, 110)
    out = Image.new("RGBA", (W, H), ocol + (0,))
    out.putalpha(outl)
    out.paste(img, (0, 0), em)
    gl = {"astra": (150, 110, 255), "rainbow": (255, 220, 120)}.get(cond)
    if gl:
        g = em.filter(ImageFilter.MaxFilter(int(15 * SS * size[0] / 300) | 1)).filter(ImageFilter.GaussianBlur(18 * SS * size[0] / 300))
        g = g.point(lambda v: int(v * (0.85 if cond == "astra" else 0.55)))
        base_l = Image.new("RGBA", (W, H), gl + (0,))
        base_l.putalpha(g)
        base_l.alpha_composite(out)
        out = base_l
    if cond == "astra":
        od = ImageDraw.Draw(out)
        for sx, sy, rr in ((0.12, 0.22, 0.05), (0.9, 0.34, 0.04), (0.86, 0.8, 0.055)):
            star(od, sx * W, sy * H, rr * W, (255, 245, 200, 255), 0.2)
    return out.resize(size, Image.LANCZOS)


def tile_swatch(w, h):
    im = Image.new("RGB", (w * SS, h * SS), (150, 146, 138))
    d = ImageDraw.Draw(im)
    ts = 120 * SS
    rng = np.random.default_rng(3)
    for ty in range(-1, h * SS // ts + 2):
        for tx in range(-1, w * SS // ts + 2):
            v = int(rng.integers(-8, 9))
            d.rounded_rectangle([tx * ts + 4 * SS, ty * ts + 4 * SS, (tx + 1) * ts - 4 * SS, (ty + 1) * ts - 4 * SS], 10 * SS,
                                fill=(176 + v, 170 + v, 158 + v))
    return im.resize((w, h), Image.LANCZOS)


def card(cond, style, pattern, w=300, h=420, eggh=360, label=True):
    c = Image.new("RGBA", (w, h))
    c.paste(tile_swatch(w, h), (0, 0))
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(ov).ellipse([w * 0.18, h * 0.80 - 4, w * 0.82, h * 0.80 + 28], fill=(30, 25, 20, 110))
    c.alpha_composite(ov.filter(ImageFilter.GaussianBlur(5)))
    e = render_egg(cond, style, pattern, (int(eggh * 300 / 380), eggh))
    c.alpha_composite(e, ((w - e.width) // 2, int(h * 0.80 + 8 - e.height * 0.96)))
    if label:
        d = ImageDraw.Draw(c)
        n, s = LABEL[cond]
        d.rounded_rectangle([14, h - 56, w - 14, h - 10], 14, fill=(20, 32, 53, 235))
        d.text((w // 2, h - 42), n, font=font(22), fill=(255, 210, 63), anchor="mm")
        d.text((w // 2, h - 22), s, font=font(15), fill=(255, 255, 255), anchor="mm")
    return c


def board(style, out):
    name = "A  sticker-clean" if style == "A" else "B  painterly soft"
    W, H = 1640, 1330
    b = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(b)
    d.text((30, 16), "Condition eggs - style " + name, font=font(34), fill=(255, 210, 63))
    d.text((30, 60), "Top: plain egg   Middle: with spot pattern   Bottom: 64 px strip + phone shop panel", font=font(18), fill=(190, 205, 230))
    for r, pat in enumerate((False, True)):
        for i, c in enumerate(CONDS):
            b.paste(card(c, style, pat).convert("RGB"), (30 + i * 318, 100 + r * 436))
    y0 = 980
    d.text((30, y0), "64 px legibility (plain / pattern)", font=font(18), fill=(190, 205, 230))
    strip = Image.new("RGB", (5 * 2 * 84 + 20, 84), (176, 170, 158))
    for pi, pat in enumerate((False, True)):
        for i, c in enumerate(CONDS):
            e = render_egg(c, style, pat, (50, 64))
            strip.paste(e, (10 + (pi * 5 + i) * 84 + 8, 10), e)
    b.paste(strip, (30, y0 + 28))
    px, py, pw, ph = 1010, 975, 600, 330
    d.rounded_rectangle([px, py, px + pw, py + ph], 22, fill=(32, 50, 82), outline=(255, 210, 63), width=3)
    d.text((px + 20, py + 8), "Condition Shop (phone size)", font=font(16), fill=(255, 210, 63))
    for i, c in enumerate(CONDS):
        ry = py + 34 + i * 58
        d.rounded_rectangle([px + 14, ry, px + pw - 14, ry + 52], 14, fill=(46, 70, 112))
        e = render_egg(c, style, False, (40, 50))
        b.paste(e, (px + 22, ry + 1), e)
        n, s = LABEL[c]
        d.text((px + 78, ry + 15), n, font=font(20), fill=(255, 255, 255), anchor="lm")
        d.text((px + 78, ry + 37), s, font=font(14), fill=(190, 205, 230), anchor="lm")
        pe = render_egg(c, style, True, (40, 50))
        b.paste(pe, (px + pw - 66, ry + 1), pe)
    b.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/evidence/2026-10-14-condition-eggs")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for s in ("A", "B"):
        board(s, os.path.join(a.out, "board-%s.png" % s))
    sheet = Image.new("RGB", (1580, 940), NAVY)
    d = ImageDraw.Draw(sheet)
    for r, s in enumerate(("A", "B")):
        d.text((10, r * 470 + 6), "Style " + s, font=font(24), fill=(255, 210, 63))
        for i, c in enumerate(CONDS):
            sheet.paste(card(c, s, False, 300, 420, 330).convert("RGB"), (i * 316, r * 470 + 36))
    sheet.save(os.path.join(a.out, "comparison.png"))


if __name__ == "__main__":
    main()
