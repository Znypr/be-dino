"""Contact sheet for the BD-186 / BD-188 FX textures: each one tinted in 3 mutation colours (MutationLook tint) over a dark
and a light background, the way the runtime multiplies ImageColor3 into a white-on-alpha texture. Evidence image only
(Pillow just composites the finished Blender renders for review; it never draws or edits the textures).

    python tools/fx_contact_sheet.py docs/evidence/2026-10-16-vfx/glow-rings-contact-sheet.png
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'resources/effects/fx-v2'
FILES = ['glowPlate', 'glowPlate-round', 'glowPlate-droplet', 'glowPlate-crescent', 'ringSoft', 'ringShock', 'ringSeismic']
TINTS = [('Dewdrop #78E2BE', (0x78, 0xE2, 0xBE)), ('Ember #FF8C5A', (0xFF, 0x8C, 0x5A)), ('Blood Moon #FF7896', (0xFF, 0x78, 0x96))]
BGS = [('dark', (30, 32, 52)), ('light', (240, 238, 226))]
CELL, PAD, LABEL_W, HEAD_H = 192, 6, 150, 44


def tinted(src, rgb):
    r, g, b, a = src.split()
    mul = lambda band, k: band.point(lambda v: v * k // 255)
    return Image.merge('RGBA', (mul(r, rgb[0]), mul(g, rgb[1]), mul(b, rgb[2]), a))


def main(out):
    cols = len(TINTS) * len(BGS)
    sheet = Image.new('RGB', (LABEL_W + cols * (CELL + PAD) + PAD, HEAD_H + len(FILES) * (CELL + PAD) + PAD), (120, 120, 126))
    d = ImageDraw.Draw(sheet)
    for ci, (tname, _) in enumerate(TINTS):
        d.text((LABEL_W + ci * 2 * (CELL + PAD) + PAD, 8), tname, fill=(255, 255, 255))
        for bi, (bname, _) in enumerate(BGS):
            d.text((LABEL_W + (ci * 2 + bi) * (CELL + PAD) + PAD, 26), bname, fill=(230, 230, 235))
    for ri, name in enumerate(FILES):
        y = HEAD_H + ri * (CELL + PAD) + PAD
        d.text((8, y + CELL // 2 - 5), name, fill=(255, 255, 255))
        src = Image.open(DIR / f'{name}.png').convert('RGBA').resize((CELL, CELL), Image.LANCZOS)
        for ci, (_, rgb) in enumerate(TINTS):
            tex = tinted(src, rgb)
            for bi, (_, bg) in enumerate(BGS):
                x = LABEL_W + (ci * 2 + bi) * (CELL + PAD) + PAD
                tile = Image.new('RGBA', (CELL, CELL), bg + (255,))
                tile.alpha_composite(tex)
                sheet.paste(tile.convert('RGB'), (x, y))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, optimize=True)
    print('wrote', out, sheet.size)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'docs/evidence/2026-10-16-vfx/glow-rings-contact-sheet.png')
