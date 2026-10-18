"""BD-392..BD-396 (owner playtest 2026-10-16, P1) offline checks. Not Studio evidence.

Runs the real pure modules in Luau (ShopForDino, ConditionStageRules, BiomePlacement.Ground) and statically checks the wiring:
 - BD-392 the Original egg popup draws the big baked egg (EggPicture.baked -> ModelPreview + EggAppearance.apply with the genes).
 - BD-393 Aura and Trail shops show "For: <dino>" with the silhouette and the one-line note (docs/72 words).
 - BD-394 Conditions shop: large egg tiles, and the stage/egg art slots (ConditionStageAssetIds) take only real rbxassetid ids,
   fall back to the live eggs, and no id is invented while the owner upload is pending.
 - BD-395 PropGround rule (bottom on terrain + 0.2, highest sample under the trunk, slope compensation, raycast correction).
 - BD-396 (rules are in tools/verify_hub_walk_there.py) the client draws halo, white core, edge arrow, capped at 24 parts.
 - No new Bootstrap top-level locals (193/200 limit).
"""
from pathlib import Path
import argparse, re, subprocess, tempfile
ROOT = Path(__file__).resolve().parents[1]
def wrapped(path): return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'

LUAU = r'''
-- ---- BD-393 copy
local F = ShopForDino
assert(F.title("Compy") == "For: Compy", F.title("Compy"))
assert(F.title(nil) == "For: your dino" and F.title("") == "For: your dino" and F.title(5) == "For: your dino")
assert(#F.title("Averyveryverylongdinosaurname") <= #"For: " + F.MaxTitleLength, "long names are cut")
assert(F.Note == "Switch dinos in Dinos to style another one", "the one-line note")
assert(#F.Note <= 44 and not F.Note:find("%d"), "short, no numbers")
assert(F.HeaderHeight == 40 and F.CardsHeightDesktop == 250 and F.CardsHeightDesktop + F.HeaderHeight + 52 <= 358 + 10, "header + cards fit above the footer")

-- ---- BD-394 stage slots
local S = ConditionStageRules
assert(S.assetId(nil, "stage") == nil and S.assetId({}, "stage") == nil, "nothing bound: nil")
assert(S.assetId({stage = "rbxassetid://123"}, "stage") == "rbxassetid://123")
for _, bad in {"123", "rbxassetid://", "rbxassetid://12a", "http://x/1", "", 5, true} do assert(S.assetId({stage = bad}, "stage") == nil, "junk id refused: "..tostring(bad)) end
local none = S.resolve({}, "cracked") assert(none.stage == nil and none.egg == nil, "fallback to the live eggs")
local half = S.resolve({cracked = "rbxassetid://5"}, "cracked") assert(half.stage == nil and half.egg == nil, "an egg without the stage is not shown alone")
local full = S.resolve({stage = "rbxassetid://1", cracked = "rbxassetid://5"}, "cracked") assert(full.stage == "rbxassetid://1" and full.egg == "rbxassetid://5")
local part = S.resolve({stage = "rbxassetid://1", cracked = "rbxassetid://5"}, "dirty") assert(part.stage == "rbxassetid://1" and part.egg == nil, "missing condition egg: live egg on the stage")
assert(#S.Keys == 6 and S.Files.cracked:find("egg%-01_cracked") and S.Files.astra:find("egg%-05_astra") and S.Files.stage:find("egg%-stage%-jungle%-v1"))
-- 2026-10-17: the stage and the five condition eggs are uploaded (lead, owner standing approval) and bound by bind_assets; every id must
-- be a real rbxassetid for one of the six known keys (never an invented key or a malformed value).
local count = 0
for key, id in ProgressionConfig.ConditionStageAssetIds do
 count += 1
 assert(table.find(S.Keys, key) ~= nil, "unknown stage key " .. tostring(key))
 assert(type(id) == "string" and id:match("^rbxassetid://[1-9]%d+$"), "stage id is a real asset id: " .. tostring(key))
end
assert(count == 0 or count == 6, "either nothing uploaded yet or all six stage images bound")
assert(ConditionOverlays.ShopZoom >= 1.6 * 1.15, "shop eggs are zoomed well past the old 1.6")

-- ---- BD-395 PropGround (the pure rule; verify_world_art runs it over the whole generated island)
local G = BiomePlacement.Ground
assert(G.Clearance == 0.2 and G.Raised.tree and G.Raised.colossal and G.Raised.shrub and not G.Raised.rock)
local flat = {10, 10, 10, 10, 10}
assert(math.abs(G.restY("tree", flat, 20, 1) - 10.2) < 1e-9, "flat: bottom 0.2 above the ground")
local slope = {10, 11.5, 8.5, 10, 10} -- trunk straddles a slope: highest sample wins (the uphill side is not buried)
assert(math.abs(G.restY("colossal", slope, 78, 4) - 11.7) < 1e-9, "slope: highest point + 0.2")
assert(not G.submerged(G.restY("tree", slope, 20, 1), slope, 0), "never submerged by the rule")
assert(G.submerged(10 - 0.03 * 20, slope, 0.5), "the OLD rule (lowest - 3% of height) buried the uphill side")
assert(G.restY("rock", slope, 10, 2) < 8.5, "rocks still embed a little")
local tr = G.trunkRadius({colliders = {{0, 0, 0, 2.079, 10.5, 2.079, 0}}}, 4, 1) assert(math.abs(tr - 4.158) < 1e-9, "trunk radius from the collider")
assert(G.trunkRadius({colliders = {}}, 4, 1.5) == 1.5 and G.trunkRadius(nil, 2, 0.7) == 0.7)
assert(#G.samplePoints(5, 7, 2) == 5)
-- BD-416/417 sampling policy: plants highest - RootSink, rocks and spires lowest - embed, giant rocks follow the rock rule, tall props skip steep slopes
assert(G.RootSink == 0.15 and G.TallMaxSlope == 25 and G.Policy.plant == "highest" and G.Policy.rock == "lowest")
local ray = {10, 12, 8, 11, 9}
assert(math.abs(G.restYRay("tree", ray, 20, 1) - 11.85) < 1e-9 and math.abs(G.restYRay("shrub", ray, 1, 1) - 11.85) < 1e-9)
assert(math.abs(G.restYRay("rock", ray, 30, 1) - (8 - 0.12 * 30)) < 1e-9, "spire: lowest ray minus embed")
assert(G.restYRay("landmark", ray, 9, 1.4) == 8)
assert(G.rayLayer("colossal", "rock") == "rock" and G.rayLayer("colossal", "tree") == "colossal" and G.rayLayer("rock", "rock") == "rock")
assert(G.footprintRadius("tree", 10, 12) == 0.48 and G.footprintRadius("shrub", 60, 5) == 1 and G.footprintRadius("rock", 10, 8) == 3 and G.footprintRadius("rock", 60, 5) == 6)
assert(math.abs(G.corrected(10, {10.4, 10.1, 10.0, nil, 10.2}, "tree", 20, 1) - 10.25) < 1e-9, "raycast answer used: highest - RootSink (BD-417)")
assert(G.corrected(10, {nil, nil, 10.4}, "tree", 20, 1) == 10, "too few rays hit: keep the layout height")
assert(G.corrected(10, {40, 40, 40, 40, 40}, "tree", 20, 1) == 10, "a ray far from the layout is ignored")
assert(G.corrected(10, {}, "tree", 20, 1) == 10)
print("owner feedback p1: copy, stage slots, ground rule ok")
'''

