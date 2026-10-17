"""BD-381: with Config.LowPolyDinos on (playtest profile) no dino VIEW may build or keep a legacy model while the low-poly one is
available or still loading. Views: the world character and Sanctuary pad (ResourceVisuals), every ViewportFrame card (HOME / Dino Details /
Index / Fusion / Hatch / Shop headers, all through Shared/DinosaurPreview), NPC predators. Offline: source structure checks plus a Luau
run of the real Shared/LowPolyReady rule and of the real Shared/ResourceModels.clone with stubbed collaborators.
Usage: python tools/verify_lowpoly_views.py --runner <luau>"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
problems: list[str] = []


def read(rel: str) -> str:
    return (SRC / rel).read_text(encoding="utf-8")


def code(path: Path) -> str:
    """Source without Luau line comments."""
    return "\n".join(re.sub(r"--.*$", "", line) for line in path.read_text(encoding="utf-8").splitlines())


def files(pattern: str):
    return sorted(SRC.rglob(pattern))


def check(ok: bool, message: str):
    if not ok:
        problems.append(message)


def static_checks():
    models = read("shared/ResourceModels.luau")
    # 1. clone order on the client: low-poly first, then the pending gate, only then any legacy source.
    body = models[models.index("function ResourceModels.clone"):]
    i_clone, i_pending, i_authored = body.find("LowPoly.clone("), body.find("LowPoly.pending("), body.find("Authored.clone(")
    check(0 <= i_clone < i_pending < i_authored, "ResourceModels.clone must try LowPoly.clone, then the LowPoly.pending gate, then Authored (legacy)")
    check("patient==true and LowPoly.pending(id)" in body, "ResourceModels.clone: a patient (preview) clone must return nil while the low-poly model is pending")
    # 2. only ResourceModels may build an authored (legacy) creature; everything else asks ResourceModels or LowPolyDinos.
    for path in files("*.luau"):
        rel = path.relative_to(SRC).as_posix()
        if rel not in ("shared/ResourceModels.luau", "shared/AuthoredCreatures.luau"):
            text = code(path).replace('AuthoredCreatures").clone("egg"', "").replace('AuthoredCreatures).clone("egg"', "")  # the EGG is not a dino
            check("Authored.clone(" not in text and "AuthoredCreatures).clone(" not in text,
                  f"{rel} builds a legacy authored creature directly; go through ResourceModels.clone")
    # 3. legacy shell renderer: server character + NPC fallback only.
    callers = {p.relative_to(SRC).as_posix() for p in files("*.luau")
               if p.name != "DinosaurVisual.luau" and re.search(r"\bVisual\.render\(", p.read_text(encoding="utf-8"))}
    check(callers <= {"server/Dinosaur.luau", "server/NpcPredatorService.luau"}, f"unexpected DinosaurVisual.render callers: {sorted(callers)}")
    npc = read("server/NpcPredatorService.luau")
    check("LowPoly" in npc and npc.index("LowPoly") < npc.index("Visual.render("), "NPC predators must try the low-poly model before the legacy visual")
    # 4. ViewportFrame creators: dino cards use DinosaurPreview only.
    known = {"shared/DinosaurPreview.luau", "shared/ModelPreview.luau", "client/HatchEggV2.luau", "shared/PotionArt.luau"}
    makers = {p.relative_to(SRC).as_posix() for p in files("*.luau") if 'Instance.new("ViewportFrame")' in p.read_text(encoding="utf-8")}
    check(makers <= known, f"new ViewportFrame creator(s) {sorted(makers - known)}: dino views must go through Shared/DinosaurPreview (low-poly aware)")
    # 5. DinosaurPreview waits for a pending low-poly model in BOTH load branches and keeps a flat picture meanwhile.
    prev = read("shared/DinosaurPreview.luau")
    check("Resources.clone(speciesId,if traits then traits.genes else nil,true)" in prev, "DinosaurPreview must clone patiently (patient=true)")
    check("LowPoly.whenReady(" in prev and "LowPoly.pending(" in prev, "DinosaurPreview must wait for a pending low-poly template (whenReady / pending)")
    check("if not waiting then attempts+=1 end" in prev, "DinosaurPreview retries while pending must not use up the attempt budget")
    check("dinoImage(viewport,gold)" in prev, "DinosaurPreview keeps the flat picture while no model is ready")
    # 6. character and pad: self-heal when the template lands, and the respawn ladder (BD-389).
    rv = read("client/ResourceVisuals.client.luau")
    check("folder.ChildAdded:Connect" in rv and 'GetAttribute("LowPoly") ~= true then visual:Destroy()' in rv,
          "ResourceVisuals must replace a legacy local mesh when a template arrives")
    check("for _, wait in {0.3, 0.7, 1.5, 3, 6, 10}" in rv, "ResourceVisuals respawn retry ladder (BD-389)")
    # 7. loader: starter first, every species loaded concurrently, completion attribute is what clients wait for.
    loader = read("server/LowPolyDinoLoader.luau")
    check('loadOne("compy"' in loader and loader.index('loadOne("compy"') < loader.index("task.spawn(function()"), "LowPolyDinoLoader must load the starter compy first")
    check('SetAttribute("LowPolyDinosLoaded"' in loader and "while running > 0" in loader, "LowPolyDinoLoader must report completion after all species")
    # 8. one flag, read in one place; default off, playtest on.
    reads = {p.relative_to(SRC).as_posix() for p in files("*.luau") if re.search(r"\bConfig\b[^\n]*\.LowPolyDinos\b|\)\.LowPolyDinos\b", code(p))}
    check(reads <= {"shared/LowPolyDinos.luau"}, f"LowPolyDinos flag read outside LowPoly.enabled: {sorted(reads - {'shared/LowPolyDinos.luau'})}")
    check(re.search(r"^\s*LowPolyDinos = false,", read("shared/Config.luau"), re.M) is not None, "Config.LowPolyDinos must default to false (profiles turn it on)")
    profiles = (ROOT / "tools/release_profiles.py").read_text(encoding="utf-8")
    check('Rule("LowPolyDinos", "set", True' in profiles, "playtest profile must set LowPolyDinos true")
    # 9. Fusion: a dino without a saved pattern (the starter) is NOT fusable (rule unchanged); only the card wording is kid friendly.
    sel = read("shared/FusionSelection.luau")
    check('return "missing_pattern"' in sel, "Fusion must keep rejecting a dino without a saved pattern")
    words = re.search(r'missing_pattern = "([^"]+)"', sel)
    check(bool(words) and len(words.group(1)) <= 24 and "pattern" not in words.group(1).lower(), "missing_pattern card words: short and no rule words (docs/72)")


def luau_checks(runner: str):
    ready = read("shared/LowPolyReady.luau")
    models = read("shared/ResourceModels.luau").replace("--!strict", "", 1)
    lua = "local Ready = (function()\n" + ready + "\nend)()\n" + r'''
-- truth table: pending only for a mapped species on an enabled flag, no template, loader running, inside the wait window
assert(Ready.pending(true, true, false, false, 0) == true, "pending at start")
assert(Ready.pending(true, true, false, false, Ready.WaitSeconds - 1) == true, "pending inside the window")
assert(Ready.pending(true, true, false, false, Ready.WaitSeconds) == false, "a loader that never reports stops blocking")
assert(Ready.pending(false, true, false, false, 0) == false, "flag off: legacy is the normal look")
assert(Ready.pending(true, false, false, false, 0) == false, "unmapped species: legacy is the normal look")
assert(Ready.pending(true, true, true, false, 0) == false, "template present")
assert(Ready.pending(true, true, false, true, 0) == false, "loader done and no template = real failure, legacy fallback")

-- the real ResourceModels.clone with stubbed collaborators
local state = {lowPoly = nil, pending = false, authored = 0}
local legacy = {name = "legacy"}
local lowPolyModel = {name = "lowpoly"}
local LowPolyStub = {clone = function() return state.lowPoly end, pending = function() return state.pending end}
local AuthoredStub = {clone = function() state.authored += 1 return legacy end, has = function() return true end}
local deps = {RuntimeMeshes = {clone = function() return legacy end}, AuthoredCreatures = AuthoredStub, LowPolyDinos = LowPolyStub}
local scriptStub = {Parent = deps}
local gameStub = {GetService = function(_, name)
    if name == "RunService" then return {IsClient = function() return true end} end
    return {FindFirstChild = function() return nil end}
end}
local ResourceModels = (function(script, game, require)
''' + models + r'''
end)(scriptStub, gameStub, function(m) return m end)

local function run(lowPoly, pending, patient)
    state.lowPoly, state.pending, state.authored = lowPoly, pending, 0
    return ResourceModels.clone("compy", nil, patient), state.authored
end
local m, calls = run(lowPolyModel, false, true)
assert(m == lowPolyModel and calls == 0, "low-poly ready: preview gets it, legacy never touched")
m, calls = run(lowPolyModel, true, true)
assert(m == lowPolyModel and calls == 0, "low-poly ready beats pending")
m, calls = run(nil, true, true)
assert(m == nil and calls == 0, "PENDING preview: no legacy model (flat picture until the template lands)")
m, calls = run(nil, false, true)
assert(m == legacy and calls == 1, "loader finished without a template (real failure): legacy fallback is allowed")
m, calls = run(nil, true, nil)
assert(m == legacy and calls == 1, "non-patient (character shell): unchanged, self-heals through ResourceVisuals")
print("lowpoly views luau passed")
'''
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "lowpoly_views.luau"
        path.write_text(lua, encoding="utf-8")
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding="utf-8")
        print(result.stdout, end="")
        if result.returncode or "passed" not in result.stdout:
            print(result.stderr)
            problems.append("Luau behavior checks failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    args = parser.parse_args()
    static_checks()
    luau_checks(args.runner)
    if problems:
        print("verify_lowpoly_views FAIL")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print("verify_lowpoly_views ok")
