#!/usr/bin/env python3
"""BD-1296 (docs/246 slice 2, owner rule "mock first, parts sheet"): a 1280x720 phone-landscape MOCK of the Potion Shop and the Dino Index
on the shop menu kit, composed only from the REAL kit PNGs (resources/ui/v2/shopkit2), the bound potion pictures (resources/ui/v2/items),
the rail icons (resources/ui/v2/icons) and the V3 dino cutouts, at the rects of the REAL layout code: it runs src/shared/SaeMenuRules.luau
and ShopKit2.luau in the pinned Luau runtime and draws what they return, so the mock and the game share one set of numbers.
The kit pieces are drawn the way client/KitArt draws them (9-slice for the outline at a cap scale, the inside tiled with one stud period).
The dino pictures stand in for the game's 3D previews (ViewportFrames); a not-found dino is the same cutout as a dark silhouette.

Usage: python tools/mock_menus_slice2.py --runner luau.exe [--size 1280x720] [--inset 0] [--dinos DIR] [--out DIR]
Writes mock-potion-shop.png and mock-dino-index.png (default docs/evidence/2026-11-23-menus-slice2)."""
from pathlib import Path
import argparse
import glob
import json
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / 'resources/ui/v2/shopkit2'
ITEMS = ROOT / 'resources/ui/v2/items'
ICONS = ROOT / 'resources/ui/v2/icons'
INK = (13, 15, 20, 255)
BACKGROUND = ROOT / 'docs/evidence/2026-11-21-menus-sae-slice1/8-after-close-hud-back.jpg'  # our own Studio picture of the world

DUMP = r'''
local function enc(v)
    local t = type(v)
    if t == "table" then
        if #v > 0 or next(v) == nil then
            local out = {} for _, x in v do table.insert(out, enc(x)) end return "[" .. table.concat(out, ",") .. "]"
        end
        local out = {} for k, x in v do table.insert(out, string.format("%q", tostring(k)) .. ":" .. enc(x)) end return "{" .. table.concat(out, ",") .. "}"
    elseif t == "string" then return string.format("%q", v)
    elseif t == "boolean" then return tostring(v)
    else return tostring(v) end
end
print(enc({potion = M.potionLayout(W, H, INSET), index = M.indexLayout(W, H, INSET), studded = K.Studded, header = K.Header,
    pieces = K.headerPieces(1, 1), headerCards = K.HeaderCards, bodyCap = K.BodyCap, bodyStuds = K.BodyStuds, artCrop = K.ArtCrop}))
'''


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8').replace('\r\n', '\n')


def module(rel):
    return '(function()\n' + read(rel).replace('export type', 'type') + '\nend)()\n'


def layouts(runner, w, h, inset):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'mock.luau'
        head = f'local W, H, INSET = {w}, {h - inset}, {inset}\nlocal M=' + module('src/shared/SaeMenuRules.luau') + 'local K=' + module('src/shared/ShopKit2.luau')
        path.write_text(head + DUMP, encoding='utf-8')
        out = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8', check=True).stdout
    return json.loads(out.strip().splitlines()[-1].replace('\\\n', '\\n'))


def header_pieces(runner, w, h):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'hp.luau'
        path.write_text('local K=' + module('src/shared/ShopKit2.luau') + f'for _, p in K.headerPieces({w}, {h}) do print(p.x, p.w, p.cropX, p.cropW, p.tile) end', encoding='utf-8')
        out = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8', check=True).stdout
    rows = []
    for line in out.strip().splitlines():
        x, pw, cx, cw, tile = line.split()
        rows.append((int(x), int(pw), int(cx), int(cw), tile == 'true'))
    return rows


def font(size):
    found = sorted(glob.glob('C:/Users/*/AppData/Local/Roblox/Versions/*/content/fonts/FredokaOne-Regular.ttf'))
    try:
        return ImageFont.truetype(found[-1] if found else 'arialbd.ttf', size)
    except OSError:
        return ImageFont.load_default()


