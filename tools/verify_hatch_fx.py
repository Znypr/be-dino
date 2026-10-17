"""BD-162 / BD-171 polish: offline audit of the layered hatch FX plan (src/shared/HatchFxPlan.luau) and the flipbook cell maths
(src/shared/EffectAssets.luau). Budgets per device, tier monotonicity (more layers / colours with rarity), calm limits, Reduce Motion
(one static glow), foreground keep-out zones, droplets stay clear of the paint chips, real-id switch for the Blender textures,
no invented asset ids. Drawing (client/HatchFx.luau, FxUi.luau) is Studio-only."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path, subs=None):
    text = (ROOT / path).read_text(encoding='utf-8')
    for a, b in (subs or {}).items():
        text = text.replace(a, b)
    return '(function()\n' + text + '\nend)()'


BODY = r'''
local L = P.Limits
local names = {"sparks", "motes", "puffs", "shocks", "fg", "drops"}
-- 1. Budgets: every tier and device is within its cap; tiers never shrink; devices never grow downward; floors hold.
for _, dev in {"phone", "tablet", "desktop"} do
    local prev
    for tier = 1, 6 do
        local c = P.counts(tier, dev, false)
        assert(P.total(c) <= P.Caps[dev], dev .. " tier " .. tier .. " over the sprite cap: " .. P.total(c))
        assert(c.bloom == 3 and c.colors == R.ColorCount[tier], "bloom discs fixed, colours follow the tier")
        for _, n in names do assert(c[n] >= 0 and c[n] == math.floor(c[n])) end
        if prev then
            for _, n in names do assert(c[n] >= prev[n], dev .. " " .. n .. " must not shrink with rarity at tier " .. tier) end
            assert(c.colors >= prev.colors and P.total(c) >= P.total(prev), "total grows with rarity")
        end
        prev = c
    end
end
for tier = 1, 6 do
    local ph, tb, dk = P.counts(tier, "phone", false), P.counts(tier, "tablet", false), P.counts(tier, "desktop", false)
    for _, n in names do assert(ph[n] <= tb[n] and tb[n] <= dk[n], n .. " phone <= tablet <= desktop at tier " .. tier) end
    assert(P.total(ph) <= P.total(tb) and P.total(tb) <= P.total(dk))
end
assert(P.counts(6, "desktop", false).sparks > P.counts(1, "desktop", false).sparks, "rarer eggs get more rim sparks")
assert(P.counts(6, "desktop", false).colors > P.counts(1, "desktop", false).colors, "rarer eggs get more colours")
assert(P.counts(1, "desktop", false).fg == 0 and P.counts(6, "desktop", false).fg >= 5, "foreground pass is for rarer eggs")
for tier = 1, 6 do assert(P.counts(tier, "phone", false).motes >= P.Floors.motes) end
-- 2. Reduce Motion: ONE static glow, nothing animated.
for _, dev in {"phone", "tablet", "desktop"} do
    for tier = 1, 6 do
        local c = P.counts(tier, dev, true)
        assert(c.bloom == 1 and P.total(c) == 1, "Reduce Motion is one static disc")
    end
end
-- 3. Palettes: colours are distinct and grow with the tier.
for _, primary in {{80, 214, 255}, {70, 205, 170}, {46, 206, 255}, {194, 86, 255}, {255, 210, 43}, {247, 57, 48}, {93, 237, 31}, {128, 142, 158}} do
    for tier = 1, 6 do
        local pal = P.palette(primary, tier)
        assert(#pal == R.ColorCount[tier])
        for i = 1, #pal do for j = i + 1, #pal do assert(R.distance(pal[i], pal[j]) > 20, "palette colours distinct for " .. primary[1] .. "," .. primary[2] .. " tier " .. tier) end end
    end
end
-- 4. Bloom grows through the build-up, never shrinks, and stays soft.
local prevScale = 0
for k = 0, 20 do
    local p = k / 20
    local sc = P.bloomScale(p, nil)
    assert(sc >= prevScale - 1e-9 and sc >= 0.3 and sc <= 1.0001, "bloom grows monotonically through the build-up")
    prevScale = sc
    for i = 1, 3 do
        local a = P.bloomAlpha(i, p, nil)
        assert(a >= 0 and a <= 0.4, "bloom discs stay translucent")
    end
end
for k = 0, 30 do
    local since = k / 10
    assert(P.bloomScale(1, since) <= 1.2 and P.bloomScale(1, since) >= 0.9)
    for i = 1, 3 do assert(P.bloomAlpha(i, 1, since) <= 0.4) end
end
-- 5. Rim sparks: calm orbit (spin limit), bounded opacity / size, depth in -1..1.
for tier = 1, 6 do
    local n = P.counts(tier, "desktop", false).sparks
    for i = 1, n do
        for k = 0, 40 do
            local dx, dy, depth, op, size = P.rimSpark(i, n, k * 0.25, tier, 1)
            assert(depth >= -1 and depth <= 1 and op >= 0 and op <= L.maxAlpha and size > 0 and size <= L.sparkSize, "spark bounds")
            assert(math.abs(dx) <= 150 and math.abs(dy) <= 100, "sparks stay near the rim")
        end
    end
    local x1, y1 = P.rimSpark(1, n, 10, tier, 1)
    local x2, y2 = P.rimSpark(1, n, 10.1, tier, 1)
    local a1, a2 = math.atan2((y1 + 6) / 0.62, x1), math.atan2((y2 + 6) / 0.62, x2)
    local d = math.abs(a2 - a1) if d > math.pi then d = 2 * math.pi - d end
    assert(d / 0.1 <= L.orbitSpin + 1e-3, "orbit spin within the calm limit")
end
-- 6. Burst: smoke puffs stay see-through and end; shock rings are bounded and end.
for i = 1, 5 do
    local peak = 0
    for k = 0, 60 do
        local dx, dy, size, op = P.puff(i, 5, k * 0.02)
        peak = math.max(peak, op)
        assert(op <= L.puffAlpha + 1e-9 and size >= 0 and size <= 260, "puff bounds")
    end
    assert(peak > 0.05, "puff is visible")
    assert(select(4, P.puff(i, 5, L.puffLife + 0.01)) == 0 and select(4, P.puff(i, 5, -0.1)) == 0)
end
for i = 1, 3 do
    for k = 0, 60 do
        local size, op = P.shock(i, k * 0.02)
        assert(op <= L.maxAlpha and size <= 460 and op >= 0)
    end
    assert(select(2, P.shock(i, 2)) == 0)
end
assert(select(2, P.shock(2, 0.05)) == 0, "second ring is staggered")
-- 7. Background motes: stay inside the panel, gentle opacity.
for tier = 1, 6 do
    for i = 1, P.counts(tier, "desktop", false).motes do
        for k = 0, 80 do
            local x, y, size, op = P.mote(i, k * 0.5, tier)
            assert(x >= 0 and x <= 824 and y >= -40 and y <= 440 and size <= L.moteSize and op <= L.maxAlpha)
        end
    end
end
-- 8. Foreground sparkle pass: ONLY side margins, never in a keep-out zone (dino, chips, tap hint, ribbons), gentle and small.
for i = 1, 6 do
    for k = 0, 400 do
        local x, y, size, op = P.fgSpark(i, 6, k * 0.37)
        assert(not P.inKeepOut(x, y, size), "foreground sparkle " .. i .. " at " .. x .. "," .. y .. " overlaps a keep-out zone")
        assert(x >= 0 and x <= 824 and y >= 0 and y <= 402)
        assert(size <= L.fgSize and op <= L.fgAlpha + 1e-9, "foreground stays small and gentle")
    end
end
assert(P.inKeepOut(412, 100) and P.inKeepOut(147, 160) and P.inKeepOut(677, 160) and P.inKeepOut(412, 292) and P.inKeepOut(412, 350), "keep-out zones cover dino, chips, hint")
-- BD-220 / BD-223 chips: one under each bucket (bucket hover x = egg x -/+ 265), none overlap, all inside the panel. The panel
-- scales uniformly, so no overlap here means no overlap at any phone size.
do
    local names = {"left", "right", "pattern", "condition"}
    for i, a in names do
        local ra = P.chipRect(a)
        assert(ra[1] >= 0 and ra[3] <= 824 and ra[2] >= 0 and ra[4] <= 402, a .. " chip inside the panel")
        assert(P.Chips[a][4] <= 50, a .. " chip is one line")
        for j = i + 1, #names do assert(not P.overlaps(ra, P.chipRect(names[j])), a .. " overlaps " .. names[j]) end
    end
    assert(P.Chips.left[1] == 412 - 265 and P.Chips.right[1] == 412 + 265, "colour chips sit right under their buckets")
    assert(P.Chips.left[2] > 100 and P.Chips.right[2] == P.Chips.left[2], "both colour chips below the buckets, same row")
    -- splash droplets (both systems) never land on a colour chip
    for _, side in {-1, 1} do
        for j = 1, 12 do
            for k = 0, 54 do
                local dx, dy = P.drop(j, 12, k * 0.01, side)
                for _, n in {"left", "right"} do
                    local rc = P.chipRect(n)
                    local x, y = 412 + side * 40 + dx, 100 + dy
                    assert(not (x >= rc[1] and x <= rc[3] and y >= rc[2] and y <= rc[4]), "droplet lands on the " .. n .. " chip")
                end
            end
        end
    end
end
-- 9. Paint droplets: low arcs, end, never reach the chips (y 255+) from the splash points (y 100), colours per side.
for _, side in {-1, 1} do
    for tier = 1, 6 do
        local n = P.counts(tier, "desktop", false).drops
        for j = 1, n do
            for k = 0, 54 do
                local s = k * 0.01
                local dx, dy, op, size = P.drop(j, n, s, side)
                assert(op >= 0 and op <= L.maxAlpha and size >= 3 and size <= L.dropSize, "drop bounds op " .. op .. " size " .. size)
                assert(dy <= L.maxFall + 1e-9 and 100 + dy < 255, "droplet stays clear of the pattern / condition chips")
                assert(math.abs(dx) <= 120, "droplet stays near the splash")
            end
            assert(select(3, P.drop(j, n, L.dropLife + 0.01, side)) == 0, "droplets end")
        end
    end
end
assert(P.counts(6, "desktop", false).drops > P.counts(1, "desktop", false).drops, "rarer reveals splash more droplets")
-- 10. Flipbook cells + real-id switch (EffectAssets): fallback shows no cell, a real id selects one of 16 cells of the sheet.
-- FX v3 (2026-10-16): smoke / sparkle / flame / swirl are real 1024 px uploads (256 px cells); crystalSheet still falls back.
-- 2026-10-17: crystalSheet and glowPlate are bound to owner uploads now; the fallback checks clear them and restore them.
local savedCrystal, savedPlate = A.Requested.crystalSheet.id, A.Requested.glowPlate.id
A.Requested.crystalSheet.id, A.Requested.glowPlate.id = "", ""
assert(A.cellRect("crystalSheet", 1) == nil, "no cell while the key still uses a built-in sprite")
assert(A.resolve("glowPlate") == A.Builtin.spark and not A.isReal("glowPlate"))
A.Requested.crystalSheet.id, A.Requested.glowPlate.id = savedCrystal, savedPlate
assert(A.cellRect("crystalSheet", 1) ~= nil or savedCrystal == "", "a bound crystalSheet selects a cell")
assert(A.isReal("smokeSheet") and A.isReal("sparkSheet") and A.isReal("starFour") and A.isReal("flameSheet") and A.isReal("swirl") and A.isReal("rays"))
local savedGlow, savedRing = A.Requested.glowPlate.id, A.Requested.ringShock.id
local fakeId = "rbxassetid://1234567"
A.Requested.glowPlate.id = fakeId A.Requested.ringShock.id = fakeId
assert(A.resolve("glowPlate") == fakeId and A.resolve("ringShock") == fakeId, "real ids are used automatically")
A.Requested.glowPlate.id, A.Requested.ringShock.id = savedGlow, savedRing
for _, key in {"smokeSheet", "sparkSheet", "starFour", "flameSheet", "swirl"} do
    local seen = {}
    for cell = 1, 32 do
        local x, y, size = A.cellRect(key, cell)
        assert(x and size == 256 and x >= 0 and y >= 0 and x + size <= 1024 and y + size <= 1024, key .. " cell inside the sheet")
        if cell <= 16 then assert(not seen[x .. "," .. y], "16 distinct cells") seen[x .. "," .. y] = true end
    end
end
assert(A.cellRect("glowPlate", 3) == nil and A.cellRect("rays", 3) == nil, "single images have no cells")
-- the fx3 uploads now carry alpha (2026-10-16 re-upload): UI and world use the real textures
for _, key in {"smokeSheet", "sparkSheet", "starFour", "flameSheet", "swirl", "rays"} do
    assert(A.HasAlpha[key] == true and not A.isAdditive(key) and A.isRealUi(key) and A.resolveUi(key) == A.resolve(key), key .. " uses the alpha upload")
end
-- clearing HasAlpha falls back: world additive, UI built-in sprite with no cell
A.HasAlpha.smokeSheet = nil
assert(A.isAdditive("smokeSheet") and not A.isRealUi("smokeSheet") and A.resolveUi("smokeSheet") == A.Builtin.smoke)
local probe = {} assert(A.setCell(probe, "smokeSheet", 3) == false and probe.ImageRectSize == nil, "no cell on a built-in UI sprite")
A.HasAlpha.smokeSheet = true
-- hatch puff (smoke-anime, OneShot) plays its cells in order across the puff life
local last = 0
for k = 0, 20 do local c = A.frameAt("smokeSheet", k / 20 * 0.999, 0, 3) assert(c >= last) last = c end
assert(last == 16)
print("HatchFxPlan checks passed")
'''


def script():
    s = 'local R = ' + module('src/shared/FxRecipes.luau') + '\n'
    s += 'local A = ' + module('src/shared/EffectAssets.luau') + '\n'
    s += 'local P = ' + module('src/shared/HatchFxPlan.luau', {'require(script.Parent.FxRecipes)': 'R'}) + '\n' + BODY
    return s


def scan():
    seq = (ROOT / 'src/client/HatchSequence.luau').read_text(encoding='utf-8')
    for needle in ['HatchFx.begin', 'HatchFx.update', 'HatchFx.style', 'HatchFx.splash', 'HatchFx.paintStyle', 'HatchFx.hide']:
        assert needle in seq, 'HatchSequence must call ' + needle
    fx = (ROOT / 'src/client/HatchFx.luau').read_text(encoding='utf-8')
    for needle in ['HatchFxPlan', 'EffectAssets', 'glowPlate', 'ringShock', 'smokeSheet', 'sparkSheet', 'starFour']:
        assert needle in fx, 'HatchFx must use ' + needle
    ui = (ROOT / 'src/shared/FxUi.luau').read_text(encoding='utf-8')
    assert 'Assets.isReal("glowPlate")' in ui and 'Assets.setCell' in ui and 'MAX_ACTIVE = 8' in ui, 'FxUi must switch to real ids and cap previews at 8'
    assert 'FxUi.mount(view, "mutation"' in (ROOT / 'src/client/PreviewTraits.luau').read_text(encoding='utf-8'), 'hero previews mount the mutation FX'
    assert 'FxUi.mount(stage, "mutation"' in (ROOT / 'src/client/EggsScreen.luau').read_text(encoding='utf-8'), 'egg card mounts a mutation FX'
    for path in ['src/shared/HatchFxPlan.luau', 'src/client/HatchFx.luau']:
        assert not re.search(r'rbxassetid://\d+', (ROOT / path).read_text(encoding='utf-8')), path + ' must not contain asset ids'
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    assert 'HatchFx' not in boot and 'FxUi' not in boot, 'Bootstrap is at the 200 local-register limit: no new locals for this feature'
    print('Source scan passed: hatch FX wired, mutation previews mounted, no invented asset ids, Bootstrap untouched')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-scan', action='store_true')
    args = parser.parse_args()
    if not args.no_scan:
        scan()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'hatchfx.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
