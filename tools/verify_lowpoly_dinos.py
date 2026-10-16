"""BD-225/234 spike checks: low-poly dino registry (ids numeric, unique, every flagged species mapped, flag OFF) and the
pure idle/walk pose function (bounded, deterministic, speed-scaled, Reduce Motion exact rest). Pinned Luau runtime."""
from pathlib import Path
import argparse
import json
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
# BD-225/BD-232: every shipped species (Config.SpeciesOrder) is mapped; ids are the real published generate_mesh ids.
EXPECTED_IDS = {
    "compy": "94548957808227", "raptor": "83260397513385", "triceratops": "107596736973492", "tyrannosaurus": "70893952304488",
    "stegosaurus": "92335618053209", "brachiosaurus": "104593280278631", "ankylosaurus": "125812700099310",
    "archaeopteryx": "108659121473793", "baryonyx": "131708938808155", "dimorphodon": "117242533934118",
    "elasmosaurus": "76344726254379", "gallimimus": "99873366835296", "ichthyosaurus": "133825037148251",
    "microraptor": "137027841072493", "mosasaurus": "116180724806366", "pachycephalosaurus": "75417530223759",
    "parasaurolophus": "125203763120290", "plesiosaurus": "107885207120586", "pteranodon": "101283644467729",
    "quetzalcoatlus": "126028097030256", "spinosaurus": "94005222354362", "therizinosaurus": "94894343028103",
}
CLASSES = {"Fly": {"pteranodon", "quetzalcoatlus", "dimorphodon", "archaeopteryx", "microraptor"},
           "Water": {"plesiosaurus", "mosasaurus", "ichthyosaurus", "elasmosaurus"}, "Armored": {"ankylosaurus"}}
# Part-name sets by body plan (generation part lists; names vary by species, matcher must classify every one).
BIPED = ["body", "head", "tail", "left arm", "right arm", "left leg", "right leg"]
QUAD = ["body", "head", "tail", "front left leg", "front right leg", "back left leg", "back right leg"]
WINGED = ["body", "head", "tail", "left wing", "right wing", "left leg", "right leg"]
FLIPPER = ["body", "neck and head", "tail", "front left flipper", "front right flipper", "back left flipper", "back right flipper"]
NECK = ["body", "neck", "head", "tail", "front left leg", "front right leg", "back left leg", "back right leg"]
PART_SETS = {"quad": QUAD, "biped": BIPED, "wings": WINGED, "flippers": FLIPPER, "neck": NECK,
             "quote": ['"left arm"_geom', '"Right Leg"_geom', '"head"_geom', '"tail"_geom', '"body"_geom', 'left wing [1]', 'neck and head']}
PLAN = {"quad": {"triceratops", "stegosaurus", "ankylosaurus"},
        "biped": {"compy", "raptor", "tyrannosaurus", "baryonyx", "gallimimus", "pachycephalosaurus", "parasaurolophus", "spinosaurus",
                  "therizinosaurus"},
        "wings": CLASSES["Fly"], "flippers": CLASSES["Water"], "neck": {"brachiosaurus"}}


def registry():
    text = (ROOT / 'src/shared/LowPolyDinoAssets.luau').read_text(encoding='utf-8')
    return re.findall(r'(\w+) = \{assetId = (\d+), version = "(v\d+)", scale = ([\d.]+), tier = (\d), class = "(\w+)"\}', text)


def check_registry():
    entries = registry()
    names = [e[0] for e in entries]
    ids = [e[1] for e in entries]
    config = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
    order = re.search(r'SpeciesOrder = \{([^}]*)\}', config).group(1)
    order = re.findall(r'"(\w+)"', order)
    assert len(order) == 22 and sorted(names) == sorted(order), f"registry species {sorted(names)} != Config.SpeciesOrder"
    assert dict(zip(names, ids)) == EXPECTED_IDS, "asset ids differ from the published generate_mesh ids"
    assert len(set(ids)) == len(ids), "duplicate asset ids"
    assert all(i.isdigit() and 10 <= len(i) <= 16 for i in ids), "asset ids must be numeric"
    assert all(0.5 <= float(e[3]) <= 6 for e in entries), "scale out of range"
    tiers = dict(re.findall(r'(\w+) = (\d)(?=[,\s])', re.search(r'SpeciesRarities = \{(.*?)\n    \}', config, re.S).group(1)))
    for name, _, _, scale, tier, cls in entries:
        assert tiers[name] == tier, f"{name} tier {tier} != Config.SpeciesRarities {tiers[name]}"
        expect = next((c for c, group in CLASSES.items() if name in group), "Ground")
        assert cls == expect, f"{name} class {cls} != {expect}"
        ladder = 2.0 * 1.1 ** (int(tier) - 1)
        shape = float(scale) / ladder
        assert 0.75 <= shape <= 1.65, f"{name} shape factor {shape:.2f} unreasonable"
    by_tier = {}
    for name, _, _, scale, tier, _ in entries:
        by_tier.setdefault(tier, []).append(float(scale))
    means = [sum(v) / len(v) for _, v in sorted(by_tier.items())]
    assert all(b > a for a, b in zip(means, means[1:])), f"mean scale must grow every tier: {means}"
    assert sum(len(v) for v in PLAN.values()) == 22 and set().union(*PLAN.values()) == set(names), "part plan must cover all species"
    assert re.search(r'^\s*LowPolyDinos = false,', config, re.M), "Config.LowPolyDinos must default to false"
    for name in names:
        assert re.search(r'\b' + name + r'\b', config), f"{name} is not a game species"
    return entries


