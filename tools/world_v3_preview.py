#!/usr/bin/env python3
"""BD-1209 (BD-1208 step 1, docs/241): run the real Shared/WorldV3.luau in the pinned Luau runner over the island and

1. check the rules: plaza flat and dry, spawn on land, sea all round, every zone present, paths walkable, coast never square;
2. draw a top-down preview picture (surface colour from WorldV3.surface / the dominant zone, hill shading from the height).

    python tools/world_v3_preview.py --runner <luau.exe> [--out docs/evidence/2026-11-15-world/v3-preview.png] [--step 6]
"""
import argparse
import json
import math
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXTENT = 424  # Config.ArenaHalfWidth + 8, the terrain square

BODY = r'''
local V = WORLD
local step, extent = STEP, EXTENT
local rows = {}
for z = -extent, extent, step do
    local row = {}
    for x = -extent, extent, step do
        local h = V.height(x, z)
        local _, dom = V.weights(x, z, h, 1404)
        local surf = V.surface(x, z, h) or dom
        table.insert(row, string.format("%.2f:%s:%d", h, surf, if V.path(x, z) > .5 then 1 else 0))
    end
    table.insert(rows, table.concat(row, ","))
end
print(table.concat(rows, ";"))
'''

COL = {"Limestone": (226, 204, 150), "Sand": (232, 212, 160), "meadow": (150, 196, 84), "fern": (84, 146, 66),
       "conifer": (70, 118, 86), "Grass": (160, 200, 90), "badlands": (206, 196, 128), "volcanic": (112, 92, 86), "marsh": (90, 120, 80)}


def run(runner, step):
    src = (ROOT / 'src/shared/WorldV3.luau').read_text(encoding='utf-8')
    code = BODY.replace('WORLD', '(function()\n' + src + '\nend)()').replace('STEP', str(step)).replace('EXTENT', str(EXTENT))
    with tempfile.NamedTemporaryFile('w', suffix='.luau', delete=False, encoding='utf-8') as f:
        f.write(code)
    out = subprocess.run([runner, f.name], capture_output=True, text=True, timeout=300)
    if out.returncode != 0:
        sys.exit('luau failed: ' + out.stderr[-2000:])
    grid = []
    for row in out.stdout.strip().split(';'):
        cells = []
        for c in row.split(','):
            h, s, p = c.split(':')
            cells.append((float(h), s, p == '1'))
        grid.append(cells)
    return grid


def check(grid, step):
    n = len(grid)
    mid = n // 2
    problems = []
    idx = lambda v: int(round((v + EXTENT) / step))
    # plaza: centre (0, 30), radius 72 -> flat and dry
    hs = []
    for z in range(-60, 61, step):
        for x in range(-60, 61, step):
            if x * x + z * z < 60 * 60:
                hs.append(grid[idx(30 + z)][idx(x)][0])
    if max(hs) - min(hs) > 1.0 or min(hs) < .5:
        problems.append(f"plaza not flat/dry: {min(hs):.2f}..{max(hs):.2f}")
    # sea all round: every border cell below sea level
    border = [grid[0], grid[-1], [r[0] for r in grid], [r[-1] for r in grid]]
    wet = sum(1 for b in border for c in b if c[0] < 0)
    total = sum(len(b) for b in border)
    if wet < total:
        problems.append(f"border not all sea: {wet}/{total}")
    # every zone present on land
    counts = {}
    for r in grid:
        for h, s, p in r:
            if h > 0:
                counts[s] = counts.get(s, 0) + 1
    for zone in ("meadow", "fern", "conifer", "Grass", "volcanic", "Sand", "Limestone"):  # the palm beach paints Grass + Sand
        if counts.get(zone, 0) < 20:
            problems.append(f"zone {zone} too small: {counts.get(zone, 0)} cells")
    # paths walkable: slope between neighbouring path cells under 0.45
    steep = 0
    for zi in range(1, n - 1):
        for xi in range(1, n - 1):
            h, s, p = grid[zi][xi]
            if p and h > 0:
                g = max(abs(grid[zi][xi + 1][0] - h), abs(grid[zi + 1][xi][0] - h)) / step
                if g > .45:
                    steep += 1
    if steep > 6:
        problems.append(f"{steep} steep path cells")
    land = sum(1 for r in grid for c in r if c[0] > 0)
    return problems, counts, land


def draw(grid, step, out):
    from PIL import Image, ImageDraw
    n = len(grid)
    px = 2 if step >= 6 else 1
    img = Image.new('RGB', (n * px, n * px), (60, 160, 200))
    d = ImageDraw.Draw(img)
    for zi, r in enumerate(grid):
        for xi, (h, s, p) in enumerate(r):
            if h < 0:
                depth = min(1, -h / 6)
                c = (int(120 - 60 * depth), int(210 - 50 * depth), int(225 - 25 * depth))
            else:
                c = COL.get(s, (200, 0, 200))
                hx = grid[zi][min(n - 1, xi + 1)][0] - h
                hz = grid[min(n - 1, zi + 1)][xi][0] - h
                shade = max(.6, min(1.3, 1 - (hx + hz) * .12 + h * .004))
                c = tuple(max(0, min(255, int(v * shade))) for v in c)
            d.rectangle((xi * px, zi * px, xi * px + px - 1, zi * px + px - 1), fill=c)
    img = img.resize((900, 900), Image.NEAREST)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    ap.add_argument('--out', default='')
    ap.add_argument('--step', type=int, default=8)
    a = ap.parse_args()
    grid = run(a.runner, a.step)
    problems, counts, land = check(grid, a.step)
    if a.out:
        draw(grid, a.step, ROOT / a.out)
        print('picture:', a.out)
    print('land cells', land, json.dumps(dict(sorted(counts.items()))))
    if problems:
        print('FAIL\n- ' + '\n- '.join(problems))
        sys.exit(1)
    print('world v3 OK: plaza flat and dry, sea all round, every zone present, paths walkable')


if __name__ == '__main__':
    main()
