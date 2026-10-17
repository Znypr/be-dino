# Stitch the renders from build_plants_v3.py into labelled sheets, version 1 (current kit grass, flowers, ferns) on top of
# version 2 (new plants). Run with system Python + Pillow:  python tools/blender/compose_plants_v3.py docs/evidence/2026-10-17-plants
import sys, os
from PIL import Image, ImageDraw, ImageFont
d = sys.argv[1] if len(sys.argv) > 1 else "docs/evidence/2026-10-17-plants"
info = {}
tp = os.path.join(d, "tris.txt")
if os.path.exists(tp):
    for line in open(tp):
        k, t, n = line.split(); info[k] = (t, n)
try: font = ImageFont.truetype("arialbd.ttf", 26); small = ImageFont.truetype("arial.ttf", 20)
except OSError: font = small = ImageFont.load_default()
LABEL = {'v1': 'V1: current kit grass, flowers, ferns', 'v2': 'V2: new plants'}
def panel(path, crop, width=1400):
    im = Image.open(path).convert("RGB").crop(crop)
    return im.resize((width, round(width * im.size[1] / im.size[0])), Image.LANCZOS)
def sheet(name, shot, crop, title, with_tris=True):
    ims = []
    for v in ('v1', 'v2'):
        p = os.path.join(d, f"_{v}_{shot}.png")
        if not os.path.exists(p): return
        ims.append((v, panel(p, crop)))
    w, h = ims[0][1].size; bar = 44; gap = 6
    out = Image.new("RGB", (w, (h + bar) * 2 + gap), (24, 24, 30)); dr = ImageDraw.Draw(out)
    for i, (v, im) in enumerate(ims):
        y = i * (h + bar + gap); out.paste(im, (0, y + bar))
        t = LABEL[v] + (f"   {info[v][0]} tris in {info[v][1]} plants" if (with_tris and v in info) else "")
        dr.text((12, y + 8), t, fill=(255, 255, 255), font=font)
        if i == 0: dr.text((w - 20 - dr.textlength(title, font=small), y + 14), title, fill=(200, 200, 210), font=small)
    out.save(os.path.join(d, name), optimize=True); print("wrote", name, out.size)
for shot, title in [('play25-spawn', '25 studs, spawn-size dino'), ('play25-big', '25 studs, 1.5x dino')]:
    sheet(f"plants-{shot}.png", shot, (40, 330, 1560, 790), title)
for shot, title in [('play40-spawn', '40 studs, spawn-size dino'), ('play40-big', '40 studs, 1.5x dino')]:
    sheet(f"plants-{shot}.png", shot, (260, 340, 1340, 640), title)
sheet("plants-lineup.png", 'lineup', (0, 150, 1600, 780), 'close lineup, 19 studs, spawn-size dino at the left', with_tris=False)
