"""Contact sheet for the BD-186 / BD-188 FX textures: each one tinted in 3 mutation colours (MutationLook tint) over a dark
and a light background, the way the runtime multiplies ImageColor3 into a white-on-alpha texture. Evidence image only
(Pillow just composites the finished Blender renders for review; it never draws or edits the textures).

    python tools/fx_contact_sheet.py docs/evidence/2026-10-16-vfx/glow-rings-contact-sheet.png
    python tools/fx_contact_sheet.py --sheets docs/evidence/2026-10-16-vfx/smoke-motifs-contact-sheet.png

`--sheets` is the BD-187 / BD-189 version: each 512 px flipbook sheet tinted in the same 3 mutation colours over a dark
background, plus an animated-frame strip (all 16 frames in the sheet's own mutation colour) and an animated GIF of all ten
sheets playing. The aurora ribbons are coloured, so they are shown untinted.
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


# ------------------------------------------------------------------------------------------------ flipbook sheets
# (sheet, the mutation colour it is made for, or None for the coloured aurora)
SHEETS = [
    ('smokeSoft', ('Dewdrop', (0x78, 0xE2, 0xBE))), ('smokeDense', ('Ember', (0xFF, 0x8C, 0x5A))),
    ('smokeWispy', ('Frost', (0xA0, 0xE8, 0xFF))), ('motifDroplets', ('Dewdrop', (0x78, 0xE2, 0xBE))),
    ('motifSoftSparks', ('Charged', (0xFF, 0xE2, 0x78))), ('motifSnowCrystals', ('Frost', (0xA0, 0xE8, 0xFF))),
    ('motifPebbles', ('Seismic', (0xE2, 0xBE, 0x82))), ('motifEmbers', ('Ember', (0xFF, 0x8C, 0x5A))),
    ('motifAurora', None), ('motifCrimson', ('Blood Moon', (0xFF, 0x78, 0x96))),
]
GRID, FCELL = 4, 128


def frames_of(sheet):
    return [sheet.crop(((i % GRID) * FCELL, (i // GRID) * FCELL, (i % GRID + 1) * FCELL, (i // GRID + 1) * FCELL))
            for i in range(GRID * GRID)]


def on_bg(img, bg=(30, 32, 52)):
    tile = Image.new('RGBA', img.size, bg + (255,))
    tile.alpha_composite(img)
    return tile


def sheets_main(out):
    big, small, label_w, pad = 192, 64, 150, 6
    strip_w = GRID * GRID * (small + 2)
    width = label_w + len(TINTS) * (big + pad) + pad + strip_w + pad
    head = 44
    sheet = Image.new('RGB', (width, head + len(SHEETS) * (big + pad) + pad), (120, 120, 126))
    d = ImageDraw.Draw(sheet)
    for ci, (tname, _) in enumerate(TINTS):
        d.text((label_w + ci * (big + pad) + pad, 8), tname, fill=(255, 255, 255))
    d.text((label_w + len(TINTS) * (big + pad) + pad, 8), 'animation strip: frames 1-16 in the sheet colour', fill=(255, 255, 255))
    gif_frames = [[] for _ in range(GRID * GRID)]
    for ri, (name, natural) in enumerate(SHEETS):
        y = head + ri * (big + pad) + pad
        d.text((8, y + big // 2 - 5), name, fill=(255, 255, 255))
        src = Image.open(DIR / f'{name}.png').convert('RGBA')
        if natural is None:
            d.text((8, y + big // 2 + 8), '(coloured, no tint)', fill=(230, 230, 235))
        for ci, (_, rgb) in enumerate(TINTS):
            tex = src if natural is None else tinted(src, rgb)
            tile = on_bg(tex.resize((big, big), Image.LANCZOS))
            sheet.paste(tile.convert('RGB'), (label_w + ci * (big + pad) + pad, y))
        tex = src if natural is None else tinted(src, natural[1])
        for fi, fr in enumerate(frames_of(tex)):
            cell = on_bg(fr.resize((small, small), Image.LANCZOS))
            sheet.paste(cell.convert('RGB'), (label_w + len(TINTS) * (big + pad) + pad + fi * (small + 2), y + (big - small) // 2))
            gif_frames[fi].append(on_bg(fr).convert('RGB'))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, optimize=True)
    print('wrote', out, sheet.size)
    # animated GIF: all ten flipbooks playing at once (5 x 2 tiles at 128 px, 100 ms per frame)
    tiles = []
    for fr in gif_frames:
        g = Image.new('RGB', (5 * FCELL, 2 * FCELL), (30, 32, 52))
        for k, tile in enumerate(fr):
            g.paste(tile, ((k % 5) * FCELL, (k // 5) * FCELL))
        tiles.append(g.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
    gif = Path(out).with_name('smoke-motifs-animated.gif')
    tiles[0].save(gif, save_all=True, append_images=tiles[1:], duration=100, loop=0, optimize=True)
    print('wrote', gif, gif.stat().st_size, 'bytes')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--sheets':
        sheets_main(sys.argv[2] if len(sys.argv) > 2 else ROOT / 'docs/evidence/2026-10-16-vfx/smoke-motifs-contact-sheet.png')
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'docs/evidence/2026-10-16-vfx/glow-rings-contact-sheet.png')