BODY = r'''
local out = P.new()
local roles = {"body", "head", "neck", "tail", "arm", "leg", "flipper"}
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
-- every class and role: finite, bounded (a folded wing may exceed MaxAngle up to MaxFold), Reduce Motion = rest (wing keeps its fold)
for _, class in {"Ground", "Fly", "Water", "Armored"} do
    for _, role in {"body", "head", "neck", "tail", "arm", "leg", "flipper", "wing"} do
        for _, side in {-1, 1} do
            for step = 0, 300 do
                for _, w in {0, 0.5, 1} do
                    P.sample(role, side, step % 2 == 0, step * 0.07, step * 0.11, w, 1, out, class)
                    for k, v in out do
                        assert(v == v and math.abs(v) <= (if role == "wing" and k == "roll" then P.MaxFold else P.MaxAngle) + 1e-9, role .. " " .. k) end
                    P.sample(role, side, true, step * 0.07, step * 0.11, w, 0, out, class)
                    for k, v in out do
                        if role == "wing" and k == "roll" then assert(math.abs(v + side * P.FoldAngle) < 1e-9, "wing fold lost")
                        else assert(v == 0, "reduce motion not rest: " .. role .. " " .. k) end
                    end
                end
            end
        end
    end
end
-- wings rest folded on both sides (tips down toward the body), mirrored, even while idle and walking
local fl, fr = P.new(), P.new()
for _, w in {0, 1} do
    P.sample("wing", -1, false, 1.3, 0.7, w, 1, fl, "Fly") P.sample("wing", 1, false, 1.3, 0.7, w, 1, fr, "Fly")
    assert(fr.roll < -0.9 and fl.roll > 0.9, "wings must stay folded")
end
-- water stays low: lower body than ground, shorter strokes
local gb, wb, gl, wl = P.new(), P.new(), P.new(), P.new()
P.sample("body", 1, false, 0, 1.0, 1, 1, gb, "Ground") P.sample("body", 1, false, 0, 1.0, 1, 1, wb, "Water")
assert(wb.dy < gb.dy, "water body must sit lower")
P.sample("leg", 1, false, 0, 1.0, 1, 1, gl, "Ground") P.sample("leg", 1, false, 0, 1.0, 1, 1, wl, "Water")
assert(math.abs(wl.pitch) < math.abs(gl.pitch), "water strokes shorter")
-- the default (no class) is Ground and old call shape still works
local d1, d2 = P.new(), P.new()
P.sample("leg", 1, false, 0, 1.0, 1, 1, d1) P.sample("leg", 1, false, 0, 1.0, 1, 1, d2, "Ground")
assert(d1.pitch == d2.pitch)
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
-- BD-233: jump / leap / land / water-surge actions. Every class x phase x role x side x aggr: finite, bounded, Reduce Motion = rest, continuity.
local ctx = P.newCtx()
local ROLES = {"body", "head", "neck", "tail", "arm", "leg", "flipper", "wing"}
local function run(class, phase, aggr, p, t, amp, role, side, lead, o)
    ctx.phase, ctx.p, ctx.t, ctx.aggr, ctx.carry = phase, p, t, aggr, 0.7
    return P.sampleAction(role, side, lead, ctx, amp, o, class)
end
local phasesFor = {Ground = {"crouch", "push", "air", "land"}, Armored = {"crouch", "push", "air", "land"},
    Fly = {"crouch", "push", "air", "land"}, Water = {"surge"}}
local checked = 0
for class, phases in phasesFor do
    for _, phase in phases do
        for _, aggr in {0, 0.5, 1} do
            for step = 0, 20 do
                local p, t = step / 20, step * 0.06
                local dur = P.duration(phase, aggr, class)
                assert(dur >= 0 and dur < 1, class .. " duration " .. phase)
                local k = P.actionWeight(phase, p)
                assert(k >= 0 and k <= 1, "weight")
                for _, role in ROLES do
                    for _, side in {-1, 1} do
                        local o, rest = P.new(), P.new()
                        run(class, phase, aggr, p, t, 1, role, side, true, o)
                        for key, v in o do
                            local cap = if role == "wing" and key == "roll" then P.MaxFold else P.MaxAngle
                            assert(v == v and math.abs(v) <= cap + 1e-9, class .. " " .. phase .. " " .. role .. " " .. key)
                        end
                        assert(math.abs(o.dy) <= P.MaxOffset and math.abs(o.dz) <= P.MaxOffset)
                        -- calm: nothing violent (no angle above ~0.9 rad, offsets inside 8 percent of the height)
                        run(class, phase, aggr, p, t, 0, role, side, true, rest)
                        for key, v in rest do
                            if role == "wing" and key == "roll" then assert(math.abs(v + side * P.FoldAngle) < 1e-9, "wing fold lost")
                            else assert(v == 0, "reduce motion not rest: " .. class .. " " .. phase .. " " .. role .. " " .. key) end
                        end
                        checked += 1
                    end
                end
            end
        end
    end
end
-- smooth: a small time step never jumps the pose (calm, no shaking) in any timed phase
for class, phases in phasesFor do
    for _, phase in phases do
        for _, role in ROLES do
            local a, b = P.new(), P.new()
            local dur = math.max(P.duration(phase, 1, class), 0.5)
            for step = 0, 99 do
                local t0 = step / 100 * dur
                run(class, phase, 1, math.clamp(t0 / dur, 0, 1), t0, 1, role, 1, true, a)
                run(class, phase, 1, math.clamp((t0 + 0.005) / dur, 0, 1), t0 + 0.005, 1, role, 1, true, b)
                for key, v in a do assert(math.abs(v - b[key]) < 0.06, "jerky " .. class .. " " .. phase .. " " .. role .. " " .. key) end
            end
        end
    end
end
-- continuity: the action starts and ends at the exact rest pose, hands over to idle with zero weight
for class, phases in phasesFor do
    local first, last = phases[1], phases[#phases]
    assert(P.actionWeight(first, 0) == 0 or class == "Water" and P.actionWeight("surge", 0) == 0 or first == "crouch" and P.actionWeight("crouch", 0) == 0)
    for _, role in ROLES do
        for _, side in {-1, 1} do
            local o, idle = P.new(), P.new()
            run(class, first, 1, 0, 0, 1, role, side, true, o)
            local f = if role == "wing" then -side * P.FoldAngle else 0
            assert(math.abs(o.pitch) < 1e-9 and math.abs(o.yaw) < 1e-9 and math.abs(o.dy) < 1e-9 and math.abs(o.dz) < 1e-9 and math.abs(o.roll - f) < 1e-9, class .. " start not rest " .. role)
            run(class, last, 1, 1, P.duration(last, 1, class), 1, role, side, true, o)
            assert(math.abs(o.pitch) < 1e-9 and math.abs(o.yaw) < 1e-9 and math.abs(o.dy) < 1e-9 and math.abs(o.dz) < 1e-9 and math.abs(o.roll - f) < 1e-9, class .. " end not rest " .. role)
            -- the final handed-over pose is exactly the idle/walk pose, and rest itself is within tolerance of idle at t=0
            P.sample(role, side, true, 0, 0, 0, 1, idle, class)
            assert(math.abs(idle.pitch) < 0.05 and math.abs(idle.dy) < 0.03 and math.abs(idle.roll - f) < 0.05, "idle not near rest " .. role)
            local blended = P.sample(role, side, true, 1.7, 0.4, 0.6, 1, P.new(), class)
            local walk = P.sample(role, side, true, 1.7, 0.4, 0.6, 1, P.new(), class)
            P.blend(blended, o, P.actionWeight(last, 1))
            for key, v in blended do assert(math.abs(v - walk[key]) < 1e-12, "land end must be the base pose") end
        end
    end
    assert(P.actionWeight(last, 1) == 0, class .. " last weight")
end
-- class character: Armored crouches deeper and lands heavier, Fly opens its wings in the air and folds again, Water surges forward
local g, ar = P.new(), P.new()
run("Ground", "crouch", 0, 1, 0.1, 1, "body", 1, false, g) run("Armored", "crouch", 0, 1, 0.1, 1, "body", 1, false, ar)
assert(ar.dy < g.dy, "armored crouches lower")
run("Ground", "land", 0, 0.25, 0.1, 1, "body", 1, false, g) run("Armored", "land", 0, 0.25, 0.1, 1, "body", 1, false, ar)
assert(ar.dy < g.dy, "armored lands heavier")
local wr, wl = P.new(), P.new()
run("Fly", "air", 0, 0, 0.5, 1, "wing", 1, false, wr) run("Fly", "air", 0, 0, 0.5, 1, "wing", -1, false, wl)
assert(math.abs(wr.roll) < 0.6 and math.abs(wl.roll) < 0.6 and wr.roll * wl.roll <= 0, "fly wings open (mirrored) in the air")
run("Fly", "crouch", 0, 0, 0, 1, "wing", 1, false, wr)
assert(wr.roll < -P.FoldAngle + 1e-9, "fly wings folded before takeoff")
local jb, lb, jh, lh = P.new(), P.new(), P.new(), P.new()
run("Water", "surge", 0, 0.5, 0.2, 1, "body", 1, false, jb) run("Water", "surge", 1, 0.5, 0.275, 1, "body", 1, false, lb)
assert(jb.dz < -0.02 and lb.dz < jb.dz, "water surge forward, leap bigger")
for _, p in {0.4, 0.5, 0.6} do
    run("Water", "surge", 1, p, 0.2, 1, "head", 1, false, lh) if lh.pitch < -0.2 then jh.pitch = 1 end
end
assert(jh.pitch == 1, "water leap head snap")
for _, class in {"Ground", "Armored", "Fly", "Water"} do
    local o = P.new()
    ctx.phase, ctx.p, ctx.t, ctx.aggr, ctx.carry = "air", 0/0, 0/0, 0/0, 0/0
    P.sampleAction("body", 1, false, ctx, 0/0, o, class)
    for key, v in o do assert(v == v and v == 0, "nan " .. key) end
end
print("lowpoly action tests passed", checked)
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


def role_body():
    lines = ["local roles = {}"]
    for plan, names in PART_SETS.items():
        lines.append("roles[%s] = {%s}" % (json.dumps(plan), ", ".join(json.dumps(n) for n in names)))
    lines.append(r'''
