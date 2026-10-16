"""Contact sheet for the BD-131 weather particle textures. Each texture is shown the way the weather code tints it
(WeatherVisuals.client.luau colours multiplied into the white-on-alpha texture) over a dark and a mid sky background, and every
flipbook gets a strip of all 16 frames. Evidence image only: Pillow composites the finished Blender renders for review and never
draws or edits a texture.

    python tools/weather_contact_sheet.py docs/evidence/2026-10-16-vfx/weather-textures-contact-sheet.png
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'resources/effects/fx-v2'
# (texture, weather event, runtime tint, kind). Tints are the Color / Color3 the weather rigs use today (rounded).
ROWS = [
    ('rainStreak', 'Rain, Thunderstorm', (190, 220, 255), 'single'),
    ('lightningBolt', 'Thunderstorm bolt strip (tiles twice)', (225, 215, 255), 'single'),
    ('snowFlakeSheet', 'Blizzard snow', (235, 244, 255), 'sheet'),
    ('ashFlake', 'Volcano ash fall', (70, 64, 68), 'sheet'),
    ('emberSpark', 'Volcano embers, lava sparks', (255, 140, 50), 'sheet'),
    ('dustSand', 'Earthquake dust, sand', (196, 170, 128), 'sheet'),
    ('auroraCurtain', 'Northern Lights curtain (loops)', (110, 255, 200), 'sheet'),
    ('bloodMoonMotes', 'Blood Moon motes', (255, 90, 110), 'sheet'),
    ('bloodMoonDisc', 'Blood Moon disc', (255, 96, 64), 'single'),
]
BGS = [('dark sky', (30, 32, 52)), ('dusk sky', (96, 104, 128))]
GRID, FC = 4, 128
ROW_H, LABEL_W, PAD, SM = 200, 190, 6, 76


def tinted(src, rgb):
    r, g, b, a = src.split()
    mul = lambda band, k: band.point(lambda v: v * k // 255)
    return Image.merge('RGBA', (mul(r, rgb[0]), mul(g, rgb[1]), mul(b, rgb[2]), a))


def on(img, bg):
    tile = Image.new('RGBA', img.size, bg + (255,))
    tile.alpha_composite(img)
    return tile.convert('RGB')


def fit(img, h):
    w = max(1, round(img.size[0] * h / img.size[1]))
    return img.resize((w, h), Image.LANCZOS)


def main(out):
    strip_w = GRID * GRID * (SM + 2)
    strip_x = LABEL_W + 2 * (ROW_H + PAD) + PAD
    width = strip_x + strip_w + PAD
    sheet = Image.new('RGB', (width, 40 + len(ROWS) * (ROW_H + PAD) + PAD), (120, 120, 126))
    d = ImageDraw.Draw(sheet)
    d.text((8, 12), 'BD-131 weather textures, tinted as WeatherVisuals tints them', fill=(255, 255, 255))
    for ri, (name, event, rgb, kind) in enumerate(ROWS):
        y = 40 + ri * (ROW_H + PAD) + PAD
        d.text((8, y + 6), name, fill=(255, 255, 255))
        d.text((8, y + 22), event, fill=(225, 225, 232))
        d.text((8, y + 38), f'tint {rgb[0]},{rgb[1]},{rgb[2]}', fill=(225, 225, 232))
        src = Image.open(DIR / f'{name}.png').convert('RGBA')
        x = LABEL_W
        if name == 'lightningBolt':
            two = Image.new('RGBA', (src.size[0] * 2, src.size[1]), (0, 0, 0, 0))
            two.alpha_composite(src, (0, 0))
            two.alpha_composite(src, (src.size[0], 0))
            tex = tinted(two, rgb)
            for bi, (_, bg) in enumerate(BGS):
                strip = on(tex, bg).resize((2 * ROW_H + PAD, ROW_H // 2 - 4), Image.LANCZOS)
                sheet.paste(strip, (x, y + bi * (ROW_H // 2)))
            x += 2 * (ROW_H + PAD) + PAD
            continue
        tex = tinted(src, rgb)
        for bi, (bname, bg) in enumerate(BGS):
            tile = on(fit(tex, ROW_H) if kind == 'single' else tex.resize((ROW_H, ROW_H), Image.LANCZOS), bg)
            sheet.paste(tile, (x, y))
            x += ROW_H + PAD
        if kind == 'sheet':
            for fi in range(GRID * GRID):
                fr = tex.crop(((fi % GRID) * FC, (fi // GRID) * FC, (fi % GRID + 1) * FC, (fi // GRID + 1) * FC))
                cell = on(fr.resize((SM, SM), Image.LANCZOS), BGS[0][1] if name != 'ashFlake' else BGS[1][1])
                sheet.paste(cell, (strip_x + fi * (SM + 2), y + (ROW_H - SM) // 2))
    d.text((strip_x + 8, 24), 'animation strip: frames 1-16 (ash on the dusk sky)', fill=(255, 255, 255))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, optimize=True)
    print('wrote', out, sheet.size)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'docs/evidence/2026-10-16-vfx/weather-textures-contact-sheet.png')
