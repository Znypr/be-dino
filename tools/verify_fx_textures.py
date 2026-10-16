"""Check the Blender-rendered FX textures are safe to tint at runtime (BD-186, BD-187, BD-188, BD-189).

Single images (glow plates, rings, BD-186 / BD-188): 256 x 256 RGBA PNG, under 400 KB, RGB pure white wherever alpha > 0
(no dark fringes when tinted), the frame border is fully transparent (no clipped edge), and it is not empty or a solid block.

Flipbook sheets (smoke puffs BD-187, motif sheets BD-189): 512 x 512 RGBA PNG, 4 x 4 cells of 128 px, under 400 KB, and per
cell: the cell's outer ring is fully transparent (nothing bleeds into the neighbour cell when sampled with filtering), the
cell is not empty (only frame 1 and frame 16 may be an empty fade in / out), and the colour is safe to tint by kind:
  * white   RGB white (>= 250) wherever alpha > 0, so MutationLook multiplies cleanly (droplets, sparks, crystals, embers, crimson);
  * shaded  neutral grey/white (channels within 4 of each other, all >= 120) wherever alpha >= 24: soft self-shadowing
            in the smoke and pebbles, never a dark fringe;
  * colour  the aurora ribbons (the only coloured sheet): no dark fringe, i.e. the brightest channel is >= 190 wherever
            alpha >= 24.
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
                elif kind == 'shaded' and a >= 24 and (max(r, g, b) - min(r, g, b) > 4 or min(r, g, b) < 120):
                    bad = bad or f'{name}: cell {ci} not neutral/light at {x},{y} rgb=({r},{g},{b}) alpha={a}'
                elif kind == 'colour' and a >= 24 and max(r, g, b) < 190:
                    bad = bad or f'{name}: cell {ci} dark fringe at {x},{y} rgb=({r},{g},{b}) alpha={a}'
        if visible < 12 and ci not in (0, GRID * GRID - 1):   # the first and last frame may be a clean empty fade in / out
            bad = bad or f'{name}: cell {ci} is empty ({visible} visible pixels)'
        if visible > 0.85 * CELL * CELL:
            bad = bad or f'{name}: cell {ci} fills the whole cell'
    if bad:
        errors.append(bad)

if errors:
    print('\n'.join(errors))
    sys.exit(1)
print(f'verify_fx_textures: OK ({len(FILES)} textures, {len(SHEETS)} flipbook sheets)')