def img(path):
    return Image.open(path).convert('RGBA')


def nine(pic, slice_, k, w, h):
    """Roblox ScaleType.Slice: corners at k x their picture size, edges stretched one way, the centre both ways."""
    W, H = pic.size
    x0, y0, x1, y1 = slice_
    cl, ct, cr, cb = x0, y0, W - x1, H - y1
    L, T, R, B = round(cl * k), round(ct * k), round(cr * k), round(cb * k)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    xs = [(0, x0, 0, L), (x0, x1, L, w - R), (x1, W, w - R, w)]
    ys = [(0, y0, 0, T), (y0, y1, T, h - B), (y1, H, h - B, h)]
    for sx0, sx1, dx0, dx1 in xs:
        for sy0, sy1, dy0, dy1 in ys:
            if dx1 > dx0 and dy1 > dy0:
                out.alpha_composite(pic.crop((sx0, sy0, sx1, sy1)).resize((dx1 - dx0, dy1 - dy0), Image.LANCZOS), (dx0, dy0))
    return out


def studded(canvas, d, x, y, w, h, cap, stud):
    """client/KitArt.studded: the picture 9-sliced for its outline, the inside covered by a tile of one stud period."""
    pic = img(KIT / (d['slot'].replace('shopkit2_', '').replace('_', '-') + '.png'))
    s, i, c = d['slice'], d['inner'], d['crop']
    k = max(0.05, min(cap, w / (d['w'] - (s[2] - s[0])), h / (d['h'] - (s[3] - s[1]))))
    canvas.alpha_composite(nine(pic, s, k, w, h), (x, y))
    l, t, r, b = int(i['l'] * k), int(i['t'] * k), int(i['r'] * k), int(i['b'] * k)
    tw, th = max(4, round(c['w'] * stud)), max(4, round(c['h'] * stud))
    tile = pic.crop((c['x'], c['y'], c['x'] + c['w'], c['y'] + c['h'])).resize((tw, th), Image.LANCZOS)
    iw, ih = max(0, w - l - r), max(0, h - t - b)
    box = Image.new('RGBA', (iw, ih))
    for yy in range(0, ih, th):
        for xx in range(0, iw, tw):
            box.alpha_composite(tile, (xx, yy))
    canvas.alpha_composite(box, (x + l, y + t))


