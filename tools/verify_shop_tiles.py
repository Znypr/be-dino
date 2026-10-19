"""BD-047: offline check of the Crystal Shop art (Blender renders in resources/ui/v2/icons/) and of its wiring.

Images: 4 tab icons (shop-tab-<auras|trails|conditions|crystals>-v1.png, 128 px) and the green-spotted egg (egg-green-spotted-v1.png, 256 px)
are RGBA with transparent corners, keep a clear margin, wear the light rim plus navy line, differ in silhouette (never colour only) and show
their palette colours (docs/114: crystals amber; the egg cream with green spots). The 5 tiles (shop-tile-<tab>-v1.png, 256 px) have transparent
rounded corners, a light rim, navy line, and five clearly different backdrop colours.
Wiring: tools/asset_slots.json names every slot with a reader, AssetSlots.Images holds only empty or valid ids, ShopTiles shows each image only
when its id exists (today's look stays otherwise), Bootstrap routes the tab strip, the egg and the landing page through ShopTiles, the Blender
script / .blend / contact sheet are kept, tools/upload_batch.py lists the files, CI runs this check. With --runner the pure rules in
src/shared/ShopArt.luau run under the Luau runtime.
Run: python tools/verify_shop_tiles.py [--runner C:/path/to/luau.exe]
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / 'resources/ui/v2/icons'
errors = []


def err(msg):
    errors.append(msg)


TAB_FILES = {'shop_tab_auras': 'shop-tab-auras-v1.png', 'shop_tab_trails': 'shop-tab-trails-v1.png',
             'shop_tab_conditions': 'shop-tab-conditions-v1.png', 'shop_tab_crystals': 'shop-tab-crystals-v1.png',
             'egg_green_spotted': 'egg-green-spotted-v1.png'}
TILE_FILES = {f'shop_tile_{t}': f'shop-tile-{t}-v1.png' for t in ('auras', 'trails', 'eggs', 'conditions', 'crystals')}
SIZES = {**{k: 128 for k in TAB_FILES}, 'egg_green_spotted': 256, **{k: 256 for k in TILE_FILES}}
NAVY = (44, 50, 98)


def near(px, solid, want, dist):
    return sum(1 for x, y in solid if sum((px[x, y][i] - want[i]) ** 2 for i in range(3)) < dist * dist)


def load(slot, fn):
    path = ICONS / fn
    if not path.exists():
        err(f'{slot}: {fn} missing')
        return None
    img = Image.open(path)
    want = SIZES[slot]
    if img.size != (want, want) or img.mode != 'RGBA':
        err(f'{slot}: expected {want}x{want} RGBA, got {img.size} {img.mode}')
        return None
    px = img.load()
    if any(px[x, y][3] != 0 for x, y in ((0, 0), (want - 1, 0), (0, want - 1), (want - 1, want - 1))):
        err(f'{slot}: corners must be transparent')
    solid = [(x, y) for y in range(want) for x in range(want) if px[x, y][3] > 200]
    return img, px, solid, want


masks = {}
for slot, fn in TAB_FILES.items():
    got = load(slot, fn)
    if not got:
        continue
    img, px, solid, n = got
    cover = len(solid) / (n * n)
    if not 0.25 <= cover <= 0.75:
        err(f'{slot}: icon covers {cover:.0%} of the frame (want 25-75%)')
    xs, ys = [x for x, _ in solid], [y for _, y in solid]
    margin = max(1, n // 64)
    if min(xs) < margin or min(ys) < margin or n - 1 - max(xs) < margin or n - 1 - max(ys) < margin:
        err(f'{slot}: icon touches the frame edge (keep a margin so the rim is not clipped)')
    if sum(1 for x, y in solid if min(px[x, y][:3]) > 225) < 150 * (n // 128) ** 2:
        err(f'{slot}: no light rim found')
    if near(px, solid, NAVY, 45) < 300 * (n // 128) ** 2:
        err(f'{slot}: no navy outer line found')
    small = img.resize((64, 64), Image.BOX)
    sp = small.load()
    masks[slot] = {(x, y) for y in range(64) for x in range(64) if sp[x, y][3] > 128}
    if slot == 'shop_tab_crystals' and near(px, solid, (255, 210, 43), 60) / len(solid) < 0.2:
        err(f'{slot}: crystals must be amber / gold (docs/114 s5.3), found {near(px, solid, (255, 210, 43), 60) / len(solid):.0%}')
    if slot == 'egg_green_spotted':
        green = near(px, solid, (29, 175, 75), 50) / len(solid)
        cream = near(px, solid, (247, 234, 196), 50) / len(solid)
        if green < 0.04:
            err(f'{slot}: only {green:.1%} green spot pixels (the egg needs visible green spots)')
        if cream < 0.35:
            err(f'{slot}: only {cream:.0%} cream pixels (the egg body should be cream)')
    if slot == 'shop_tab_auras' and near(px, solid, (98, 236, 112), 60) / len(solid) < 0.2:
        err(f'{slot}: the aura icon should be mostly Meadow green (docs/114 s5.7)')
    if slot == 'shop_tab_conditions':
        for name, rgb in (('red', (247, 57, 48)), ('gold', (255, 210, 43)), ('green', (93, 237, 31)), ('blue', (46, 206, 255))):
            if near(px, solid, rgb, 55) < 120:
                err(f'{slot}: no {name} rainbow band found')

ids = list(masks)
for i, a in enumerate(ids):
    for b in ids[i + 1:]:
        iou = len(masks[a] & masks[b]) / max(1, len(masks[a] | masks[b]))
        if iou > 0.86:   # the round Auras ring and the rainbow arch are both round blobs (83%); they differ by inner structure and hue
            err(f'{a} and {b}: silhouettes are {iou:.0%} the same (each tab needs its own shape)')

backs = {}
for slot, fn in TILE_FILES.items():
    got = load(slot, fn)
    if not got:
        continue
    img, px, solid, n = got
    cover = len(solid) / (n * n)
    if not 0.7 <= cover <= 0.92:
        err(f'{slot}: tile covers {cover:.0%} (want a rounded square, 70-92%)')
    xs, ys = [x for x, _ in solid], [y for _, y in solid]
    if min(xs) < 3 or min(ys) < 3 or n - 1 - max(xs) < 3 or n - 1 - max(ys) < 3:
        err(f'{slot}: tile touches the frame edge')
    if sum(1 for x, y in solid if min(px[x, y][:3]) > 225) < 4000:
        err(f'{slot}: no light rim found')
    if near(px, solid, NAVY, 45) < 3000:
        err(f'{slot}: no navy outer line found')
    # backdrop colour = median colour of a patch just inside the rim in the top-left corner
    band = [px[x, y][:3] for y in range(24, 40) for x in range(24, 60) if px[x, y][3] > 250]
    if band:
        band.sort()
        backs[slot] = band[len(band) // 2]
names = list(backs)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        d = sum((backs[a][k] - backs[b][k]) ** 2 for k in range(3)) ** 0.5
        if d < 45:
            err(f'{a} and {b}: backdrop colours are too alike ({d:.0f}); each category needs its own colour')

# slots -------------------------------------------------------------------------------------------------------------------------
slots = {s['name']: s for s in json.loads((ROOT / 'tools/asset_slots.json').read_text(encoding='utf-8'))['slots']}
asset_slots = (ROOT / 'src/shared/AssetSlots.luau').read_text(encoding='utf-8')
art = (ROOT / 'src/shared/ShopArt.luau').read_text(encoding='utf-8')
for slot in list(TAB_FILES) + list(TILE_FILES):
    s = slots.get(slot)
    if not s or s.get('table') != 'Images' or s.get('file') != 'src/shared/AssetSlots.luau' or not s.get('reader'):
        err(f'{slot}: tools/asset_slots.json needs an Images slot with a reader')
    m = re.search(rf'^\s*{slot} = "([^"]*)",', asset_slots, re.M)
    if not m:
        err(f'{slot}: no line in AssetSlots.Images')
    elif m.group(1) and not re.fullmatch(r'rbxassetid://[1-9][0-9]{4,18}', m.group(1)):
        err(f'{slot}: malformed id {m.group(1)!r}')
    if s and s.get('reader') and s['reader'][1] not in art:
        err(f'{slot}: reader needle {s["reader"][1]!r} is not in ShopArt.luau')

# wiring ------------------------------------------------------------------------------------------------------------------------
tiles = (ROOT / 'src/client/ShopTiles.luau').read_text(encoding='utf-8')
for needle, why in (('Art.tabIconId(Slots.Images, tab)', 'tab icons read the bound id'), ('if not id then return end', 'no icon id leaves the tab as it is'),
                    ('Art.eggProductId(Slots.Images)', 'the egg product reads the bound id'), ('if not id then return false end', 'no egg id keeps the old egg'),
                    ('Art.landingReady(Slots.Images, tabs)', 'the landing needs every tile id'), ('Art.tileId(Slots.Images, tab)', 'the tile reads its id')):
    if needle not in tiles:
        err(f'ShopTiles.luau: missing {needle!r} ({why})')
if re.search(r'rbxassetid://\d', tiles + art):
    err('ShopTiles / ShopArt must never hold a hard-coded asset id')
boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8') + (ROOT / 'src/client/ShopScreens.luau').read_text(encoding='utf-8')  # BD-1088: the shop screens moved
for needle, why in (('ShopTiles.decorateTab(tabButton,tab,tabsHeight)', 'tab strip icons'), ('ShopTiles.eggProduct(body,', 'green-spotted egg on the Eggs tab'),
                    ('art(body,"egg",20,cardsY+12,220)', 'the old egg stays as the fallback'), ('if ShopTiles.landing then', 'landing page'),
                    ('ShopTiles).enter(', 'SHOP / crystal counter / hub open start on the landing')):
    if needle not in boot:
        err(f'Bootstrap.client.luau: missing {needle!r} ({why})')
if len(re.findall(r'ShopTiles\)\.enter\(', boot)) < 3:
    err('Bootstrap: the SHOP button, the crystal counter and the hub travel open must all call ShopTiles.enter')
if re.search(r'^local\s+ShopTiles\s*=', boot, re.M):
    err('Bootstrap: ShopTiles must stay a require inside the auras branch (the file is near the 200 local limit)')

# tools, docs, CI ---------------------------------------------------------------------------------------------------------------
for rel in ('tools/blender/build_shop_tiles.py', 'tools/blender/shop_tiles.blend', 'tools/make_shop_tile_sheet.py',
            'docs/evidence/2026-10-17-shop/shop-tiles-contact-sheet.png'):
    if not (ROOT / rel).exists():
        err(f'missing {rel}')
src = (ROOT / 'tools/blender/build_shop_tiles.py').read_text(encoding='utf-8')
if 'PIL' in src or 'putpixel' in src:
    err('the Blender script must not draw pixels with PIL')
batch = (ROOT / 'tools/upload_batch.py').read_text(encoding='utf-8')
if 'shop-(tab|tile)' not in batch or 'egg-green-spotted' not in batch:
    err('tools/upload_batch.py does not list the shop icons, tiles and the green-spotted egg')
reg = (ROOT / 'docs/77-asset-registry.md').read_text(encoding='utf-8')
doc120 = (ROOT / 'docs/120-pending-owner-uploads-checklist.md').read_text(encoding='utf-8')
for slot in list(TAB_FILES) + list(TILE_FILES):
    if f'| {slot} |' not in reg:
        err(f'docs/77 has no row for {slot}')
    if f'Images.{slot}`' not in doc120:
        err(f'docs/120 has no Bind in entry for {slot}')
ci = (ROOT / '.github/workflows/build-generated-place.yml').read_text(encoding='utf-8')
if 'tools/verify_shop_tiles.py' not in ci:
    err('CI does not run tools/verify_shop_tiles.py')

# pure rules under the Luau runtime ---------------------------------------------------------------------------------------------
BODY = r'''
local good = "rbxassetid://12345678"
local all = {}
for _, key in P.TabIconKeys do all[key] = good end
for _, tab in P.Tabs do all[P.tileKey(tab)] = good end
-- ids: only real asset ids pass
assert(P.validId(good) == good and P.validId("") == nil and P.validId("junk") == nil and P.validId(nil) == nil and P.validId(12345678) == nil)
for _, tab in P.Tabs do
 assert(P.tabIconId(all, tab) == good, tab)
 assert(P.tabIconId({}, tab) == nil and P.tabIconId(nil, tab) == nil and P.tabIconId({[P.TabIconKeys[tab]] = ""}, tab) == nil, tab)
 assert(P.tileId(all, tab) == good and P.tileId({}, tab) == nil, tab)
 assert(P.Titles[tab] and #P.Titles[tab] > 0, tab)
end
assert(P.TabIconKeys.eggs == P.EggProductKey, "the Eggs tab icon and the Eggs product art are the same green-spotted egg")
assert(P.eggProductId(all) == good and P.eggProductId({}) == nil and P.eggProductId(nil) == nil)
-- the landing page needs EVERY visible tab's tile (a half-uploaded set keeps today's look)
local four = {"auras", "trails", "eggs", "crystals"}
assert(P.landingReady(all, P.Tabs) and P.landingReady(all, four))
assert(not P.landingReady({}, P.Tabs) and not P.landingReady(nil, P.Tabs) and not P.landingReady(all, {}))
local partial = table.clone(all) partial[P.tileKey("eggs")] = ""
assert(not P.landingReady(partial, P.Tabs) and not P.landingReady(partial, four))
local noConditions = table.clone(all) noConditions[P.tileKey("conditions")] = nil
assert(P.landingReady(noConditions, four), "a hidden tab's tile is not needed")
-- tab layout: no icon = today's layout; an icon leaves room for the text and keeps it at least 14 px
local plain = P.tabLayout(false, 40)
assert(plain.icon == 0 and plain.pad == 0 and plain.textSize == 20)
for _, h in {40, 44, 52} do
 local l = P.tabLayout(true, h)
 assert(l.icon >= 30 and l.icon <= h and l.pad > l.icon and l.textSize >= P.MinText and l.textSize < 20, h)
 assert(155 - l.pad - 4 >= 100, "CONDITIONS still has about 100 px")
end
-- tile layout: 4 or 5 tiles fit the 824 px body, each far above the 44 px tap target
for n = 1, 5 do
 local t = P.tileLayout(n)
 assert(t.width * n + (n - 1) * P.TileGap <= 824 and t.width <= P.TileWidthMax and t.image == t.width - 12, n)
 assert(t.width >= 44 and t.height >= 44, n)
end
assert(P.tileLayout(5).height <= 402 - 40, "five tiles leave room for the hint line")
assert(P.tileLayout(4).height <= 402 - 40)
-- subtitles: kid words, never empty
assert(P.countOwned({a = true, b = true, c = false}) == 2 and P.countOwned(nil) == 0 and P.countOwned({}) == 0)
assert(P.subtitle("auras", {auras = 0}) == "Glow around you" and P.subtitle("auras", {auras = 2}) == "You have 2")
assert(P.subtitle("trails", {trails = 0}) == "Leave a trail" and P.subtitle("trails", {trails = 3}) == "You have 3")
assert(P.subtitle("eggs", {eggPrice = 100}) == "100 Crystals" and P.subtitle("conditions", {}) == "Better eggs")
assert(P.subtitle("crystals", {crystals = 40}) == "You have 40")
for _, tab in P.Tabs do assert(#P.subtitle(tab, {}) > 0, tab) end
print("shop tile rules ok")
'''


def run_luau(runner):
    code = 'local P=(function()\n' + art + '\nend)()\n' + BODY
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'shop_tiles.luau'
        path.write_text(code, encoding='utf-8')
        result = subprocess.run([runner, str(path)], capture_output=True, text=True)
    print(result.stdout, end='')
    print(result.stderr, end='')
    if result.returncode != 0:
        err('ShopArt rules failed under the Luau runtime')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', help='Luau runtime; when given the pure rules run too')
    args = ap.parse_args()
    if args.runner:
        run_luau(args.runner)
    if errors:
        print('Shop tiles check FAILED:\n  ' + '\n  '.join(errors))
        sys.exit(1)
    print(f'Shop tiles OK: {len(TAB_FILES)} icons and {len(TILE_FILES)} tiles are RGBA with transparent corners, rim and navy line, distinct; slots and wiring checked')