local expect = {body = "body", head = "head", tail = "tail", neck = "neck", wing = "wing", flipper = "flipper", arm = "arm", leg = "leg"}
local function want(name)
    local n = string.lower(name)
    if string.find(n, "head") then return "head" end
    for _, k in {"tail", "wing", "flipper", "neck", "arm", "leg", "body"} do if string.find(n, k, 1, true) then return k end end
    return nil
end
for plan, names in roles do
    local seen = {}
    for _, name in names do
        local role = P.roleOf(name)
        assert(role ~= nil and role == want(name), plan .. ": " .. name .. " -> " .. tostring(role))
        seen[role] = true
    end
    assert(seen.body and seen.head or seen.neck, plan .. ": body/head missing")
end
assert(P.roleOf("xyz") == nil)
print("lowpoly role tests passed")
''')
    return "\n".join(lines)


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
        rolesrc = 'local P=(function()\n' + (ROOT / 'src/shared/LowPolyPose.luau').read_text(encoding='utf-8') + '\nend)()\n' + role_body()
        path3 = Path(tmp) / 'lowpoly_roles.luau'
        path3.write_text(rolesrc, encoding='utf-8')
        result = subprocess.run([args.runner, str(path3)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)

# Regression (docs/108): the preview must not run the legacy "authored creature" checks on a low-poly model, or 16 species fall back to the flat picture.
for _name in ("DinosaurPreview", "ModelPreview"):
    _src = (ROOT / f"src/shared/{_name}.luau").read_text(encoding="utf-8")
    _line = [l for l in _src.splitlines() if "Authored.verify(model)" in l][0]
    assert 'GetAttribute("LowPoly")' in _line, f"{_name}: Authored.verify must skip low-poly models"
_dp = (ROOT / "src/shared/DinosaurPreview.luau").read_text(encoding="utf-8")
assert [l for l in _dp.splitlines() if "Authored.has(speciesId)" in l and 'GetAttribute("LowPoly")' in l], "DinosaurPreview: Authored.has must skip low-poly models"
print("low-poly preview guards passed")
