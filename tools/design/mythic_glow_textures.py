#!/usr/bin/env python3
"""Mythic Glow aura/trail textures (BD-087/BD-088 DRAFTS, owner-picked style 2026-10-14).

Deterministic (fixed seeds, no clock, no network). Every texture is WHITE light on a transparent
background: the game tints it per aura/trail with Color3/ColorSequence, so one sheet serves every
colour. Alpha carries the shape; RGB stays white except where a texture needs a hot core.

Usage (repo root, Pillow + numpy):
  python tools/design/mythic_glow_textures.py            # write resources/effects/mythic-glow + review sheet
  python tools/design/mythic_glow_textures.py --check    # verify committed files match the generator

Status: drafts for owner review (docs/72 pipeline: brief, draft, review, final, upload). Nothing is
uploaded and no asset IDs exist until the owner (or the lead through Studio) uploads them.
"""
import argparse
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "resources", "effects", "mythic-glow")
SHEET = os.path.join(ROOT, "docs", "evidence", "2026-10-14-mythic-glow-v2", "texture-sheet.png")
NAVY = (20, 32, 53)
SS = 4  # supersampling for line art


def rune(seed):
    """Same glyph grammar as the concept boards (tools/design/aura_trail_concepts.py)."""
    rng = np.random.RandomState(seed)
    pts = [(x, y) for x in (-1, 0, 1) for y in (-1, 0, 1)]
    segs, cur = [], pts[rng.randint(9)]
    for _ in range(3 + seed % 2):
        nxt = pts[rng.randint(9)]
        if nxt != cur:
            segs.append((cur, nxt))
            cur = nxt
    if seed % 3 == 0:
        segs.append(((0, -1.2), (0, 1.2)))
    return segs


def to_rgba(alpha, core=None):
    """alpha: float array 0..1. core: optional 0..1 'white-hot' mask (kept white, others light grey)."""
    a = np.clip(alpha, 0, 1)
    rgb = np.full(a.shape + (3,), 255.0)
    if core is not None:
        # outer glow slightly dimmer so tinting keeps a white centre and a coloured rim
        rgb *= (0.78 + 0.22 * np.clip(core, 0, 1))[..., None]
    out = np.dstack([rgb, a[..., None] * 255]).round().astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def line_layer(size, draw_fn, blur=0.0):
    """Draw white lines supersampled into an L mask, return float 0..1 array at `size`."""
    w, h = size
    im = Image.new("L", (w * SS, h * SS), 0)
    draw_fn(ImageDraw.Draw(im), SS)
    im = im.resize((w, h), Image.LANCZOS)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im).astype(float) / 255


def glow(mask, radius, gain):
    """Add a soft halo around a line mask."""
    im = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8))
    halo = np.asarray(im.filter(ImageFilter.GaussianBlur(radius))).astype(float) / 255
    return np.clip(mask + halo * gain, 0, 1)


def draw_rune(d, seg, x, y, r, width):
    for (a, b) in seg:
        d.line([(x + a[0] * r, y + a[1] * r), (x + b[0] * r, y + b[1] * r)], 255, int(width))
        for p in (a, b):
            d.ellipse([x + p[0] * r - width / 2, y + p[1] * r - width / 2, x + p[0] * r + width / 2, y + p[1] * r + width / 2], 255)


# ---------------------------------------------------------------- textures
def glow_dot(n=128):
    y, x = np.mgrid[0:n, 0:n] + 0.5
    r = np.hypot(x - n / 2, y - n / 2) / (n / 2)
    a = np.exp(-(r / 0.42) ** 2) * (r < 1)
    core = np.exp(-(r / 0.12) ** 2)
    return to_rgba(np.clip(a + core * 0.4, 0, 1), core)


