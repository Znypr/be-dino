"""Check the Blender-rendered FX textures are safe to tint at runtime (BD-186, BD-187, BD-188, BD-189).

Single images (glow plates, rings, BD-186 / BD-188): 256 x 256 RGBA PNG, under 400 KB, RGB pure white wherever alpha > 0
(no dark fringes when tinted), the frame border is fully transparent (no clipped edge), and it is not empty or a solid block.

Flipbook sheets (smoke puffs BD-187, motif sheets BD-189): 512 x 512 RGBA PNG, 4 x 4 cells of 128 px, under 400 KB, and per
cell: the cell's outer ring is fully transparent (nothing bleeds into the neighbour cell when sampled with filtering), the
cell is not empty (only frame 1 and frame 16 may be an empty fade in / out), and the colour is safe to tint by kind:
  * white   RGB white (>= 250) wherever alpha > 0, so MutationLook multiplies cleanly (droplets, sparks, crystals, embers, crimson);
  * shaded  neutral grey/white (channels within 4 of each other, all >= 96) wherever alpha >= 24: soft self-shadowing
            in the smoke and pebbles, never a dark fringe;
  * colour  the aurora ribbons (the only coloured sheet): no dark fringe, i.e. the brightest channel is >= 190 wherever
            alpha >= 24.
Weather textures (BD-131): rainStreak 64x256, lightningBolt 512x128 (tileable along x), bloodMoonDisc 512x512, and six 512 flipbooks
(snowFlakeSheet, ashFlake, emberSpark, dustSand, auroraCurtain, bloodMoonMotes): all RGB white wherever alpha > 0, clean transparent
borders, no empty cells, auroraCurtain loops (frame 16 flows into frame 1).
Anime FX P0 / P1 (BD-430, BD-431): flameTongue and starPop are white 512 flipbooks (clean cell borders, no empty cells, calm frame-to-frame
steps, the flame stays rooted at its base, the star pops open and shrinks away); domeGradient 512x512, shaftGradient 256x512 and shellEdge
512x512 are UV gradient textures (white on alpha, empty top and bottom rows so the mesh ends never show a line, tileable around, the
profile is where the mesh wants it); speedStreaks 512x512 holds exactly four separate soft streaks. The three FX meshes
(assets/blender/fx/*.fbx) are read with tools/fbx_stats.py: triangle budgets, UVs present, sizes, and the manifest matches the files.
Read-only; uses Pillow only to inspect (never to draw).
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'resources/effects/fx-v2'
FILES = ['glowPlate', 'glowPlate-round', 'glowPlate-droplet', 'glowPlate-crescent', 'ringSoft', 'ringShock', 'ringSeismic']
errors = []

for name in FILES:
    path = DIR / f'{name}.png'
    if not path.exists():
        errors.append(f'{name}: missing {path}')
        continue
    if path.stat().st_size > 400 * 1024:
        errors.append(f'{name}: {path.stat().st_size} bytes is over 400 KB')
    im = Image.open(path)
    if im.size != (256, 256) or im.mode != 'RGBA':
        errors.append(f'{name}: expected 256x256 RGBA, got {im.size} {im.mode}')
        continue
    px = im.load()
    w, h = im.size
    opaque = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 0:
                opaque += 1
                if min(r, g, b) < 250:
                    errors.append(f'{name}: dark fringe at {x},{y} rgb=({r},{g},{b}) alpha={a}')
                    break
            if (x in (0, w - 1) or y in (0, h - 1)) and a != 0:
                errors.append(f'{name}: border pixel {x},{y} has alpha {a}')
                break
        else:
            continue
        break
    if opaque < 2000:
        errors.append(f'{name}: nearly empty ({opaque} visible pixels)')
    if opaque > 0.9 * w * h:
        errors.append(f'{name}: covers the whole frame')

# ---------------------------------------------------------------------------------------------- flipbook sheets
SHEETS = {
    # name: colour kind (see the docstring)
    'smokeSoft': 'shaded', 'smokeDense': 'shaded', 'smokeWispy': 'shaded',
    'motifDroplets': 'white', 'motifSoftSparks': 'white', 'motifSnowCrystals': 'white', 'motifPebbles': 'shaded',
    'motifEmbers': 'white', 'motifAurora': 'colour', 'motifCrimson': 'white',
    'flameTongue': 'white', 'starPop': 'white',   # BD-430
}
CELL, GRID = 128, 4

for name, kind in SHEETS.items():
    path = DIR / f'{name}.png'
    if not path.exists():
        errors.append(f'{name}: missing {path}')
        continue
    if path.stat().st_size > 400 * 1024:
        errors.append(f'{name}: {path.stat().st_size} bytes is over 400 KB')
    im = Image.open(path)
    if im.size != (CELL * GRID, CELL * GRID) or im.mode != 'RGBA':
        errors.append(f'{name}: expected {CELL * GRID}x{CELL * GRID} RGBA, got {im.size} {im.mode}')
        continue
    px = im.load()
    bad = None
    for ci in range(GRID * GRID):
        ox, oy = (ci % GRID) * CELL, (ci // GRID) * CELL
        visible = 0
        for y in range(CELL):
            for x in range(CELL):
                r, g, b, a = px[ox + x, oy + y]
                if a > 8:
                    visible += 1
                if (x in (0, CELL - 1) or y in (0, CELL - 1)) and a != 0:
                    bad = bad or f'{name}: cell {ci} border pixel {x},{y} has alpha {a} (bleeds into the next cell)'
                if kind == 'white' and a > 0 and min(r, g, b) < 250:
                    bad = bad or f'{name}: cell {ci} dark fringe at {x},{y} rgb=({r},{g},{b}) alpha={a}'
                elif kind == 'shaded' and a >= 24 and (max(r, g, b) - min(r, g, b) > 4 or min(r, g, b) < 96):
                    bad = bad or f'{name}: cell {ci} not neutral/light at {x},{y} rgb=({r},{g},{b}) alpha={a}'
                elif kind == 'colour' and a >= 24 and max(r, g, b) < 190:
                    bad = bad or f'{name}: cell {ci} dark fringe at {x},{y} rgb=({r},{g},{b}) alpha={a}'
        if visible < 12 and ci not in (0, GRID * GRID - 1):   # the first and last frame may be a clean empty fade in / out
            bad = bad or f'{name}: cell {ci} is empty ({visible} visible pixels)'
        if visible > 0.85 * CELL * CELL:
            bad = bad or f'{name}: cell {ci} fills the whole cell'
    if bad:
        errors.append(bad)

# ---------------------------------------------------------------------------------------------- weather textures (BD-131)
# All white on alpha (the runtime tints them), phone sized: singles 64x256 / 512x128 / 512x512, flipbooks 512 = 4 x 4 of 128 px.
WEATHER_SINGLES = {
    # name: (size, borders that must be fully transparent, tileable along x)
    'rainStreak': ((64, 256), 'all', False),
    'lightningBolt': ((512, 128), 'tb', True),
    'bloodMoonDisc': ((512, 512), 'all', False),
}
WEATHER_SHEETS = ['snowFlakeSheet', 'ashFlake', 'emberSpark', 'dustSand', 'auroraCurtain', 'bloodMoonMotes']
LOOPING = ['auroraCurtain']   # frame 16 runs back into frame 1


def white_ok(name, px, w, h, errs):
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 0 and min(r, g, b) < 250:
                errs.append(f'{name}: dark fringe at {x},{y} rgb=({r},{g},{b}) alpha={a}')
                return


def check_single(name, size, borders, tile, max_visible=0.9):
    """One single-image texture: size, white RGB, transparent borders, not empty / solid, tiles along x when asked. Returns the image."""
    path = DIR / f'{name}.png'
    if not path.exists():
        errors.append(f'{name}: missing {path}')
        return None
    if path.stat().st_size > 400 * 1024:
        errors.append(f'{name}: {path.stat().st_size} bytes is over 400 KB')
    im = Image.open(path)
    if im.size != size or im.mode != 'RGBA':
        errors.append(f'{name}: expected {size[0]}x{size[1]} RGBA, got {im.size} {im.mode}')
        return None
    px, (w, h) = im.load(), im.size
    white_ok(name, px, w, h, errors)
    edge = [(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)]
    if borders == 'all':
        edge += [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
    if any(px[x, y][3] != 0 for x, y in edge):
        errors.append(f'{name}: a border pixel is not transparent (clipped edge)')
    visible = sum(1 for y in range(h) for x in range(w) if px[x, y][3] > 8)
    if visible < 0.02 * w * h or visible > max_visible * w * h:
        errors.append(f'{name}: {visible} visible pixels looks empty or solid')
    if tile:   # tiles along x: the strip must leave and enter at the same height (alpha centroid of the first and last column)
        def centroid(x):
            col = [px[x, y][3] for y in range(h)]
            tot = sum(col)
            return sum(y * a for y, a in enumerate(col)) / tot if tot else None
        c0, c1 = centroid(0), centroid(w - 1)
        if c0 is None or c1 is None or abs(c0 - c1) > 3.0:
            errors.append(f'{name}: not tileable, first/last column centre {c0} vs {c1}')
    return im


for name, (size, borders, tile) in WEATHER_SINGLES.items():
    check_single(name, size, borders, tile)

for name in WEATHER_SHEETS:
    path = DIR / f'{name}.png'
    if not path.exists():
        errors.append(f'{name}: missing {path}')
        continue
    if path.stat().st_size > 400 * 1024:
        errors.append(f'{name}: {path.stat().st_size} bytes is over 400 KB')
    im = Image.open(path)
    if im.size != (CELL * GRID, CELL * GRID) or im.mode != 'RGBA':
        errors.append(f'{name}: expected {CELL * GRID}x{CELL * GRID} RGBA, got {im.size} {im.mode}')
        continue
    px = im.load()
    bad, cells = None, []
    for ci in range(GRID * GRID):
        ox, oy = (ci % GRID) * CELL, (ci // GRID) * CELL
        visible = 0
        for y in range(CELL):
            for x in range(CELL):
                r, g, b, a = px[ox + x, oy + y]
                if a > 8:
                    visible += 1
                if (x in (0, CELL - 1) or y in (0, CELL - 1)) and a != 0:
                    bad = bad or f'{name}: cell {ci} border pixel {x},{y} has alpha {a} (bleeds into the next cell)'
                if a > 0 and min(r, g, b) < 250:
                    bad = bad or f'{name}: cell {ci} dark fringe at {x},{y} rgb=({r},{g},{b}) alpha={a}'
        if visible < 40:
            bad = bad or f'{name}: cell {ci} is empty ({visible} visible pixels)'
        if visible > 0.7 * CELL * CELL:
            bad = bad or f'{name}: cell {ci} fills the whole cell'
        cells.append(im.crop((ox, oy, ox + CELL, oy + CELL)).getchannel('A'))
    if bad:
        errors.append(bad)
    if name in LOOPING:
        from PIL import ImageChops, ImageStat
        steps = [ImageStat.Stat(ImageChops.difference(cells[i], cells[(i + 1) % 16])).mean[0] for i in range(16)]
        closing, others = steps[15], max(steps[:15])
        if closing > others * 1.25 + 0.5:
            errors.append(f'{name}: loop jump frame 16 -> 1 is {closing:.1f}, larger than the biggest normal step {others:.1f}')

# ---------------------------------------------------------------------------------------------- anime FX P0 / P1 (BD-430, BD-431)
# UV gradient textures for the FX meshes: name -> (size, borders that must be transparent, tiles around x, max visible share)
STEP_LIMIT = 22.0   # calm limit for the mean alpha change between two flipbook frames
ANIME_SINGLES = {
    'domeGradient': ((512, 512), 'tb', True, 0.9),
    'shaftGradient': ((256, 512), 'tb', True, 0.98),
    'shellEdge': ((512, 512), 'tb', True, 0.98),
    'speedStreaks': ((512, 512), 'all', False, 0.9),
}


def row_alpha(im, y0, y1):
    """(mean, max) alpha of the rows y0..y1-1."""
    px, (w, _) = im.load(), im.size
    vals = [px[x, y][3] for y in range(y0, y1) for x in range(w)]
    return sum(vals) / len(vals), max(vals)


anime = {name: check_single(name, size, b, tile, mv) for name, (size, b, tile, mv) in ANIME_SINGLES.items()}
dome, shaft, shell, streak = (anime[n] for n in ('domeGradient', 'shaftGradient', 'shellEdge', 'speedStreaks'))
if dome:    # v = 0 at the BOTTOM row: a bright thin rim at the base, a soft body, an empty apex
    h = dome.size[1]
    if row_alpha(dome, 0, int(h * 0.15))[1] > 8:
        errors.append('domeGradient: the apex (top 15% of rows) must be empty')
    if row_alpha(dome, int(h * 0.8), h)[1] < 200:
        errors.append('domeGradient: no bright rim near the base (bottom 20% of rows)')
    if row_alpha(dome, int(h * 0.55), int(h * 0.7))[0] < 15:
        errors.append('domeGradient: the body above the rim is empty')
if shaft:   # v = 1 at the TOP row (the source): brighter at the top than at the bottom
    h = shaft.size[1]
    if row_alpha(shaft, int(h * 0.05), int(h * 0.30))[0] < 2.0 * row_alpha(shaft, int(h * 0.75), h)[0] + 5:
        errors.append('shaftGradient: the source end (top) must be clearly brighter than the far end (bottom)')
if shell:   # empty at both poles, a band in the middle
    h = shell.size[1]
    if row_alpha(shell, 0, int(h * 0.02))[1] > 8 or row_alpha(shell, int(h * 0.98), h)[1] > 8:
        errors.append('shellEdge: both poles (top and bottom rows) must be empty')
    if row_alpha(shell, int(h * 0.4), int(h * 0.7))[0] < 40:
        errors.append('shellEdge: the middle band is too faint')
if streak:  # four separate streaks: runs of rows that carry alpha
    px, (w, h) = streak.load(), streak.size
    rows = [any(px[x, y][3] > 8 for x in range(w)) for y in range(h)]
    runs = sum(1 for y in range(h) if rows[y] and (y == 0 or not rows[y - 1]))
    if runs != 4:
        errors.append(f'speedStreaks: expected 4 separate streaks, found {runs}')

# flipbook shape checks: the flame stays rooted and calm, the star pops open and shrinks away
from PIL import ImageChops, ImageStat  # noqa: E402


def cells_of(name):
    path = DIR / f'{name}.png'
    if not path.exists():
        return []
    im = Image.open(path).convert('RGBA')
    return [im.crop(((i % GRID) * CELL, (i // GRID) * CELL, (i % GRID + 1) * CELL, (i // GRID + 1) * CELL)).getchannel('A') for i in range(GRID * GRID)]


for name in ('flameTongue', 'starPop'):
    cells = cells_of(name)
    if len(cells) != GRID * GRID:
        continue
    steps = [ImageStat.Stat(ImageChops.difference(cells[i], cells[i + 1])).mean[0] for i in range(15)]
    if max(steps) > STEP_LIMIT:   # mean alpha change per pixel between two frames (0..255): a calm grow / shrink, never a flicker
        errors.append(f'{name}: a frame-to-frame jump of {max(steps):.1f} is too abrupt (calm limit {STEP_LIMIT})')
    boxes = [c.point(lambda v: 255 if v > 8 else 0).getbbox() for c in cells]
    if name == 'flameTongue':
        bottoms = [b[3] for b in boxes[3:13] if b]
        if bottoms and max(bottoms) - min(bottoms) > 6:
            errors.append(f'flameTongue: the base moves ({min(bottoms)}..{max(bottoms)} px); the tongue must stay rooted')
        sizes = [(b[3] - b[1]) for b in boxes if b]
        if max(sizes) < 1.8 * min(sizes[0], sizes[-1]) or sizes.index(max(sizes)) in (0, 15):
            errors.append('flameTongue: it must grow from a bud, peak mid-way and shrink at the end')
    else:
        widths = [(b[2] - b[0]) if b else 0 for b in boxes]
        if not (widths[0] < 0.5 * max(widths) and widths[15] < 0.5 * max(widths) and 3 <= widths.index(max(widths)) <= 9):
            errors.append(f'starPop: expected a pop (small, wide in the middle, small again), widths {widths}')

# the FX meshes (FBX) against their triangle budgets (docs/123 s3: about 120 / 80 / 150), read from the real files
sys.path.insert(0, str(ROOT / 'tools'))
import fbx_stats  # noqa: E402
import json  # noqa: E402

MESH_DIR = ROOT / 'assets/blender/fx'
MESHES = {  # file: (max tris, min tris, expected height / width)
    'shock-dome.fbx': (130, 90, 0.5),
    'shaft-cone.fbx': (90, 60, 1.8),
    'aura-shell.fbx': (160, 100, 1.0),
}
manifest = {}
if (MESH_DIR / 'fx-meshes.json').exists():
    manifest = json.loads((MESH_DIR / 'fx-meshes.json').read_text(encoding='utf-8'))
else:
    errors.append('assets/blender/fx/fx-meshes.json is missing')
for fname, (top, bottom, ratio) in MESHES.items():
    path = MESH_DIR / fname
    if not path.exists():
        errors.append(f'{fname}: missing {path}')
        continue
    try:
        st = fbx_stats.stats(path)
    except Exception as e:  # noqa: BLE001
        errors.append(f'{fname}: unreadable FBX ({e})')
        continue
    if not (bottom <= st['tris'] <= top):
        errors.append(f'{fname}: {st["tris"]} triangles, expected {bottom}..{top}')
    if not st['uv']:
        errors.append(f'{fname}: no UV layer (the gradient texture needs it)')
    w, d, hgt = st['size']
    if abs(w - d) > 0.5 or hgt <= 0:
        errors.append(f'{fname}: not round about the vertical axis ({w:.2f} x {d:.2f})')
    if abs(hgt / w - ratio) > 0.12:
        errors.append(f'{fname}: height / width {hgt / w:.2f}, expected about {ratio}')
    if not (0.5 <= hgt <= 40 and 0.5 <= w <= 40):
        errors.append(f'{fname}: size {w:.2f} x {hgt:.2f} studs is out of range for an FX shell')
    m = manifest.get(fname)
    if not m or m.get('tris') != st['tris'] or m.get('verts') != st['verts']:
        errors.append(f'{fname}: fx-meshes.json does not match the file ({m} vs {st["tris"]} tris, {st["verts"]} verts)')
    if path.stat().st_size > 64 * 1024:
        errors.append(f'{fname}: {path.stat().st_size} bytes is too big for a {st["tris"]}-triangle shell')

if errors:
    print('\n'.join(errors))
    sys.exit(1)
print(f'verify_fx_textures: OK ({len(FILES)} textures, {len(SHEETS)} flipbook sheets, '
      f'{len(WEATHER_SINGLES)} weather singles, {len(WEATHER_SHEETS)} weather flipbooks, '
      f'{len(ANIME_SINGLES)} anime gradients/streaks, {len(MESHES)} FX meshes)')
