"""Execute the pure BD-254 Sanctuary decoration table (src/shared/SanctuaryDecor.luau) with the pinned Luau runtime.
Checks: only real generated-mesh keys, part budget (BD-168), nothing on the spawn plaza or outside the hedge ring,
every egg rests in a nest, deterministic. Instances and the look are checked in Studio (docs/102, kanban BD-254).
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]

BODY = r'''
local rows = M.layout()
local kinds = {}
for _, r in rows do kinds[r.kind] = (kinds[r.kind] or 0) + 1 end
assert(kinds.statue == 1 and kinds.nest == 5 and kinds.egg == #M.EggNests and kinds.bush >= 12 and kinds.flower >= 8, "decoration mix")
assert(M.partCount() <= M.PartBudget and M.partCount() <= 150, "Sanctuary part budget " .. M.partCount())
for _, r in rows do
 assert(math.abs(r.x) <= M.Inner.halfX and math.abs(r.dz) <= M.Inner.halfZ, "decoration inside the fences: " .. r.kind)
 assert(r.width > 0 and r.width <= 16, "sane width")
 if r.kind ~= "nest" and r.kind ~= "egg" then
  local onPlaza = math.abs(r.x) <= M.Plaza.halfX + r.width / 2 and math.abs(r.dz) <= M.Plaza.halfZ + r.width / 2
  assert(not onPlaza, "spawn plaza stays clear: " .. r.kind .. " " .. r.x .. "," .. r.dz)
 end
 if r.kind == "egg" then
  local n = M.NestXs[r.nest]
  assert(n and n == r.x and r.dz == M.NestDz, "egg rests in its nest")
 end
 if r.kind == "bush" and r.dz == 37 then assert(math.abs(r.x) > 14, "sign stays clear of hedge") end
end
local again = M.layout()
assert(#again == #rows and again[3].x == rows[3].x and again[#again].dz == rows[#rows].dz, "deterministic")
for _, s in M.stones() do assert(s.dz >= M.Plaza.halfZ and s.dz < M.NestDz - 2, "stones between plaza and nests") end
print("sanctuary decor tests passed " .. M.partCount() .. " parts")
'''


def script():
    return 'local M=(function()\n' + (ROOT / 'src/shared/SanctuaryDecor.luau').read_text(encoding='utf-8') + '\nend)()\n' + BODY


def keys_are_real():
    """Statue / nest / egg keys must be published ids in WorldGeneratedMeshes (no invented ids)."""
    decor = (ROOT / 'src/shared/SanctuaryDecor.luau').read_text(encoding='utf-8')
    meshes = (ROOT / 'src/shared/WorldGeneratedMeshes.luau').read_text(encoding='utf-8')
    ids = dict(re.findall(r'^\s{4}(\w+) = \{assetId = "(\d+)"', meshes, re.M))
    want = {'landmark_dino_statue': '82545380144820', 'nest': '102765517629578', 'food_egg': '80664439797104'}
    for key, asset in want.items():
        assert ids.get(key) == asset, f'{key} must be the real published id {asset}'
        assert f'"{key}"' in decor, f'{key} not used by SanctuaryDecor'
    assert not re.search(r'\b\d{12,}\b', decor), 'SanctuaryDecor must not carry asset ids'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    keys_are_real()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'sanctuary_decor.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
