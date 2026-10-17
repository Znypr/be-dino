"""Execute the pure BD-149/150/151 logic with the pinned Luau runtime:
- src/shared/InspectMath.luau: 12 px drag threshold (a plain tap never rotates), 360 degree yaw with wrap, inertia
  decay and stop, no inertia / idle spin in Reduced Motion, zoom clamps, reset.
- src/shared/MyDinos.luau + EggTraits.selected(preferredKey): the Dino Index "My dinos" selection (best copy first),
  per-copy equip request / ownership validation, the single "Equipped" tag, and filter/sort PARITY with
  FusionSelection (the Fusion menu and the Index share one model).
Drawing (ViewportFrames, input, sheet) is Studio-only. Text checks pin the wiring (hatch tap gating, server equip
validation, workflow) so refactors cannot silently drop it.
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    text = (ROOT / path).read_text(encoding='utf-8')
    text = re.sub(r'require\(script\.Parent\.(\w+)\)', r'MOD_\1', text)
    return '(function()\n' + text + '\nend)()'


def script():
    mods = ['Config', 'ProgressionConfig', 'EggGenetics', 'EggTraits', 'FusionSelection', 'InspectMath', 'MyDinos']
    out = ''
    for name in mods:
        out += 'local MOD_%s=%s\n' % (name, module('src/shared/%s.luau' % name))
    return out + r'''
local M, I, Sel, Traits = MOD_MyDinos, MOD_InspectMath, MOD_FusionSelection, MOD_EggTraits
local function near(a, b, e) return math.abs(a - b) <= (e or 1e-6) end

-- ===== Inspect math =====
assert(I.DragThreshold == 12)
local s = I.new()
I.press(s, 100, 100, 0)
assert(not I.move(s, 110, 105, .01) and s.yaw == 0 and not s.moved, "under 12 px nothing rotates")
assert(I.release(s, .02, true) == "tap" and not I.consumedTap(s), "a plain tap stays a tap (continue tap works)")
I.press(s, 100, 100, 0)
assert(not I.move(s, 111, 100, .01) and not s.moved, "11 px is still a tap")
assert(not I.move(s, 112, 100, .02) and s.moved and s.yaw == 0, "12 px crosses the threshold, starts from there (no jump)")
assert(I.move(s, 162, 100, .05) and near(s.yaw, 50 * I.RadiansPerPixel), "then rotation follows the finger")
assert(I.consumedTap(s) and I.release(s, .06, true) == "drag", "a drag is never a tap (hatch must not advance)")
I.press(s, 5, 5, 1) assert(not I.consumedTap(s), "the next press clears the drag flag")
I.release(s, 1.01, true)
-- One full 360 degrees is reachable and wraps into [0, 2 pi).
s = I.new() I.press(s, 0, 0, 0) I.move(s, 20, 0, .01)
local x = 20
for i = 1, 200 do x += 5 I.move(s, x, 0, .01 + i * .004) end
assert(s.yaw >= 0 and s.yaw < I.TAU, "wrapped")
assert(x * I.RadiansPerPixel > I.TAU, "a long drag turns more than 360 degrees")
-- Inertia: a flick keeps turning, slows monotonically, and stops; held still = no fling.
s = I.new() I.press(s, 0, 0, 0)
for i = 1, 12 do I.move(s, i * 14, 0, i * .008) end
assert(I.release(s, 12 * .008 + .004, true) == "drag" and math.abs(s.vel) > 1, "flick has speed")
local prev, t, stopped = math.abs(s.vel), 0, nil
while t < 6 do
    I.step(s, 1 / 60, true) t += 1 / 60
    assert(math.abs(s.vel) <= prev + 1e-9, "inertia only decays")
    prev = math.abs(s.vel)
    if s.vel == 0 then stopped = t break end
end
assert(stopped and stopped < 3.5, "inertia stops by itself")
s = I.new() I.press(s, 0, 0, 0) for i = 1, 12 do I.move(s, i * 14, 0, i * .008) end
I.release(s, 3, true) assert(s.vel == 0, "finger held still before release: no fling")
assert(math.abs(I.MaxSpin) >= 1)
s = I.new() I.press(s, 0, 0, 0) I.move(s, 20, 0, .001) I.move(s, 4000, 0, .002)
assert(math.abs(s.vel) <= I.MaxSpin + 1e-9, "flick speed is capped")
-- Reduced motion: drag only.
s = I.new() I.press(s, 0, 0, 0) for i = 1, 12 do I.move(s, i * 14, 0, i * .008) end
I.release(s, .1, false) assert(s.vel == 0, "no inertia without motion")
local yaw = s.yaw for _ = 1, 120 do I.step(s, 1 / 60, false) end
assert(s.yaw == yaw, "no auto-spin / inertia in Reduced Motion")
-- Idle spin until the first touch (full motion).
s = I.new() local before = s.yaw
for _ = 1, 60 do I.step(s, 1 / 60, true) end
assert(s.yaw > before and near(s.yaw, I.IdleSpin, .01), "slow idle spin")
I.press(s, 0, 0, 0) I.release(s, .01, true)
yaw = s.yaw for _ = 1, 60 do I.step(s, 1 / 60, true) end
assert(s.yaw == yaw and s.touched, "idle spin ends at the first touch")
-- Zoom stays inside limits; NaN safe; reset restores the default view.
s = I.new()
for _ = 1, 100 do I.wheel(s, 1) end assert(s.zoom == I.MaxZoom)
for _ = 1, 100 do I.wheel(s, -1) end assert(s.zoom == I.MinZoom)
I.pinch(s, 1, 9) assert(s.zoom == I.MaxZoom) I.pinch(s, 1, 0 / 0) assert(s.zoom == 1)
s.yaw, s.vel, s.zoom = 2, 3, 1.5
assert(I.changed(s)) I.reset(s)
assert(s.yaw == 0 and s.vel == 0 and s.zoom == 1 and not I.changed(s))

-- ===== My dinos =====
local Patterns = {"01_blank", "02_emerald_islands", "03_round_spots", "04_bold_patches", "05_horizontal_bands", "06_wavy_stripes", "07_diamond_scales", "08_freckles"}
local cat = Sel.buildCatalog(MOD_Config, MOD_ProgressionConfig, Patterns)
local n = 0
local function dino(over)
    n += 1
    local d = {instanceId = "u:1/d:" .. n, speciesId = "compy", stage = "base",
        genes = {patternId = "06_wavy_stripes", primaryColorId = "green", secondaryColorId = "blue", blend = 20, hatchSuccess = true},
        big = false, shiny = false, mutationId = "", originKind = "hatch", locked = false, favorited = false, auraCount = 0, trailCount = 0}
    for k, v in over or {} do if k == "genes" then for gk, gv in v do d.genes[gk] = gv end else d[k] = v end end
    return d
end
local all = {}
for _ = 1, 14 do table.insert(all, dino()) end
local shiny = dino({shiny = true}) local big = dino({big = true, genes = {primaryColorId = "red"}})
local spots = dino({genes = {patternId = "03_round_spots", primaryColorId = "red"}})
local gold = dino({stage = "gold"}) local diamond = dino({stage = "diamond", genes = {patternId = "08_freckles"}})
local rainbow = dino({genes = {primaryColorId = "red"}})
local ember = dino({mutationId = "ember"})
local raptor = dino({speciesId = "raptor"})
for _, d in {shiny, big, spots, gold, diamond, rainbow, ember, raptor} do table.insert(all, d) end

local mine = M.forSpecies(all, "compy")
assert(#mine == #all - 1 and M.header("Compy", 14) == "Compy x 14")
for _, d in mine do assert(d.speciesId == "compy") end

-- Default selection = the first card of the Rarest sort (the rarest copy), identical to FusionSelection.
local best = M.defaultSelection(mine, cat)
assert(best == Sel.sort(mine, "rarest", {}, {}, cat)[1].instanceId and best == shiny.instanceId)

-- Parity: every sheet filter group maps to a FusionSelection field and gives the SAME result as Sel.filter.
for _, group in M.FilterGroups do assert(table.find(Sel.FilterFields, M.field(group)), "unknown filter field " .. group) end
for _, key in M.SortKeys do assert(table.find(Sel.SortKeys, key) and M.SortLabels[key], "unknown sort key " .. key) end
assert(Sel.SortNames.recent == "Newest" and M.SortLabels.recent == "Newest" and M.SortLabels.rarest == Sel.SortNames.rarest)
local function ids(list) local r = {} for _, d in list do table.insert(r, d.instanceId) end return table.concat(r, ",") end
local options = M.options(mine, cat)
local samples = {colorId = "red", patternId = "03_round_spots", mutationId = "ember", shiny = true, big = true, stageId = "gold"}
assert(not table.find(M.FilterGroups, "conditionId") and options.conditionId == nil, "dinosaurs have no Condition filter")
for group, value in samples do
    assert(table.find(options[group], value), "option present for " .. group)
    local filters = {[M.field(group)] = value}
    assert(ids(M.view(mine, {[group] = value}, "rarest", cat)) == ids(Sel.sort(Sel.filter(mine, filters), "rarest", {}, {}, cat)), "parity " .. group)
end
assert(#M.view(mine, {colorId = "red"}, "rarest", cat) == 3 and #M.view(mine, {stageId = "gold"}, "rarest", cat) == 1)
assert(#M.view(mine, {shiny = true, colorId = "red"}, "rarest", cat) == 0, "filters combine (AND)")
assert(not table.find(options.mutationId, "none") and table.find(options.mutationId, "ember"))
assert(options.stageId[1] == "base" and options.stageId[#options.stageId] == "diamond", "stages in ladder order")
for _, key in M.SortKeys do
    assert(ids(M.view(mine, {}, key, cat)) == ids(Sel.sort(mine, key, {}, {}, cat)), "sort parity " .. key)
    assert(ids(M.view(mine, {}, key, cat)) == ids(M.view(mine, {}, key, cat)), "deterministic " .. key)
end
assert(ids(M.view(mine, {}, "nonsense", cat)) == ids(M.view(mine, {}, "rarest", cat)), "unknown sort falls back to Rarest")
assert(M.view(mine, {}, "recent", cat)[1] == raptor or M.view(mine, {}, "recent", cat)[1] == ember, "Newest first")
-- Active chips are removable, in sheet order, with short words.
local chips = M.activeChips({shiny = true, colorId = "red", stageId = "gold"}, cat)
assert(#chips == 3 and chips[1].group == "colorId" and chips[1].text == "Red" and chips[2].text == "Shiny" and chips[3].text == "Gold")
-- Empty state: nothing matches -> empty view, selection settles to nil, clearing restores all.
local none = M.view(mine, {shiny = true, stageId = "diamond"}, "rarest", cat)
assert(#none == 0 and M.settleSelection(none, shiny.instanceId) == nil)
assert(#M.view(mine, {}, "rarest", cat) == #mine)
assert(M.settleSelection(mine, gold.instanceId) == gold.instanceId, "selection is kept while visible")
assert(M.settleSelection({big}, gold.instanceId) == big.instanceId, "else first card")
-- Paging: at most PageSize cards are drawn; the rest sits behind SHOW MORE.
local shown, more = M.page(mine, M.PageSize)
assert(shown == math.min(#mine, M.PageSize) and shown + more == #mine)
local many = {} for i = 1, 100 do many[i] = dino() end
shown, more = M.page(many, M.PageSize) assert(shown == M.PageSize and more == 100 - M.PageSize)
shown, more = M.page(many, M.PageSize * 2) assert(shown == M.PageSize * 2)

-- Virtualization window: never more than MaxLivePreviews live card previews (EditableImage cap), follows the scroll.
for total = 1, 80 do
    for y = 0, 3000, 137 do
        local first, last = M.window(y, 300, 138, 8, 4, total)
        assert(last - first + 1 <= M.MaxLivePreviews and first >= 1 and last <= total, "window bounded")
    end
end
-- BD-507: card rows. Ribbons (SHINY / BIG pills, mutation badge) sit UNDER the thumbnail, never over the dino.
do
    local C = M.Card
    for pills = 0, 2 do
        for _, chip in {false, true} do
            local r = M.cardRows(pills, chip)
            local thumbBottom = C.top + r.thumbH
            assert(r.thumbH >= C.minThumbH, "thumbnail keeps a readable size: " .. pills .. tostring(chip))
            if pills > 0 then assert(r.pillY >= thumbBottom, "pills start under the thumbnail") end
            if chip then assert(r.chipY >= thumbBottom, "mutation badge starts under the thumbnail") end
            if pills > 0 and chip then assert(r.pillY + C.pillH <= r.chipY, "pill row above the badge row") end
            local lowest = if chip then r.chipY + C.chipH elseif pills > 0 then r.pillY + C.pillH else thumbBottom
            assert(lowest <= r.labelY and r.labelY + C.labelH <= r.swatchY and r.swatchY + C.swatchH <= r.tagY and r.tagY + C.tagH <= C.h, "card rows stack without overlap")
            assert(C.pillH >= 17 and C.chipH >= 22, "14 px pill text fits its pill")
        end
    end
    assert(M.cardRows(0, false).thumbH > M.cardRows(2, true).thumbH, "a plain dino keeps the bigger thumbnail")
end
local f, l = M.window(0, 300, 138, 8, 4, 60) assert(f == 1 and l >= 12, "visible rows are inside the window")
f, l = M.window(1460, 300, 138, 8, 4, 60) assert(f > 20 and f <= 41 and l >= 53, "window follows the scroll (cards scrolled away unmount)")
f, l = M.window(0, 300, 138, 8, 4, 0) assert(l < f)

-- Equip requests: the exact owned copy for keyed base copies, the species only for the rest.
assert(M.variantKey(all[1]) == Traits.key("", false, false, all[1].genes), "genes-bearing base copy has a key")
assert(M.variantKey(shiny) == Traits.key("", true, false, shiny.genes))
assert(M.variantKey(gold) == nil and M.variantKey(diamond) == nil, "Gold/Diamond equip as the species")
local noGenes = dino() noGenes.genes = nil
assert(M.variantKey(noGenes) == nil, "a plain legacy copy has no per-copy identity")
local req = M.equipRequest(shiny) assert(req.speciesId == "compy" and req.variantKey == M.variantKey(shiny))
assert(M.equipRequest(gold).variantKey == nil and M.equipRequest(nil) == nil)
-- Server mirror: only a key present in the player's own collection with count > 0 is equippable.
local entry = {variants = {[M.variantKey(shiny) :: string] = {count = 2, shiny = true, big = false, mutationId = "", genes = shiny.genes},
    [M.variantKey(big) :: string] = {count = 0, shiny = false, big = true, mutationId = "", genes = big.genes}}}
assert(M.ownsVariant(entry, M.variantKey(shiny)))
assert(not M.ownsVariant(entry, M.variantKey(big)), "count 0 = not owned")
assert(not M.ownsVariant(entry, "evil:key") and not M.ownsVariant(entry, 5) and not M.ownsVariant(entry, "") and not M.ownsVariant(entry, string.rep("x", 161)))
assert(not M.ownsVariant({}, M.variantKey(shiny)) and not M.ownsVariant(nil, "a"))
-- EggTraits.selected honours the chosen copy while owned and falls back to the best copy otherwise.
local variants = {}
for _, d in {shiny, big, all[1]} do
    variants[M.variantKey(d) :: string] = {count = 1, shiny = d.shiny, big = d.big, mutationId = "", genes = d.genes}
end
local e = {variants = variants}
assert(Traits.selected(e).key == M.variantKey(big), "default = server best copy (BIG outranks Shiny there)")
assert(Traits.selected(e, M.variantKey(all[1])).key == M.variantKey(all[1]), "chosen copy equips")
variants[M.variantKey(all[1]) :: string].count = 0
assert(Traits.selected(e, M.variantKey(all[1])).key == M.variantKey(big), "a copy no longer owned falls back")
assert(Traits.selected(e, "bogus").key == M.variantKey(big))
assert(Traits.selected(e, nil).key == M.variantKey(big))

-- "Equipped" tag appears on exactly one card.
local function attrsOf(d) return {speciesId = d.speciesId, genes = d.genes, shiny = d.shiny, big = d.big, mutationId = d.mutationId} end
local bestFirst = M.view(mine, {}, "rarest", cat)
assert(M.equippedId(bestFirst, attrsOf(shiny)) == shiny.instanceId)
assert(M.equippedId(bestFirst, attrsOf(big)) == big.instanceId)
local twin = M.equippedId(bestFirst, attrsOf(all[1]))
assert(twin and mine[1] and Sel.index(mine)[twin].genes.patternId == "06_wavy_stripes")
assert(M.equippedId(bestFirst, {speciesId = "raptor", genes = raptor.genes, shiny = false, big = false, mutationId = ""}) == nil, "other species")
local plain = M.equippedId(bestFirst, {speciesId = "compy", genes = nil, shiny = false, big = false, mutationId = ""})
assert(plain == gold.instanceId or plain == diamond.instanceId, "species-only equip tags the best keyless copy")
assert(M.equippedId({}, attrsOf(shiny)) == nil and M.equippedId(bestFirst, nil) == nil)

print("Inspect and My dinos checks passed")
'''


def run(runner, source, name):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        path.write_text(source, encoding='utf-8')
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def check_wiring():
    hatch = read('src/client/HatchSequence.luau')
    assert 'InspectView.attach(a.dino' in hatch and 'surface = overlay' in hatch, 'hatch reveal uses InspectView on the tap catcher'
    assert re.search(r'if inspect and \(inspect :: InspectView\.Handle\)\.wasDrag\(\) then return end', hatch), 'a drag never advances the hatch'
    assert 'inspect.destroy()' in hatch, 'inspect handle is released with the egg'
    assert 'Timeline.tap(state)' in hatch and 'overlay.Activated:Connect(onTap)' in hatch, 'tap gating intact'
    camera = read('src/shared/PreviewCamera.luau')
    assert 'InspectYaw' in camera and 'InspectZoom' in camera
    view = read('src/client/InspectView.luau')
    for needle in ('Theme.MotionEnabled', 'Drag to turn', 'ResetView', 'Vector2.new(1, 0)', 'UDim2.fromOffset(72, 44)', 'TouchPinch', 'MouseWheel'):
        assert needle in view, needle
    assert 'Instance.new("ViewportFrame")' not in view and ':Clone()' not in view, 'one viewport, no clones'
    panels = read('src/client/DinoIndexPanels.luau')
    for needle in ('InspectView.attach', 'MyDinos.PageSize', 'MyDinos.window', 'entry.unmount()', 'No dinos match, clear filters', 'Not discovered yet', 'action = "details"', 'action = "list"', 'EQUIPPED', 'MyDinos.cardRows(#pills, mutationId ~= nil)', 'rows.thumbH'):
        assert needle in panels, needle
    assert 'Badge.Height = 22' in read('src/client/MutationBadge.luau'), 'MyDinos.Card.chipH matches the mutation badge height'
    assert 'fromOffset(7, y)' not in panels, 'BD-507: no pill sits at a fixed spot over the thumbnail'
    assert 'Instance.new("ViewportFrame")' not in panels, 'previews come from DinosaurPreview (patient loading)'
    boot = read('src/client/Bootstrap.client.luau')
    assert 'DinoIndexPanels.supported()' in boot and 'equip:FireServer(speciesId,Http:GenerateGUID(false),variantKey)' in boot
    # Server: the optional variant key is validated twice (event handler shape, repository ownership).
    service = read('src/server/CollectionService.luau')
    assert 'invalid_variant' in service and 'profileRepository.equipSpecies(player, speciesId, variantKey)' in service
    repo = read('src/server/ProfileRepository.luau')
    assert repo.count('not_owned') >= 1 and 'profileValue.equippedVariantKey = variantKey' in repo
    assert 'EggTraits.selected(collection[equippedId], equippedKey)' in repo and 'local function equippedOf' in repo  # BD-606: the dino actually played (a secret species sits beside the fallback pair)
    workflow = read('.github/workflows/build-generated-place.yml')
    assert 'verify_inspect.py' in workflow, 'verify_inspect.py must run in CI'
    print('Wiring checks passed: hatch tap gating, camera hooks, server equip validation, workflow')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    check_wiring()
    run(args.runner, script(), 'inspect.luau')
