#!/usr/bin/env python3
"""BD-1069..1073 (docs/193): hatch screen polish, proved offline with the pinned Luau runtime. Owner complaints of 2026-10-18 reproduced by Studio
QA round 4 (docs/192 part C): the paint bucket looked cheap and the colour chip dot was not the colour named, chips matched nothing else in the game,
the egg changed size when the second colour arrived, the Rainbow egg looked pale, the reveal card layout was cramped.

1. PURE: HatchEggSize (the flat and the 3D egg are the same size, the zoomed 3D egg fits its box), ChipStyle spec (rounded rectangle, 3 px outline,
   14 px text, 28 / 44 px high), HatchTimeline (colour reveal carries the exact EggColors rgb for every colour, the stop reason), HatchFxPlan (the Rainbow
   budget fits every device cap, calm limits, the reveal card layout keeps clear of the ribbons, chips and dinosaur).
2. SMOKE: the real HatchSequence runs in the close-path mock (tools/close_paths_smoke.luau, section 6b): swatch and bucket paint are exactly the palette
   rgb (not the blended tint), every chip is a px-corner rounded rectangle with a 3 px outline, the counter lives in the header left of X, the dinosaur
   view starts at the card top and ends at the name, the stop tag names a Rainbow egg.
3. MUTANTS: the smoke must FAIL when each old defect is put back.
4. SOURCE: HatchSequence builds every chip through the shared ChipStyle helper (no private full-round pills), the 3D egg is sized by HatchEggSize,
   the paint bucket is still listed as a PLACEHOLDER, Bootstrap is untouched by this change.
Not Studio evidence: nothing here shows how it looks. Usage: python tools/verify_hatch_polish.py --runner luau.exe
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_close_paths as cp  # noqa: E402


def module(path, subs=None):
    text = (ROOT / path).read_text(encoding='utf-8')
    for a, b in (subs or {}).items():
        assert a in text, 'missing %s in %s' % (a, path)
        text = text.replace(a, b)
    return '(function()\n' + text + '\nend)()'


BODY = r'''
local function near(a, b, e) return math.abs(a - b) <= (e or 1e-6) end
-- 1. BD-1071: the egg keeps one size. Flat picture 188.7 px (210 of 512 px of the art, on the 460 px stage), the 3D egg zoomed to match.
local flat = Size.flat()
assert(near(flat.w, 188.7, .1) and near(flat.h, 248, .5), "the flat egg picture is about 189 x 248 px (the Studio measure was 188)")
local same, spread = Size.sameSize()
assert(same, "the flat and the 3D egg differ by " .. spread .. ": one egg size in every state")
assert(Size.native().w >= 183 and Size.native().w <= 194, "the 3D egg is about 188 px wide, not 114")
assert(Size.fitsBox(), "the zoomed egg fits its 268 px box (no cropped crack)")
local dx, dy = Size.nativeOffset()
assert(dx == 0 and dy == -10, "the 3D egg sits on the flat egg's centre (10 px above the middle of the box): " .. dx .. "," .. dy)
for _, w in Size.states() do assert(math.abs(w - flat.w) / flat.w <= Size.Tolerance, "every state within the tolerance") end
-- a change to the zoom or the box must trip the check
local keep = Size.NativeZoom
Size.NativeZoom = 1.0
assert(not Size.sameSize(), "the old 1.0 zoom (114 px next to 188 px) is caught")
Size.NativeZoom = keep

-- 2. BD-1070: the chunky tag spec.
local S = Chip.Spec
assert(S.outline == 3 and S.textStroke == 2 and S.minText >= 14 and S.minHeight >= 28 and S.tapHeight >= 44, "chunky tag numbers (docs/192 s4, docs/72)")
assert(S.radius > 0 and S.radius <= 12 and S.swatchRadius > 0 and S.swatchRadius < S.radius, "a rounded rectangle corner in px, never a pill")
assert(Chip.heightOk(28) and not Chip.heightOk(27) and Chip.heightOk(44, true) and not Chip.heightOk(43, true))
for h = 28, 60 do assert(Chip.textSize(h) >= 14, "chip text never under 14 px at height " .. h) end

-- 3. BD-1069: the colour reveal carries each colour's own rgb (the chip dot and the bucket use exactly it).
local colors = Prog.EggColors
local genesOf = function(a, b) return {primaryColorId = a, secondaryColorId = b, blend = 50} end
for _, row in colors do
    local r = T.colorReveal(colors, genesOf(row.id, "white"))
    local rgb = T.revealRgb(r)
    assert(rgb and rgb[1] == row.rgb[1] and rgb[2] == row.rgb[2] and rgb[3] == row.rgb[3], row.id .. " reveal carries its own EggColors rgb")
    local second = T.revealRgb(T.colorReveal(colors, genesOf("white", row.id), "secondary"))
    assert(second and second[1] == row.rgb[1] and second[2] == row.rgb[2] and second[3] == row.rgb[3], row.id .. " secondary reveal carries its own rgb")
end
-- the blended tint is NOT the colour: Blue over Cream at 50% differs from both (this is what the swatch used to show)
local cream, blue = T.revealRgb(T.colorReveal(colors, genesOf("white", "blue"))), T.revealRgb(T.colorReveal(colors, genesOf("blue", "white")))
assert(cream[1] ~= blue[1] and cream[3] ~= blue[3], "two different colours have two different swatches")
assert(T.revealRgb(nil) == nil and T.revealRgb({}) == nil and T.revealRgb({rgb = {1, 2}}) == nil, "a reveal without rgb gives nil (the caller keeps its fallback)")

-- 4. BD-1073: why Skip stops.
assert(T.stopReason({conditionId = "rainbow"}) == "Rainbow egg!" and T.stopReason({conditionId = "astra"}) == "Astra egg!")
assert(T.stopReason({shiny = true}) == "Shiny!" and T.stopReason({big = true}) == "BIG!" and T.stopReason({mutationName = "Frost"}) == "Frost!")
assert(T.stopReason({}) == nil and T.stopReason({conditionId = "dirty"}) == nil and T.stopReason(nil) == nil and T.stopReason({conditionId = "rainbow", failed = true}) == nil, "ordinary and failed eggs give no reason")
assert(#T.StopLine <= 20, "the stop line is short")

-- 5. BD-1072: the Rainbow egg stays inside every device budget, calm, and has a Reduce Motion form.
local R = P.Rainbow
for _, dev in {"phone", "tablet", "desktop"} do
    for tier = 1, 6 do
        local c = P.counts(tier, dev, false, true)
        assert(c.rainbow == R.bands[dev] and c.rainbow >= 4, dev .. " tier " .. tier .. " has its rainbow rings")
        assert(P.total(c) <= P.Caps[dev], dev .. " tier " .. tier .. " rainbow egg within the sprite cap: " .. P.total(c))
        assert(P.counts(tier, dev, false, false).rainbow == 0 and P.counts(tier, dev, false).rainbow == 0, "an ordinary egg has no rainbow rings")
        local still = P.counts(tier, dev, true, true)
        assert(still.rainbow == 0 and P.total(still) == 1, "Reduce Motion: one static glow, no rings")
    end
end
assert(#R.hues == 6, "six hues: red, orange, yellow, green, blue, violet")
for n = 1, 6 do
    assert(P.rainbowHue(1, n)[1] > 200 and P.rainbowHue(1, n)[3] < 150, "the outermost ring is red")
    if n > 1 then assert(P.rainbowHue(n, n)[3] > 200, "the innermost ring is violet") end
end
local seen = {}
for i = 1, R.bands.desktop do
    local hue = P.rainbowHue(i, R.bands.desktop)
    local key = hue[1] .. "," .. hue[2] .. "," .. hue[3]
    assert(not seen[key], "six distinct hues") seen[key] = true
end
local lastD = 1e9
for i = 1, R.bands.desktop do
    for _, p in {0, .5, 1} do
        for _, since in {false, 0, 1, 3} do
            local d, o = P.rainbowBand(i, R.bands.desktop, 1.7, p, if since == false then nil else since)
            assert(o >= 0 and o <= P.Limits.maxAlpha + 1e-9 and d > 0, "calm: never above maxAlpha")
        end
    end
    local d = P.rainbowBand(i, R.bands.desktop, 0, 1, nil)
    assert(d < lastD, "rings get smaller inside") lastD = d
end
assert(P.rainbowBand(1, 6, 0, 0, nil) < P.rainbowBand(1, 6, 0, 1, nil), "the rainbow grows through the build-up")
local _, early = P.rainbowBand(3, 6, 0, 0, nil)
local _, late = P.rainbowBand(3, 6, 0, 1, nil)
assert(early == 0 and late > .3, "it fades in with the build-up and is clearly readable (not pale) at the end")

-- 6. BD-1073: the reveal card layout.
local dino, tag = P.cardRect("dino"), P.cardRect("stopTag")
assert(dino[2] >= 0, "the dinosaur view starts at the top of the card (it used to start 12 px above)")
assert(dino[4] <= P.Card.nameTop, "the dinosaur view ends where the name starts")
assert(P.Card.baseZoom <= 1.2, "the zoom no longer cuts the head")
assert(tag[1] >= 0 and tag[3] <= 824 and tag[2] >= 0 and tag[4] <= 402 and P.Card.stopTag.h >= 44, "the stop tag is on the card and tall enough to read two lines")
assert(not P.overlaps(tag, {212, 0, 612, 262}) or tag[3] <= 216, "the stop tag stays in the left margin, out of the dinosaur")
assert(not P.overlaps(tag, {11, 26, 221, 132}), "the stop tag is under the Shiny / mutation ribbons")
assert(not P.overlaps(tag, {649, 36, 799, 130}), "and far from the BIG / NEW ribbons")
assert(P.inKeepOut(116, 160), "the foreground sparkles keep out of the stop tag")
print("Hatch polish pure checks passed")
'''


def pure_script():
    return ('local RS = ' + module('src/shared/RevealSkip.luau') + '\n'
            'local V2 = ' + module('src/shared/HatchV2Plan.luau') + '\n'
            'local script = {Parent = {RevealSkip = RS, HatchV2Plan = V2}}\nlocal function require(x) return x end\n'
            'local T = ' + module('src/shared/HatchTimeline.luau') + '\n'
            'local R0 = ' + module('src/shared/FxRecipes.luau') + '\n'
            'local P = ' + module('src/shared/HatchFxPlan.luau', {'require(script.Parent.FxRecipes)': 'R0'}) + '\n'
            'local Size = ' + module('src/shared/HatchEggSize.luau') + '\n'
            'local Chip = ' + module('src/shared/ChipStyle.luau', {'local Theme = require(script.Parent.UITheme)': 'local Theme = {Colors = {}}',
                                                                       'Enum.Font.FredokaOne': '"FredokaOne"'}) + '\n'
            'local Prog = ' + module('src/shared/ProgressionConfig.luau') + '\n' + BODY)


def run(runner, source, name):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        path.write_text(source, encoding='utf-8')
        return subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


# Each old defect put back must make the smoke fail.
MUTANTS = {
    'chip dot and bucket take the blended shell tint again (BD-1069)': {
        'HatchSequence': [('kit.chipSwatches[i].BackgroundColor3 = if rgb then Chip.color(rgb) else paintColors[i]', 'kit.chipSwatches[i].BackgroundColor3 = a.paintColors[i]')],
    },
    'bucket pours the blended tint, not the colour (BD-1069)': {
        'HatchSequence': [('if exact and not v2 then paintColors[i] = Chip.color(exact) end', '')],
    },
    'chips are full-round pills again (BD-1070)': {
        'ChipStyle': [('corner.CornerRadius = Chip.radius()', 'corner.CornerRadius = UDim.new(1, 0)')],
    },
    'chip outline is thin again (BD-1070)': {
        'ChipStyle': [('stroke.Thickness, stroke.Color, stroke.ApplyStrokeMode = Chip.Spec.outline,', 'stroke.Thickness, stroke.Color, stroke.ApplyStrokeMode = 1,')],
    },
    'the Egg N of M counter lies over the dinosaur again (BD-1073)': {
        'HatchSequence': [('counter.ZIndex, counter.Parent = a.header.ZIndex + 3, a.header', 'counter.ZIndex, counter.Parent = a.body.ZIndex + 6, a.body')],
    },
    'the dinosaur view starts above the card again (BD-1073)': {
        'HatchSequence': [('a.dino.Size = UDim2.fromOffset(card.w, card.h)', 'a.dino.Size = UDim2.fromOffset(card.w, 284)')],
    },
    'the zoom is back to 1.4 (BD-1073)': {
        'HatchSequence': [('baseZoom = FxPlan.Card.baseZoom,', 'baseZoom = 1.4,')],
    },
    'the viewport keeps its own BIG label (BD-1073)': {
        'HatchSequence': [('if traitBadge and traitBadge:IsA("GuiObject") then traitBadge.Visible = false end', '')],
    },
    'Skip stops without saying why (BD-1073)': {
        'HatchSequence': [('            if why then\n                local tagRect', '            if false then\n                local tagRect')],
    },
}


def check_mutants(runner):
    for name, replacements in MUTANTS.items():
        result = run(runner, cp.build_script(replacements), 'close_paths_smoke.luau')
        assert result.returncode != 0, 'MUTANT SURVIVED (the smoke did not notice): ' + name
        print('  mutant caught: ' + name)


def check_source():
    seq = read('src/client/HatchSequence.luau')
    assert "require(Shared.ChipStyle)" in seq, 'HatchSequence uses the shared chip style'
    # every chip is built through the helper: no private full-round corner on a chip, pill, badge or swatch
    for var in ('chip', 'pill', 'badge', 'swatch', 'tag'):
        assert not re.search(r'\bcorner\(%s\)' % var, seq), 'a chip (%s) must not get the default full-round corner' % var
    assert 'Chip.new(' in seq and 'Chip.swatch(' in seq and 'Chip.apply(pill' in seq, 'colour chips, tier tags, the swatch and the rarity line use ChipStyle'
    assert 'UDim.new(1, 0)' in seq and seq.count('UDim.new(1, 0)') == 1, 'the only full-round radius left in HatchSequence is the effects helper (rings, splashes, drops)'
    assert 'PLACEHOLDER' in seq[seq.index('Paint-bucket kit'):][:600], 'the paint bucket stays marked PLACEHOLDER until the icon is bound'
    assert 'Timeline.revealRgb(reveal)' in seq and 'bucketPaints' in seq, 'swatch and bucket use the exact palette rgb'
    chipstyle = read('src/shared/ChipStyle.luau')
    assert 'UDim.new(0, Chip.Spec.radius)' in chipstyle and 'UDim.new(1' not in chipstyle and 'UDim.new(.5' not in chipstyle, 'ChipStyle never makes a full-round corner'
    pres = read('src/shared/HatchPresentation.luau')
    assert 'EggSize.NativeZoom' in pres and 'EggSize.nativeOffset()' in pres and 'UDim2.fromOffset(268,268)' not in pres, 'the 3D egg is sized by HatchEggSize, not a private 268'
    fx = read('src/client/HatchFx.luau')
    assert 'ringSoft' in fx and 'Plan.rainbowBand' in fx and 'function M.rainbow' in fx, 'the Rainbow rings use the existing ringSoft texture'
    assert not re.search(r'rbxassetid://\d+', fx + read('src/shared/ChipStyle.luau') + read('src/shared/HatchEggSize.luau')), 'no invented asset ids'
    assert 'ChipStyle' not in read('src/client/Bootstrap.client.luau'), 'Bootstrap is at its byte ratchet: this change does not touch it'
    assert "'ChipStyle'" in read('tools/verify_close_paths.py'), 'the close-path smoke loads ChipStyle'
    print('Source checks passed: ChipStyle everywhere on the hatch screen, no private pills, bucket still a PLACEHOLDER, one egg size')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    check_source()
    result = run(args.runner, pure_script(), 'polish.luau')
    print(result.stdout, end='')
    if result.returncode or 'passed' not in result.stdout:
        print(result.stderr)
        sys.exit(result.returncode or 1)
    smoke = run(args.runner, cp.build_script(), 'close_paths_smoke.luau')
    assert smoke.returncode == 0 and 'polish' not in smoke.stdout.replace('Close paths smoke passed', ''), smoke.stdout + smoke.stderr
    if not args.no_mutants:
        check_mutants(args.runner)
    print('Hatch polish passed: pure numbers, the real hatch screen in the mock, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS)))


if __name__ == '__main__':
    main()
