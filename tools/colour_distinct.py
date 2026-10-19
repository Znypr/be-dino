"""BD-1037: are the egg colours CLEARLY different from each other? Numbers, not eyes.

Reads the real colour table (src/shared/ProgressionConfig.luau, EggColors) and measures every pair of colours:

  * CIEDE2000 distance (de00). About 1 is the smallest change an eye can see; 2 to 10 is "you notice it if you look";
    20 and more is "clearly another colour at a glance".
  * the same distance after simulating the three common kinds of colour-blindness (Machado 2009, full strength):
    protanopia and deuteranopia (red / green confusion) and tritanopia (blue / yellow confusion).
  * the MIDDLE BLEND. A dino has a main and an accent colour and its tint is the two mixed (EggGenetics.tint: Color3:Lerp in
    plain sRGB, share 1..99; the middle is 50). A mix of two colours may look like a THIRD colour (red + cream looks like pink).
    For every pair we mix at 50 percent and measure the distance to each single colour that is not one of the two ingredients.

Thresholds (documented here, PROVISIONAL, the owner can overrule; the lead picked them on 2026-10-19):
  NORMAL_MIN = 18   normal vision, any two colours (a bit under "clearly different at a glance", chosen so that sixteen colours fit)
  CVD_MIN    = 10   after colour-blindness simulation (colour-blind players lose information, so the bar is lower; a pair that
                    differs a lot in LIGHTNESS stays easy to tell apart even then)
  BLEND_MIN  = 8    a 50 / 50 mix against any single colour that is not an ingredient (there are about 100 mixes, so a stricter
                    bar cannot hold; 8 means "you can tell them apart if you put them side by side")
Plus single-colour checks: lightness L* between 12 and 95 (not a black hole, not a white blob; Black is the one allowed dark colour
and Cream the one allowed light colour), chroma at most 80 (matte, no neon), the colour is not near the terrain it walks on (informational).

Usage:
  python tools/colour_distinct.py table               # markdown tables for the docs
  python tools/colour_distinct.py check               # exit 1 when a pair is below a threshold
  python tools/colour_distinct.py propose --count 7   # pick new colours by farthest-point search; --fixed keeps the table, hex list
  python tools/colour_distinct.py sheet OUT.png       # REVIEW-ONLY contact sheet (not game art)
Tests: python tools/verify_colour_distinct.py
"""
from pathlib import Path
import argparse, itertools, math, re, sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'src' / 'shared' / 'ProgressionConfig.luau'

NORMAL_MIN, CVD_MIN, BLEND_MIN = 18.0, 10.0, 8.0
L_MIN, L_MAX, CHROMA_MAX = 12.0, 95.0, 80.0
TIERS = ['Common', 'Uncommon', 'Rare', 'Epic', 'Legendary', 'Mythic']
ALLOWED_DARK, ALLOWED_LIGHT = {'black'}, {'white'}  # ids that may leave the lightness band (Black, Cream)

# The nine colours that shipped before BD-1037. Their ids, names and rgb never change (saved dinos keep them), so a weak pair
# made only of these is reported as LEGACY and does not fail `check`.
LEGACY_IDS = ('white', 'blue', 'green', 'teal', 'pink', 'gold', 'violet', 'red', 'black')

# Terrain a dino walks on (docs/114 section 5.8, BiomeMap.Colors): a colour that melts into it is hard to see.
TERRAIN = {'Grass': (132, 166, 68), 'LeafyGrass': (88, 132, 62), 'Mud': (92, 76, 55), 'Ground': (112, 100, 66), 'Sand': (214, 190, 136),
           'Sandstone': (186, 122, 80), 'Slate': (92, 102, 108), 'Basalt': (50, 47, 55), 'Rock': (114, 133, 137)}
TERRAIN_MIN = 12.0

# ---------------------------------------------------------------- colour maths
def _lin(c):
    c = np.asarray(c, dtype=float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def _unlin(v):
    v = np.clip(np.asarray(v, dtype=float), 0.0, 1.0)
    return 255.0 * np.where(v <= 0.0031308, 12.92 * v, 1.055 * v ** (1 / 2.4) - 0.055)

_M_XYZ = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
_WHITE = np.array([0.95047, 1.0, 1.08883])

def rgb_to_lab(rgb):
    """sRGB 0..255 (a triple, or an array of shape (..., 3)) to CIELAB D65."""
    xyz = _lin(rgb) @ _M_XYZ.T / _WHITE
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    out = np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)
    return tuple(float(v) for v in out) if out.ndim == 1 else out

