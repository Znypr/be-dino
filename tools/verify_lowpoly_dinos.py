"""BD-225/234 spike checks: low-poly dino registry (ids numeric, unique, every flagged species mapped, flag OFF) and the
pure idle/walk pose function (bounded, deterministic, speed-scaled, Reduce Motion exact rest). Pinned Luau runtime."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
FLAGGED = ["compy", "raptor", "triceratops"]


def registry():
    text = (ROOT / 'src/shared/LowPolyDinoAssets.luau').read_text(encoding='utf-8')
    return re.findall(r'(\w+) = \{assetId = (\d+), version = "(v\d+)", scale = ([\d.]+)\}', text)


def check_registry():
    entries = registry()
    names = [e[0] for e in entries]
    ids = [e[1] for e in entries]
    assert sorted(names) == sorted(FLAGGED), f"registry species {names} != {FLAGGED}"
    assert len(set(ids)) == len(ids), "duplicate asset ids"
    assert all(i.isdigit() and 10 <= len(i) <= 16 for i in ids), "asset ids must be numeric"
    assert all(0.5 <= float(e[3]) <= 6 for e in entries), "scale out of range"
    config = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
    assert re.search(r'^\s*LowPolyDinos = false,', config, re.M), "Config.LowPolyDinos must default to false"
    for name in names:
        assert re.search(r'\b' + name + r'\b', config), f"{name} is not a game species"
    return entries


BODY = r'''
local out = P.new()
local roles = {"body", "head", "tail", "arm", "leg"}
for _, role in roles do
    for _, side in {-1, 1} do
        for _, lead in {true, false} do
            for step = 0, 600 do
                local t, phase = step * 0.05, step * 0.13
                for _, w in {0, 0.3, 1} do
                    P.sample(role, side, lead, t, phase, w, 1, out)
                    for k, v in out do assert(v == v and math.abs(v) <= P.MaxAngle, role .. " " .. k) end
                    assert(math.abs(out.dy) <= P.MaxOffset and math.abs(out.dz) <= P.MaxOffset)
                    P.sample(role, side, lead, t, phase, w, 0, out)
                    for k, v in out do assert(v == 0, "reduce motion not rest: " .. role .. " " .. k) end
                end
            end
        end
    end
end
local moved = false
for i = 0, 200 do P.sample("tail", 1, false, i * 0.1, 0, 0, 1, out) if math.abs(out.yaw) > 0.05 then moved = true end end
assert(moved, "idle tail sway missing")
assert(P.stepRate(1) > P.stepRate(0) and P.stepRate(0) > 0 and P.stepRate(2) == P.stepRate(1))
local l, r = P.new(), P.new()
P.sample("leg", -1, false, 0, 1.0, 1, 1, l) P.sample("leg", 1, false, 0, 1.0, 1, 1, r)
assert(math.abs(l.pitch + r.pitch) < 1e-9 and math.abs(l.pitch) > 0.1, "legs must alternate")
local t1 = P.new()
P.sample("tail", 1, false, 0, 1.0, 1, 1, t1)
assert(t1.yaw ~= 0, "tail counter-swings while walking")
local a, b = P.new(), P.new()
P.sample("head", 1, true, 3.3, 2.2, 0.7, 1, a) P.sample("head", 1, true, 3.3, 2.2, 0.7, 1, b)
for k, v in a do assert(v == b[k]) end
P.sample("head", 1, true, 0/0, 0/0, 0/0, 0/0, a)
for k, v in a do assert(v == v and v == 0, "nan " .. k) end
print("lowpoly pose tests passed")
'''


RECOLOR_BODY = r'''
local function near(a, b) return math.abs(a - b) < 1e-6 end
-- eyes stay black, cream belly stays cream, for every gene colour
local eyes = {{0.06, 0.06, 0.06}, {0.0, 0.0, 0.0}, {0.19, 0.19, 0.19}}
local belly = {{0.82, 0.82, 0.56}, {0.82, 0.69, 0.56}, {0.95, 0.93, 0.85}, {1, 1, 1}}
local targets = {{1, 0.2, 0.2}, {0.2, 0.3, 1}, {0.7, 0.2, 0.9}, {0.9, 0.9, 0.2}, {0, 0, 0}}
for _, t in targets do
    for _, p in eyes do
        local r, g, b = R.pixel(p[1], p[2], p[3], t[1], t[2], t[3], R.baseOf("compy"))
        assert(near(r, p[1]) and near(g, p[2]) and near(b, p[3]), "eye pixel changed")
    end
    for _, p in belly do
        local r, g, b = R.pixel(p[1], p[2], p[3], t[1], t[2], t[3], R.baseOf("raptor"))
        assert(near(r, p[1]) and near(g, p[2]) and near(b, p[3]), "belly pixel changed")
    end
end
-- body colour becomes the gene colour (at base brightness), keeps shading, stays in range
for species, base in R.Base do
    local r, g, b = R.pixel(base[1], base[2], base[3], 1, 0.2, 0.2, base)
    assert(near(r, 1) and near(g, 0.2) and near(b, 0.2), species .. " body not recoloured")
    local dr, dg, db = R.pixel(base[1] * 0.5, base[2] * 0.5, base[3] * 0.5, 1, 0.2, 0.2, base)
    assert(dr < r and dr > 0, species .. " shading lost")
    for _, k in {0.3, 0.8, 1.2, 2} do
        local x, y, z = R.pixel(math.min(1, base[1] * k), math.min(1, base[2] * k), math.min(1, base[3] * k), 0.9, 0.9, 0.9, base)
        assert(x >= 0 and x <= 1 and y >= 0 and y <= 1 and z >= 0 and z <= 1)
    end
end
assert(R.bodyWeight(0.5, 0.5, 0.5) == 0 and R.bodyWeight(0, 0, 0) == 0 and R.bodyWeight(0.1, 0.5, 0.1) > 0.9)
print("lowpoly recolor tests passed")
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    entries = check_registry()
    print(f"low-poly registry ok: {len(entries)} species, flag off")
    src = 'local P=(function()\n' + (ROOT / 'src/shared/LowPolyPose.luau').read_text(encoding='utf-8') + '\nend)()\n' + BODY
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'lowpoly_pose.luau'
        path.write_text(src, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
        rsrc = 'local R=(function()\n' + (ROOT / 'src/shared/LowPolyRecolor.luau').read_text(encoding='utf-8') + '\nend)()\n' + RECOLOR_BODY
        path2 = Path(tmp) / 'lowpoly_recolor.luau'
        path2.write_text(rsrc, encoding='utf-8')
        result = subprocess.run([args.runner, str(path2)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