def picture(canvas, path, x, y, w, h, crop=None, silhouette=False):
    pic = img(path)
    if crop:
        pic = pic.crop((crop['x'], crop['y'], crop['x'] + crop['w'], crop['y'] + crop['h']))
    k = min(w / pic.width, h / pic.height)
    pic = pic.resize((max(1, round(pic.width * k)), max(1, round(pic.height * k))), Image.LANCZOS)
    if silhouette:
        a = pic.getchannel('A')
        pic = Image.new('RGBA', pic.size, (32, 33, 39, 255))  # charcoal #202127
        pic.putalpha(a.point(lambda v: int(v * 0.85)))
    canvas.alpha_composite(pic, (x + (w - pic.width) // 2, y + (h - pic.height) // 2))


def words(canvas, text, x, y, w, h, size, colour=(255, 255, 255, 255), align='center'):
    """Kit words: FredokaOne, a 3 px ink outline, an ink copy 3 px under it (client/KitArt.words)."""
    d = ImageDraw.Draw(canvas)
    f = font(size)
    box = d.textbbox((0, 0), text, font=f, stroke_width=3)
    tw, th = box[2] - box[0], box[3] - box[1]
    tx = x + (w - tw) // 2 if align == 'center' else x
    ty = y + (h - th) // 2 - box[1]
    d.text((tx - box[0], ty + 3), text, font=f, fill=INK, stroke_width=3, stroke_fill=INK)
    d.text((tx - box[0], ty), text, font=f, fill=colour, stroke_width=3, stroke_fill=INK)


def button(canvas, L, x, y, w, h, *, price=None, word=None, grey=False, text=26, gem=True):
    d = L['studded']['shopkit2_button_' + ('grey' if grey else 'green')]
    k = h / d['h']
    studded(canvas, d, x, y, w, h, k, k)
    lift = int(h * 0.06)
    if price is not None:
        icon = round(h * 0.72)
        f = font(text)
        tw = ImageDraw.Draw(canvas).textbbox((0, 0), f'{price:,}', font=f, stroke_width=3)[2]
        left = max(4, (w - (icon + 4 + tw)) // 2)
        if gem:
            picture(canvas, ICONS / 'amber.png', x + left, y + (h - icon) // 2 - lift, icon, icon)
        words(canvas, f'{price:,}', x + left + icon + 4, y - lift, tw + 6, h, text, align='left')
    else:
        words(canvas, word or 'OPEN', x, y - lift, w, h, text)


def strip(canvas, L, x, y, w, h, text, size):
    d = L['studded']['shopkit2_effect_strip']
    k = h / d['h']
    studded(canvas, d, x, y, w, h, k, k)
    if text:
        words(canvas, text, x, y - int(h * 0.05), w, h, size)


def window(canvas, L, lay, title, colour, runner):
    """client/KitWindow: the dark studded body, the header strip (kit 2 strip, or the kit 2 card piece for a colour with no strip), the
    title at the left, the red X at the right."""
    win = lay['window']
    x0, y0 = win['x'], win['y'] + lay.get('_inset', 0)
    studded(canvas, L['studded']['shopkit2_effect_strip'], x0, y0, win['w'], win['h'], L['bodyCap'], L['bodyStuds'] * win['h'] / 517)
    hi, hh = lay['headerInset'], lay['headerH']
    hw = win['w'] - 2 * hi
    hx, hy = x0 + hi, y0 + hi
    card = (L.get('headerCards') or {}).get(colour)
    if card:
        d = L['studded']['shopkit2_card_' + card]
        studK = (hh / 2) / d['crop']['h']
        studded(canvas, d, hx, hy, hw, hh, studK * 0.9, studK)
    else:
        pic = img(KIT / f'header-{colour}.png')
        k = hh / L['header']['h']
        for px, pw, cx, cw, tile in header_pieces(runner, hw, hh):
            crop = pic.crop((cx, 0, cx + cw, pic.height))
            if tile:
                tw = max(1, round(cw * k))
                t = crop.resize((tw, hh), Image.LANCZOS)
                for xx in range(0, pw, tw):
                    piece = t.crop((0, 0, min(tw, pw - xx), hh))
                    canvas.alpha_composite(piece, (hx + px + xx, hy))
            else:
                canvas.alpha_composite(crop.resize((pw, hh), Image.LANCZOS), (hx + px, hy))
    xin = (hh - lay['close']) // 2
    picture(canvas, KIT / 'close.png', hx + hw - xin - lay['close'], hy + xin, lay['close'], lay['close'])
    words(canvas, title, hx + int(hh * 0.2), hy - int(hh * 0.04), int(hw * 0.6), hh, lay['titleSize'], align='left')
    return x0, y0


def rail(canvas, lay, tabs, selected, icons, inset):
    r = lay['rail']
    for i, (tab, word) in enumerate(tabs):
        s = r['slots'][i]
        size = round(r['icon'] * 0.95) if tab == selected else r['icon']
        cx = s['x'] + s['w'] // 2
        tile = round(r['icon'] * 1.15)
        iy = s['y'] + inset + r['icon'] - size - ((tile - size) // 2 if tab == selected else 0)
        if tab == selected:  # client/KitRail: the lime kit tile behind the active icon
            d = LAYOUT['studded']['shopkit2_button_green']
            k = tile / d['h']
            studded(canvas, d, cx - tile // 2, iy + (size - tile) // 2, tile, tile, k * 0.9, k * 0.6)
        if icons.get(tab):
            picture(canvas, icons[tab], cx - size // 2, iy, size, size)
        words(canvas, word, s['x'] - 6, s['y'] + inset + r['icon'], s['w'] + 12, r['labelSize'] + 2, r['labelSize'])


def backdrop(w, h):
    bg = img(BACKGROUND)
    k = max(w / bg.width, h / bg.height)
    bg = bg.resize((round(bg.width * k), round(bg.height * k)), Image.LANCZOS)
    bg = bg.crop(((bg.width - w) // 2, (bg.height - h) // 2, (bg.width - w) // 2 + w, (bg.height - h) // 2 + h)).filter(ImageFilter.GaussianBlur(7))
    cover = Image.new('RGBA', (w, h), (0, 0, 0, round(255 * 0.06)))
    bg.alpha_composite(cover)
    return bg


LAYOUT = {}
SHOP_ICONS = {'featured': ICONS / 'shop-tab-crystals-v1.png', 'auras': ICONS / 'shop-tab-auras-v2.png', 'trails': ICONS / 'shop-tab-trails-v2.png',
              'eggs': ICONS / 'shop-tile-eggs-v2.png', 'potions': ITEMS / 'potion-swift-sip-512.png'}
INDEX_ICONS = {'dinos': ICONS / 'dinos.png', 'patterns': ICONS / 'index-tab-patterns-v1.png', 'colours': ICONS / 'index-tab-colours-v1.png',
               'fusion': ICONS / 'fusion.png'}
# sample data: three offers of one page (Common, Uncommon, Rare) and two owned potions
POTIONS = [('Swift Sip', 'Common', 'swift-sip', 'Run faster!', 'Lasts 5 min', 20), ('Hearty Brew', 'Uncommon', 'hearty-brew', 'Grow faster!', 'Lasts 7 min', 71),
           ('Prime Feast', 'Rare', 'prime-feast', 'Grow faster!', 'Lasts 10 min', 200)]
OWNED = []  # the Studio test player owns none: the strip says "No potions yet!"


def potion_mock(L, runner, w, h, inset):
    canvas = backdrop(w, h)
    lay = L['potion']
    lay['_inset'] = inset
    x0, y0 = window(canvas, L, lay, 'Potion Shop', 'green', runner)
    for (name, rarity, file, kind, lasts, price), r in zip(POTIONS, lay['cards']):
        x, y, cw, ch = x0 + r['x'], y0 + r['y'], r['w'], r['h']
        d = L['studded']['shopkit2_card_' + rarity.lower()]
        studK = cw / d['w']
        studded(canvas, d, x, y, cw, ch, studK * 0.7, studK)
        e = lay['edge']
        words(canvas, name, x + 4, y + e, cw - 8, lay['nameH'], lay['cardTitle'])
        words(canvas, lasts, x + 4, y + e + lay['nameH'] - 2, cw - 8, lay['rarityH'], lay['rarityText'])
        by = ch - e - lay['button']
        sy = by - lay['innerGap'] - lay['lineH']
        art = min(lay['art'], sy - 2 - lay['artTop'], cw - 4)
        picture(canvas, ITEMS / f'potion-{file}-512.png', x + (cw - art) // 2, y + lay['artTop'] + (sy - 2 - lay['artTop'] - art) // 2, art, art)
        strip(canvas, L, x + lay['stripInset'], y + sy, cw - 2 * lay['stripInset'], lay['lineH'], kind, lay['lineText'])
        button(canvas, L, x + lay['buttonInset'], y + by, cw - 2 * lay['buttonInset'], lay['button'], price=price, text=lay['buttonText'])
    rs, mo = lay['restock'], lay['more']
    words(canvas, 'New potions in 2 min', x0 + rs['x'], y0 + rs['y'], rs['w'], rs['h'], rs['size'], align='left')
    button(canvas, L, x0 + mo['x'], y0 + mo['y'], mo['w'], mo['h'], word='Next >', grey=True, text=lay['buttonText'])
    b = lay.get('band')
    if b:
        strip(canvas, L, x0 + b['x'], y0 + b['y'], b['w'], b['h'], '', b['text'])
        words(canvas, 'Yours', x0 + b['x'] + 14, y0 + b['y'], 90, b['h'], b['text'], align='left')
        ix = x0 + b['x'] + 14 + 90
        if not OWNED:
            words(canvas, 'No potions yet!', ix, y0 + b['y'], b['w'] - ix + x0, b['h'], b['text'], align='left')
        for file, n in OWNED:
            picture(canvas, ITEMS / f'potion-{file}-512.png', ix, y0 + b['y'] + (b['h'] - b['icon']) // 2, b['icon'], b['icon'])
            words(canvas, f'x{n}', ix + b['icon'] - 6, y0 + b['y'], 50, b['h'], b['text'], align='left')
            ix += b['icon'] + 56
    rail(canvas, lay, [('featured', 'Featured'), ('auras', 'Auras'), ('trails', 'Trails'), ('eggs', 'Eggs'), ('potions', 'Potions')], 'potions', SHOP_ICONS, inset)
    return canvas


# sample Index page 1: the first eight species of Config.SpeciesOrder, five found (count), the selected one the Triceratops
DINO_FILES = {'tyrannosaurus': 't-rex'}  # cutout file names that differ from the species id
RARITY = {1: 'common', 2: 'uncommon', 3: 'rare', 4: 'epic', 5: 'legendary'}
INDEX = [('compy', 'Compy', 1, 3), ('triceratops', 'Triceratops', 3, 1), ('tyrannosaurus', 'Tyrannosaurus', 5, 0), ('raptor', 'Raptor', 1, 2),
         ('stegosaurus', 'Stegosaurus', 2, 1), ('ankylosaurus', 'Ankylosaurus', 4, 0), ('archaeopteryx', 'Archaeopteryx', 2, 1), ('baryonyx', 'Baryonyx', 3, 0)]


def index_mock(L, runner, w, h, inset, dinos):
    canvas = backdrop(w, h)
    lay = L['index']
    lay['_inset'] = inset
    x0, y0 = window(canvas, L, lay, 'Dino Index', 'cyan', runner)
    selected = 'triceratops'
    for (sid, name, tier, n), r in zip(INDEX, lay['cards']):
        x, y, cw, ch = x0 + r['x'], y0 + r['y'], r['w'], r['h']
        if sid == selected:
            x, y, cw, ch = x - 3, y - 3, cw + 6, ch + 6
        d = L['studded']['shopkit2_card_' + (RARITY[tier] if n > 0 else 'common')]
        studK = cw / d['w']
        studded(canvas, d, x, y, cw, ch, studK * 0.9, studK)
        if sid == selected:
            ImageDraw.Draw(canvas).rounded_rectangle((x - 2, y - 2, x + cw + 1, y + ch + 1), radius=8, outline=(92, 214, 245, 255), width=4)
        rend = lay['cardRender']
        ry = max(4, (ch - (rend + lay['countText'] + 2)) // 2)
        big = round(rend * (1.4 if n > 0 else 1.3))  # the game zooms its preview boxes; the cutouts have no margin, so a smaller factor
        picture(canvas, Path(dinos) / (DINO_FILES.get(sid, sid) + '.png'), x + (cw - big) // 2, y + ry + (rend - big) // 2, big, big, silhouette=n == 0)
        words(canvas, f'x{n}' if n > 0 else '?', x, y + ry + rend - 2, cw, lay['countText'] + 4, lay['countText'])
    p, pp = lay['panel'], lay['panelParts']
    px, py = x0 + p['x'], y0 + p['y']
    d = L['studded']['shopkit2_card_common']  # the light panel, the rarity as a badge
    studK = p['w'] / d['w']
    studded(canvas, d, px, py, p['w'], p['h'], studK * 0.7, studK)
    words(canvas, 'Triceratops', px + 4, py + pp['edge'], p['w'] - 8, pp['nameText'] + 2, min(pp['nameText'], max(19, int((p['w'] - 12) / (11 * 0.56)))))
    bw = min(p['w'] - 2 * pp['inset'], int(len('Rare') * 0.56 * pp['wordText']) + 24)
    bx0, by0 = px + (p['w'] - bw) // 2, py + pp['edge'] + pp['nameText'] + 2
    db = L['studded']['shopkit2_card_rare']
    studded(canvas, db, bx0, by0, bw, pp['badge'], bw / db['w'] * 0.5, bw / db['w'])
    words(canvas, 'Rare', bx0, by0 - 1, bw, pp['badge'], pp['wordText'])
    by = p['h'] - pp['edge'] - pp['button']
    sy = by - pp['gap'] - pp['line']
    rend = min(pp['render'], sy - pp['gap'] - pp['renderTop'])
    picture(canvas, Path(dinos) / 'triceratops.png', px + (p['w'] - rend) // 2, py + pp['renderTop'] + (sy - pp['gap'] - pp['renderTop'] - rend) // 2, rend, rend)  # fills its box like the zoomed preview
    strip(canvas, L, px + pp['inset'], py + sy, p['w'] - 2 * pp['inset'], pp['line'], 'You have 1', pp['wordText'])
    button(canvas, L, px + pp['inset'], py + by, p['w'] - 2 * pp['inset'], pp['button'], word='View', text=pp['buttonText'])
    bar = lay['bar']
    bx, byy = x0 + bar['x'], y0 + bar['y']
    strip(canvas, L, bx, byy, bar['w'], bar['h'], '', bar['text'])
    fill = round(bar['w'] * 5 / 22)  # exact
    dg = L['studded']['shopkit2_button_green']
    k = bar['h'] / dg['h']
    studded(canvas, dg, bx, byy, fill, bar['h'], k, k)
    words(canvas, 'Found 5/22', bx, byy - int(bar['h'] * 0.05), bar['w'], bar['h'], bar['text'])
    for key, word in (('prev', '<'), ('next', '>')):
        r = lay[key]
        button(canvas, L, x0 + r['x'], y0 + r['y'], r['w'], r['h'], word=word, grey=True, text=pp['buttonText'])
    rail(canvas, lay, [('dinos', 'Dinos'), ('patterns', 'Patterns'), ('colours', 'Colours'), ('fusion', 'Fusion')], 'dinos', INDEX_ICONS, inset)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    ap.add_argument('--size', default='1280x720')
    ap.add_argument('--inset', type=int, default=0, help='top bar px above the ScreenGui (the Studio canvas has 58)')
    ap.add_argument('--dinos', default=str(ROOT / 'resources/ui/v2/dinos/v3'), help='folder of the V3 dino cutouts (<species>.png)')
    ap.add_argument('--out', default=str(ROOT / 'docs/evidence/2026-11-23-menus-slice2'))
    ap.add_argument('--suffix', default='')
    a = ap.parse_args()
    w, h = (int(v) for v in a.size.split('x'))
    L = layouts(a.runner, w, h, a.inset)
    LAYOUT.update(L)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    potion_mock(L, a.runner, w, h, a.inset).convert('RGB').save(out / f'mock-potion-shop{a.suffix}.png')
    index_mock(L, a.runner, w, h, a.inset, a.dinos).convert('RGB').save(out / f'mock-dino-index{a.suffix}.png')
    print('wrote', out / f'mock-potion-shop{a.suffix}.png', out / f'mock-dino-index{a.suffix}.png')


if __name__ == '__main__':
    main()
