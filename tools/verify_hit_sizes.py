"""BD-514 (docs/115 HS1): offline verifier for the server hit size, src/shared/HitSize.luau + src/server/HitRadius.luau.

It runs the REAL pure module (HitSize, with ScaleLadder and CombatConfig) and the REAL server glue (HitRadius, with stubbed
ReplicatedStorage and stub models) in Luau, and fails when:
  1. LADDER: for all 22 species at growth scale 1, 2 and 4 the radius is not the ScaleLadder-derived value
     clamp(max(width, length) / 2 x scale, 1, CombatConfig.BodyRadiusMax) (the raw value is also compared, unclamped), or the
     width / length it uses differ from the Studio boxes in tools/verify_scale_ladder.py (MEASURED);
  2. SAME RULE: a player (character attributes SpeciesId / VisualScale) and a wild predator (its species and drawn scale) of the same
     species and scale do not get the same radius, for every species at scales 1, 2, 4 and for the NPC species at the NPC drawn scales
     (the player clamp of CombatRules.bodyRadius and the NPC clamp [1, 14] leave the value unchanged);
  3. LEGACY SHELL: with the low-poly sizes on the server model is still measured (GetExtentsSize is called) or the result depends on the
     shell box (the 4.2 x 5.6 x 9.8 fallback box must not matter); an unknown species must use the CombatRules fallback, not a box;
  4. FLAG OFF: with LowPolyDinos off (or no LowPolyDinos module, a test harness) the radius is exactly today's max(X, Z) / 2 of the
     measured model, and 0 when it cannot be measured;
  5. STATIC: no gameplay code measures a model's bounding box (src/server: only HitRadius.luau (the flag-off branch) and ImportedResources
     (asset import, not gameplay); src/shared: only the listed VISUAL modules), CombatService and NpcPredatorService both call HitRadius,
     HitSize is pure (no Instances, no flag), HitRadius reads the flag only through LowPolyDinos.enabled (verify_lowpoly_views rule), and
     CombatEnabled stays false.
Not Studio evidence: combat is OFF in the playtest build; nothing here shows a bite in a running game.
Usage: python tools/verify_hit_sizes.py --runner luau.exe [--print]   (--print writes the before / after table)
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_scale_ladder import MEASURED as _SHIPPED, SECRET_BOXES  # noqa: E402  (width, height, length at spawn of all 22 species, Studio-measured BD-471 / BD-500)
MEASURED = {**_SHIPPED, **SECRET_BOXES}  # BD-606: plus the 7 secret species (design estimates until their meshes exist): HitSize reads ScaleLadder.dinoRow for both

SCALES = (1, 2, 4)
MIN_R, MAX_R = 1.0, 14.0
# The server legacy shell (DinoVisual) as the BD-514 row measured it in Studio (width x height x length, studs, growth scale 1).
# 3 species have a legacy model; the other 15 measured species share the procedural fallback box. Only for the before/after table.
LEGACY = {
    "compy": (4.2, 5.6, 6.1),
    "stegosaurus": (4.2, 5.6, 6.9),
    "ankylosaurus": (4.2, 5.6, 6.2),
}
LEGACY_FALLBACK = (4.2, 5.6, 9.8)
# Gameplay code must not measure a model: these are the ONLY files allowed to call GetExtentsSize / GetBoundingBox / GetBoundingBox-like.
SERVER_MEASURERS = {"server/HitRadius.luau", "server/ImportedResources.luau"}
SHARED_VISUAL_MEASURERS = {  # visual helpers (previews, particles, mesh scaling), not gameplay
    "shared/LowPolyDinos.luau", "shared/MutationEffects.luau", "shared/PotionArt.luau", "shared/PreviewCamera.luau",
    "shared/ResourceModels.luau", "shared/ShinyEffects.luau",
}

problems: list = []


def check(ok: bool, message: str):
    if not ok:
        problems.append(message)


def read(rel: str) -> str:
    return (SRC / rel).read_text(encoding="utf-8")


def code(rel: str) -> str:
    return "\n".join(re.sub(r"--.*$", "", line) for line in read(rel).splitlines())


def expected(species: str, scale: float):
    w, _h, l = MEASURED[species]
    raw = max(w, l) / 2 * scale
    return raw, min(MAX_R, max(MIN_R, raw))


def npc_cases():
    text = read("shared/NpcPredatorRules.luau")
    species = re.search(r"Species = \{([^}]*)\}", text)
    lo = re.search(r"VisualScaleMin = ([0-9.]+)", text)
    hi = re.search(r"VisualScaleMax = ([0-9.]+)", text)
    if not (species and lo and hi):
        problems.append("could not read NpcPredatorRules Species / VisualScaleMin / VisualScaleMax")
        return [], []
    ids = re.findall(r'"([a-z]+)"', species.group(1))
    lo_s, hi_s = float(lo.group(1)), float(hi.group(1))
    return ids, [lo_s, (lo_s + hi_s) / 2, hi_s]


def module(rel: str) -> str:
    return "(function()\n" + read(rel) + "\nend)()"


def luau_script() -> str:
    ids = sorted(MEASURED)
    npc_species, npc_scales = npc_cases()
    hit_radius = read("server/HitRadius.luau")
    parts = [
        "local M={}", "local script={Parent=M}", "local require=function(x) return x end",
        "M.CombatConfig=" + module("shared/CombatConfig.luau"),
        "M.CombatStats=" + module("shared/CombatStats.luau"),
        "M.CombatState=" + module("shared/CombatState.luau"),
        "M.CombatTeamUp=" + module("shared/CombatTeamUp.luau"),
        "M.LowPolyDinoAssets=" + module("shared/LowPolyDinoAssets.luau"),
        "M.CombatRules=" + module("shared/CombatRules.luau"),
        "M.ScaleLadder=" + module("shared/ScaleLadder.luau"),
        "M.HitSize=" + module("shared/HitSize.luau"),
        "local HitSize,Rules,Ladder,Cfg=M.HitSize,M.CombatRules,M.ScaleLadder,M.CombatConfig",
        "local IDS={" + ",".join(f'"{i}"' for i in ids) + "}",
        "local NPC_SPECIES={" + ",".join(f'"{i}"' for i in npc_species) + "}",
        "local NPC_SCALES={" + ",".join(repr(s) for s in npc_scales) + "}",
        "local SCALES={" + ",".join(str(s) for s in SCALES) + "}",
        # the real server glue, with a stubbed ReplicatedStorage and a typeof that knows the stub Vector3
        "local function stubTypeof(v) if type(v)=='table' and v.X~=nil and v.Z~=nil then return 'Vector3' end return type(v) end",
        "local HitRadiusSrc=(function(game,require,typeof)\n" + hit_radius.replace("--!strict", "", 1) + "\nend)",
        "local function loadHitRadius(lowPolyModule)",
        "  local shared={HitSize=M.HitSize,LowPolyDinos=lowPolyModule}",
        "  local rs={Shared=shared}",
        "  local game={GetService=function(_,name) assert(name=='ReplicatedStorage'); return rs end}",
        "  return HitRadiusSrc(game,function(m) return m end,stubTypeof)",
        "end",
        BODY,
    ]
    return "\n".join(parts)


BODY = r'''
local function model(attrs, box, counter)
  return {GetAttribute=function(_,k) return attrs[k] end, GetExtentsSize=function() counter.n+=1 return box end}
end
local SHELL={X=4.2,Y=5.6,Z=9.8} -- the legacy server shell fallback box
local on={enabled=function() return true end}
local off={enabled=function() return false end}
local HR=loadHitRadius(on)

-- 1. LADDER + 2. SAME RULE, all 22 species at growth scale 1, 2, 4
local lines={}
for _,id in IDS do
  local row=Ladder.dinoRow(id) -- BD-606: 22 shipped species + 7 secret species
  for _,s in SCALES do
    local raw=HitSize.rawRadius(id,s)
    local derived=math.max(row.width,row.length)/2*s
    assert(math.abs(raw-derived)<1e-9,id.." raw radius is max(width,length)/2 x scale")
    local r=HitSize.radius(id,s)
    assert(math.abs(r-math.clamp(derived,HitSize.MinRadius,HitSize.MaxRadius))<1e-9,id.." clamped radius")
    assert(HitSize.MaxRadius==Cfg.BodyRadiusMax,"the hit cap is the CombatRules cap")
    local counter={n=0}
    local playerRadius=HR.of(model({SpeciesId=id,VisualScale=s},SHELL,counter))
    local npcRadius=HR.of(model({},SHELL,counter),id,s)
    assert(playerRadius==r and npcRadius==r,id.." player, NPC and HitSize agree at scale "..s)
    assert(Rules.bodyRadius(playerRadius,s)==playerRadius,"the CombatRules clamp leaves a player radius unchanged")
    assert(math.clamp(npcRadius,1,14)==npcRadius,"the NPC clamp leaves the radius unchanged")
    assert(counter.n==0,id.." the server model was measured while the low-poly sizes are on")
    local w,l=HitSize.footprint(id,s)
    assert(math.abs(w-row.width*s)<1e-9 and math.abs(l-row.length*s)<1e-9)
    table.insert(lines,string.format("R %s %g %.9f %.9f",id,s,raw,r))
  end
end
for _,l in lines do print(l) end

-- 2b. NPC species at the NPC drawn scales (1.0 to 1.3) match a player of the same scale
for _,id in NPC_SPECIES do
  for _,s in NPC_SCALES do
    local counter={n=0}
    local player=HR.of(model({SpeciesId=id,VisualScale=s},SHELL,counter))
    local npc=HR.of(model({},SHELL,counter),id,s)
    assert(player==npc and npc==HitSize.radius(id,s) and counter.n==0,id.." NPC vs player at drawn scale "..s)
  end
end

-- 3. the legacy shell never matters while the low-poly sizes are on
do
  local counter={n=0}
  local tiny=model({SpeciesId="spinosaurus",VisualScale=1},{X=1,Y=1,Z=1},counter)
  local huge=model({SpeciesId="spinosaurus",VisualScale=1},{X=90,Y=90,Z=90},counter)
  assert(HR.of(tiny)==HR.of(huge) and HR.of(tiny)==HitSize.radius("spinosaurus",1) and counter.n==0,"shell box ignored")
  -- unknown / missing species: the CombatRules fallback BodyRadiusPerScale x scale, still no measuring
  assert(HR.of(model({SpeciesId="nope",VisualScale=2},SHELL,counter))==Cfg.BodyRadiusPerScale*2,"unknown species fallback")
  assert(HR.of(model({},SHELL,counter))==Cfg.BodyRadiusPerScale,"no attributes: fallback at scale 1")
  assert(HR.of(model({SpeciesId="compy"},SHELL,counter))==HitSize.radius("compy",1),"missing scale = 1")
  assert(counter.n==0)
  -- junk scales cannot open an infinite range or a negative one
  for _,junk in {0/0,-5,0,1e12,math.huge,"x"} do
    local r=HitSize.radius("ankylosaurus",junk)
    assert(r and r>=HitSize.MinRadius and r<=HitSize.MaxRadius and r==r,"junk scale clamped")
  end
  assert(HitSize.radius("nope",1)==nil and HitSize.radius(nil,1)==nil and HitSize.radius(42,1)==nil and HitSize.rawRadius({},1)==nil)
  assert(HitSize.radius("compy",0.1)==HitSize.radius("compy",1),"a scale below 1 is read as 1 (the game never goes below)")
  assert(HitSize.radius("compy",99)==HitSize.radius("compy",6))
  -- monotonic in the growth scale
  for _,id in IDS do
    local prev=0
    for s=1,6,0.25 do local r=HitSize.rawRadius(id,s); assert(r>=prev); prev=r end
  end
end

-- 4. FLAG OFF = today's rule, max(X,Z)/2 of the measured model (0 when it cannot be measured)
for _,variant in {"flag false","no module"} do -- LowPolyDinos.enabled() false, and no LowPolyDinos module at all (a harness)
  local HRoff=loadHitRadius(if variant=="flag false" then off else nil)
  local counter={n=0}
  local m=model({SpeciesId="compy",VisualScale=2},{X=4.2,Y=5.6,Z=9.8},counter)
  assert(HRoff.of(m)==4.9 and counter.n==1,"flag off: bounding box half-size of the longer horizontal side")
  assert(HRoff.of(model({SpeciesId="spinosaurus"},{X=30,Y=5,Z=8},counter))==15)
  assert(HRoff.of(m,"spinosaurus",1.3)==4.9,"flag off: species and scale arguments are ignored, the model is measured")
  local broken={GetAttribute=function() return nil end,GetExtentsSize=function() error("no model") end}
  assert(HRoff.of(broken)==0,"flag off: a model that cannot be measured is 0")
  assert(HRoff.lowPolyOn()==false)
end
assert(HR.lowPolyOn()==true)
-- a LowPolyDinos module without enabled() (or not a table) counts as off
assert(loadHitRadius({}).lowPolyOn()==false and loadHitRadius(5).lowPolyOn()==false)

print("hit sizes passed: 22 species + 7 secret species x scales 1/2/4 equal the ScaleLadder value, player = NPC, the shell is not measured, flag off keeps the old box rule")
'''


def static_checks():
    # 5a. nobody but the allowed files measures a model
    pattern = re.compile(r"GetExtentsSize|GetBoundingBox")
    for path in sorted(SRC.rglob("*.luau")):
        rel = path.relative_to(SRC).as_posix()
        if rel.startswith("server/") and rel not in SERVER_MEASURERS:
            check(not pattern.search(code(rel)), f"{rel} measures a model's bounding box; gameplay sizes come from Shared/HitSize via server/HitRadius (docs/115 HS1)")
        if rel.startswith("shared/") and rel not in SHARED_VISUAL_MEASURERS:
            check(not pattern.search(code(rel)), f"{rel} measures a model's bounding box; only the listed visual modules may (docs/115 HS1)")
    # 5b. the two users go through HitRadius
    combat = code("server/CombatService.luau")
    npc = code("server/NpcPredatorService.luau")
    check("HitRadius" in combat and "HitRadius.of(model)" in combat, "CombatService.radiusOf must call HitRadius.of")
    check("HitRadius.of(model, npc.species, npc.visualScale)" in npc, "NpcPredatorService must size a wild predator with HitRadius.of(model, species, visualScale)")
    check("HitRadius.of(character)" in npc, "NpcPredatorService must size a targeted player with HitRadius.of(character), like CombatService")
    check("addNpc(npc.key, model," in npc, "NpcPredatorService must hand the NPC radius to CombatService.addNpc")
    check("api.npcRadius[npcKey] or radiusOf(npcModel)" in combat, "CombatService must use the NPC's own radius for a bite on it")
    # 5c. HitRadius: flag only through LowPolyDinos.enabled, legacy measure only in the flag-off branch
    hr = code("server/HitRadius.luau")
    check(re.search(r"\bConfig\b", hr) is None, "HitRadius must not read Config (the LowPolyDinos flag goes through LowPolyDinos.enabled)")
    check("require(shared.LowPolyDinos)" in hr and ".enabled() == true" in hr, "HitRadius must use the lowPolyOn() pattern")
    check(hr.count("GetExtentsSize") == 1 and hr.find("GetExtentsSize") > hr.find("local function legacyMeasured") >= 0, "HitRadius: the one GetExtentsSize belongs to legacyMeasured")
    body = hr[hr.find("function HitRadius.of"):]
    i_on, i_legacy = body.find("if lowPolyOn() then"), body.find("legacyMeasured(model)")
    check(0 <= i_on < i_legacy and "return HitSize.radiusOrFallback(" in body,
          "HitRadius.of must return the HitSize radius before the legacy measure when the low-poly sizes are on")
    # 5d. HitSize is pure
    hs = code("shared/HitSize.luau")
    check(re.search(r"\b(game|workspace|Instance|Config|GetService|GetAttribute)\b", hs) is None, "HitSize must be pure numbers (no Instances, no Config)")
    check(set(re.findall(r"require\(script\.Parent\.(\w+)\)", hs)) == {"ScaleLadder", "CombatConfig"}, "HitSize requires only ScaleLadder and CombatConfig")
    # 5e. combat stays off
    check(re.search(r"^\s*CombatEnabled = false,", read("shared/Config.luau"), re.M) is not None, "Config.CombatEnabled must stay false (BD-252 gate)")
    # 5f. the flag is still read in one place
    reads = {p.relative_to(SRC).as_posix() for p in SRC.rglob("*.luau") if re.search(r"\bConfig\b[^\n]*\.LowPolyDinos\b|\)\.LowPolyDinos\b", code(p.relative_to(SRC).as_posix()))}
    check(reads <= {"shared/LowPolyDinos.luau"}, f"LowPolyDinos flag read outside LowPoly.enabled: {sorted(reads)}")


def run_luau(runner: str):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "hit_sizes.luau"
        path.write_text(luau_script(), encoding="utf-8")
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding="utf-8")
    if result.returncode or "hit sizes passed" not in result.stdout:
        print(result.stdout)
        print(result.stderr)
        problems.append("Luau behavior checks failed")
        return {}
    got = {}
    for line in result.stdout.splitlines():
        m = re.match(r"R (\w+) (\S+) (\S+) (\S+)$", line)
        if m:
            got[(m.group(1), float(m.group(2)))] = (float(m.group(3)), float(m.group(4)))
    print(result.stdout.splitlines()[-1])
    return got


def python_cross_check(got):
    check(len(got) == len(MEASURED) * len(SCALES), f"expected {len(MEASURED) * len(SCALES)} radius rows, got {len(got)}")
    for species in MEASURED:
        for scale in SCALES:
            raw, clamped = expected(species, scale)
            have = got.get((species, float(scale)))
            check(have is not None and abs(have[0] - raw) < 1e-6 and abs(have[1] - clamped) < 1e-6,
                  f"{species} scale {scale}: Luau {have} differs from the ScaleLadder value raw {raw:.6f} / clamped {clamped:.6f}")


def legacy_radius(species: str, scale: float):
    w, _h, l = LEGACY.get(species, LEGACY_FALLBACK)
    return min(MAX_R, max(w, l) / 2 * scale)  # the legacy shell scales with the growth scale; CombatRules clamps at 14


def print_before_after():
    names = ["compy", "stegosaurus", "ankylosaurus", "spinosaurus", "mosasaurus", "quetzalcoatlus"]
    print("species | shell box (W x H x L) | before s1 / s2 / s4 | after s1 / s2 / s4 (cap 14)")
    for sp in names:
        w, h, l = LEGACY.get(sp, LEGACY_FALLBACK)
        before = " / ".join(f"{legacy_radius(sp, s):.2f}" for s in SCALES)
        after = " / ".join(f"{expected(sp, s)[1]:.2f}" for s in SCALES)
        print(f"{sp} | {w} x {h} x {l}{'' if sp in LEGACY else ' (fallback)'} | {before} | {after}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    parser.add_argument("--print", action="store_true")
    args = parser.parse_args()
    static_checks()
    python_cross_check(run_luau(args.runner))
    if args.print:
        print_before_after()
    if problems:
        print("verify_hit_sizes FAIL")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print("verify_hit_sizes ok")
