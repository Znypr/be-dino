"""BD-047: contact sheet of the Crystal Shop art (Blender renders in resources/ui/v2/icons/).

Top: the five tab icons (the Eggs one is the green-spotted egg) at 128, 64, 48 and 32 px on a light and a dark UI panel, plus the 32 px
version enlarged 4x with nearest-neighbour so its pixels can be judged. Bottom: the five landing tiles at 256 px (light panel) and at 128 px
(dark panel, about what a phone shows). Sizes below the source are box-filtered (a mipmap-style downscale, the way the engine minifies);
this is layout only, every icon pixel comes from Blender. No text is baked into any image.
Output: docs/evidence/2026-10-17-shop/shop-tiles-contact-sheet.png
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / 'resources/ui/v2/icons'
OUT = ROOT / 'docs/evidence/2026-10-17-shop/shop-tiles-contact-sheet.png'
TABS = [('auras', 'shop-tab-auras-v1.png', 'Auras tab'), ('trails', 'shop-tab-trails-v1.png', 'Trails tab'),
        ('eggs', 'egg-green-spotted-v1.png', 'Eggs tab + product'), ('conditions', 'shop-tab-conditions-v1.png', 'Conditions tab'),
        ('crystals', 'shop-tab-crystals-v1.png', 'Crystals tab')]
TILES = [(t, f'shop-tile-{t}-v1.png') for t in ('auras', 'trails', 'eggs', 'conditions', 'crystals')]
LIGHT = (242, 244, 250)   # light UI card
DARK = (42, 40, 53)       # docs/114 panel #2A2835
INK = (30, 34, 52)
PAD = 14
SIZES = [128, 64, 48, 32]


def fit(icon, size):
    return icon.resize((size, size), Image.BOX)


def main():
    font = ImageFont.load_default(size=15)
    small = ImageFont.load_default(size=13)
    cells = SIZES + [128]   # last = 32 px enlarged 4x
    block_w = sum(cells) + PAD * (len(cells) + 1)
    label_w = 170
    head_h = 58
    row_h = 128 + PAD * 2
    width = max(label_w + block_w * 2, 5 * (256 + PAD) + PAD)
    tiles_h = 30 + 256 + PAD * 2 + 30 + 128 + PAD * 2
    sheet = Image.new('RGB', (width, head_h + row_h * len(TABS) + tiles_h), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 8), 'BD-047 Crystal Shop art', fill=INK, font=font)
    d.text((PAD, 34), 'Blender renders', fill=INK, font=small)
    for b, (name, bg) in enumerate((('Light UI (#F2F4FA)', LIGHT), ('Dark UI (#2A2835)', DARK))):
        x0 = label_w + b * block_w
        d.rectangle([x0, head_h, x0 + block_w - 1, head_h + row_h * len(TABS) - 1], fill=bg)
        d.text((x0 + PAD, 8), name, fill=INK, font=font)
        x = x0 + PAD
        for size, zoomed in zip(cells, [False] * 4 + [True]):
            d.text((x, 34), '32 px x4' if zoomed else f'{size} px', fill=INK, font=small)
            x += size + PAD
    for r, (_tab, fn, label) in enumerate(TABS):
        icon = Image.open(ICONS / fn).convert('RGBA')
        y = head_h + r * row_h
        d.text((PAD, y + row_h // 2 - 18), label, fill=INK, font=font)
        d.text((PAD, y + row_h // 2 + 2), fn.replace('-v1.png', ''), fill=(90, 94, 110), font=small)
        for b in range(2):
            x = label_w + b * block_w + PAD
            for size, zoomed in zip(cells, [False] * 4 + [True]):
                img = fit(icon, 32).resize((128, 128), Image.NEAREST) if zoomed else fit(icon, size)
                sheet.paste(img, (x, y + PAD + (128 - img.height) // 2), img)
                x += img.width + PAD
    y0 = head_h + row_h * len(TABS)
    d.rectangle([0, y0, width, sheet.height], fill=LIGHT)
    d.text((PAD, y0 + 6), 'Landing tiles, 256 px on a light panel', fill=INK, font=font)
    for i, (_t, fn) in enumerate(TILES):
        img = Image.open(ICONS / fn).convert('RGBA')
        sheet.paste(img, (PAD + i * (256 + PAD), y0 + 30), img)
    y1 = y0 + 30 + 256 + PAD * 2
    d.rectangle([0, y1, width, sheet.height], fill=DARK)
    d.text((PAD, y1 + 6), 'The same tiles at 128 px on a dark panel (about phone size)', fill=(235, 238, 245), font=font)
    for i, (_t, fn) in enumerate(TILES):
        img = fit(Image.open(ICONS / fn).convert('RGBA'), 128)
        sheet.paste(img, (PAD + i * (256 + PAD), y1 + 30), img)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print('wrote', OUT.relative_to(ROOT), sheet.size)


if __name__ == '__main__':
    main()