def lab_chroma(lab):
    lab = np.asarray(lab, dtype=float)
    out = np.hypot(lab[..., 1], lab[..., 2])
    return float(out) if out.ndim == 0 else out

def ciede2000(lab1, lab2):
    """CIEDE2000 colour difference (Sharma, Wu, Dalal 2005). Each argument is a Lab triple, or an array of shape (..., 3) (broadcasts)."""
    l1, l2 = np.asarray(lab1, dtype=float), np.asarray(lab2, dtype=float)
    L1, a1, b1 = l1[..., 0], l1[..., 1], l1[..., 2]
    L2, a2, b2 = l2[..., 0], l2[..., 1], l2[..., 2]
    c1, c2 = np.hypot(a1, b1), np.hypot(a2, b2)
    cbar7 = ((c1 + c2) / 2) ** 7
    g = 0.5 * (1 - np.sqrt(cbar7 / (cbar7 + 25 ** 7)))
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.where(c1p == 0, 0.0, np.degrees(np.arctan2(b1, a1p)) % 360)
    h2p = np.where(c2p == 0, 0.0, np.degrees(np.arctan2(b2, a2p)) % 360)
    dL, dC = L2 - L1, c2p - c1p
    dh = h2p - h1p
    dh = np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh))
    dh = np.where(c1p * c2p == 0, 0.0, dh)
    dH = 2 * np.sqrt(c1p * c2p) * np.sin(np.radians(dh / 2))
    Lbar, Cbar = (L1 + L2) / 2, (c1p + c2p) / 2
    hsum = h1p + h2p
    hbar = np.where(c1p * c2p == 0, hsum,
                    np.where(np.abs(h1p - h2p) <= 180, hsum / 2, np.where(hsum < 360, (hsum + 360) / 2, (hsum - 360) / 2)))
    T = (1 - 0.17 * np.cos(np.radians(hbar - 30)) + 0.24 * np.cos(np.radians(2 * hbar))
         + 0.32 * np.cos(np.radians(3 * hbar + 6)) - 0.20 * np.cos(np.radians(4 * hbar - 63)))
    dTheta = 30 * np.exp(-(((hbar - 275) / 25) ** 2))
    rc = 2 * np.sqrt(Cbar ** 7 / (Cbar ** 7 + 25 ** 7))
    sl = 1 + 0.015 * (Lbar - 50) ** 2 / np.sqrt(20 + (Lbar - 50) ** 2)
    sc, sh = 1 + 0.045 * Cbar, 1 + 0.015 * Cbar * T
    rt = -np.sin(np.radians(2 * dTheta)) * rc
    out = np.sqrt((dL / sl) ** 2 + (dC / sc) ** 2 + (dH / sh) ** 2 + rt * (dC / sc) * (dH / sh))
    return float(out) if out.ndim == 0 else out

# Machado, Oliveira, Fernandes 2009, severity 1.0, applied to LINEAR rgb.
CVD = {
    'protan': ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    'deutan': ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    'tritan': ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}

def simulate(rgb, kind):
    """The colour as a colour-blind person sees it (kind: protan, deutan, tritan). Triple or array (..., 3)."""
    out = _unlin(_lin(rgb) @ np.array(CVD[kind]).T)
    return tuple(float(v) for v in out) if out.ndim == 1 else out

def blend(a, b, t=0.5):
    """What EggGenetics.tint does: Color3:Lerp in plain sRGB values (t = share of b)."""
    return tuple(float(a[i] + (b[i] - a[i]) * t) for i in range(3))

def de(rgb1, rgb2, kind=None):
    if kind:
        rgb1, rgb2 = simulate(rgb1, kind), simulate(rgb2, kind)
    return ciede2000(rgb_to_lab(rgb1), rgb_to_lab(rgb2))

def hex_of(rgb):
    return '#%02X%02X%02X' % tuple(int(round(c)) for c in rgb)