def script():
    return ('local Color3={fromRGB=function(r,g,b) return {r,g,b} end}\n'
            + 'local Enum={Material=setmetatable({},{__index=function(_,k) return k end})}\n'
            + 'local ShopForDino=' + wrapped('src/shared/ShopForDino.luau') + '\n'
            + 'local ConditionStageRules=' + wrapped('src/shared/ConditionStageRules.luau') + '\n'
            + 'local ProgressionConfig=' + wrapped('src/shared/ProgressionConfig.luau') + '\n'
            + 'local ConditionOverlays=' + wrapped('src/shared/ConditionOverlays.luau') + '\n'
            + 'local BiomePlacement=' + wrapped('src/shared/BiomePlacement.luau') + '\n' + LUAU)

def run(runner):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_owner_feedback_p1.luau'; path.write_text(script(), encoding='utf-8')
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-3000:] + out.stderr)
        return out.stdout.strip()

def read(path): return (ROOT / path).read_text(encoding='utf-8')

def static_checks():
    pic = read('src/client/EggPicture.luau')
    assert 'function EggPicture.baked' in pic and 'ModelPreview.add' in pic and 'EggAppearance.apply(view, genes, true)' in pic, 'BD-392 baked egg uses the hatch path'
    panels = read('src/client/DinoIndexPanels.luau')
    popup = panels[panels.index('local function eggPopup'):panels.index('function Panels.species')]
    assert 'EggPicture.baked(' in popup and 'EggStage' in popup, 'BD-392 popup shows the big baked egg'
    assert 'UDim2.fromOffset(580, 390)' in popup and 'EggPicture.baked(stage, genes, 262)' in popup, 'BD-392 egg is large'
    boot = read('src/client/Bootstrap.client.luau')
    boot_top = boot  # the local count below is Bootstrap's own
    boot = boot + read('src/client/ShopScreens.luau')  # BD-1020: the shop screens moved
    assert 'ShopCards).forHeader(' in boot and 'ShopForDino' in boot, 'BD-393 header in the aura and trail shops'
    assert boot.index('forHeader(') < boot.index('require(script.Parent.ShopCards).build('), 'BD-393 header is drawn before the cards'
    cards = read('src/client/ShopCards.luau')
    assert 'function Cards.forHeader' in cards and '"silhouette"' in cards and 'ForDinoNote' in cards, 'BD-393 silhouette + note'
    assert 'ConditionStage).background(' in boot and 'ConditionStage).egg(' in boot, 'BD-394 stage slot wired'
    ep = (ROOT / 'src/client/EggPicture.luau').read_text(encoding='utf-8')
    assert 'EggConditionBoost' in ep and 'look :: any).stack' in ep, 'BD-141 faint overlays stacked in the flat egg'
    assert 'EggPicture).add(tile,EggGenetics.neutral(row.id),150)' in boot and 'cardsY+62,155,144' in boot, 'BD-141 flat condition egg tiles (BD-394 size)'
    arena = read('src/server/Arena.luau')
    assert 'Ground.corrected(' in arena and 'RaycastParams.new()' in arena and 'workspace.Terrain' in arena, 'BD-395 raycast ground correction'
    assert 'WorldKitRayMoved' in arena, 'BD-395 counter for the Studio measurement'
    top = [l for l in boot_top.splitlines() if re.match(r'^local\s', l)]
    from bootstrap_sources import MAX_TOP_LOCALS
    assert len(top) <= MAX_TOP_LOCALS, 'client Bootstrap top-level locals stay at or below %d (tools/bootstrap_sources.py): %d' % (MAX_TOP_LOCALS, len(top))
    # the owner's stage files exist in the repo (the slot waits for their upload)
    for f in ('resources/ui/v2/stage/egg-stage-jungle-v1.jpg', 'resources/ui/v2/stage/eggs/egg-01_cracked.png', 'resources/ui/v2/stage/eggs/egg-02_dirty.png',
              'resources/ui/v2/stage/eggs/egg-03_normal.png', 'resources/ui/v2/stage/eggs/egg-04_rainbow.png', 'resources/ui/v2/stage/eggs/egg-05_astra.png'):
        assert (ROOT / f).exists(), 'stage art file present: ' + f

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runner', required=True); args = p.parse_args()
    static_checks()
    print(run(args.runner))
