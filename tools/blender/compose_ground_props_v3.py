# Stitch the renders from build_ground_props_v3.py into labelled side-by-side sheets (run with system Python + Pillow).
#   python tools/blender/compose_ground_props_v3.py docs/evidence/2026-10-16-props
import sys, os
from PIL import Image, ImageDraw, ImageFont
d = sys.argv[1] if len(sys.argv) > 1 else "docs/evidence/2026-10-16-props"
tris = {}
tp = os.path.join(d, "tris.txt")
if os.path.exists(tp):
    for line in open(tp):
        k, v = line.split(); tris[k] = v
try: font = ImageFont.truetype("arialbd.ttf", 26); small = ImageFont.truetype("arial.ttf", 20)
except OSError: font = small = ImageFont.load_default()
LABEL = {'v1': 'V1: current props (approx.)', 'v2': 'V2: new ground props'}
CROP = (330, 130, 1270, 700)  # of the 1600x900 render: the camera is the gameplay camera, the crop only trims empty sky and ground
def panel(path, crop):
    im = Image.open(path).convert("RGB").crop(crop)
    return im.resize((1000, round(1000 * im.size[1] / im.size[0])), Image.LANCZOS)
def sheet(name, shot, crop, title):
    ims = []
    for v in ('v1', 'v2'):
        p = os.path.join(d, f"_{v}_{shot}.png")
        if not os.path.exists(p): return
        ims.append((v, panel(p, crop)))
    w, h = ims[0][1].size; bar = 44; gap = 6
    out = Image.new("RGB", (w * 2 + gap, h + bar), (24, 24, 30)); dr = ImageDraw.Draw(out)
    for i, (v, im) in enumerate(ims):
        x = i * (w + gap); out.paste(im, (x, bar))
        t = f"{LABEL[v]}" + (f"   {tris[v]} tris" if (v in tris and shot != 'lineup') else "")
        dr.text((x + 12, 8), t, fill=(255, 255, 255), font=font)
    dr.text((w * 2 - 20 - dr.textlength(title, font=small), 14), title, fill=(200, 200, 210), font=small)
    out.save(os.path.join(d, name), optimize=True); print("wrote", name, out.size)
for shot, title in [('play25-spawn', '25 studs, spawn-size dino'), ('play25-big', '25 studs, 1.5x dino'), ('play40-spawn', '40 studs, spawn-size dino'), ('play40-big', '40 studs, 1.5x dino')]:
    c = CROP if '25' in shot else (400, 190, 1200, 650)
    sheet(f"props-{shot}.png", shot, c, title)
sheet("props-lineup.png", 'lineup', (60, 300, 1540, 690), 'close lineup, 34 studs')
