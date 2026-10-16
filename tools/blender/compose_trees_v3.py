# Stitch the per-variant renders from build_trees_v3.py into labelled side-by-side comparison sheets (run with system Python + Pillow).
import sys, os
from PIL import Image, ImageDraw, ImageFont
d = sys.argv[1] if len(sys.argv) > 1 else "docs/evidence/2026-10-16-trees"
tris = {}
for line in open(os.path.join(d, "tris.txt")) if os.path.exists(os.path.join(d, "tris.txt")) else []:
    k, v = line.split(); tris[k] = v
try: font = ImageFont.truetype("arialbd.ttf", 26); small = ImageFont.truetype("arial.ttf", 20)
except OSError: font = small = ImageFont.load_default()
# crop boxes (of the 1600x900 render): the camera is the real gameplay camera, the crop only trims empty sky/ground
CROP = {'play': (380, 210, 1220, 685), 'scale': (150, 120, 1450, 800), 'grove': (200, 170, 1400, 820), 'close': (300, 60, 1300, 840)}
LABEL = {'cur': 'CURRENT (approx.)', 'v2': 'V2 kit', 'v3': 'V3 REDESIGN'}
for fam in ('broadleaf', 'conifer', 'palm'):
    for shot in ('play', 'scale', 'grove', 'close'):
        ims = []
        for v in ('cur', 'v2', 'v3'):
            p = os.path.join(d, f"_{fam}_{v}_{shot}.png")
            if not os.path.exists(p): break
            im = Image.open(p).convert("RGB"); im = im.crop(CROP[shot]); im = im.resize((900, round(900 * im.size[1] / im.size[0])), Image.LANCZOS); ims.append((v, im))
        if len(ims) < 3: continue
        w, h = ims[0][1].size; bar = 44; gap = 6
        sheet = Image.new("RGB", (w * 3 + gap * 2, h + bar), (24, 24, 30)); dr = ImageDraw.Draw(sheet)
        for i, (v, im) in enumerate(ims):
            x = i * (w + gap); sheet.paste(im, (x, bar))
            t = f"{LABEL[v]}   {tris.get(fam + '_' + v, '')} tris".strip()
            dr.text((x + 12, 8), t, fill=(255, 255, 255), font=font)
        sheet.save(os.path.join(d, f"{fam}-{shot}.png"), optimize=True)
        print("wrote", fam, shot, sheet.size)