def sigil(n, rings, runes, seed0, tick_count):
    def fn(d, s):
        c = n * s / 2
        for rr, wd in rings:
            R = rr * c
            d.ellipse([c - R, c - R, c + R, c + R], outline=255, width=int(wd * s))
        R = rings[0][0] * c
        for i in range(tick_count):  # small ticks between outer ring pair
            a = 2 * math.pi * i / tick_count
            r0, r1 = R * 0.9, R * 0.96
            d.line([(c + math.cos(a) * r0, c + math.sin(a) * r0), (c + math.cos(a) * r1, c + math.sin(a) * r1)], 255, int(1.6 * s))
        rr = (rings[0][0] + rings[1][0]) / 2 * c if len(rings) > 1 else R * 0.8
        for i in range(runes):
            a = 2 * math.pi * i / runes - math.pi / 2
            draw_rune(d, rune(seed0 + i), c + math.cos(a) * rr, c + math.sin(a) * rr, n * s * 0.028, 2.2 * s)
    mask = line_layer((n, n), fn)
    return to_rgba(glow(mask, 5, 0.9), mask)


def rune_atlas(n=512, grid=4):
    cell = n // grid

    def fn(d, s):
        for i in range(grid * grid):
            cx = (i % grid + 0.5) * cell * s
            cy = (i // grid + 0.5) * cell * s
            draw_rune(d, rune(i + 1), cx, cy, cell * s * 0.26, 7 * s)
    mask = line_layer((n, n), fn)
    return to_rgba(glow(mask, 7, 1.0), mask)


def ribbon(w=512, h=64, kind="plain"):
    """Trail texture: u along the trail (tiles horizontally), v across the width."""
    u = (np.arange(w) + 0.5) / w
    v = (np.arange(h) + 0.5) / h
    U, V = np.meshgrid(u, v)
    if kind == "plain":
        across = np.exp(-((V - 0.5) / 0.26) ** 2)
        core = np.exp(-((V - 0.5) / 0.07) ** 2)
        shimmer = 0.85 + 0.15 * np.sin(2 * math.pi * 3 * U)
        return to_rgba(np.clip(across * shimmer + core * 0.3, 0, 1), core)
    if kind == "plasma":
        a = np.zeros_like(U)
        core = np.zeros_like(U)
        for k, phase in enumerate((0.0, 0.5)):
            centre = 0.5 + 0.22 * np.sin(2 * math.pi * (2 * U + phase))
            a += np.exp(-((V - centre) / 0.09) ** 2) * (0.9 - 0.15 * k)
            core += np.exp(-((V - centre) / 0.03) ** 2)
        a += 0.25 * np.exp(-((V - 0.5) / 0.3) ** 2)
        return to_rgba(np.clip(a, 0, 1), np.clip(core, 0, 1))
    if kind == "lightning":
        rng = np.random.RandomState(7)
        steps = 24
        ys = 0.5 + (rng.rand(steps + 1) - 0.5) * 0.6
        ys[-1] = ys[0]  # tiles horizontally

        def fn(d, s):
            pts = [(i / steps * w * s, ys[i] * h * s) for i in range(steps + 1)]
            d.line(pts, 255, int(3 * s))
            for j in range(5):  # short forks
                i = 2 + j * 4
                x0, y0 = pts[i]
                d.line([(x0, y0), (x0 + 18 * s, y0 + (rng.rand() - 0.5) * h * 0.7 * s)], 255, int(2 * s))
        mask = line_layer((w, h), fn)
        return to_rgba(glow(mask, 4, 1.2), mask)
    raise ValueError(kind)


def light_pillar(w=512, h=128):
    """Beam texture: u (image x) runs along the beam from the feet (u=0, strongest) to the top."""
    u = (np.arange(w) + 0.5) / w
    v = (np.arange(h) + 0.5) / h
    U, V = np.meshgrid(u, v)
    across = np.exp(-((V - 0.5) / 0.2) ** 2)
    core = np.exp(-((V - 0.5) / 0.05) ** 2)
    along = np.clip((1 - U) / 0.15, 0, 1) * ((1 - U) ** 0.6)  # strongest at the feet, transparent at the top
    streaks = 0.8 + 0.2 * np.sin(2 * math.pi * (V * 6 + U * 2))
    return to_rgba(np.clip((across * streaks + core * 0.5) * along, 0, 1), core * along)


def halo_ring(n=256):
    def fn(d, s):
        c = n * s / 2
        R = n * s * 0.36
        d.ellipse([c - R, c - R, c + R, c + R], outline=255, width=int(4 * s))
        R2 = R * 0.84
        d.ellipse([c - R2, c - R2, c + R2, c + R2], outline=255, width=int(1.5 * s))
        for i in range(9):
            a = 2 * math.pi * i / 9 - math.pi / 2
            rr = R * 1.18
            draw_rune(d, rune(i + 11), c + math.cos(a) * rr, c + math.sin(a) * rr, n * s * 0.035, 2 * s)
    mask = line_layer((n, n), fn)
    return to_rgba(glow(mask, 4, 0.9), mask)


def twinkle(n=512, grid=4):
    """16-frame loop: a four-point star that grows, flares and fades (FlipbookLayout Grid4x4)."""
    cell = n // grid
    alpha = np.zeros((n, n))
    core_all = np.zeros((n, n))
    yy, xx = np.mgrid[0:cell, 0:cell] + 0.5
    dx, dy = (xx - cell / 2) / (cell / 2), (yy - cell / 2) / (cell / 2)
    for f in range(grid * grid):
        t = f / (grid * grid)
        k = math.sin(math.pi * t) ** 1.5  # 0 -> 1 -> 0, seamless loop
        rot = t * math.pi / 2
        c, s = math.cos(rot), math.sin(rot)
        rx, ry = dx * c - dy * s, dx * s + dy * c
        spikes = np.exp(-(np.abs(rx) / 0.05) ** 1.2) * np.exp(-(np.abs(ry) / (0.85 * k + 1e-3)) ** 2)
        spikes += np.exp(-(np.abs(ry) / 0.05) ** 1.2) * np.exp(-(np.abs(rx) / (0.85 * k + 1e-3)) ** 2)
        core = np.exp(-(np.hypot(dx, dy) / (0.14 * k + 1e-3)) ** 2)
        a = np.clip((spikes * 0.9 + core) * k, 0, 1)
        oy, ox = (f // grid) * cell, (f % grid) * cell
        alpha[oy:oy + cell, ox:ox + cell] = a
        core_all[oy:oy + cell, ox:ox + cell] = core * k
    return to_rgba(alpha, core_all)


def textures():
    """name -> (Image, roblox use) ; sizes are powers of two."""
    return {
        "sigil-outer": (sigil(512, [(0.94, 3.0), (0.62, 1.6)], 12, 21, 72), "aura ground sigil, outer ring (Decal on a flat disc, rotates)"),
        "sigil-inner": (sigil(512, [(0.7, 2.6), (0.42, 1.4), (0.12, 1.2)], 8, 41, 48), "aura ground sigil, inner ring (tier 2+, counter-rotates)"),
        "runes": (rune_atlas(), "rune glyph motes (ParticleEmitter, FlipbookLayout Grid4x4, FlipbookMode Random)"),
        "glow-dot": (glow_dot(), "energy motes and head glow (ParticleEmitter)"),
        "ribbon-plain": (ribbon(kind="plain"), "main trail ribbon (Trail.Texture, TextureMode Wrap)"),
        "ribbon-plasma": (ribbon(kind="plasma"), "braided second strand (trail class 3+) and aura comets (Beam)"),
        "ribbon-lightning": (ribbon(kind="lightning"), "Electric Arc strand (trail)"),
        "light-pillar": (light_pillar(), "aura light pillar (Beam, tier 2+)"),
        "halo-ring": (halo_ring(), "halo over the head (BillboardGui ImageLabel, tier 3)"),
        "twinkle": (twinkle(), "sparkle pops (ParticleEmitter, FlipbookLayout Grid4x4, FlipbookMode OneShot)"),
    }


# ---------------------------------------------------------------- review sheet
def tinted(img, rgb):
    a = np.asarray(img).astype(float) / 255
    out = a.copy()
    whiteness = (a[..., :3].mean(axis=2) - 0.78) / 0.22  # 0 at rim, 1 at hot core
    for i in range(3):
        out[..., i] = np.clip(rgb[i] / 255 * (1 - 0.6 * whiteness) + 0.6 * whiteness, 0, 1)
    return Image.fromarray((out * 255).astype(np.uint8), "RGBA")


def additive(bg, fg, gain=1.0):
    b = np.asarray(bg.convert("RGB")).astype(float)
    f = np.asarray(fg).astype(float)
    rgb = f[..., :3] * (f[..., 3:] / 255) * gain
    return Image.fromarray(np.clip(b + rgb, 0, 255).astype(np.uint8))


def sheet(tex):
    from PIL import ImageFont
    cols = [(180, 106, 255), (80, 214, 255), (98, 236, 112), (255, 213, 94), (255, 130, 232)]
    tile = 200
    names = list(tex)
    W = 40 + len(names) * (tile + 16)
    H = 40 + 3 * (tile + 34) + 40
    board = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(board)
    try:
        f = ImageFont.load_default(size=16)
    except TypeError:
        f = ImageFont.load_default()
    d.text((20, 10), "Mythic Glow v2 textures (DRAFT for owner review). Row 1: raw white on navy. Row 2: tinted, additive on navy. Row 3: tinted on grass with navy under-layer.", fill=(255, 210, 63), font=f)
    grass = Image.new("RGB", (tile, tile), (88, 168, 70))
    rng = np.random.RandomState(3)
    g = np.asarray(grass).astype(float) + rng.randint(-14, 14, (tile, tile, 1))
    grass = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8))
    for i, name in enumerate(names):
        img = tex[name][0]
        thumb = img.copy()
        thumb.thumbnail((tile, tile), Image.LANCZOS)
        canvas = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
        canvas.paste(thumb, ((tile - thumb.width) // 2, (tile - thumb.height) // 2))
        x = 20 + i * (tile + 16)
        col = cols[i % len(cols)]
        rows = [
            additive(Image.new("RGB", (tile, tile), NAVY), canvas),
            additive(Image.new("RGB", (tile, tile), NAVY), tinted(canvas, col), 1.1),
        ]
        under = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
        ua = np.asarray(canvas)[..., 3].astype(float)
        ua = np.asarray(Image.fromarray(ua.astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))).astype(float) * 0.55
        under = Image.fromarray(np.dstack([np.full(ua.shape + (3,), NAVY, dtype=float), ua]).astype(np.uint8), "RGBA")
        gb = grass.copy().convert("RGBA")
        gb.alpha_composite(under)
        rows.append(additive(gb.convert("RGB"), tinted(canvas, col), 1.1))
        for r, im in enumerate(rows):
            y = 40 + r * (tile + 34)
            board.paste(im, (x, y))
        d.text((x, 40 + 3 * (tile + 34) - 10), name, fill=(255, 255, 255), font=f)
    return board


def write(out_dir, sheet_path):
    os.makedirs(out_dir, exist_ok=True)
    tex = textures()
    for name, (img, _) in tex.items():
        img.save(os.path.join(out_dir, name + ".png"), optimize=True)
    os.makedirs(os.path.dirname(sheet_path), exist_ok=True)
    sheet(tex).save(sheet_path, optimize=True)
    return tex


def check():
    problems = []
    for name, (img, _) in textures().items():
        path = os.path.join(OUT, name + ".png")
        if not os.path.exists(path):
            problems.append(f"missing {path}")
            continue
        saved = Image.open(path)
        w, h = saved.size
        if saved.mode != "RGBA" or w & (w - 1) or h & (h - 1):
            problems.append(f"{name}: must be RGBA with power-of-two size, got {saved.mode} {w}x{h}")
        a = np.asarray(saved).astype(int)
        b = np.asarray(img).astype(int)
        if a.shape != b.shape or np.abs(a - b).max() > 1:
            problems.append(f"{name}: differs from the generator (run without --check and commit)")
        if a[..., 3].max() < 200 or a[..., 3].mean() > 200:
            problems.append(f"{name}: alpha range looks wrong")
        if os.path.getsize(path) > 600_000:
            problems.append(f"{name}: over 600 KB")
    total = sum(os.path.getsize(os.path.join(OUT, n + ".png")) for n in textures() if os.path.exists(os.path.join(OUT, n + ".png")))
    if total > 3_000_000:
        problems.append(f"style total {total} bytes is over the 3 MB budget (docs/70)")
    if problems:
        print("\n".join(problems))
        return 1
    print(f"Mythic Glow textures OK: {len(textures())} files, {total // 1024} KB, deterministic, RGBA power-of-two")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        sys.exit(check())
    write(OUT, SHEET)
    print("wrote", OUT, "and", SHEET)
