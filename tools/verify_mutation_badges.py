"""BD-190: offline check of the 7 mutation badge icons (Blender renders, resources/ui/v2/icons/mutation-<id>-v1.png).

For each mutation in MutationLook.Order: the PNG exists, is 128 x 128 RGBA with a transparent corner, fills a sensible part of the
frame, keeps a clear margin, shows the MutationLook badge colour on a good share of its opaque pixels, and has a light rim ring
(bright opaque pixels at the silhouette). Also checks the AssetSlots keys and that the Blender script and .blend are kept.
No Roblox runner needed. Run: python tools/verify_mutation_badges.py
"""
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
errors = []


def err(msg):
    errors.append(msg)


look = (ROOT / 'src/shared/MutationLook.luau').read_text(encoding='utf-8')
order = re.search(r'Look\.Order = \{([^}]*)\}', look).group(1)
ids = re.findall(r'"(\w+)"', order)
badge = {m.group(1): tuple(int(m.group(i)) for i in (2, 3, 4))
         for m in re.finditer(r'\{id = "(\w+)".*?badge = \{(\d+), (\d+), (\d+)\}', look, re.S)}
slots = (ROOT / 'src/shared/AssetSlots.luau').read_text(encoding='utf-8')

for mid in ids:
    path = ROOT / f'resources/ui/v2/icons/mutation-{mid}-v1.png'
    if not path.exists():
        err(f'{mid}: {path.name} missing')
        continue
    img = Image.open(path)
    if img.size != (128, 128) or img.mode != 'RGBA':
        err(f'{mid}: expected 128x128 RGBA, got {img.size} {img.mode}')
        continue
    px = img.load()
    if px[0, 0][3] != 0 or px[127, 0][3] != 0 or px[0, 127][3] != 0 or px[127, 127][3] != 0:
        err(f'{mid}: corners must be transparent')
    solid = [(x, y) for y in range(128) for x in range(128) if px[x, y][3] > 200]
    cover = len(solid) / (128 * 128)
    if not 0.22 <= cover <= 0.6:
        err(f'{mid}: icon covers {cover:.0%} of the frame (want 22-60%)')
    xs = [x for x, _ in solid]
    ys = [y for _, y in solid]
    if min(xs) < 3 or min(ys) < 3 or max(xs) > 124 or max(ys) > 124:
        err(f'{mid}: icon touches the frame edge (keep a margin so the rim is not clipped)')
    want = badge[mid]
    near = sum(1 for x, y in solid if sum((px[x, y][i] - want[i]) ** 2 for i in range(3)) < 60 * 60)
    if near / len(solid) < 0.25:
        err(f'{mid}: only {near / len(solid):.0%} of opaque pixels are within 60 of the MutationLook badge colour {want}')
    rim = sum(1 for x, y in solid if min(px[x, y][:3]) > 225)
    if rim < 150:
        err(f'{mid}: no light rim found ({rim} bright pixels)')
    if f'mutation_{mid} = ""' not in slots and f'mutation_{mid} = "rbxassetid://' not in slots:
        err(f'{mid}: AssetSlots.Images.mutation_{mid} missing')

for rel in ('tools/blender/build_mutation_badges.py', 'tools/blender/mutation_badges.blend', 'tools/make_mutation_badge_sheet.py',
            'docs/evidence/2026-10-16-vfx/mutation-badges-contact-sheet.png'):
    if not (ROOT / rel).exists():
        err(f'missing {rel}')
src = (ROOT / 'tools/blender/build_mutation_badges.py').read_text(encoding='utf-8')
if 'PIL' in src or 'putpixel' in src:
    err('the Blender script must not draw pixels with PIL')
bind = (ROOT / 'src/client/MutationBadge.luau').read_text(encoding='utf-8') + (ROOT / 'src/client/PreviewTraits.luau').read_text(encoding='utf-8')
if 'iconImage' not in bind or 'Name, icon.BackgroundTransparency' not in bind:
    err('MutationBadge / PreviewTraits must show the icon when the slot is bound')

if errors:
    print('Mutation badge check FAILED:\n  ' + '\n  '.join(errors))
    sys.exit(1)
print(f'Mutation badges OK: {len(ids)} icons, 128 px RGBA, transparent, light rim, MutationLook colours')
