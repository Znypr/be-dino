"""BD-178: contact sheet of the 10 trail icons (Blender renders, resources/ui/v2/icons/trail-<id>-v1.png).

Each icon is shown at 128, 64 and 32 px on a light and a dark UI panel, plus the 32 px version enlarged 4x with nearest-neighbour so the
pixels can be judged. Sizes below 128 are box-filtered (a mipmap-style downscale, the way the engine minifies a 128 px image); this is
layout only, the icon pixels themselves come from Blender. Output: docs/evidence/2026-10-17-trails/trail-icons-contact-sheet.png
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / 'resources/ui/v2/icons'
OUT = ROOT / 'docs/evidence/2026-10-17-trails/trail-icons-contact-sheet.png'
ORDER = [('white', 'puff'), ('fern', 'leaf'), ('tidal', 'bubbles'), ('ember', 'flame'), ('violet', 'pulse rings'), ('electric', 'arc'), ('frost', 'comet'), ('solar', 'sun'), ('nova', 'sparkle'), ('astra', 'star')]
LIGHT = (242, 244, 250)   # light UI card
DARK = (42, 40, 53)       # docs/114 panel #2A2835
INK = (30, 34, 52)
PAD = 14
CELLS = [128, 64, 32, 128]   # the last is the 32 px icon enlarged 4x (nearest)


def cell(icon, size, bg, zoom=False):
    img = icon.resize((size, size), Image.BOX) if size != 128 or zoom else icon
    if zoom:
        img = icon.resize((32, 32), Image.BOX).resize((128, 128), Image.NEAREST)
    return img


def main():
    font = ImageFont.load_default(size=15)
    small = ImageFont.load_default(size=13)
    block_w = sum(CELLS) + PAD * (len(CELLS) + 1)
    label_w = 190
    head_h = 58
    row_h = 128 + PAD * 2
    width = label_w + block_w * 2
    sheet = Image.new('RGB', (width, head_h + row_h * len(ORDER)), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for b, (name, bg) in enumerate((('Light UI (#F2F4FA)', LIGHT), ('Dark UI (#2A2835)', DARK))):
        x0 = label_w + b * block_w
        d.rectangle([x0, head_h, x0 + block_w - 1, sheet.height], fill=bg)
        d.text((x0 + PAD, 8), name, fill=INK, font=font)
        x = x0 + PAD
        for size, zoomed in zip(CELLS, (False, False, False, True)):
            d.text((x, 34), '32 px x4' if zoomed else f'{size} px', fill=INK, font=small)
            x += size + PAD
    d.text((PAD, 8), 'BD-178 trail icons', fill=INK, font=font)
    d.text((PAD, 34), 'Blender renders', fill=INK, font=small)
    for r, (mid, shape) in enumerate(ORDER):
        icon = Image.open(ICONS / f'trail-{mid}-v1.png').convert('RGBA')
        assert icon.size == (128, 128), mid
        y = head_h + r * row_h
        d.text((PAD, y + row_h // 2 - 18), shape, fill=INK, font=font)
        d.text((PAD, y + row_h // 2 + 2), mid, fill=(90, 94, 110), font=small)
        for b, bg in enumerate((LIGHT, DARK)):
            x = label_w + b * block_w + PAD
            for size, zoomed in zip(CELLS, (False, False, False, True)):
                img = cell(icon, size, bg, zoomed)
                yy = y + PAD + (128 - img.height) // 2
                sheet.paste(img, (x, yy), img)
                x += size + PAD
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print('wrote', OUT.relative_to(ROOT), sheet.size)


if __name__ == '__main__':
    main()
