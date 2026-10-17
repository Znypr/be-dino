# Stitch the renders from build_cave_rockforms_v3.py into one labelled sheet (run with system Python + Pillow).
#   python tools/blender/compose_cave_rockforms_v3.py docs/evidence/2026-10-17-cave
# Writes cave-rockforms-sheet.png: row 1 = the wall today (approximated) vs with the six rock forms, row 2 = the gate niche today vs with the
# arch frame and its warm light, row 3 = the six forms and the arch close up in daylight (so the shapes can be judged apart from the cave mood).
import sys, os
from PIL import Image, ImageDraw, ImageFont
d = sys.argv[1] if len(sys.argv) > 1 else "docs/evidence/2026-10-17-cave"
stats = {}
tp = os.path.join(d, "tris.txt")
if os.path.exists(tp):
    for line in open(tp):
        parts = line.split(); stats[parts[0]] = dict(p.split("=") for p in parts[1:])
try: font = ImageFont.truetype("arialbd.ttf", 26); small = ImageFont.truetype("arial.ttf", 20)
except OSError: font = small = ImageFont.load_default()
W = 900; GAP = 6; BAR = 44
def panel(name, w=W):
    im = Image.open(os.path.join(d, name)).convert("RGB")
    return im.resize((w, round(w * im.size[1] / im.size[0])), Image.LANCZOS)
def pair(left, right, ltitle, rtitle, lkey, rkey):
    a, b = panel(left), panel(right)
    out = Image.new("RGB", (W * 2 + GAP, a.size[1] + BAR), (24, 24, 30)); dr = ImageDraw.Draw(out)
    out.paste(a, (0, BAR)); out.paste(b, (W + GAP, BAR))
    for x, t, k in ((12, ltitle, lkey), (W + GAP + 12, rtitle, rkey)):
        s = stats.get(k)
        extra = (f"   +{int(s['tris'])} tris" if s and int(s['tris']) else "") + (f"   render luminance {float(s['luminance']):.2f}" if s else "")
        dr.text((x, 8), t + extra, fill=(255, 255, 255), font=font)
    return out
rows = [
    pair("_wall_v1.png", "_wall_v2.png", "Wall today (approx.)", "With 6 wall rock forms", "wall_v1", "wall_v2"),
    pair("_arch_v1.png", "_arch_v2.png", "Gate today: faint 6 stud niche", "With arch frame + hooks + warm light", "arch_v1", "arch_v2"),
]
a = panel("_lineup.png", W); b = panel("_archclose.png", W)
h = max(a.size[1], b.size[1])
row3 = Image.new("RGB", (W * 2 + GAP, h + BAR), (24, 24, 30)); dr = ImageDraw.Draw(row3)
row3.paste(a, (0, BAR)); row3.paste(b, (W + GAP, BAR))
dr.text((12, 8), "The six rock forms (daylight, close)", fill=(255, 255, 255), font=font)
dr.text((W + GAP + 12, 8), "Gate arch frame: keystone, two lantern hooks", fill=(255, 255, 255), font=font)
rows.append(row3)
H = sum(r.size[1] for r in rows) + GAP * (len(rows) - 1)
sheet = Image.new("RGB", (W * 2 + GAP, H), (24, 24, 30)); y = 0
for r in rows:
    sheet.paste(r, (0, y)); y += r.size[1] + GAP
sheet.save(os.path.join(d, "cave-rockforms-sheet.png"), optimize=True)
print("wrote cave-rockforms-sheet.png", sheet.size)
