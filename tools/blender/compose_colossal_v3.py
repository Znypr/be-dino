"""BD-474: compose the raw Blender frames of build_colossal_v3.py (`-- render`, `-- grove`, `-- lod`) into the comparison sheets.
Run: python tools/blender/compose_colossal_v3.py <dir with the _*.png frames> [out dir]   (default out dir = the same folder)
Sheets (top row = the scaled stand-in, bottom row = the new colossal mesh):
  colossal-<family>-gameplay.png   gameplay camera with a spawn dino, a size 1.5 dino and a max size 4 dino
  colossal-lineup.png              side-on height lineup, three Compies (spawn, 1.5, max 4) at the trunk, three families
  colossal-grove-skyline.png       the three families together, seen from the spawn dino at the gameplay minimum
  colossal-lod.png                 LOD0 vs LOD1 close, and both at 300 studs
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

src = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else src
CELL = (640, 360)
FAMS = ["broadleaf", "conifer", "palm"]
SHOTS = [("spawn", "spawn size 1"), ("s15", "size 1.5"), ("s4", "max size 4")]


def font(n):
    for f in ("arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, n)
        except OSError:
            pass
    return ImageFont.load_default()


def load(name, size=CELL):
    p = os.path.join(src, name)
    return Image.open(p).convert("RGB").resize(size, Image.LANCZOS) if os.path.exists(p) else Image.new("RGB", size, (90, 90, 90))


def label(im, text, x=8, y=8):
    d = ImageDraw.Draw(im)
    f = font(20)
    w = d.textlength(text, font=f)
    d.rectangle([x - 4, y - 3, x + w + 6, y + 26], fill=(20, 40, 30))
    d.text((x, y), text, font=f, fill=(255, 255, 255))


def grid(rows, cols, cells, size=CELL):
    sheet = Image.new("RGB", (cols * size[0], rows * size[1]))
    for (r, c), im in cells.items():
        sheet.paste(im, (c * size[0], r * size[1]))
    return sheet


def sheet_family(fam):
    cells = {}
    for c, (shot, title) in enumerate(SHOTS):
        for r, var in enumerate(("old", "new")):
            im = load(f"_{fam}_{var}_{shot}.png")
            label(im, ("scaled stand-in, " if var == "old" else "new colossal, ") + title)
            cells[(r, c)] = im
    grid(2, 3, cells).save(os.path.join(out, f"colossal-{fam}-gameplay.png"))


def sheet_lineup():
    cells = {}
    for c, fam in enumerate(FAMS):
        for r, var in enumerate(("old", "new")):
            im = load(f"_{fam}_{var}_lineup.png")
            label(im, f"{fam}: " + ("scaled stand-in" if var == "old" else "new colossal"))
            cells[(r, c)] = im
    grid(2, 3, cells).save(os.path.join(out, "colossal-lineup.png"))


def sheet_grove():
    big = (800, 400)
    cells = {}
    for r, var in enumerate(("old", "new")):
        im = load(f"_grove_{var}.png", big)
        label(im, "scaled stand-ins" if var == "old" else "new colossal trees")
        cells[(r, 0)] = im
    grid(2, 1, cells, big).save(os.path.join(out, "colossal-grove-skyline.png"))


def sheet_lod():
    cells = {}
    for c, fam in enumerate(FAMS):
        for r, (name, title) in enumerate([("lod_%s_0" % fam, "LOD0 close"), ("lod_%s_1" % fam, "LOD1 close"), ("far_%s_0" % fam, "LOD0 at 300 studs"), ("far_%s_1" % fam, "LOD1 at 300 studs")]):
            im = load(f"_{name}.png")
            label(im, f"{fam} {title}")
            cells[(r, c)] = im
    grid(4, 3, cells).save(os.path.join(out, "colossal-lod.png"))


if __name__ == "__main__":
    os.makedirs(out, exist_ok=True)
    for f in FAMS:
        sheet_family(f)
    sheet_lineup()
    if os.path.exists(os.path.join(src, "_grove_new.png")):
        sheet_grove()
    if os.path.exists(os.path.join(src, "_lod_broadleaf_0.png")):
        sheet_lod()
    print("composed into", out)
