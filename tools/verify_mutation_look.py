"""BD-155: offline audit of src/shared/MutationLook.luau, the one look table for event mutations.
Every mutation in ProgressionConfig has a complete soft look (matte material, bounded tint pull, valid colours),
the badge colour equals the config colour, and the blend maths stays between base and tint.
Also scans that the world dino, previews and the mist all read the shared module (no private colour tables)."""
from pathlib import Path
import argparse
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
local ids = {}
for _, m in Config.EventMutations do ids[m.id] = m end
assert(#Look.Order == #Config.EventMutations, "look order covers every mutation")
local function rgb(c, what) assert(type(c) == "table" and #c == 3, what) for i = 1, 3 do assert(c[i] >= 0 and c[i] <= 255, what .. " range") end end
for _, id in Look.Order do
    local e = Look.get(id) assert(e and e.id == id and ids[id], id)
    assert(e.name == ids[id].name, id .. " name matches config")
    for _, key in {"tint", "rim", "mist", "spark", "badge"} do rgb(e[key], id .. "." .. key) end
    for i = 1, 3 do assert(e.badge[i] == ids[id].color[i], id .. " badge colour == ProgressionConfig colour") end
    assert(e.amount > 0 and e.amount <= Look.MaxAmount and Look.MaxAmount <= 0.35, id .. " tint pull stays gentle")
    assert(e.glow >= 0 and e.glow <= 0.6, id .. " glow stays soft")
    assert(e.material == "Plastic", id .. " dinos stay matte (BD-173)")
    assert(type(e.mood) == "string" and #e.mood > 0)
    -- tint must be a light pastel, never a dark or neon-saturated wall
    assert(math.max(e.tint[1], e.tint[2], e.tint[3]) >= 200, id .. " tint is bright")
end
assert(Look.get("") == nil and Look.get(nil) == nil and Look.get("clear") == nil and Look.get(5) == nil)
-- blend maths: between base and tint, capped, identity for unknown ids
local base = {100, 100, 100}
for _, id in Look.Order do
    local e = Look.get(id)
    local out = Look.blend(base, id)
    for i = 1, 3 do
        local lo, hi = math.min(base[i], e.tint[i]), math.max(base[i], e.tint[i])
        assert(out[i] >= lo - 1e-6 and out[i] <= hi + 1e-6, id .. " blend inside range")
        assert(math.abs(out[i] - base[i]) <= math.abs(e.tint[i] - base[i]) * Look.MaxAmount + 1e-6, id .. " capped pull")
    end
    local forced = Look.blend(base, id, 5) -- caller cannot exceed the ceiling
    assert(math.abs(forced[1] - base[1]) <= math.abs(e.tint[1] - base[1]) * Look.MaxAmount + 1e-6)
end
local same = Look.blend(base, "nope")
assert(same[1] == 100 and same[2] == 100 and same[3] == 100)
print("MutationLook passed: " .. #Look.Order .. " mutations, matte, gentle tint (<= " .. Look.MaxAmount .. "), badge colours match config")
'''


def script():
    s = 'local Config = ' + module('src/shared/ProgressionConfig.luau') + '\n'
    # Color3 is only used inside Look.color/Look.apply (call time); the pure table and Look.blend need no Roblox types.
    s += 'local Look = ' + module('src/shared/MutationLook.luau') + '\n' + BODY
    return s


def scan():
    checks = {
        'src/shared/MutationEffects.luau': 'MutationLook',
        'src/shared/DinosaurPreview.luau': 'MutationLook.apply',
        'src/client/PreviewTraits.luau': 'MutationLook.apply',
        'src/client/CosmeticVisuals.client.luau': 'Look.apply',
    }
    for path, needle in checks.items():
        assert needle in (ROOT / path).read_text(encoding='utf-8'), path + ' must use the shared MutationLook'
    # no private mutation colour table may remain in MutationEffects
    assert 'dewdrop = {Color3' not in (ROOT / 'src/shared/MutationEffects.luau').read_text(encoding='utf-8')
    # BD-154: every visible/gettable hook is still wired
    wired = {
        'src/server/FoodService.luau': 'RunEggTags.apply(events,weatherId',
        'src/client/HudV2.luau': 'for i = #tags, tagsSeen + 1, -1', # BD-378: the weather egg is named in the ONE found-egg toast
        'src/client/HatchSequence.luau': 'r.mutationName',
        'src/client/EggsScreen.luau': 'MutationLook.get(entry.mutationId)',
        'src/client/CosmeticVisuals.client.luau': 'kind~="mutation" and (#state.rigs>0 or mutationId~="")',  # BD-353: mutation keeps its own detail, aura/trail go lite
        'src/client/DinoIndexPanels.luau': 'mutationId = if d.stage == "base"',
    }
    for path, needle in wired.items():
        assert needle in (ROOT / path).read_text(encoding='utf-8'), path + ' lost its mutation hook: ' + needle
    assert 'MutationBadge.chip(' in (ROOT / 'src/client/DinoIndexPanels.luau').read_text(encoding='utf-8'), 'My dinos mutation chip must use the look badge colour'
    # BD-351/352: readable badge, calm hero smoke behind the dino, drag pill off the head
    badge = (ROOT / 'src/client/MutationBadge.luau').read_text(encoding='utf-8')
    assert 'Badge.MinTextSize = 14' in badge and 'Look.color(look.badge)' in badge and 'TextSize, text.TextColor3' in badge, 'badge: own colour, text >= 14 px'
    fxui = (ROOT / 'src/shared/FxUi.luau').read_text(encoding='utf-8')
    assert 'Ui.HeroSmokeSize, Ui.HeroSmokeAlpha, Ui.HeroSmokeRate = 0.4, 0.5, 0.5' in fxui and 'frame.ZIndex = math.max(view.ZIndex - 1, 0)' in fxui, 'hero smoke is thin and behind the viewport'
    hatch = (ROOT / 'src/client/HatchSequence.luau').read_text(encoding='utf-8')
    assert 'hintPosition = UDim2.fromScale(.17, .6)' in hatch and 'hintPosition = UDim2.fromScale(.5, .37)' not in hatch, 'Drag to turn must stay off the dino head'
    print('Source scan passed: world dino, previews and mist all read MutationLook; badge, hero smoke and drag pill rules hold')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    scan()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'mutation_look.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
