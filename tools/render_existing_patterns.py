#!/usr/bin/env python3
"""BD-1034: write the pattern masks that are already in the game as black-and-white tile pictures.

The 8 gene patterns are made in code (src/shared/LowPolyPattern.luau, the UV-space mask). This runs that
real module with the Luau runner, then cuts each 0..1 mask at the share of secondary colour a dino with a
50/50 colour blend gets (LowPolyPattern.coverage), so white = colour 2 and black = colour 1, as in the game.
The pictures are only a comparison aid for tools/pattern_similarity.py, not new art.

  python tools/render_existing_patterns.py resources/patterns/existing --runner C:/.../luau.exe
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = 12345
# secondary-colour share at a 50/50 blend: area patterns follow the blend, spot-like ones are capped (Pattern.Coverage)
COVER = {"03_round_spots": 0.275, "08_freckles": 0.20, "07_diamond_scales": 0.25}
DUMP = """
local P = require("./LowPolyPattern")
for _, id in ipairs(P.Ids) do
  print("ID " .. id)
  for y = 0, 255 do
    local r = table.create(256)
    for x = 0, 255 do r[x + 1] = string.format("%.3f", math.clamp(P.mask(id, x, y, __SEED__), 0, 1)) end
    print(table.concat(r, " "))
  end
end
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--runner", required=True, help="luau.exe")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(os.path.join(ROOT, "src", "shared", "LowPolyPattern.luau"), os.path.join(tmp, "LowPolyPattern.luau"))
        script = os.path.join(tmp, "dump.luau")
        with open(script, "w") as f:
            f.write(DUMP.replace("__SEED__", str(SEED)))
        out = subprocess.run([a.runner, script], capture_output=True, text=True, check=True).stdout.splitlines()
    os.makedirs(a.out_dir, exist_ok=True)
    cur, rows = None, []
    def flush():
        if cur and cur != "01_blank":
            m = np.array(rows, dtype=np.float32)
            share = COVER.get(cur, 0.5)
            cut = np.quantile(m, 1 - share)
            bw = (m > cut).astype(np.uint8) * 255
            Image.fromarray(bw).save(os.path.join(a.out_dir, cur + ".png"))
            print("%s white=%.2f" % (cur, bw.mean() / 255))
    for line in out:
        if line.startswith("ID "):
            flush()
            cur, rows = line[3:].strip(), []
        elif line.strip():
            rows.append([float(v) for v in line.split()])
    flush()


if __name__ == "__main__":
    sys.exit(main())
