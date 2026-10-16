"""Check the Blender-rendered glow plates and rings (BD-186, BD-188) are safe to tint at runtime.

For each file: 256 x 256 RGBA PNG, under 400 KB, RGB pure white wherever alpha > 0 (no dark fringes when tinted),
the frame border is fully transparent (no clipped edge), and it is not empty or a solid block.
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

if errors:
    print('\n'.join(errors))
    sys.exit(1)
print(f'verify_fx_textures: OK ({len(FILES)} textures)')
