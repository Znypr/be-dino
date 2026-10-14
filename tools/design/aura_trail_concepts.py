#!/usr/bin/env python3
"""Be Dino! aura / trail concept boards (BD-086 draft art).

Procedural, deterministic (fixed seeds, no clock) renderer for three style
directions. Composites effects onto the real Compy render from
docs/evidence/2026-10-12-bd061-fusion-visuals/v2-compy-base.png.

Usage (from repo root):
  PYTHONPATH=<site-packages with Pillow+numpy> python tools/design/aura_trail_concepts.py
  ... --styles candy mythic --out docs/evidence/2026-10-14-aura-trail-concepts --no-sheet

Outputs: board-<style>.png (1600x1060), comparison-sheet.png.
Concept art only: nothing here is shipped to Roblox.
"""
import argparse
import math
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SS = 3  # supersampling factor for every panel
NAVY = (20, 32, 53)
PANEL = (20, 32, 53)
PANEL_EDGE = (46, 70, 112)
YELLOW = (255, 210, 63)
WHITE = (255, 255, 255)
SPRITE_SRC = "docs/evidence/2026-10-12-bd061-fusion-visuals/v2-compy-base.png"

# ---------------------------------------------------------------- catalog data
RARITY6 = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"]
RARITY_COL = [(170, 188, 210), (98, 236, 112), (80, 214, 255), (190, 120, 255), (255, 201, 60), (255, 130, 232)]


def T(id_, name, old, tier, col, acc, motif, **kw):
    return dict(id=id_, name=name, old=old, tier=tier, color=col, accent=acc, motif=motif, **kw)


TRAILS = [  # colors/names/old rarity are Seen in ProgressionConfig.Trails; tier = proposed 6-class index
    T("white", "Normal White", "Common", 0, (245, 247, 255), (255, 255, 255), "puff"),
    T("fern", "Fern Drift", "Common", 0, (98, 236, 112), (225, 255, 190), "leaf"),
    T("tidal", "Tidal Wake", "Common", 1, (80, 214, 255), (195, 249, 255), "drop"),
    T("ember", "Ember Trail", "Rare", 1, (255, 116, 62), (255, 216, 107), "flame"),
    T("violet", "Violet Pulse", "Rare", 2, (180, 106, 255), (255, 171, 241), "ring"),
    T("electric", "Electric Arc", "Rare", 2, (80, 243, 255), (239, 255, 149), "bolt"),
    T("frost", "Frost Comet", "Rare", 3, (135, 233, 255), (255, 255, 255), "snow"),
    T("solar", "Solar Flare", "Legendary", 3, (255, 213, 94), (255, 245, 204), "sun"),
    T("nova", "Nova Ribbon", "Legendary", 4, (180, 106, 255), (255, 215, 115), "star"),
    T("astra", "Astra", "Legendary", 5, (112, 255, 205), (255, 130, 232), "prism", rainbow=True),
]
TR = {t["id"]: t for t in TRAILS}

AURAS = [  # first three Seen in ProgressionConfig.Auras; the rest are Proposal (names/numbers provisional)
    dict(id="meadow", name="Meadow Glow", rarity="Common", growth=1.15, color=(98, 236, 112), accent=(225, 255, 190), motif="leaf", tier=1, seen=True),
    dict(id="honey", name="Honey Spark", rarity="Common", growth=1.25, color=(255, 205, 60), accent=(255, 245, 190), motif="hex", tier=1, seen=False),
    dict(id="tidal", name="Tidal Halo", rarity="Rare", growth=1.35, color=(80, 214, 255), accent=(195, 249, 255), motif="drop", tier=2, seen=True),
    dict(id="ember", name="Ember Crown", rarity="Rare", growth=1.5, color=(255, 116, 62), accent=(255, 216, 107), motif="flame", tier=2, seen=False),
    dict(id="royal", name="Royal Nova", rarity="Legendary", growth=1.7, color=(180, 106, 255), accent=(255, 215, 115), motif="star", tier=3, seen=True),
    dict(id="prism", name="Prism Dream", rarity="Legendary", growth=1.9, color=(255, 130, 232), accent=(112, 255, 205), motif="heart", tier=3, seen=False, rainbow=True),
]
AU = {a["id"]: a for a in AURAS}


def font(size, black=False):
    for f in (["ariblk.ttf"] if black else []) + ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


# ---------------------------------------------------------------- math helpers
def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


def hsv(h, s=0.6, v=1.0):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (r * 255, g * 255, b * 255)


def scale_c(c, k):
    return tuple(min(255, v * k) for v in c)


def rgba(c, a=255):
    return (int(c[0]), int(c[1]), int(c[2]), int(a))


def smooth(pts, n=2):
    for _ in range(n):
        out = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            out += [(a[0] * .75 + b[0] * .25, a[1] * .75 + b[1] * .25), (a[0] * .25 + b[0] * .75, a[1] * .25 + b[1] * .75)]
        pts = out
    return pts


def star_pts(n, r, ri, rot=0.0):
    pts = []
    for i in range(n * 2):
        a = rot - math.pi / 2 + i * math.pi / n
        rr = r if i % 2 == 0 else r * ri
        pts.append((math.cos(a) * rr, math.sin(a) * rr))
    return pts


def shape(kind, r, rot=0.0):
    """Polygon (centered at 0) for a motif kind."""
    if kind == "leaf":
        up = [((u * 2 - 1) * r * 1.25, -r * .62 * math.sin(math.pi * u) ** .8) for u in np.linspace(0, 1, 9)]
        dn = [((u * 2 - 1) * r * 1.25, r * .62 * math.sin(math.pi * u) ** .8) for u in np.linspace(1, 0, 9)[1:-1]]
        pts = up + dn
        rot -= math.pi / 4
    elif kind == "drop":
        pts = [(0, -1.35 * r)] + [(.78 * r * math.cos(math.radians(a)), .3 * r + .78 * r * math.sin(math.radians(a))) for a in range(-25, 206, 15)]
    elif kind == "flame":
        pts = smooth([(0, -1.5 * r), (.45 * r, -.55 * r), (.8 * r, .2 * r), (.55 * r, .9 * r), (0, 1.15 * r), (-.55 * r, .9 * r), (-.8 * r, .2 * r), (-.35 * r, -.35 * r), (-.25 * r, -.9 * r)], 2)
    elif kind == "bolt":
        pts = [(.25 * r, -1.3 * r), (-.65 * r, .1 * r), (-.05 * r, .1 * r), (-.3 * r, 1.3 * r), (.7 * r, -.3 * r), (.08 * r, -.3 * r)]
    elif kind == "snow":
        pts = star_pts(6, r * 1.15, .38, rot)
        rot = 0
    elif kind == "sun":
        pts = star_pts(8, r * 1.2, .58, rot)
        rot = 0
    elif kind == "star":
        pts = star_pts(5, r * 1.2, .48, rot)
        rot = 0
    elif kind == "spark":
        pts = star_pts(4, r * 1.3, .2, rot)
        rot = 0
    elif kind == "prism":
        pts = [(0, -1.3 * r), (.75 * r, 0), (0, 1.3 * r), (-.75 * r, 0)]
    elif kind == "hex":
        pts = star_pts(6, r * 1.05, 1.0, math.pi / 6)
        rot = 0
    elif kind == "heart":
        pts = [(r * .0625 * 16 * math.sin(a) ** 3, -r * .0625 * (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)) * .95) for a in np.linspace(0, 2 * math.pi, 28, endpoint=False)]
        pts = [(x * .85, y * .85 + r * .1) for x, y in pts]
    else:  # puff / ring / default circle
        pts = [(math.cos(a) * r, math.sin(a) * r) for a in np.linspace(0, 2 * math.pi, 18, endpoint=False)]
    c, s = math.cos(rot), math.sin(rot)
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def rune(seed):
    """Deterministic 3-4 stroke glyph on a 3x3 grid, coords in [-1,1]."""
    rng = np.random.RandomState(seed)
    pts = [(x, y) for x in (-1, 0, 1) for y in (-1, 0, 1)]
    segs, cur = [], pts[rng.randint(9)]
    for _ in range(3 + seed % 2):
        nxt = pts[rng.randint(9)]
        if nxt != cur:
            segs.append((cur, nxt))
            cur = nxt
    segs.append(((0, -1.2), (0, 1.2))) if seed % 3 == 0 else None
    return segs