def rgb_of_hex(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

# ---------------------------------------------------------------- the real table
def load_colours(path=CONFIG):
    """[(id, name, rarity, weight, (r, g, b))] in table order, parsed from the Luau source."""
    text = Path(path).read_text(encoding='utf-8')
    block = text[text.index('EggColors={'):]
    block = block[:block.index('\n    },')]
    rows = []
    for m in re.finditer(r'\{id="([^"]+)",name="([^"]+)",rarity="([^"]+)",weight=(\d+),rgb=\{(\d+),(\d+),(\d+)\}\}', block):
        rows.append((m.group(1), m.group(2), m.group(3), int(m.group(4)), (int(m.group(5)), int(m.group(6)), int(m.group(7)))))
    return rows

# ---------------------------------------------------------------- analysis
def pair_table(colours):
    """[{a, b, normal, protan, deutan, tritan, worst_cvd, score}] for every unordered pair. score < 1 means flagged."""
    out = []
    for x, y in itertools.combinations(colours, 2):
        row = {'a': x[1], 'b': y[1], 'a_id': x[0], 'b_id': y[0], 'normal': de(x[4], y[4])}
        for k in CVD: row[k] = de(x[4], y[4], k)
        row['worst_cvd'] = min(row[k] for k in CVD)
        row['score'] = min(row['normal'] / NORMAL_MIN, row['worst_cvd'] / CVD_MIN)
        out.append(row)
    return out

def blend_table(colours, t=0.5):
    """Every 50/50 mix of two colours against every single colour that is not an ingredient.
    Returns [{mix: (a, b), nearest: name, dist}] one row per mix (its closest single colour), sorted by dist."""
    out = []
    for x, y in itertools.combinations(colours, 2):
        if x[0] == y[0]: continue
        mix = blend(x[4], y[4], t)
        best = min(((de(mix, c[4]), c[1]) for c in colours if c[0] not in (x[0], y[0])), default=(999.0, ''))
        out.append({'a': x[1], 'b': y[1], 'dist': best[0], 'nearest': best[1], 'mix': mix})
    return sorted(out, key=lambda r: r['dist'])

def single_issues(colours):
    """Per-colour problems: too dark / too light / too strong, and camouflage against the terrain (informational)."""
    issues = []
    for cid, name, _, _, rgb in colours:
        lab = rgb_to_lab(rgb)
        if lab[0] < L_MIN and cid not in ALLOWED_DARK: issues.append((name, f'too dark (L* {lab[0]:.0f})'))
        if lab[0] > L_MAX and cid not in ALLOWED_LIGHT: issues.append((name, f'too light (L* {lab[0]:.0f})'))
        if lab_chroma(lab) > CHROMA_MAX: issues.append((name, f'too strong / neon (chroma {lab_chroma(lab):.0f})'))
    return issues

def terrain_notes(colours):
    notes = []
    for cid, name, _, _, rgb in colours:
        near = min(((de(rgb, t), n) for n, t in TERRAIN.items()))
        if near[0] < TERRAIN_MIN: notes.append((name, near[1], near[0]))
    return notes

def flagged(colours):
    """All problems at once: {'pairs': [...], 'blends': [...], 'single': [...]}."""
    pairs = [p for p in pair_table(colours) if p['score'] < 1.0]
    blends = [b for b in blend_table(colours) if b['dist'] < BLEND_MIN]
    return {'pairs': sorted(pairs, key=lambda p: p['score']), 'blends': blends, 'single': single_issues(colours)}

def closest_pair(colours):
    return min(pair_table(colours), key=lambda p: p['normal'])

# ---------------------------------------------------------------- proposing new colours
def lab_to_rgb(lab):
    """CIELAB D65 to sRGB 0..255, or None when outside the sRGB gamut."""
    L, a, b = lab
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200
    def finv(t):
        return t ** 3 if t > 6 / 29 else 3 * (6 / 29) ** 2 * (t - 4 / 29)
    x, y, z = 0.95047 * finv(fx), finv(fy), 1.08883 * finv(fz)
    r = 3.2404542 * x - 1.5371385 * y - 0.4985314 * z
    g = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
    bl = 0.0556434 * x - 0.2040259 * y + 1.0572252 * z
    if min(r, g, bl) < -0.0005 or max(r, g, bl) > 1.0005: return None
    return tuple(float(v) for v in _unlin([r, g, bl]))

def candidate_pool(hue=(0, 360), lightness=(L_MIN + 6, L_MAX - 8), chroma=(8, CHROMA_MAX)):
    """A grid of matte colours in LCH (L* step 3, chroma step 4, hue step 3), kept inside the sRGB gamut and the windows.
    hue is a (from, to) pair in degrees and may wrap round 360 (for example (340, 20))."""
    pool = set()
    h0, h1 = hue
    for L in np.arange(lightness[0], lightness[1] + 0.01, 3.0):
        for C in np.arange(chroma[0], chroma[1] + 0.01, 4.0):
            for H in range(0, 360, 3):
                inside = (h0 <= H <= h1) if h0 <= h1 else (H >= h0 or H <= h1)
                if not inside: continue
                rgb = lab_to_rgb((L, C * math.cos(math.radians(H)), C * math.sin(math.radians(H))))
                if rgb is not None: pool.add(tuple(int(round(c)) for c in rgb))
    return sorted(pool)

def _variants(rgbs):
    """Lab of the colours as seen normally and through each colour-blindness: shape (4, N, 3)."""
    arr = np.asarray(rgbs, dtype=float).reshape(-1, 3)
    return np.stack([rgb_to_lab(arr)] + [rgb_to_lab(simulate(arr, k)) for k in CVD])

def score_pair(rgb1, rgb2):
    """Worst of (normal / NORMAL_MIN, each colour-blind / CVD_MIN): at least 1 means the pair passes."""
    a, b = _variants([rgb1]), _variants([rgb2])
    d = ciede2000(a[:, 0], b[:, 0])
    return float(min(d[0] / NORMAL_MIN, d[1:].min() / CVD_MIN))

def propose(colours, count, pool=None, extra=(), **window):
    """Farthest-point search: add `count` colours one by one, each the candidate whose WORST score against everything so far is best
    (score_pair: 1 means the pair just passes). `extra` = more colours (rgb triples) to keep away from; `window` narrows the pool
    (hue, lightness, chroma). Returns [(rgb, score)]."""
    pool = pool or candidate_pool(**window)
    have = [tuple(c[4]) for c in colours] + [tuple(e) for e in extra]
    cand = _variants(pool)
    picks = []
    for _ in range(count):
        hv = _variants(have)
        d = ciede2000(cand[:, :, None, :], hv[:, None, :, :])  # (4, N, M)
        score = np.minimum(d[0] / NORMAL_MIN, d[1:].min(axis=0) / CVD_MIN).min(axis=1)
        i = int(score.argmax())
        picks.append((tuple(pool[i]), float(score[i])))
        have.append(tuple(pool[i]))
    return picks

# ---------------------------------------------------------------- where the colour is shown (chips, cards)
CARD = (61, 58, 73)        # Theme.Colors.card: the fill of a hatch chip and of a found Index card
DARK_CARD = (46, 46, 58)   # PatternColourCards DARK: a card not found yet
OUTLINE = (13, 15, 20)     # Theme.Colors.outline: the 3 px outline round every chip swatch
WHITE = (255, 255, 255)
SWATCH_DE_MIN = 12.0       # a swatch closer than this to the card needs its outline to be seen (information, not a failure)

def wcag_luminance(rgb):
    r, g, b = (float(_lin(c)) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def wcag_contrast(a, b):
    """The same maths as src/shared/TextStyle.luau (TextStyle.contrast)."""
    la, lb = wcag_luminance(a), wcag_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

def surface_table(colours):
    """Per colour: contrast of the swatch against the chip card (WCAG ratio), the colour distance to that card, and the contrast of the
    game's text pair (white text with a dark 2 px outline, TextStyle) when the colour itself is a chip fill (Fusion details)."""
    rows = []
    for cid, name, tier, _, rgb in colours:
        rows.append({'id': cid, 'name': name, 'tier': tier, 'vs_card': wcag_contrast(rgb, CARD), 'de_card': de(rgb, CARD),
                     'vs_dark_card': wcag_contrast(rgb, DARK_CARD), 'white_text': wcag_contrast(WHITE, rgb), 'dark_text': wcag_contrast(OUTLINE, rgb)})
    return rows

# ---------------------------------------------------------------- output
def fmt_table(colours):
    pairs = sorted(pair_table(colours), key=lambda p: p['normal'])
    lines = ['| Colour A | Colour B | Normal | Protan | Deutan | Tritan | Flag |', '|---|---|---:|---:|---:|---:|---|']
    for p in pairs:
        why = []
        if p['normal'] < NORMAL_MIN: why.append('normal')
        if p['worst_cvd'] < CVD_MIN: why.append('colour-blind')
        lines.append(f"| {p['a']} | {p['b']} | {p['normal']:.1f} | {p['protan']:.1f} | {p['deutan']:.1f} | {p['tritan']:.1f} | {', '.join(why) or 'ok'} |")
    return '\n'.join(lines)

def report(colours, rows=12):
    pairs = sorted(pair_table(colours), key=lambda p: p['normal'])
    out = [f'{len(colours)} colours, {len(pairs)} pairs. Limits: normal >= {NORMAL_MIN:g}, colour-blind >= {CVD_MIN:g}, mix >= {BLEND_MIN:g}.', '',
           f'Closest {rows} pairs (normal vision):']
    for p in pairs[:rows]:
        out.append(f"  {p['a']:<9}{p['b']:<9} normal {p['normal']:5.1f}  protan {p['protan']:5.1f}  deutan {p['deutan']:5.1f}  tritan {p['tritan']:5.1f}")
    fl = flagged(colours)
    out += ['', f"Pairs below a limit: {len(fl['pairs'])}"]
    for p in fl['pairs']:
        out.append(f"  {p['a']} / {p['b']}: normal {p['normal']:.1f}, worst colour-blind {p['worst_cvd']:.1f}")
    out += ['', f"50/50 mixes closer than {BLEND_MIN:g} to a single colour: {len(fl['blends'])}"]
    for b in fl['blends']:
        out.append(f"  {b['a']} + {b['b']} looks like {b['nearest']} (distance {b['dist']:.1f}, mix {hex_of(b['mix'])})")
    out += ['', f"Single-colour problems: {len(fl['single'])}"]
    for n, why in fl['single']: out.append(f'  {n}: {why}')
    tn = terrain_notes(colours)
    out += ['', f'Close to the ground it walks on (information, limit {TERRAIN_MIN:g}): {len(tn)}']
    for n, t, d in tn: out.append(f'  {n} is near {t} ({d:.1f})')
    return '\n'.join(out)

def sheet(colours, path, title='Egg colours (REVIEW ONLY, not game art)'):
    """Contact sheet for the owner: one swatch per colour in tier order, its name, tier, chance for one slot and hex, a NEW tag for the colours
    added by BD-1037, and under each swatch the colour as a hatch chip shows it (dot with the dark outline on the chip card, name in white with a
    dark outline). Drawn by a script on purpose: REVIEW ONLY, never game art."""
    from PIL import Image, ImageDraw, ImageFont
    cols = 4
    cell_w, cell_h = 300, 190
    ordered = sorted(colours, key=lambda c: (TIERS.index(c[2]), c[0] not in LEGACY_IDS))
    rows = math.ceil(len(ordered) / cols)
    img = Image.new('RGB', (cols * cell_w + 20, rows * cell_h + 90), (46, 44, 56))
    d = ImageDraw.Draw(img)
    try:
        f, fs, fb = (ImageFont.truetype('arialbd.ttf', 20), ImageFont.truetype('arial.ttf', 15), ImageFont.truetype('arialbd.ttf', 16))
    except OSError:
        f = fs = fb = ImageFont.load_default()
    d.text((10, 10), title, fill=(255, 255, 255), font=f)
    d.text((10, 40), 'Common to Mythic, left to right and top to bottom. NEW = added by BD-1037. Chance = one colour slot of an egg (an egg has two).', fill=(200, 200, 215), font=fs)
    total = sum(c[3] for c in colours)
    for i, (cid, name, tier, weight, rgb) in enumerate(ordered):
        x, y = 10 + (i % cols) * cell_w, 72 + (i // cols) * cell_h
        d.rounded_rectangle((x, y, x + cell_w - 16, y + 90), 12, fill=tuple(rgb), outline=(13, 15, 20), width=3)
        if cid not in LEGACY_IDS:
            d.rounded_rectangle((x + cell_w - 78, y + 8, x + cell_w - 24, y + 30), 6, fill=(255, 210, 43), outline=(13, 15, 20), width=2)
            d.text((x + cell_w - 70, y + 11), 'NEW', fill=(13, 15, 20), font=fb)
        d.text((x + 2, y + 96), f'{name}   {tier}', fill=(255, 255, 255), font=f)
        d.text((x + 2, y + 122), f'{hex_of(rgb)}   {100 * weight / total:.4g}% per slot', fill=(200, 200, 215), font=fs)
        # as a hatch chip shows it: card fill, dot with the dark outline, name in white with a dark outline
        d.rounded_rectangle((x, y + 146, x + cell_w - 16, y + 180), 9, fill=CARD, outline=(13, 15, 20), width=3)
        d.rounded_rectangle((x + 8, y + 152, x + 30, y + 174), 5, fill=tuple(rgb), outline=(13, 15, 20), width=2)
        d.text((x + 40, y + 154), name, fill=(255, 255, 255), font=fb, stroke_width=2, stroke_fill=(13, 15, 20))
    img.save(path)

# BD-1037: where each new colour may live. A window is a hue range (degrees in CIELAB, 0 = red-orange, 90 = yellow, 140 = green,
# 200 = cyan, 270 = blue, 320 = purple), a lightness range (L*, 0 black to 100 white) and a chroma range (0 grey to about 80 strong).
# The windows are only the FAMILY (a friendly yellow-green, a brown, a deep blue ...). The exact value inside is found by the search.
BD1037_FAMILIES = [
    ('Lime',  'Uncommon',  dict(hue=(80, 125),  lightness=(72, 92), chroma=(35, 60))),
    ('Sky',   'Uncommon',  dict(hue=(205, 255), lightness=(66, 88), chroma=(18, 34))),
    ('Lilac', 'Rare',      dict(hue=(275, 315), lightness=(66, 88), chroma=(25, 45))),
    ('Navy',  'Epic',      dict(hue=(270, 310), lightness=(26, 42), chroma=(40, 66))),
    ('Wine',  'Legendary', dict(hue=(5, 45),    lightness=(30, 42), chroma=(28, 58))),
    ('Stone', 'Common',    dict(hue=(0, 360),   lightness=(44, 72), chroma=(3, 10))),
    ('Clay',  'Common',    dict(hue=(30, 90),   lightness=(34, 60), chroma=(22, 46))),
]

# A mix only matters when it can really happen: the chance that a dino has this pair of colours is 2 * p1 * p2 (p = chance of one slot).
LIKELY_PAIR = 0.0005

def tier_shares():
    """Chance of each of the six tiers (the shared ladder, r = 1/5), as RarityCurve.weights(6)."""
    w = [0.2 ** k for k in range(6)]
    return [x / sum(w) for x in w]

def slot_chances(tiers):
    """Chance of ONE colour slot for each colour, given the list of its tier names (equal split inside a tier)."""
    shares = tier_shares()
    count = {t: tiers.count(t) for t in TIERS}
    return [shares[TIERS.index(t)] / count[t] for t in tiers]

def joint_scores(pool, fixed, fixed_p, cand_p, neutral=False):
    """For every candidate in `pool` (rgb triples): the worst of
       * the pair score against every fixed colour (1 = just passes the normal and colour-blind limits),
       * the blend score: every LIKELY 50/50 mix of the candidate with a fixed colour, and (unless `neutral`) every likely mix of two
         fixed colours, must stay at least BLEND_MIN from every single colour that is not an ingredient (score = distance / BLEND_MIN)."""
    cand = np.asarray(pool, dtype=float)
    fx = np.asarray(fixed, dtype=float)
    cv, fv = _variants(cand), _variants(fx)
    d = ciede2000(cv[:, :, None, :], fv[:, None, :, :])  # (4, N, M)
    score = np.minimum(d[0] / NORMAL_MIN, d[1:].min(axis=0) / CVD_MIN).min(axis=1)
    fl = fv[0]  # Lab of the fixed colours, normal vision
    cl = cv[0]
    m = len(fx)
    for j in range(m):  # (i) the candidate mixed with fixed colour j must not look like a third colour
        if 2 * cand_p * fixed_p[j] < LIKELY_PAIR or m < 2: continue
        mix = rgb_to_lab((cand + fx[j]) / 2)  # (N, 3)
        others = [k for k in range(m) if k != j]
        dist = ciede2000(mix[:, None, :], fl[None, others, :]).min(axis=1)
        score = np.minimum(score, dist / BLEND_MIN)
    if not neutral:  # (ii) a likely mix of two fixed colours must not look like the candidate
        for j, k in itertools.combinations(range(m), 2):
            if 2 * fixed_p[j] * fixed_p[k] < LIKELY_PAIR: continue
            mix = np.asarray(rgb_to_lab((fx[j] + fx[k]) / 2))
            score = np.minimum(score, ciede2000(mix[None, :], cl) / BLEND_MIN)
    return score

NEUTRAL_FAMILIES = ('Stone', 'Clay')  # greys and browns are what other colours mix to; a mix landing on them cannot be avoided

def optimise(base, families, rounds=8):
    """Pick one colour per family so that the WORST score (pairs and likely mixes, see joint_scores) is as high as possible: a greedy
    first pass, then `rounds` passes that re-pick each colour with all the others held fixed. Returns [(name, tier, rgb, worst_score)]."""
    pools = [candidate_pool(**w) for _, _, w in families]
    tiers = [c[2] for c in base] + [t for _, t, _ in families]
    chances = slot_chances(tiers)
    nb = len(base)
    picks = []
    for i, pool in enumerate(pools):  # greedy start: only what is already chosen counts
        fixed = [tuple(c[4]) for c in base] + picks
        sc = joint_scores(pool, fixed, chances[:nb] + chances[nb:nb + len(picks)], chances[nb + i], families[i][0] in NEUTRAL_FAMILIES)
        picks.append(tuple(pool[int(sc.argmax())]))
    best = [0.0] * len(picks)
    for _ in range(rounds):
        for i, pool in enumerate(pools):
            others = [j for j in range(len(picks)) if j != i]
            fixed = [tuple(c[4]) for c in base] + [picks[j] for j in others]
            fixed_p = chances[:nb] + [chances[nb + j] for j in others]
            sc = joint_scores(pool, fixed, fixed_p, chances[nb + i], families[i][0] in NEUTRAL_FAMILIES)
            picks[i], best[i] = tuple(pool[int(sc.argmax())]), float(sc.max())
    return [(name, tier, rgb, score) for (name, tier, _), rgb, score in zip(families, picks, best)]

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['table', 'check', 'report', 'propose', 'families', 'surfaces', 'sheet'])
    ap.add_argument('out', nargs='?')
    ap.add_argument('--count', type=int, default=7)
    ap.add_argument('--config', default=str(CONFIG))
    ap.add_argument('--hue', nargs=2, type=float, default=[0, 360], help='propose: hue window in degrees (may wrap, e.g. 340 20)')
    ap.add_argument('--lightness', nargs=2, type=float, default=[L_MIN + 6, L_MAX - 8], help='propose: L* window')
    ap.add_argument('--chroma', nargs=2, type=float, default=[8, CHROMA_MAX], help='propose: chroma window')
    ap.add_argument('--also', default='', help='propose: comma list of extra hex colours to keep away from')
    a = ap.parse_args(argv)
    colours = load_colours(a.config)
    if a.cmd == 'table': print(fmt_table(colours))
    elif a.cmd == 'report': print(report(colours))
    elif a.cmd == 'check':
        fl = flagged(colours)
        print(report(colours))
        return 1 if (fl['pairs'] or fl['blends'] or fl['single']) else 0
    elif a.cmd == 'propose':
        extra = [rgb_of_hex(h) for h in a.also.split(',') if h.strip()]
        for rgb, s in propose(colours, a.count, extra=extra, hue=tuple(a.hue), lightness=tuple(a.lightness), chroma=tuple(a.chroma)):
            lab = rgb_to_lab(rgb)
            print(hex_of(rgb), tuple(rgb), f'score {s:.2f}  L* {lab[0]:.0f}  C {lab_chroma(lab):.0f}  hue {math.degrees(math.atan2(lab[2], lab[1])) % 360:.0f}')
    elif a.cmd == 'surfaces':
        print('| Colour | Tier | Swatch against chip card | Distance to card | White text on it | Dark text on it |')
        print('|---|---|---:|---:|---:|---:|')
        for r in surface_table(colours):
            print(f"| {r['name']} | {r['tier']} | {r['vs_card']:.1f} : 1 | {r['de_card']:.0f} | {r['white_text']:.1f} : 1 | {r['dark_text']:.1f} : 1 |")
    elif a.cmd == 'families':
        base = [c for c in colours if c[0] in LEGACY_IDS]
        for name, tier, rgb, worst in optimise(base, BD1037_FAMILIES):
            lab = rgb_to_lab(rgb)
            print(f'{name:<6}{tier:<10}{hex_of(rgb)} {tuple(rgb)}  worst pair score {worst:.2f}  L* {lab[0]:.0f}  C {lab_chroma(lab):.0f}')
    elif a.cmd == 'sheet':
        sheet(colours, a.out or 'colours.png')
    return 0

if __name__ == '__main__':
    sys.exit(main())
