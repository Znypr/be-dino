"""BD-178: offline check of the 10 trail shop icons (Blender renders, resources/ui/v2/icons/trail-<id>-v1.png).

For each trail in ProgressionConfig.Trails: the PNG exists, is 128 x 128 RGBA with transparent corners, fills a sensible part of the
frame, keeps a clear margin, shows the trail's `color` (or `accent`) on a good share of its opaque pixels, and has a light rim ring.
No two icons share a silhouette (never colour only). Also checks the slots: tools/asset_slots.json names trail_<id> (read by
ShopCards), TrailIconAssetIds holds only empty or valid ids, ShopCards shows the icon when the id exists and keeps today's look
otherwise, and that the Blender script, .blend and contact sheet are kept.
No Roblox runner needed. Run: python tools/verify_trail_icons.py
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
errors = []


def err(msg):
    errors.append(msg)


cfg = (ROOT / 'src/shared/ProgressionConfig.luau').read_text(encoding='utf-8')
trails = {m.group(1): (tuple(int(m.group(i)) for i in (2, 3, 4)), tuple(int(m.group(i)) for i in (5, 6, 7)))
          for m in re.finditer(r'\{id="(\w+)",name="[^"]*",rarity="\w+",price=\d+,level=\d+,speed=[\d.]+,'
                               r'color=\{(\d+),(\d+),(\d+)\},accent=\{(\d+),(\d+),(\d+)\}', cfg)}
ids = list(trails)
if len(ids) != 10:
    err(f'expected 10 trails in ProgressionConfig.Trails, found {len(ids)}')

slots = {s['name']: s for s in json.loads((ROOT / 'tools/asset_slots.json').read_text(encoding='utf-8'))['slots']}
masks = {}
for tid in ids:
    path = ROOT / f'resources/ui/v2/icons/trail-{tid}-v1.png'
    if not path.exists():
        err(f'{tid}: {path.name} missing')
        continue
    img = Image.open(path)
    if img.size != (128, 128) or img.mode != 'RGBA':
        err(f'{tid}: expected 128x128 RGBA, got {img.size} {img.mode}')
        continue
    px = img.load()
    if any(px[x, y][3] != 0 for x, y in ((0, 0), (127, 0), (0, 127), (127, 127))):
        err(f'{tid}: corners must be transparent')
    solid = [(x, y) for y in range(128) for x in range(128) if px[x, y][3] > 200]
    masks[tid] = set(solid)
    cover = len(solid) / (128 * 128)
    if not 0.2 <= cover <= 0.6:
        err(f'{tid}: icon covers {cover:.0%} of the frame (want 20-60%)')
    xs, ys = [x for x, _ in solid], [y for _, y in solid]
    if min(xs) < 3 or min(ys) < 3 or max(xs) > 124 or max(ys) > 124:
        err(f'{tid}: icon touches the frame edge (keep a margin so the rim is not clipped)')
    color, accent = trails[tid]

    def near(want):
        return sum(1 for x, y in solid if sum((px[x, y][i] - want[i]) ** 2 for i in range(3)) < 70 * 70)
    share = max(near(color), near(accent)) / len(solid)
    if share < 0.18:
        err(f'{tid}: only {share:.0%} of opaque pixels are within 70 of the trail colour {color} or accent {accent}')
    rim = sum(1 for x, y in solid if min(px[x, y][:3]) > 225)
    if rim < 150:
        err(f'{tid}: no light rim found ({rim} bright pixels)')
    s = slots.get(f'trail_{tid}')
    if not s or s.get('table') != 'TrailIconAssetIds' or s.get('key') != tid:
        err(f'{tid}: tools/asset_slots.json has no trail_{tid} slot in TrailIconAssetIds')

# every pair must differ in silhouette (intersection over union of the opaque masks)
for i, a in enumerate(ids):
    for b in ids[i + 1:]:
        if a in masks and b in masks:
            iou = len(masks[a] & masks[b]) / max(1, len(masks[a] | masks[b]))
            if iou > 0.8:
                err(f'{a} and {b}: silhouettes are {iou:.0%} the same (each trail needs its own shape)')

table = re.search(r'TrailIconAssetIds=\{(.*?)\n    \},', cfg, re.S)
if not table:
    err('ProgressionConfig.TrailIconAssetIds missing')
else:
    for m in re.finditer(r'^\s*(\w+)="([^"]*)"', re.sub(r'--[^\n]*', '', table.group(1)), re.M):
        if not re.fullmatch(r'rbxassetid://[1-9][0-9]{4,18}', m.group(2)):
            err(f'TrailIconAssetIds.{m.group(1)}: malformed id {m.group(2)!r}')

for rel in ('tools/blender/build_trail_icons.py', 'tools/blender/trail_icons.blend', 'tools/make_trail_icon_sheet.py',
            'docs/evidence/2026-10-17-trails/trail-icons-contact-sheet.png'):
    if not (ROOT / rel).exists():
        err(f'missing {rel}')
src = (ROOT / 'tools/blender/build_trail_icons.py').read_text(encoding='utf-8')
if 'PIL' in src or 'putpixel' in src:
    err('the Blender script must not draw pixels with PIL')
cards = (ROOT / 'src/client/ShopCards.luau').read_text(encoding='utf-8')
if 'P.trailIconId(Config.TrailIconAssetIds' not in cards or '"TrailIcon"' not in cards or 'Theme.icon(s, "trail_" .. item.id)' not in cards:
    err('ShopCards must show the trail icon when the id exists and keep the live preview otherwise')

if errors:
    print('Trail icon check FAILED:\n  ' + '\n  '.join(errors))
    sys.exit(1)
print(f'Trail icons OK: {len(ids)} icons, 128 px RGBA, transparent, light rim, trail colours, distinct silhouettes, slots wired')