# ---------------------------------------------------------------- drawing core
class D:
    """ImageDraw wrapper working in 1x panel coordinates."""

    def __init__(self, img):
        self.im, self.d = img, ImageDraw.Draw(img)

    @staticmethod
    def C(c):
        return None if c is None else tuple(int(max(0, min(255, v))) for v in c)

    def P(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def poly(self, pts, fill=None, outline=None, ow=0):
        if len(pts) < 3:
            return
        self.d.polygon(self.P(pts), fill=self.C(fill))
        if outline is not None and ow > 0:
            self.line(list(pts) + [pts[0]], outline, ow)

    def line(self, pts, fill, w, round_caps=True):
        p = self.P(pts)
        wi = max(1, int(round(w * SS)))
        fill = self.C(fill)
        self.d.line(p, fill=fill, width=wi, joint="curve")
        if round_caps and wi > 3:
            for q in (p[0], p[-1]):
                self.d.ellipse([q[0] - wi / 2, q[1] - wi / 2, q[0] + wi / 2, q[1] + wi / 2], fill=fill)

    def circle(self, c, r, fill=None, outline=None, ow=0):
        self.ellipse(c, r, r, fill, outline, ow)

    def ellipse(self, c, rx, ry, fill=None, outline=None, ow=0):
        box = [(c[0] - rx) * SS, (c[1] - ry) * SS, (c[0] + rx) * SS, (c[1] + ry) * SS]
        self.d.ellipse(box, fill=self.C(fill), outline=self.C(outline), width=max(1, int(ow * SS)) if outline else 0)


class Scene:
    def __init__(self, w, h, bg=None):
        self.w, self.h, self.W, self.H = w, h, w * SS, h * SS
        if bg is not None:
            self.buf = np.asarray(bg.convert("RGB").resize((self.W, self.H), Image.BICUBIC), np.float32).copy()
        else:
            self.buf = np.zeros((self.H, self.W, 3), np.float32)

    def paint(self, fn, mode="over", halo=0.0, hgain=0.8, gain=1.0, opacity=1.0, blur=0.0):
        img = Image.new("RGBA" if mode == "over" else "RGB", (self.W, self.H), (0, 0, 0, 0) if mode == "over" else (0, 0, 0))
        fn(D(img))
        if mode == "over":
            if blur:
                img = img.filter(ImageFilter.GaussianBlur(blur * SS))
            arr = np.asarray(img, np.float32) / 255.0
            a = arr[..., 3:4] * opacity
            self.buf = self.buf * (1 - a) + arr[..., :3] * 255 * a
        else:
            arr = np.asarray(img, np.float32) * gain * opacity
            out = arr
            if halo:
                out = arr + np.asarray(img.filter(ImageFilter.GaussianBlur(halo * SS)), np.float32) * hgain * gain * opacity * 2.2
            self.screen(out)

    def screen(self, add, y0=0, y1=None, x0=0, x1=None):
        """Screen blend: keeps hue instead of clipping to white on bright grass."""
        y1 = self.H if y1 is None else y1
        x1 = self.W if x1 is None else x1
        a = np.clip(add / 255.0, 0, .97)
        self.buf[y0:y1, x0:x1] = 255 - (255 - self.buf[y0:y1, x0:x1]) * (1 - a)

    def glow(self, x, y, r, col, k=1.0):
        R = int(r * SS * 2.6)
        x0, y0 = int(x * SS) - R, int(y * SS) - R
        xs0, ys0, xs1, ys1 = max(0, x0), max(0, y0), min(self.W, x0 + 2 * R), min(self.H, y0 + 2 * R)
        if xs1 <= xs0 or ys1 <= ys0:
            return
        yy, xx = np.mgrid[ys0:ys1, xs0:xs1].astype(np.float32)
        d2 = ((xx - x * SS) ** 2 + (yy - y * SS) ** 2) / (r * SS) ** 2
        v = np.exp(-d2 * 1.6)[..., None] * k
        self.screen(v * np.array(col, np.float32), ys0, ys1, xs0, xs1)

    def column(self, cx, gy, w, h, col, k=1.0):
        """Soft vertical light pillar rising from (cx, gy)."""
        x0, x1 = int((cx - w * 2.2) * SS), int((cx + w * 2.2) * SS)
        y0, y1 = int((gy - h) * SS), int(gy * SS)
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(self.W, x1), min(self.H, y1)
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        fx = np.exp(-(((xx - cx * SS) / (w * SS)) ** 2) * 1.4)
        fy = np.clip((gy * SS - yy) / (h * SS), 0, 1)
        fy = (1 - fy) ** 0.8 * np.minimum(1, (gy * SS - yy) / (6 * SS))
        self.screen((fx * fy * k)[..., None] * np.array(col, np.float32), y0, y1, x0, x1)

    def paste_sprite(self, spr, x, y):
        w, h = spr.size
        big = spr.resize((w * SS, h * SS), Image.LANCZOS)
        layer = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        layer.paste(big, (int(x * SS), int(y * SS)))
        arr = np.asarray(layer, np.float32) / 255.0
        a = arr[..., 3:4]
        self.buf = self.buf * (1 - a) + arr[..., :3] * 255 * a

    def result(self):
        img = Image.fromarray(np.clip(self.buf, 0, 255).astype(np.uint8))
        return img.resize((self.w, self.h), Image.LANCZOS)


# ---------------------------------------------------------------- scene assets
_SPRITE = None


def sprite():
    global _SPRITE
    if _SPRITE is None:
        im = Image.open(SPRITE_SRC).convert("RGB")
        a = np.asarray(im).astype(float)
        g, b, r = a[..., 1], a[..., 2], a[..., 0]
        m = (((b > .68 * g) | ((g - r > 34) & (b > .6 * g))) & (b > 62))
        m[:200] = False
        m[520:] = False
        m[:, 478:] = False
        m[:, :80] = False
        M = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
        inv = M.point(lambda v: 255 - v)
        ImageDraw.floodfill(inv, (2, 2), 0, thresh=0)
        M = Image.fromarray(np.maximum(np.asarray(M), np.asarray(inv))).filter(ImageFilter.MedianFilter(5)).filter(ImageFilter.GaussianBlur(.7))
        cut = im.convert("RGBA")
        cut.putalpha(M)
        _SPRITE = cut.crop(cut.getbbox())
    return _SPRITE


def grass_bg(w, h, seed=1):
    rng = np.random.RandomState(seed)
    y = np.linspace(0, 1, h)[:, None, None]
    base = np.array([150, 178, 70], np.float32) * (1 - y) + np.array([128, 158, 58], np.float32) * y
    arr = np.broadcast_to(base, (h, w, 3)).copy()
    noise = Image.fromarray((rng.rand(max(3, h // 70), max(3, w // 70)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    arr += ((np.asarray(noise, np.float32) - 128) / 128 * 10)[..., None] * np.array([.6, 1, .4], np.float32)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for _ in range(int(w * h / 900)):
        x, yy = rng.randint(0, w), rng.randint(0, h)
        s = rng.randint(3, 7)
        col = (112, 146, 50) if rng.rand() < .6 else (170, 198, 84)
        d.polygon([(x - 1.5, yy), (x, yy - s), (x + 1.5, yy)], fill=col)
    for _ in range(int(w * h / 9000)):
        x, yy = rng.randint(0, w), rng.randint(0, h)
        c = [(255, 255, 255), (255, 226, 110), (255, 170, 200)][rng.randint(3)]
        d.ellipse([x - 2, yy - 2, x + 2, yy + 2], fill=c)
    return img


def make_scene(w, h, dh, cx, gy, seed=1, bg=True, tl=1.0):
    S = Scene(w, h, grass_bg(w, h, seed) if bg else None)
    spr = sprite()
    sw = spr.size[0] * dh / spr.size[1]
    geom = dict(cx=cx, gy=gy, dh=dh, dw=sw, x0=cx - sw / 2, y0=gy - dh, sc=dh / 260.0,
                body_y=gy - dh * .52, head_y=gy - dh * .98, origin=(cx - sw * .30, gy - dh * .11), tl=tl,
                spr=spr.resize((max(1, int(sw)), max(1, int(dh))), Image.LANCZOS) if False else spr)
    return S, geom


def draw_shadow(S, g):
    def f(d):
        d.ellipse((g["cx"] - g["dw"] * .02, g["gy"] - g["dh"] * .03), g["dw"] * .42, g["dh"] * .075, fill=(40, 60, 20, 255))
    S.paint(f, "over", opacity=.4, blur=g["dh"] * .03)


def draw_dino(S, g):
    sp = sprite().resize((int(g["dw"]), int(g["dh"])), Image.LANCZOS)
    S.paste_sprite(sp, g["x0"], g["y0"])


def trail_path(g, t, length, amp, waves=1.4, n=90, phase=0.0, drop=0.0):
    ax, ay = g["origin"]
    pts = []
    for i in range(n):
        s = i / (n - 1)
        x = ax - s * length
        y = ay - g["dh"] * .03 + amp * math.sin((s * waves - t + phase) * 2 * math.pi) * (.2 + .8 * s) + drop * s * s
        pts.append((x, y))
    return pts


def normals(path):
    p = np.array(path, np.float32)
    t = np.gradient(p, axis=0)
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-6)
    return np.stack([-t[:, 1], t[:, 0]], 1)  # "up" for leftward travel


def at(path, s):
    i = min(len(path) - 1.001, max(0, s * (len(path) - 1)))
    j = int(i)
    f = i - j
    return (path[j][0] * (1 - f) + path[j + 1][0] * f, path[j][1] * (1 - f) + path[j + 1][1] * f)


def widths(n, w0, power=.6, minw=.6):
    s = np.linspace(0, 1, n)
    return np.maximum(minw, w0 * (1 - s) ** power * np.minimum(1, .4 + s * 14))


def ribbon(d, path, w, colfn, off=0.0, alpha=lambda s: 255):
    N = normals(path)
    P = np.array(path, np.float32)
    n = len(path)
    L = P + N * (w[:, None] / 2 + off)
    R = P - N * (w[:, None] / 2 - off)
    for i in range(n - 1):
        s = i / (n - 1)
        c = rgba(colfn(s), alpha(s))
        d.d.polygon(d.P([tuple(L[i]), tuple(L[i + 1]), tuple(R[i + 1]), tuple(R[i])]), fill=c, outline=c)


def orbit(cx, cy, rx, ry, phi):
    return (cx + rx * math.cos(phi), cy + ry * math.sin(phi))


def frac(x):
    return x - math.floor(x)


def hash01(i, k=0):
    return frac(math.sin(i * 12.9898 + k * 78.233) * 43758.5453)


def col_along(td, s, a=None):
    if td.get("rainbow"):
        return hsv(.45 + s * .65 + (a or 0), .55, 1)
    return lerp(td["color"], td["accent"], s)


# ================================================================ STYLE 1: CANDY POP
def candy_motif(d, kind, x, y, r, col, rot=0.0, alpha=255, ow=2.0):
    ow = max(ow, 1.7)
    if kind == "ring":
        d.circle((x, y), r, None, rgba(NAVY, alpha), ow * 3.2)
        d.circle((x, y), r, None, rgba(col, alpha), ow * 1.6)
        d.circle((x - r * .35, y - r * .35), r * .16, rgba(WHITE, alpha))
        return
    pts = [(px + x, py + y) for px, py in shape(kind, r, rot)]
    d.poly(pts, rgba(col, alpha), rgba(NAVY, alpha), ow)
    d.circle((x - r * .3, y - r * .32), r * .17, rgba(WHITE, int(alpha * .9)))


def candy_trail(S, g, td, t):
    sc, tier = g["sc"], td["tier"]
    n = 90
    path = trail_path(g, t, g["dh"] * g["tl"] * (1.7 + .1 * tier), g["dh"] * .11, 1.3)
    w = widths(n, (78 + 9 * tier) * sc, .42)
    colfn = lambda s: col_along(td, s)
    ow = max(2.6, 3.4 * sc)
    # soft pop glow under the ribbon
    S.paint(lambda d: ribbon(d, path, w * 1.15, lambda s: scale_c(colfn(s), .5)), "add", halo=7 * sc, hgain=.5)
    if tier >= 3:  # braided second ribbon
        p2 = trail_path(g, t, g["dh"] * g["tl"] * (1.7 + .1 * tier), g["dh"] * .11, 1.3, phase=.5, drop=0)
        w2 = widths(n, (50 + 6 * tier) * sc, .5)
        c2 = lambda s: col_along(td, 1 - s)

        def f2(d):
            ribbon(d, p2, w2 + ow * 2, lambda s: NAVY)
            ribbon(d, p2, w2, c2)
        S.paint(f2, "over")

    def main(d):
        ribbon(d, path, w + ow * 2, lambda s: NAVY, alpha=lambda s: 255)
        bands = 5 + tier * 2
        if tier >= 2 or td.get("rainbow"):
            cf = lambda s: lerp(colfn(s), WHITE, .35) if int(s * bands * 1.0 + t * 1) % 2 == 0 else colfn(s)
        else:
            cf = colfn
        ribbon(d, path, w, cf)
        # chunky highlight along the upper edge
        N = normals(path)
        hl = [(path[i][0] + N[i][0] * w[i] * .26, path[i][1] + N[i][1] * w[i] * .26) for i in range(int(n * .75))]
        d.line(hl, rgba(WHITE, 190), 2.4 * sc)
        if tier >= 1:  # polka dots (tier 1) / white motif stamps (tier 2+)
            for j in range(6 + tier * 2):
                s = frac(j / (6 + tier * 2) + t) * .9
                x, y = at(path, s)
                ww = w[int(s * (n - 1))]
                if tier >= 2:
                    d.poly([(x + px, y + py + sc) for px, py in shape(td["motif"], ww * .24, 0)], rgba(WHITE, 215), rgba(lerp(td["color"], NAVY, .35), 200), 1.4 * sc)
                else:
                    d.circle((x, y + 1 * sc), max(1.2, ww * .13), rgba(WHITE, 170))
    S.paint(main, "over")

    def motifs(d):
        m = 4 + tier * 2
        for j in range(m):
            s = frac(j / m + t) * .92
            x, y = at(path, s)
            rr = (11 + 1.6 * tier) * sc * math.sin(math.pi * min(1, s * 1.05)) ** .6
            side = -1 if j % 2 else 1
            y += side * (w[int(s * (n - 1))] * .55 + 7 * sc) + math.sin((t + j * .37) * 2 * math.pi) * 3 * sc
            x += math.cos((t + j * .21) * 2 * math.pi) * 3 * sc
            col = lerp(td["color"], td["accent"], (j % 3) / 2.0)
            if td.get("rainbow"):
                col = hsv(.5 + j * .13)
            candy_motif(d, td["motif"], x, y, rr, col, rot=math.sin((t + j * .13) * 6.28) * .5, alpha=int(255 * (1 - s ** 3)))
    S.paint(motifs, "over")

    def pops(d):
        for j in range(2 + tier):
            ph = frac(t + j * .31)
            x, y = at(path, .04 + .08 * j)
            r = (5 + 5 * math.sin(math.pi * ph)) * sc
            d.poly([(x + px + (j - 1) * 6 * sc, y + py - 9 * sc * (j % 2)) for px, py in shape("spark", r)], rgba(WHITE), None, 0)
    S.paint(pops, "add", halo=3 * sc)


def candy_ring_pts(g, rx, ry, cy, k=64):
    return [orbit(g["cx"], cy, rx, ry, 2 * math.pi * i / k) for i in range(k + 1)]


def candy_aura(S, g, ad, t, part):
    sc, tier, dh = g["sc"], ad["tier"], g["dh"]
    col, acc = ad["color"], ad["accent"]
    if ad.get("rainbow"):
        col, acc = (255, 130, 232), (112, 255, 205)
    gy = g["gy"] - dh * .03
    rx, ry = dh * (.78 + .06 * tier), dh * (.16 + .02 * tier)

    def ring(d, front_only):
        k = 72
        for rr, scl, wd in [(1, 1, 20 * sc)] + ([(.68, .68, 12 * sc)] if tier >= 2 else []):
            for i in range(k):
                a0, a1 = 2 * math.pi * i / k, 2 * math.pi * (i + 1.15) / k
                if front_only and math.sin((a0 + a1) / 2) < 0:
                    continue
                seg = [orbit(g["cx"], gy, rx * rr, ry * rr, a0 + (a1 - a0) * u) for u in (0, .5, 1)]
                d.line(seg, rgba(NAVY), wd + 3.6 * sc, round_caps=False)
        for rr, scl, wd in [(1, 1, 20 * sc)] + ([(.68, .68, 12 * sc)] if tier >= 2 else []):
            for i in range(k):
                a0, a1 = 2 * math.pi * i / k, 2 * math.pi * (i + 1.15) / k
                if front_only and math.sin((a0 + a1) / 2) < 0:
                    continue
                c = col if int(i / 4 + t * 2) % 2 == 0 else acc
                seg = [orbit(g["cx"], gy, rx * rr, ry * rr, a0 + (a1 - a0) * u) for u in (0, .5, 1)]
                d.line(seg, rgba(c), wd, round_caps=False)
        # glossy highlight on the far rim
        if not front_only:
            d.line([orbit(g["cx"], gy - 3 * sc, rx, ry, a) for a in np.linspace(math.pi * 1.1, math.pi * 1.7, 14)], rgba(WHITE, 170), 2.4 * sc)

    if part == "back":
        S.paint(lambda d: d.ellipse((g["cx"], gy), rx, ry, rgba(lerp(col, WHITE, .4))), "over", opacity=.35)
        if tier >= 3:  # candy rainbow arcs
            def arcs(d):
                for i, c in enumerate([col, acc, lerp(col, WHITE, .6)]):
                    r = dh * (.98 - .15 * i)
                    pts = [orbit(g["cx"], g["gy"] - dh * .28, r * 1.05, r * .9, math.pi + a * math.pi) for a in np.linspace(0, 1, 40)]
                    d.line(pts, rgba(NAVY), 20 * sc + 3.6 * sc)
                for i, c in enumerate([col, acc, lerp(col, WHITE, .6)]):
                    r = dh * (.98 - .15 * i)
                    pts = [orbit(g["cx"], g["gy"] - dh * .28, r * 1.05, r * .9, math.pi + a * math.pi) for a in np.linspace(0, 1, 40)]
                    d.line(pts, rgba(c), 20 * sc)
            S.paint(arcs, "over", opacity=.95)
        S.paint(lambda d: ring(d, False), "over")
    else:
        S.paint(lambda d: ring(d, True), "over")

    # rising bubbles, split by depth
    N = 7 + 3 * tier

    def bubbles(d):
        for j in range(N):
            th = j * 2.399963
            u = frac(j / N + t)
            rb = (.5 + .4 * hash01(j, 1)) * dh * (1.0 + .05 * tier)
            x = g["cx"] + math.cos(th) * rb + math.sin((u + j * .13) * 6.283) * 5 * sc
            y = gy - u * dh * 1.12
            front = math.sin(th) > 0
            if (part == "front") != front:
                continue
            r = (9 + 9 * hash01(j, 2)) * sc * min(1, math.sin(math.pi * u) * 2)
            if r < 1:
                continue
            a = int(255 * min(1, math.sin(math.pi * u) * 1.6))
            d.circle((x, y), r, rgba(lerp(col, WHITE, .35), int(a * .45)), rgba(WHITE, int(a * .95)), 2 * sc)
            d.circle((x - r * .35, y - r * .38), r * .25, rgba(WHITE, a))
            d.circle((x + r * .3, y + r * .4), r * .1, rgba(WHITE, int(a * .7)))
    S.paint(bubbles, "over")

    if part == "front":
        if tier >= 2:  # chunky orbiting candy ribbon loop
            def loop(d):
                k = 80
                cy = g["body_y"]
                for pass_ in (0, 1):
                    for i in range(k):
                        a0 = 2 * math.pi * i / k + t * 2 * math.pi
                        a1 = a0 + 2 * math.pi * 1.2 / k
                        if math.sin((a0 + a1) / 2) < 0:
                            continue
                        seg = [orbit(g["cx"], cy, dh * 1.0, dh * .26, a0 + (a1 - a0) * u) for u in (0, .5, 1)]
                        c = NAVY if pass_ == 0 else (col if int(i / 5) % 2 == 0 else acc)
                        d.line(seg, rgba(c), (14 + (3.6 if pass_ == 0 else 0)) * sc, round_caps=False)
            S.paint(loop, "over")
        if tier >= 3:  # floating star crown
            def crown(d):
                for j in range(5):
                    a = math.radians(-150 + j * 30)
                    x = g["cx"] + g["dw"] * .22 + math.cos(a) * dh * .5
                    y = g["head_y"] + dh * .16 + math.sin(a) * dh * .22 + math.sin((t + j * .2) * 6.283) * 3 * sc
                    candy_motif(d, "star", x, y, (9 - abs(j - 2) * 1.2) * sc, (255, 220, 70) if not ad.get("rainbow") else hsv(j / 5), rot=math.sin((t + j * .2) * 6.283) * .25)
            S.paint(crown, "over")

        def floaters(d):
            N2 = 3 + 2 * tier
            for j in range(N2):
                u = frac(j / N2 + t * 1.0 + .13)
                x = g["cx"] + (-1 + 2 * hash01(j, 21)) * g["dw"] * .62 + math.sin((u * 2 + j * .3) * 3.14) * 7 * sc
                y = gy - dh * .05 - u * dh * 1.05
                r = (10 + 3 * tier) * sc * min(1, math.sin(math.pi * u) * 2.2)
                if r < 1:
                    continue
                c = hsv(hash01(j, 22), .55) if ad.get("rainbow") else (col if j % 2 else acc)
                candy_motif(d, ad["motif"], x, y, r, c, math.sin((u + j * .2) * 6.28) * .5, int(255 * min(1, math.sin(math.pi * u) * 2)))
        S.paint(floaters, "over")

        def pops(d):
            for j in range(4 + 2 * tier):
                ph = frac(t + hash01(j, 5))
                x = g["cx"] + (hash01(j, 3) - .5) * g["dw"] * 1.5
                y = gy - hash01(j, 4) * dh * 1.1
                r = (4 + 6 * math.sin(math.pi * ph) ** 2) * sc
                d.poly([(x + px, y + py) for px, py in shape("spark", r)], (255, 255, 255))
        S.paint(pops, "add", halo=3 * sc)


# ================================================================ STYLE 2: MYTHIC GLOW
def rune_draw(d, seg, x, y, r, col, w):
    for (a, b) in seg:
        d.line([(x + a[0] * r, y + a[1] * r), (x + b[0] * r, y + b[1] * r)], col, w)


def mythic_trail(S, g, td, t):
    sc, tier = g["sc"], td["tier"]
    n = 90
    L = g["dh"] * g["tl"] * (1.8 + .1 * tier)
    layers = 2 + (tier + 1) // 2
    col, acc = td["color"], td["accent"]
    base = trail_path(g, t, L, g["dh"] * .09, 1.25)
    # dark legibility underlay so additive glow reads on bright grass
    S.paint(lambda d: ribbon(d, base, widths(n, (92 + 6 * tier) * sc, .5), lambda s: NAVY, alpha=lambda s: 130 * (1 - s) ** .7), "over", blur=6 * sc)
    for k in range(layers):
        amp = g["dh"] * (.08 + .07 * k)
        p = trail_path(g, t, L * (1 - .05 * k), amp, 1.2 + .45 * k, phase=k * .37 + (.2 if k % 2 else 0))
        if td["id"] == "electric":
            rng = np.random.RandomState(int(t * 8) * 7 + k)
            p = [(x + (rng.rand() - .5) * 9 * sc * min(1, i / 8), y + (rng.rand() - .5) * 9 * sc * min(1, i / 8)) for i, (x, y) in enumerate(p)]
        wk = widths(n, (50 - 9 * k + 5 * tier) * sc, .7) * np.minimum(1, .12 + np.linspace(0, 1, n) * 7)
        inten = lambda s, k=k: (1 - s) ** .85 * (.85 - .12 * k)

        def wide(d, p=p, wk=wk, inten=inten):
            ribbon(d, p, wk, lambda s: scale_c(col_along(td, s), inten(s) * 1.25))
        S.paint(wide, "add", halo=6 * sc, hgain=.3, gain=.85)

        def core(d, p=p, wk=wk, inten=inten):
            ribbon(d, p, wk * .34, lambda s: scale_c(lerp(col_along(td, s), WHITE, .25), min(1.0, inten(s) * 1.3)))
        S.paint(core, "add", halo=2 * sc, hgain=.25, gain=.7)
    # drifting energy motes and streaks
    def motes(d):
        m = 22 + tier * 8
        for j in range(m):
            s = frac(hash01(j, 1) + t) * .95
            x, y = at(base, s)
            y += (hash01(j, 2) - .5) * 30 * sc * (.3 + s) + math.sin((t + hash01(j, 3)) * 6.283) * 3 * sc
            r = (1 + 2.2 * hash01(j, 4)) * sc * (1 - s)
            c = scale_c(col_along(td, hash01(j, 5)), 1.0 * (1 - s))
            d.circle((x, y), r, c)
            if j % 4 == 0:
                d.line([(x, y), (x + 14 * sc * (1 - s), y)], scale_c(c, .6), max(.8, r * .8))
    S.paint(motes, "add", halo=2.5 * sc)

    if tier >= 2:  # glyphs fading in and out along the ribbon
        def runes(d):
            for j in range(3 + tier):
                s = frac(j / (3 + tier) + t) * .9
                x, y = at(base, s)
                y -= 20 * sc
                a = math.sin(math.pi * s) ** 1.5
                rune_draw(d, rune(j + 3), x, y, 6.5 * sc, scale_c(lerp(td["accent"], WHITE, .3), a * 1.0), 1.6 * sc)
        S.paint(runes, "add", halo=2.5 * sc)
    if tier >= 3:  # motif sigils and comet head
        def sig(d):
            for j in range(2 + tier - 3):
                s = frac(j * .4 + t) * .85
                x, y = at(base, s)
                y += 22 * sc * (1 if j % 2 else -1)
                pts = [(px + x, py + y) for px, py in shape(td["motif"], 7 * sc, t * 3)]
                d.poly(pts, scale_c(col_along(td, .5), .35 * (1 - s)), scale_c(WHITE, .8 * (1 - s)), 1.4 * sc)
        S.paint(sig, "add", halo=3 * sc)
        S.glow(base[0][0], base[0][1], 16 * sc, lerp(td["color"], WHITE, .4), .9)


def mythic_aura(S, g, ad, t, part):
    sc, tier, dh = g["sc"], ad["tier"], g["dh"]
    col, acc = ad["color"], ad["accent"]
    gy = g["gy"] - dh * .03
    rx, ry = dh * (.82 + .06 * tier), dh * (.17 + .02 * tier)
    cx = g["cx"]

    def cc(s):  # color along aura palette
        return hsv(.0 + s * .9, .55, 1) if ad.get("rainbow") else lerp(col, acc, s)

    if part == "back":
        S.paint(lambda d: d.ellipse((cx, gy), rx * 1.18, ry * 1.18, rgba(NAVY, 255)), "over", opacity=.42, blur=6 * sc)
        S.paint(lambda d: d.ellipse((cx, gy), rx * .95, ry * .95, scale_c(col, .5)), "add", halo=14 * sc, hgain=.6, opacity=.4 + .08 * math.sin(t * 6.283))
        if tier >= 2:
            S.column(cx, gy, rx * .5, dh * 1.5, scale_c(lerp(col, WHITE, .3), 1), .55 + .12 * math.sin(t * 6.283))
        if tier >= 3:
            S.column(cx - rx * .6, gy, rx * .16, dh * 1.1, scale_c(acc, 1), .4)
            S.column(cx + rx * .6, gy, rx * .16, dh * 1.1, scale_c(acc, 1), .4)

    def sigil(d, front_only):
        rings = [(1.0, 2.4)] + ([(.72, 1.6)] if tier >= 2 else []) + ([(1.22, 1.2)] if tier >= 3 else [])
        for rr, wd in rings:
            for i in range(96):
                a0, a1 = 2 * math.pi * i / 96, 2 * math.pi * (i + 1.2) / 96
                if front_only != (math.sin((a0 + a1) / 2) > 0):
                    continue
                d.line([orbit(cx, gy, rx * rr, ry * rr, a0), orbit(cx, gy, rx * rr, ry * rr, a1)], scale_c(cc(i / 96), .95), wd * sc, round_caps=False)
        gl = 8 + 2 * tier
        for i in range(gl):
            a = 2 * math.pi * (i + t) / gl
            if front_only != (math.sin(a) > 0):
                continue
            x, y = orbit(cx, gy, rx * 1.1, ry * 1.1, a)
            rune_draw(d, rune(i + 1), x, y, 6 * sc * (1 + .2 * math.sin(a)), scale_c(lerp(acc, WHITE, .3), .95), 1.5 * sc)

    S.paint(lambda d: sigil(d, part == "front"), "add", halo=3 * sc, hgain=.6)

    def comets(d, front_only):
        ncom = 2 + (tier >= 2) + (tier >= 3)
        for j in range(ncom):
            head = 2 * math.pi * (t * (1 if j % 2 == 0 else -1) + j / ncom)
            sgn = 1 if j % 2 == 0 else -1
            pts, vals = [], []
            for i in range(30):
                u = i / 29
                ph = head - sgn * u * 1.8
                pts.append(orbit(cx, g["body_y"] + dh * (.08 * (j - 1)), dh * (1.0 + .08 * j), dh * (.27 + .03 * j), ph))
                vals.append((1 - u) ** 1.4)
            for i in range(29):
                front = math.sin(math.atan2(pts[i][1] - (g["body_y"] + dh * .08 * (j - 1)), pts[i][0] - cx)) > 0
                if front != front_only:
                    continue
                c = scale_c(lerp(cc(j / 3), WHITE, vals[i] * .6), vals[i] * 1.1)
                d.line([pts[i], pts[i + 1]], c, (1.5 + 6.5 * vals[i]) * sc, round_caps=False)
    S.paint(lambda d: comets(d, part == "front"), "add", halo=4 * sc, hgain=.6)

    if part == "front":
        def floaters(d):
            for j in range(7 + 3 * tier):
                u = frac(j / (7 + 3 * tier) + t)
                x = cx + (hash01(j, 7) - .5) * g["dw"] * 1.6
                y = gy - u * dh * 1.2
                a = math.sin(math.pi * u) ** 1.2
                if j % 3 == 0 and tier >= 2:
                    rune_draw(d, rune(j + 5), x, y, 5.5 * sc, scale_c(lerp(acc, WHITE, .4), a), 1.4 * sc)
                else:
                    d.circle((x, y), (1.2 + 1.8 * hash01(j, 8)) * sc, scale_c(lerp(col, WHITE, .5), a))
        S.paint(floaters, "add", halo=2.5 * sc)
        if tier >= 3:  # halo ring over the head
            hx, hy = g["cx"] + g["dw"] * .2, g["head_y"] - dh * .02

            def halo(d):
                for i in range(80):
                    a0, a1 = 2 * math.pi * i / 80, 2 * math.pi * (i + 1.2) / 80
                    d.line([orbit(hx, hy, dh * .36, dh * .09, a0), orbit(hx, hy, dh * .36, dh * .09, a1)], scale_c(lerp(acc, WHITE, .4), .95), 2.6 * sc, round_caps=False)
                for i in range(9):
                    a = 2 * math.pi * (i + t) / 9
                    x, y = orbit(hx, hy, dh * .36, dh * .09, a)
                    rune_draw(d, rune(i + 11), x, y - 5 * sc, 4 * sc, scale_c(acc, .9), 1.2 * sc)
            S.paint(halo, "add", halo=4 * sc)
            S.glow(hx, hy, dh * .3, scale_c(acc, 1), .1)


# ================================================================ STYLE 3: STORYBOOK INK
INK = NAVY
PAPER = (255, 248, 226)


def ink_motif(d, kind, x, y, r, col, rot=0.0, alpha=255, ow=2.4, wob=0):
    ow = max(ow, 2.0)
    rng = np.random.RandomState(int(abs(x * 7 + y * 13)) % 9999 + wob)
    if kind == "ring":
        d.circle((x, y), r, rgba(PAPER, alpha), rgba(INK, alpha), ow)
        d.circle((x, y), r * .5, rgba(col, alpha), rgba(INK, alpha), ow * .8)
        return
    pts = [(px + x + (rng.rand() - .5) * r * .08, py + y + (rng.rand() - .5) * r * .08) for px, py in shape(kind, r, rot)]
    d.poly(pts, rgba(col, alpha), rgba(INK, alpha), ow)
    if kind == "leaf":
        c, s = math.cos(rot - math.pi / 4), math.sin(rot - math.pi / 4)
        d.line([(x - c * r, y - s * r), (x + c * r, y + s * r)], rgba(INK, alpha), ow * .6)
    elif kind in ("star", "sun", "snow", "prism", "spark"):
        d.circle((x, y), r * .22, rgba(PAPER, alpha))


def ink_trail(S, g, td, t):
    sc, tier = g["sc"], td["tier"]
    n = 90
    L = g["dh"] * g["tl"] * (1.7 + .1 * tier)
    path = trail_path(g, t, L, g["dh"] * .10, 1.2)
    w = widths(n, (72 + 8 * tier) * sc, .42)
    col, acc = td["color"], td["accent"]
    ow = max(2.6, 3 * sc)
    cf = lambda s: col_along(td, s * .4)

    def shadow(d):  # hard offset paper-cut shadow
        sp = [(x + 4 * sc, y + 5 * sc) for x, y in path]
        ribbon(d, sp, w + ow * 2, lambda s: (30, 50, 20))
    S.paint(shadow, "over", opacity=.28)

    def main(d):
        ribbon(d, path, w + ow * 2, lambda s: INK)
        bands = 8 + tier
        ribbon(d, path, w, lambda s: cf(s) if int(s * bands * 1.4 + t * 2) % 2 == 0 else lerp(cf(s), PAPER if tier < 3 else acc, .55 if tier < 3 else .8))
        # dashed centre stitch
        for i in range(0, n - 4, 6):
            j = (i + int(t * 12)) % (n - 4)
            d.line([path[j], path[min(n - 1, j + 3)]], rgba(PAPER, 230), 1.5 * sc, round_caps=False)
    S.paint(main, "over")

    def confetti(d):
        m = 6 + 3 * tier
        for j in range(m):
            s = frac(j / m + t) * .93
            x, y = at(path, s)
            side = -1 if j % 2 else 1
            y += side * (w[int(s * (n - 1))] * .6 + 6 * sc + 9 * sc * hash01(j, 2)) + math.sin((t + j * .3) * 6.283) * 4 * sc
            r = (13 + 1.6 * tier) * sc * math.sin(math.pi * min(1, s * 1.1)) ** .5
            a = int(255 * (1 - s ** 3))
            if j % 3 == 2:  # rotated paper bits
                ang = (t + j * .2) * 6.283
                cc_, ss_ = math.cos(ang), math.sin(ang)
                d.poly([(x + (px * cc_ - py * ss_), y + (px * ss_ + py * cc_)) for px, py in [(-r * .9, -r * .45), (r * .9, -r * .45), (r * .9, r * .45), (-r * .9, r * .45)]],
                       rgba(lerp(col, acc, .5) if not td.get("rainbow") else hsv(j * .17), a), rgba(INK, a), 2 * sc)
            else:
                ink_motif(d, td["motif"], x, y, r, lerp(col, acc, (j % 3) / 3) if not td.get("rainbow") else hsv(j * .15), math.sin((t + j * .1) * 6.28) * .6, a, 2 * sc, j)
    S.paint(confetti, "over")

    def whoosh(d):  # curled wind strokes at the far end
        for j in range(1 + tier // 2):
            s = .5 + .12 * j + .08 * math.sin(t * 6.283 + j)
            x, y = at(path, s)
            y -= (w[int(s * (n - 1))] * .5 + 16 * sc)
            pts = []
            for a in np.linspace(0, 1, 18):
                ang = a * 4.2 + j
                r = (1 - a) * 9 * sc + 1
                pts.append((x - a * 30 * sc + math.cos(ang) * r, y + math.sin(ang) * r))
            d.line(pts, rgba(INK), 3.2 * sc)
            d.line(pts, rgba(PAPER), 1.4 * sc)
    if tier >= 1:
        S.paint(whoosh, "over")

    if tier >= 3:  # gold stars popping at the head
        def stars(d):
            for j in range(2 + tier - 3):
                ph = frac(t + j * .37)
                x, y = at(path, .05 + .1 * j)
                ink_motif(d, "star", x - 4 * sc, y - (16 + 8 * j) * sc, (4 + 5 * math.sin(math.pi * ph)) * sc, (255, 214, 70), ph * 2, 255, 2 * sc)
        S.paint(stars, "over")


def ink_aura(S, g, ad, t, part):
    sc, tier, dh = g["sc"], ad["tier"], g["dh"]
    col, acc = ad["color"], ad["accent"]
    cx, gy = g["cx"], g["gy"] - dh * .03
    rx, ry = dh * (.8 + .06 * tier), dh * (.17 + .02 * tier)
    prism = ad.get("rainbow")

    if part == "back":
        if tier >= 3:  # sunburst paper cut behind the dino
            def burst(d):
                k = 18
                cy = g["body_y"] - dh * .05
                for i in range(k):
                    a0 = 2 * math.pi * (i + t * 2) / k
                    a1 = a0 + 2 * math.pi * .5 / k
                    d.poly([(cx, cy), (cx + math.cos(a0) * dh * 1.25, cy + math.sin(a0) * dh * 1.25 * .9), (cx + math.cos(a1) * dh * 1.25, cy + math.sin(a1) * dh * 1.25 * .9)], rgba(lerp(acc, PAPER, .35), 255))
                d.circle((cx, cy), dh * .62, rgba(PAPER, 255), rgba(INK), 3 * sc)
            S.paint(burst, "over", opacity=.5)

        def ground(d):
            d.ellipse((cx, gy), rx * 1.05, ry * 1.1, rgba(PAPER, 255))
            d.ellipse((cx, gy), rx * 1.05, ry * 1.1, None, rgba(INK), max(2.4, 3.5 * sc))
            k = 28
            for i in range(k):
                if i % 2:
                    continue
                a0, a1 = 2 * math.pi * (i + t * 2) / k, 2 * math.pi * (i + 1 + t * 2) / k
                d.line([orbit(cx, gy, rx * .86, ry * .86, a0), orbit(cx, gy, rx * .86, ry * .86, a1)], rgba(lerp(col, INK, .1)), 3.4 * sc, round_caps=False)
        S.paint(ground, "over", opacity=.85)

        def tufts(d):
            for i in range(8 + 2 * tier):
                a = 2 * math.pi * i / (8 + 2 * tier)
                if math.sin(a) < 0:
                    x, y = orbit(cx, gy, rx * 1.05, ry * 1.1, a)
                    ink_motif(d, ad["motif"], x, y - 3 * sc, 12 * sc, hsv(i * .13, .5) if prism else col, a + 1, 255, 2 * sc, i)
        S.paint(tufts, "over")

    def orbiters(d):
        m = 4 + 2 * tier
        for j in range(m):
            a = 2 * math.pi * (j / m + t)
            if (part == "front") != (math.sin(a) > 0):
                continue
            x, y = orbit(cx, g["body_y"], dh * 1.0, dh * .27, a)
            y += math.sin((t * 2 + j * .2) * 6.283) * 3 * sc
            r = (15 + 3 * tier) * sc * (.85 + .25 * math.sin(a))
            c = hsv(j / m, .5) if prism else (col if j % 2 == 0 else lerp(col, acc, .65))
            ink_motif(d, ad["motif"], x, y, r, c, a * 1.5 + t * 6.283, 255, 2.4 * sc, j)
    S.paint(orbiters, "over")

    if tier >= 2:
        def wind(d):  # painted wind-swirl ribbon with ink edge
            for j in range(1 + (tier >= 3)):
                head = 2 * math.pi * (t * (1 if j == 0 else -1) + j * .5)
                sgn = 1 if j == 0 else -1
                pts = []
                for i in range(40):
                    u = i / 39
                    pts.append(orbit(cx, g["body_y"] - dh * .1 * j, dh * (1.08 + .1 * j), dh * (.3 + .04 * j), head - sgn * u * 2.0))
                keep = [p for p in pts if (math.sin(math.atan2(p[1] - g["body_y"] + dh * .1 * j, p[0] - cx)) > 0) == (part == "front")]
                if len(keep) < 3:
                    continue
                # draw as segments with taper
                for i in range(len(pts) - 1):
                    p0, p1 = pts[i], pts[i + 1]
                    front = (p0[1] - (g["body_y"] - dh * .1 * j)) > 0
                    if front != (part == "front"):
                        continue
                    u = i / 39
                    wd = (9 * (1 - u) + 1.5) * sc
                    d.line([p0, p1], rgba(INK), wd + 3.4 * sc, round_caps=False)
                for i in range(len(pts) - 1):
                    p0, p1 = pts[i], pts[i + 1]
                    front = (p0[1] - (g["body_y"] - dh * .1 * j)) > 0
                    if front != (part == "front"):
                        continue
                    u = i / 39
                    d.line([p0, p1], rgba(lerp(PAPER, acc, .25 + .3 * u)), (9 * (1 - u) + 1.5) * sc, round_caps=False)
        S.paint(wind, "over")

    if part == "front":
        def puffs(d):
            for j in range(2 + tier):
                u = frac(t + j / (2 + tier))
                x = cx + (-.7 + 1.4 * hash01(j, 9)) * g["dw"] * .5
                y = gy - u * dh * .25
                r = (11 + 8 * math.sin(math.pi * u)) * sc
                a = int(230 * math.sin(math.pi * u))
                for ox, oy, rr in [(-r * .7, 0, r * .7), (r * .7, 0, r * .7), (0, -r * .35, r * .9)]:
                    d.circle((x + ox, y + oy), rr, rgba(INK, a))
                for ox, oy, rr in [(-r * .7, 0, r * .7 - 2 * sc), (r * .7, 0, r * .7 - 2 * sc), (0, -r * .35, r * .9 - 2 * sc)]:
                    d.circle((x + ox, y + oy), max(.5, rr), rgba(PAPER, a))
        S.paint(puffs, "over")

        def conf(d):
            for j in range(5 + 3 * tier):
                u = frac(t + hash01(j, 11))
                x = cx + (hash01(j, 12) - .5) * g["dw"] * 1.5 + math.sin((u * 2 + j) * 3) * 6 * sc
                y = g["head_y"] - dh * .12 + u * dh * 1.05
                ang = (t * 2 + j * .3) * 6.283
                c_, s_ = math.cos(ang), math.sin(ang)
                r = 8 * sc
                cl = hsv(hash01(j, 13), .55) if prism else (col if j % 2 else acc)
                a = int(255 * math.sin(math.pi * u) ** .5)
                d.poly([(x + px * c_ - py * s_, y + px * s_ + py * c_) for px, py in [(-r, -r * .5), (r, -r * .5), (r, r * .5), (-r, r * .5)]], rgba(cl, a), rgba(INK, a), 1.8 * sc)
        S.paint(conf, "over")
        if tier >= 3:  # gold star crown
            def crown(d):
                for j in range(5):
                    a = math.radians(-150 + j * 30)
                    x = g["cx"] + g["dw"] * .22 + math.cos(a) * dh * .5
                    y = g["head_y"] + dh * .16 + math.sin(a) * dh * .22 + math.sin((t + j * .2) * 6.283) * 3 * sc
                    ink_motif(d, "star", x, y, (9 - abs(j - 2) * 1.2) * sc, (255, 214, 70), 0, 255, 2.4 * sc, j)
            S.paint(crown, "over")


STYLES = {
    "candy": dict(
        key="candy", name="Candy Pop", tag="Bubbly, chunky, glossy: sticker ribbons and soft pops",
        trail=candy_trail, aura=candy_aura, hero_trail="ember", hero_aura="tidal", accent=(255, 130, 232)),
    "mythic": dict(
        key="mythic", name="Mythic Glow", tag="Layered energy ribbons, runes and additive light",
        trail=mythic_trail, aura=mythic_aura, hero_trail="electric", hero_aura="royal", accent=(180, 106, 255)),
    "ink": dict(
        key="ink", name="Storybook Ink", tag="Ink-outlined paper cut-outs, leaves and confetti",
        trail=ink_trail, aura=ink_aura, hero_trail="solar", hero_aura="meadow", accent=(98, 236, 112)),
}


# ---------------------------------------------------------------- composition
def render_effect(style, w, h, dh, cx, gy, trail=None, aura=None, t=0.0, seed=3, bg=True, tl=1.0):
    S, g = make_scene(w, h, dh, cx, gy, seed, bg, tl)
    if trail:
        style["trail"](S, g, TR[trail], t)
    if aura:
        style["aura"](S, g, AU[aura], t, "back")
    draw_shadow(S, g)
    draw_dino(S, g)
    if aura:
        style["aura"](S, g, AU[aura], t, "front")
    return S.result()


def rounded(img, r):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], r, fill=255)
    out = img.convert("RGBA")
    out.putalpha(m)
    return out


def panel(board, d, box, title=None, accent=YELLOW):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, 18, fill=PANEL, outline=PANEL_EDGE, width=3)
    if title:
        d.text((x0 + 16, y0 + 8), title, font=font(18, True), fill=accent)


def chip(d, xy, text, col, fnt=None):
    fnt = fnt or font(13, True)
    w = d.textlength(text, font=fnt) + 16
    d.rounded_rectangle([xy[0], xy[1], xy[0] + w, xy[1] + 20], 10, fill=col, outline=NAVY, width=2)
    d.text((xy[0] + 8, xy[1] + 2), text, font=fnt, fill=NAVY)
    return w


def paste_round(board, img, xy, r=14):
    board.alpha_composite(rounded(img, r), xy)


def build_board(style, out_dir):
    W, H = 1600, 1100
    board = Image.new("RGBA", (W, H), (14, 22, 44, 255))
    bd = ImageDraw.Draw(board)
    ac = style["accent"]
    bd.rounded_rectangle([20, 14, W - 20, 78], 20, fill=PANEL, outline=ac, width=4)
    bd.text((44, 18), style["name"].upper(), font=font(34, True), fill=YELLOW)
    bd.text((44 + bd.textlength(style["name"].upper(), font=font(34, True)) + 28, 30), style["tag"], font=font(20), fill=(205, 220, 245))
    bd.text((W - 60 - bd.textlength("Be Dino! aura + trail concept  |  draft art, not shipped", font=font(15)), 28), "Be Dino! aura + trail concept  |  draft art, not shipped", font=font(15), fill=(150, 170, 205))

    # ---- hero
    HX, HY, HW, HH = 20, 92, 600, 400
    panel(board, bd, (HX, HY, HX + HW + 20, HY + HH + 46), None)
    hero = render_effect(style, HW, HH, 240, 370, 365, style["hero_trail"], style["hero_aura"], .15, seed=5, tl=1.25)
    paste_round(board, hero, (HX + 10, HY + 10))
    ht, ha = TR[style["hero_trail"]], AU[style["hero_aura"]]
    bd.text((HX + 18, HY + HH + 18), f"{ha['name']} aura  +  {ht['name']} trail", font=font(17, True), fill=YELLOW)
    chip(bd, (HX + HW - 100, HY + HH + 17), "real Compy", YELLOW)

    # ---- auras 3x2
    AX, AY = 660, 92
    CW, CH = 296, 202
    panel(board, bd, (AX, AY, W - 20, AY + 2 * CH + 56), "AURAS  |  richer as the growth multiplier rises (tier 1 / 2 / 3)", ac)
    for i, a in enumerate(AURAS):
        cx_, cy_ = AX + 12 + (i % 3) * (CW + 6), AY + 38 + (i // 3) * (CH + 4)
        sw_, sh_ = CW, CH - 28
        im = render_effect(style, sw_, sh_, 132, sw_ / 2 - 4, sh_ - 22, None, a["id"], .05, seed=7 + i)
        paste_round(board, im, (cx_, cy_), 12)
        if not a["seen"]:
            chip(bd, (cx_ + 8, cy_ + 8), "proposed", (255, 255, 255), font(12, True))
        bd.text((cx_ + 6, cy_ + sh_ + 3), a["name"], font=font(16, True), fill=WHITE)
        tn = f"T{a['tier']}  x{a['growth']:.2f}"
        w_ = bd.textlength(tn, font=font(13, True)) + 16
        chip(bd, (cx_ + CW - w_ - 4, cy_ + sh_ + 4), tn, RARITY_COL[[0, 0, 2, 2, 4, 4][i]])

    # ---- trail ladder
    LX, LY = 20, HY + HH + 46 + 14
    CWL, CHL = 306, 118
    panel(board, bd, (LX, LY, W - 20, LY + 2 * CHL + 48), "TRAIL LADDER  |  10 trails in 6 rarity classes, complexity rises with class", ac)
    for i, tdef in enumerate(TRAILS):
        x = LX + 10 + (i % 5) * (CWL + 4)
        y = LY + 36 + (i // 5) * CHL
        sh_ = CHL - 26
        im = render_effect(style, CWL - 4, sh_, 78, CWL - 4 - 52, sh_ - 8, tdef["id"], None, .12, seed=11 + i, tl=1.55)
        paste_round(board, im, (x, y), 10)
        bd.text((x + 6, y + sh_ + 3), tdef["name"], font=font(15, True), fill=WHITE)
        rn = RARITY6[tdef["tier"]]
        chip(bd, (x + CWL - 4 - bd.textlength(rn, font=font(13, True)) - 20, y + sh_ + 3), rn, RARITY_COL[tdef["tier"]])

    # ---- phone legibility + animation strips
    BY = LY + 2 * CHL + 48 + 14
    PW = 320
    panel(board, bd, (20, BY, 20 + PW + 24, BY + 244), "PHONE  |  320 px wide", ac)
    ph = hero.resize((PW, int(HH * PW / HW)), Image.LANCZOS).crop((0, 14, PW, 14 + 172))
    paste_round(board, ph, (32, BY + 38), 10)
    bd.text((32, BY + 38 + 172 + 6), "hero scene at real phone width, no extra zoom", font=font(13), fill=(150, 170, 205))
    SX = 20 + PW + 24 + 12
    FW = (W - 20 - SX - 16) // 5
    panel(board, bd, (SX, BY, W - 20, BY + 244), "ANIMATION FRAMES  |  seamless 1.0 s loop: trail (top) and aura (bottom)", ac)
    for k in range(5):
        tt = k / 5.0
        x = SX + 8 + k * FW
        im = render_effect(style, FW - 4, 90, 70, FW - 4 - 54, 84, style["hero_trail"], None, tt, seed=21, tl=1.5)
        paste_round(board, im, (x, BY + 38), 10)
        bd.text((x + 8, BY + 40), f"t={tt:.1f}", font=font(13, True), fill=NAVY)
        im = render_effect(style, FW - 4, 100, 80, (FW - 4) / 2, 95, None, style["hero_aura"], tt, seed=22)
        paste_round(board, im, (x, BY + 134), 10)
        bd.text((x + 8, BY + 136), f"t={tt:.1f}", font=font(13, True), fill=NAVY)
    path = os.path.join(out_dir, f"board-{style['key']}.png")
    board.convert("RGB").save(path, optimize=True)
    return path


def build_sheet(out_dir):
    W, H = 1600, 1040
    sheet = Image.new("RGBA", (W, H), (14, 22, 44, 255))
    d = ImageDraw.Draw(sheet)
    d.text((30, 14), "AURA + TRAIL STYLES, SIDE BY SIDE", font=font(32, True), fill=YELLOW)
    d.text((30, 54), "Same Compy, same grass, same three effect levels (low / mid / top class). Left to right: Candy Pop, Mythic Glow, Storybook Ink.", font=font(16), fill=(205, 220, 245))
    rows = [("COMMON  | Fern Drift + Meadow Glow", "fern", "meadow"), ("RARE  | Violet Pulse + Tidal Halo", "violet", "tidal"), ("TOP  | Astra + Prism Dream", "astra", "prism")]
    CW, CH = 508, 250
    for c, key in enumerate(["candy", "mythic", "ink"]):
        st = STYLES[key]
        x = 24 + c * (CW + 14)
        d.rounded_rectangle([x, 92, x + CW, 130], 14, fill=PANEL, outline=st["accent"], width=3)
        d.text((x + 14, 98), st["name"].upper(), font=font(22, True), fill=YELLOW)
        for r, (lab, tr, au) in enumerate(rows):
            y = 142 + r * (CH + 44)
            im = render_effect(st, CW, CH, 150, CW - 150, CH - 40, tr, au, .15, seed=30 + r)
            paste_round(sheet, im, (x, y + 24), 14)
            d.text((x + 4, y + 2), lab, font=font(15, True), fill=(205, 220, 245))
    p = os.path.join(out_dir, "comparison-sheet.png")
    sheet.convert("RGB").save(p, optimize=True)
    return p


def main():
    global SPRITE_SRC
    ap = argparse.ArgumentParser(description="Render Be Dino! aura/trail concept boards (deterministic).")
    ap.add_argument("--out", default="docs/evidence/2026-10-14-aura-trail-concepts")
    ap.add_argument("--styles", nargs="*", default=list(STYLES), choices=list(STYLES))
    ap.add_argument("--no-sheet", action="store_true", help="skip the three-style comparison sheet")
    ap.add_argument("--sprite", default=SPRITE_SRC, help="Compy render used as the dino sprite")
    a = ap.parse_args()
    SPRITE_SRC = a.sprite
    os.makedirs(a.out, exist_ok=True)
    for k in a.styles:
        print(build_board(STYLES[k], a.out))
    if not a.no_sheet:
        print(build_sheet(a.out))


if __name__ == "__main__":
    main()
