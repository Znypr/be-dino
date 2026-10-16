"""docs/93: offline audit of src/shared/FxRecipes.luau and EffectAssets.luau (anime FX framework).
Budgets per device, tier monotonicity (more layers and colours with rarity), calm timing limits, Reduce Motion fallback,
phone rate = half, every aura/trail/mutation resolves, texture keys resolve, no invented asset ids."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
local TIME = R.Timing
local function layerById(res, id) for _, l in res.layers do if l.id == id then return l end end return nil end
local synthetic = {id = "x", color = {80, 214, 255}, accent = {195, 249, 255}, width = .6, lifetime = .9, particles = 6, rarity = "Common"}
-- 1. Tier monotonicity on a neutral item, every kind and device.
for _, kind in {"aura", "trail"} do
    for _, dev in R.DeviceOrder do
        local lastLayers, lastColors, lastAlive, lastBeams = 0, 0, 0, 0
        for t, name in R.Tiers do
            local item = {} for k, v in synthetic do item[k] = v end
            item.rarity = name
            local res = R.resolve(kind, item, {device = dev})
            assert(#res.layers >= lastLayers, kind .. " " .. dev .. " layers must not shrink with rarity at " .. name)
            assert(res.colorCount >= lastColors, "colour count must not shrink at " .. name)
            assert(res.cost.alive >= lastAlive - 1e-6 and res.cost.beams >= lastBeams, "cost must not shrink at " .. name)
            assert(#res.layers >= 2, "every tier has at least 2 layers on " .. dev)
            lastLayers, lastColors, lastAlive, lastBeams = #res.layers, res.colorCount, res.cost.alive, res.cost.beams
            for i = 1, #res.palette do for j = i + 1, #res.palette do assert(R.distance(res.palette[i], res.palette[j]) > 24, "palette colours distinct " .. name) end end
            assert(#res.palette == R.ColorCount[t])
        end
        if dev == "desktop" then assert(lastLayers >= 6, kind .. " Mythic shows 6+ layers on desktop") end
    end
end
for t = 2, 6 do assert(R.LayerCount[t] > R.LayerCount[t - 1], "LayerCount strictly grows") assert(R.ColorCount[t] >= R.ColorCount[t - 1], "ColorCount grows") end
assert(R.ColorCount[6] > R.ColorCount[1] and R.ColorCount[6] == 6)
-- 2. Every real aura / trail / mutation resolves within budget on every device; calm limits hold.
local function calm(res, label)
    for _, l in res.layers do
        local w = label .. "." .. l.id
        if l.life then assert(l.life <= TIME.maxLife, w .. " life") end
        if l.speed then assert(l.speed <= TIME.maxSpeed, w .. " speed") end
        if l.spin and (l.kind == "ring" or l.kind == "spiral") then assert(math.abs(l.spin) <= TIME.ringSpinMax, w .. " orbit spin") end
        if l.kind == "ring" or l.kind == "spiral" then assert(l.radius >= TIME.minRingRadius, w .. " stays outside the body") end
        if l.kind == "emitter" or l.kind == "burst" then
            assert(l.size <= TIME.maxParticleSize + 1e-6, w .. " size " .. l.size)
            if l.tex == "smokeSheet" then assert(l.alpha <= TIME.maxMistAlpha, w .. " smoke stays see-through") else assert(l.alpha <= TIME.maxSparkAlpha, w .. " alpha") end
        end
        assert(#l.color >= 1 and #l.color == #l.grad, w .. " colours")
        for _, c in l.color do for i = 1, 3 do assert(c[i] >= 0 and c[i] <= 255.0001, w .. " rgb range") end end
    end
end
local count = 0
for _, dev in R.DeviceOrder do
    local budget = R.Devices[dev]
    for _, a in Config.Auras do
        local res = R.resolve("aura", a, {device = dev}) count += 1
        assert(res.tierName == a.rarity) assert(#res.layers >= 2)
        for k, v in res.cost do if budget[k] then assert(v <= budget[k] + 1e-6, a.id .. " " .. dev .. " " .. k .. " " .. v .. ">" .. budget[k]) end end
        calm(res, "aura." .. a.id .. "." .. dev)
    end
    for _, tr in Config.Trails do
        local res = R.resolve("trail", tr, {device = dev}) count += 1
        assert(#res.layers >= 2, tr.id .. " " .. dev .. " has at least ribbon + one more layer")
        assert(layerById(res, "ribbon"), tr.id .. " always keeps its main ribbon")
        for k, v in res.cost do if budget[k] then assert(v <= budget[k] + 1e-6, tr.id .. " " .. dev .. " " .. k .. " " .. v .. ">" .. budget[k]) end end
        calm(res, "trail." .. tr.id .. "." .. dev)
    end
    for _, id in Look.Order do
        local e = Look.get(id)
        local res = R.resolve("mutation", e, {device = dev}) count += 1
        assert(#res.layers >= 2 and layerById(res, "glow"))
        for k, v in res.cost do if budget[k] then assert(v <= budget[k] + 1e-6, id .. " " .. dev .. " " .. k) end end
        calm(res, "mut." .. id .. "." .. dev)
        local lite = R.resolve("mutation", e, {device = dev, detail = "lite"})
        assert(#lite.layers <= R.MutationLiteLayers and layerById(lite, "ring") and layerById(lite, "motif") and lite.cost.alive <= res.cost.alive + 1e-6, "lite never costs more")
    end
end
-- 3. Rarity ordering across the real catalog: a higher-tier trail never has fewer layers than any lower-tier one on desktop.
local seen = {}
for _, tr in Config.Trails do
    local res = R.resolve("trail", tr, {device = "desktop"})
    for tier, n in seen do if tier < res.tier then assert(#res.layers >= n, tr.id .. " layers >= tier " .. tier) end end
    seen[res.tier] = math.max(seen[res.tier] or 0, #res.layers)
end
-- 4. Phone rate is half of desktop for the same layer.
for _, tr in Config.Trails do
    local d, p = R.resolve("trail", tr, {device = "desktop"}), R.resolve("trail", tr, {device = "phone"})
    for _, pl in p.layers do
        local dl = layerById(d, pl.id)
        if dl and pl.rate then assert(math.abs(pl.rate - dl.rate * 0.5) < 1e-6, tr.id .. "." .. pl.id .. " phone rate is half") end
    end
    assert(#p.layers <= #d.layers)
end
assert(R.Devices.phone.rateScale == 0.5)
for i = 2, 3 do local a, b = R.Devices[R.DeviceOrder[i - 1]], R.Devices[R.DeviceOrder[i]] for _, k in {"emitters", "beams", "trails", "alive", "burst"} do assert(b[k] >= a[k], k .. " budget grows with device") end end
-- 5. Reduce Motion: no emitters, no beams, no bursts; one soft light (aura/mutation) or one short ribbon (trail).
for _, a in Config.Auras do local r = R.resolve("aura", a, {reduce = true}) assert(r.cost.emitters == 0 and r.cost.beams == 0 and r.cost.burst == 0 and r.cost.trails == 0 and r.cost.lights == 1 and r.reduced) end
for _, id in Look.Order do local r = R.resolve("mutation", Look.get(id), {reduce = true}) assert(r.cost.emitters == 0 and r.cost.burst == 0 and r.cost.lights == 1 and r.cost.beams == 3 and r.layers[2].id == "ring" and r.layers[2].spin == 0, "Reduce Motion: still glow + a STILL ground ring (BD-353)") end
for _, tr in Config.Trails do local r = R.resolve("trail", tr, {reduce = true}) assert(r.cost.emitters == 0 and r.cost.beams == 0 and r.cost.trails == 1 and r.layers[1].life <= 0.5) end
-- 6. Curves and maths.
for name, curve in R.Curves do
    assert(curve[1][1] == 0 and curve[#curve][1] == 1, name)
    for i = 2, #curve do assert(curve[i][1] > curve[i - 1][1], name .. " ordered") end
end
assert(R.sample(R.Curves.sizePop, 0) == 0 and R.sample(R.Curves.sizePop, 1) == 0 and math.abs(R.sample(R.Curves.sizePop, 0.2) - 1) < 1e-9)
assert(R.sample(R.Curves.fadeInOut, 0.18) < R.sample(R.Curves.fadeInOut, 0) and R.sample(R.Curves.fadeInOut, 1) == 1)
assert(R.easeOutCubic(0) == 0 and R.easeOutCubic(1) == 1 and R.easeInOutSine(0.5) > 0.49 and R.easeInOutSine(0.5) < 0.51)
assert(R.pulse(0) >= 0 and R.pulse(1.7) <= 1 and TIME.pulseHz <= 0.8)
assert(R.deviceClass(true, false, 400) == "phone" and R.deviceClass(true, false, 820) == "tablet" and R.deviceClass(false, true, 1080) == "desktop" and R.deviceClass(true, true, 500) == "desktop")
-- 7. Textures: every semantic key used by a template resolves, nothing invented.
for kind, list in R.Templates do
    for _, l in list do
        if l.tex then local s = Assets.resolve(l.tex) assert(type(s) == "string" and #s > 10, kind .. "." .. l.id .. " texture " .. l.tex) end
    end
end
for _, motif in R.Motifs do local s = Assets.resolve(motif.tex) assert(#s > 10) end
for id in Look.Entries do assert(R.Motifs[id], id .. " has a motif") end
for key, req in Assets.Requested do
    assert(req.id == "" or Assets.isValid(req.id), key .. " id must be empty or a real upload")
    assert(Assets.Builtin[req.fallback], key .. " has a built-in fallback")
end
for key, id in Assets.Uploaded do assert(Assets.isValid(id), key) end
assert(not Assets.isValid("rbxassetid://") and not Assets.isValid("rbxassetid://abc") and Assets.isValid("rbxassetid://123"))
assert(Assets.resolve("nothing") == Assets.Builtin.spark and Assets.resolve("glowPlate") == Assets.Builtin.spark)
-- 8. FX v3: flipbook modes and the aura tier rules (all: smoke; Rare+: sparkles; Epic+: flame + rays; Legendary+: swirl at the feet).
assert(Assets.mode("smokeSheet") == "OneShot" and Assets.mode("sparkSheet") == "OneShot" and Assets.mode("flameSheet") == "Random" and Assets.mode("swirl") == "Loop")
assert(Assets.isSheet("smokeSheet") and Assets.isSheet("swirl") and not Assets.isSheet("rays") and Assets.isReal("rays"))
assert(Assets.frameAt("smokeSheet", 0, 0, 5) == 1 and Assets.frameAt("smokeSheet", 0.999, 0, 5) == 16 and Assets.frameAt("flameSheet", 0.5, 1, 7) == 7)
assert(Assets.frameAt("swirl", 0, 1.0, 0) == (Assets.LoopFps % 16) + 1)
for t, name in R.Tiers do
    local item = {} for k, v in synthetic do item[k] = v end
    item.rarity = name
    local res = R.resolve("aura", item, {device = "desktop"})
    assert(layerById(res, "mist"), name .. " aura has smoke")
    assert((layerById(res, "motes") ~= nil) == (t >= 3), name .. " sparkles from Rare")
    assert((layerById(res, "flame") ~= nil) == (t >= 4) and (layerById(res, "rays") ~= nil) == (t >= 4), name .. " flame + rays from Epic")
    assert((layerById(res, "swirl") ~= nil) == (t >= 5), name .. " swirl from Legendary")
    local rays = layerById(res, "rays")
    if rays then assert(rays.hz <= TIME.pulseHz and rays.alpha <= TIME.maxMistAlpha, "rays pulse slowly and stay soft") end
end
-- 7. BD-353 stacked budget by particle count: a mutated dino (mutation full + aura lite + trail lite, the worst case with all three
-- equipped) never exceeds the device's 45/30/18 alive particles; 12 such dinos (1 full + 11 lite mutation looks) stay inside 12 x budget.
do
    local aura, trail = Config.Auras[#Config.Auras], Config.Trails[#Config.Trails]
    for _, dev in R.DeviceOrder do
        local cap = R.Devices[dev].alive
        for _, id in Look.Order do
            local e = Look.get(id)
            local full = R.resolve("mutation", e, {device = dev})
            local lite = R.resolve("mutation", e, {device = dev, detail = "lite"})
            local stack = full.cost.alive + R.resolve("aura", aura, {device = dev, detail = "lite"}).cost.alive + R.resolve("trail", trail, {device = dev, detail = "lite"}).cost.alive
            assert(stack <= cap + 1e-6, id .. " " .. dev .. " stacked alive " .. stack .. " > " .. cap)
            local liteStack = lite.cost.alive + R.resolve("aura", aura, {device = dev, detail = "lite"}).cost.alive + R.resolve("trail", trail, {device = dev, detail = "lite"}).cost.alive
            assert(liteStack <= cap + 1e-6, id .. " " .. dev .. " lite stack alive " .. liteStack)
            local twelve = stack + 11 * liteStack
            assert(twelve <= 12 * cap + 1e-6, id .. " " .. dev .. " 12 dinos alive " .. twelve)
            local ring = full.layers[2]
            assert(ring.id == "ring" and ring.width >= 0.2 and ring.alpha >= 0.7 and ring.radius >= 2, "ground ring is wide and bright enough")
            if dev == "desktop" then print(string.format("%-9s desktop: mutation %4.1f alive, stack %4.1f/%d, 12 dinos %5.1f/%d", id, full.cost.alive, stack, cap, twelve, 12 * cap)) end
        end
    end
end
-- 8. every resolved layer (all kinds, tiers, devices, detail levels, Reduce Motion) carries a non-empty colour table (FxRig.colorSeq nil bug)
do
    local function check(res, label)
        for _, l in res.layers do
            assert(type(l.color) == "table" and #l.color >= 1 and #l.color == #l.grad, label .. "." .. l.id .. " has colours")
            for _, c in l.color do assert(type(c) == "table" and #c == 3, label .. "." .. l.id .. " colour triple") end
        end
    end
    for _, dev in R.DeviceOrder do
        for _, reduce in {false, true} do
            for _, detail in {"full", "lite"} do
                local o = {device = dev, reduce = reduce, detail = detail}
                for t, name in R.Tiers do
                    for _, kind in {"aura", "trail"} do
                        local item = {id = "x", rarity = name, color = {200, 120, 80}, accent = {250, 220, 120}, width = 0.5, lifetime = 0.7, particles = 3}
                        check(R.resolve(kind, item, o), kind .. name)
                    end
                end
                for _, a in Config.Auras do check(R.resolve("aura", a, o), a.id) end
                for _, tr in Config.Trails do check(R.resolve("trail", tr, o), tr.id) end
                for _, id in Look.Order do check(R.resolve("mutation", Look.get(id), o), id) end
            end
        end
    end
end
print(string.format("FxRecipes passed: %d resolutions (auras %d, trails %d, mutations %d) x 3 devices, tiers monotonic, phone rate x0.5, Reduce Motion light/ribbon only",
    count, #Config.Auras, #Config.Trails, #Look.Order))
'''


def script():
    s = 'local Config = ' + module('src/shared/ProgressionConfig.luau') + '\n'
    s += 'local Look = ' + module('src/shared/MutationLook.luau') + '\n'
    s += 'local Assets = ' + module('src/shared/EffectAssets.luau') + '\n'
    s += 'local R = ' + module('src/shared/FxRecipes.luau') + '\n' + BODY
    return s


def scan():
    for path, needles in {
        'src/client/CosmeticVisuals.client.luau': ['FxRig'],
        'src/client/FxRig.luau': ['FxRecipes', 'EffectAssets'],
        'src/shared/FxUi.luau': ['FxRecipes'],
        'src/shared/UITheme.luau': ['FxUi'],
    }.items():
        text = (ROOT / path).read_text(encoding='utf-8')
        for n in needles:
            assert n in text, path + ' must use ' + n
    for path in ['src/shared/FxRecipes.luau', 'src/shared/FxUi.luau', 'src/client/FxRig.luau']:
        assert not re.search(r'rbxassetid://\d+', (ROOT / path).read_text(encoding='utf-8')), path + ' must not contain asset ids'
    ids = re.findall(r'rbxassetid://(\d+)', (ROOT / 'src/shared/EffectAssets.luau').read_text(encoding='utf-8'))
    # Real uploads only: the BD-155 soft mist plus the five FX v3 owner uploads (docs/77 fx3_* rows, 2026-10-16).
    real = {'105629313112163', '109810080362045', '105817278245256', '71657118485647', '84584423423015', '99778248779183'}
    assert set(ids) == real, 'EffectAssets may only contain registered real uploads: ' + str(ids)
    registry = (ROOT / 'docs/77-asset-registry.md').read_text(encoding='utf-8')
    for i in real - {'105629313112163'}:
        assert 'rbxassetid://' + i in registry, i + ' must be in the asset registry'
    # Bootstrap is at Luau's 200 local-register limit: it must not gain top-level locals for this feature.
    assert 'FxRig' not in (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    print('Source scan passed: world dino and shop previews use the FX framework, no invented asset ids')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-scan', action='store_true')
    args = parser.parse_args()
    if not args.no_scan:
        scan()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'fx.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
