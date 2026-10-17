"""Execute the pure BD-253 camera occlusion rules (src/shared/CameraOcclusion.luau) with the pinned Luau runtime.
Covers which props qualify, the transparency curve (smooth, Reduce Motion snap, exact restore) and the caps.
Instances are not executed here; the Studio before/after check is in docs/102 and the kanban row.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]

BODY = r'''
local cam = {x = 0, y = 6, z = 0}
local dino = {x = 0, y = 2, z = 20}
local function prop(x, y, z, sx, sy, sz) return {x = x, y = y, z = z, sx = sx, sy = sy, sz = sz} end
-- A tree standing between camera and dino qualifies; one behind the dino, beside the path or far to the side does not.
assert(M.qualifies(prop(0, 8, 10, 8, 16, 8), cam, dino), "tree between camera and dino must fade")
assert(not M.qualifies(prop(0, 8, 40, 8, 16, 8), cam, dino), "tree behind the dino must stay solid")
assert(not M.qualifies(prop(25, 8, 10, 8, 16, 8), cam, dino), "tree well off the line must stay solid")
assert(not M.qualifies(prop(0, 8, -40, 8, 16, 8), cam, dino), "tree behind the camera and far away must stay solid")
-- The camera inside a canopy (leaves in the lens) qualifies even if the dino line is clear.
assert(M.qualifies(prop(0, 6, 0, 10, 12, 10), cam, {x = 30, y = 2, z = 0}), "camera inside a canopy must fade it")
-- A canopy above the dino: the segment dives through it.
assert(M.qualifies(prop(0, 12, 15, 14, 8, 14), {x = 0, y = 22, z = 0}, dino), "canopy over the line must fade")
-- Ground cover never qualifies, however close.
assert(not M.qualifies(prop(0, 0.5, 10, 0.8, 0.8, 0.8), cam, dino), "pebble")
assert(not M.qualifies(prop(0, 0.4, 10, 6, 1.0, 6), cam, dino), "flat ground patch")
-- BD-513: the biggest dino's default camera (BIG Ankylosaurus at growth scale 4.8: 89 studs, CameraFraming.MaxDistance 90) still fades props
-- between camera and dino; the range is above that distance and still off for a cinematic camera.
assert(M.MaxRange >= 100, "range covers the 90 stud default camera of a BIG dino")
assert(M.qualifies(prop(0, 8, 45, 8, 16, 8), {x = 0, y = 6, z = 0}, {x = 0, y = 2, z = 90}), "tree between a 90 stud camera and the dino must fade")
assert(not M.qualifies(prop(0, 8, 50, 8, 16, 8), {x = 0, y = 6, z = 0}, {x = 0, y = 2, z = M.MaxRange + 10}), "beyond the range nothing fades")
-- Camera far from the dino (cinematic, stuck camera): nothing qualifies; NaN safe.
assert(not M.qualifies(prop(0, 8, 100, 8, 16, 8), {x = 0, y = 6, z = 0}, {x = 0, y = 2, z = 200}))
assert(not M.qualifies(prop(0, 8, 10, 8, 16, 8), {x = 0 / 0, y = 0, z = 0}, dino))
-- A rock between them qualifies too (size above ground cover).
assert(M.qualifies(prop(0, 1.5, 10, 4, 3, 4), {x = 0, y = 2, z = 0}, {x = 0, y = 2, z = 20}), "rock on the line")
-- Sort key is the camera distance.
local near, far = M.qualifies(prop(0, 8, 5, 8, 16, 8), cam, dino), M.qualifies(prop(0, 8, 14, 8, 16, 8), cam, dino)
assert(near and far and near < far)

-- Transparency target stays in the owner's 0.7..0.85 window.
assert(M.FadeTransparency >= 0.7 and M.FadeTransparency <= 0.85)
-- Curve: monotonic, bounded, never overshoots, reaches exactly the target; restores to exactly 0.
local v = 0
for i = 1, 400 do
 local n = M.step(v, M.FadeTransparency, 1 / 60, false)
 assert(n >= v and n <= M.FadeTransparency, "fade must ease monotonically")
 v = n
end
assert(v == M.FadeTransparency, "fade must land exactly on the target")
local first = M.step(0, M.FadeTransparency, 1 / 60, false) assert(first > 0 and first < M.FadeTransparency / 2, "must ease, not jump")
for i = 1, 400 do local n = M.step(v, 0, 1 / 60, false) assert(n <= v and n >= 0) v = n end
assert(v == 0, "restore must end at exactly 0")
-- Reduce Motion: no animation, straight to the target either way.
assert(M.step(0, M.FadeTransparency, 1 / 60, true) == M.FadeTransparency and M.step(0.8, 0, 1 / 60, true) == 0)
-- Bad dt is safe (NaN and huge steps land on the target, zero or negative keep the value).
assert(M.step(0.3, 0.8, 0 / 0, false) == 0.8 and M.step(0.3, 0.8, 5, false) == 0.8 and M.step(0.3, 0.8, 0, false) == 0.3)

-- Grid: finds props along the segment only, no duplicates, big props span cells.
local grid = M.newGrid()
M.insert(grid, 1, 0, 10, 4) M.insert(grid, 2, 200, 200, 4) M.insert(grid, 3, 0, 33, 40)
local out = {}
local ids = M.query(grid, 0, 0, 0, 20, out)
local seen = {} for _, id in ids do assert(not seen[id], "duplicate id") seen[id] = true end
assert(seen[1] and seen[3] and not seen[2], "grid query")
-- Caps: at most MaxProps props and MaxParts parts, nearest first, deterministic.
local cands = {}
for i = 1, 30 do table.insert(cands, {id = i, dist = 100 - i, parts = 1}) end
local chosen = M.select(cands)
assert(#chosen == M.MaxProps and chosen[1] == 30, "prop cap, nearest first")
local heavy = {{id = 1, dist = 1, parts = 30}, {id = 2, dist = 2, parts = 30}, {id = 3, dist = 3, parts = 5}}
local ch = M.select(heavy)
assert(#ch == 2 and ch[1] == 1 and ch[2] == 3, "part cap skips what does not fit, keeps the rest")
local total = 0 for _, id in ch do total += heavy[id].parts end assert(total <= M.MaxParts)
assert(#M.select({}) == 0)
print("camera occlusion tests passed")
'''


def script():
    return 'local M=(function()\n' + (ROOT / 'src/shared/CameraOcclusion.luau').read_text(encoding='utf-8') + '\nend)()\n' + BODY


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'camera_occlusion.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
