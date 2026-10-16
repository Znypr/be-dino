"""BD-397 (docs/114): execute the pure v2 hatch logic with the pinned Luau runtime: the beat sheet (timings sum, each bucket
window, cracks keep their time), bucket / stream / crown / drip / squash / gloss curves (bounded, calm, settle), deterministic
splats from the egg seed, the paint-reveal time field (coat 1 coverage monotonic to 100 % inside its span, drips ahead of the
flood), the composite (accent paint only on pattern texels, base coat everywhere, cream before any impact, bytes deterministic),
the per-device budget (bake size, image bytes, sprite caps), the v2 HatchTimeline state (pending hold, fast-forward, Reduced
Motion unchanged) and the source wiring (flag off, loader guarded, fallback to v1, Bootstrap locals untouched).
Drawing (ViewportFrame, EditableImage writes) is Studio-only: docs/114 and docs/evidence/2026-10-16-hatch-v2/.
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
local function near(a, b, e) return math.abs(a - b) <= (e or 1e-6) end

-- Beat sheet: left bucket, then right bucket, pattern chip, condition, then at least CracksMin of rattle before the burst.
local P = Plan.paintPlan()
assert(P.leftStart > 0 and P.leftStart < P.leftImpact and P.leftImpact < P.leftEnd and P.leftEnd <= P.rightStart, "left bucket first")
assert(P.rightStart < P.rightImpact and P.rightImpact < P.rightEnd and P.rightEnd < P.patternAt and P.patternAt < P.patternEnd and P.patternEnd < P.endsAt, "right, pattern, condition")
assert(P.endsAt + Plan.CracksMin <= Plan.Build + 1e-9, "rattle and cracks keep at least CracksMin before the burst")
assert(near(P.leftImpact, Plan.Left + Plan.Bucket.impact) and near(P.rightImpact, Plan.Right + Plan.Bucket.impact))
assert(P.leftImpact + Plan.Coat.span + Plan.Drips.delay + Plan.Drips.span <= P.rightImpact + .3 + 1e-9, "coat 1 and its drips are done when coat 2 lands")
assert(P.rightImpact + Plan.Coat.span <= P.patternAt + .2, "accent coat covers its pattern before the pattern chip")
assert(Plan.Build >= 5 and Plan.Build <= 7, "calm: 5..7 s build-up (v1 was 3.6): " .. Plan.Build)
assert(P.window == Plan.Bucket.leave and P.wash == Plan.Coat.span and P.v2 == true)
local b = Plan.Bucket
assert(b.arrive < b.hover and b.hover <= b.tip and b.tip < b.pour and b.pour < b.impact and b.impact < b.pourEnd and b.pourEnd < b.untilt and b.untilt < b.leave, "bucket keyframes in order")
assert(b.leave <= 2, "each bucket is quick (<= 2 s)")

-- Bucket pose: starts off-side and hidden, hovers at BucketX with a soft overshoot, tilts toward the egg to pour, tips back, leaves.
for _, side in {-1, 1} do
    local x0, _, t0, a0 = Plan.bucketPose(-1, side) assert(math.abs(x0) > Plan.BucketX + 1 and t0 == 0 and a0 == 0, "off to the side before its window")
    local xi, yi, ti, ai, si = Plan.bucketPose(b.impact, side)
    assert(math.sign(xi) == side and near(math.abs(xi), Plan.BucketX, .15) and ai == 1, "beside the egg at impact")
    assert(math.sign(ti) == -side and math.abs(ti) >= 60 and math.abs(ti) <= 75, "tilts toward the egg (left bucket clockwise)")
    assert(yi > 0 and yi < Plan.BucketY + .2, "above the egg centre")
    assert(si > .9 and si < 1.1, "soft squash")
    local _, _, tb = Plan.bucketPose(b.untilt + .01, side) assert(math.abs(tb) < 1e-6, "tipped back before leaving")
    local xe, _, _, ae = Plan.bucketPose(b.leave, side) assert(math.abs(xe) > Plan.BucketX + 1 and ae < .05, "leaves and fades")
    local overshoot = 0
    for i = 0, 200 do
        local x, y, tilt, a, sq = Plan.bucketPose(i / 100, side)
        assert(math.abs(x) <= Plan.BucketX + 2.2 and y >= 0 and y <= Plan.BucketY + .2 and math.abs(tilt) <= 72.001 and a >= 0 and a <= 1 and sq > .85 and sq < 1.15, "bounded pose")
        overshoot = math.max(overshoot, Plan.BucketX - math.abs(x))
    end
    assert(overshoot > 0 and overshoot < .4, "arrives with a small overshoot, not a snap: " .. overshoot)
end
-- Stream: nothing before the pour, full at impact, thins out after the pour ends.
assert(Plan.stream(b.pour - .01) == 0 and near(Plan.stream(b.impact), 1, 1e-3) and Plan.stream(b.pourEnd + .25) == 0)
local blobs = Plan.streamBlobs(100, 50, 400, 100, 1, 12)
assert(#blobs == 12 and near(blobs[1][1], 100) and near(blobs[12][1], 400) and near(blobs[12][2], 100), "arc from the lip to the impact")
local sag = false for _, p in blobs do assert(p[3] >= 6 and p[3] <= 16) if p[2] < 50 then sag = true end end
assert(sag, "the arc rises then falls (a thrown liquid, not a straight line)")
assert(#Plan.streamBlobs(100, 50, 400, 100, .5, 12) < 12, "a half-grown stream has not reached the egg")
-- Crown droplets: up and out, gravity brings them down, never below maxFall, gone by CrownLife.
for _, side in {-1, 1} do
    local rose = false
    for j = 1, 14 do
        for k = 0, 60 do
            local dx, dy, size, op = Plan.crown(j, 14, k / 100, side, 7)
            assert(math.abs(dx) <= 260 and dy >= -200 and dy <= 140 and size >= 0 and size <= 20 and op >= 0 and op <= 1, "crown bounds")
            if dy < -5 then rose = true end
        end
        local _, _, _, gone = Plan.crown(j, 14, Plan.CrownLife, side, 7) assert(gone == 0)
    end
    assert(rose, "droplets fly up first")
end
-- Drip streaks: start after the delay, grow, dry; bounded.
local seenDrip = false
for i = 1, 6 do
    assert(Plan.dripStreak(i, 0, 3) == nil and Plan.dripStreak(i, 5, 3) == nil)
    for k = 0, 160 do
        local x, y, len, w, op = Plan.dripStreak(i, k / 100, 3)
        if x then seenDrip = true assert(math.abs(x) <= 60 and y >= 10 and y <= 16 and len >= 0 and len <= 80 and w >= 3 and w <= 7.001 and op >= 0 and op <= 1) end
    end
end
assert(seenDrip)
-- Squash and stretch: a soft bubble at impact that settles at 1; gloss rises then dries matte.
local sx0, sy0 = Plan.squash(0) assert(sx0 > 1.05 and sx0 < 1.15 and near(sx0 + sy0, 2, 1e-9), "squash wide and short at impact")
local sxE, syE = Plan.squash(2) assert(near(sxE, 1, .01) and near(syE, 1, .01), "settles")
assert(Plan.squash(-1) == 1 and Plan.gloss(-1) == 0 and near(Plan.gloss(Plan.Gloss.rise), Plan.Gloss.peak, 1e-6) and Plan.gloss(Plan.Gloss.rise + Plan.Gloss.dry) == 0)
assert(Plan.Gloss.peak <= .3, "wet shine stays gentle (docs/87 matte)")
local r, d = Plan.sway(1.3) assert(math.abs(r) <= 2.2 and math.abs(d) <= 2.5)

-- Splats: deterministic from the seed, three per coat, on the bucket's side of the egg, inside the egg's unit box.
local s1, s2 = Plan.splats(Plan.seed("egg-1"), -1, 1), Plan.splats(Plan.seed("egg-1"), -1, 1)
assert(#s1 == Plan.SplatsPerCoat and s1[1].x == s2[1].x and s1[2].y == s2[2].y and s1[3].z == s2[3].z, "same seed, same splats")
local s3 = Plan.splats(Plan.seed("egg-2"), -1, 1) assert(s3[1].x ~= s1[1].x or s3[1].y ~= s1[1].y, "another egg, other splats")
for _, s in s1 do assert(s.x < 0 and math.abs(s.x) <= .5 and math.abs(s.y) <= .5 and math.abs(s.z) <= .5 and s.t0 >= 0 and s.t0 < .3) end
for _, s in Plan.splats(1, 1, 2) do assert(s.x > 0) end
local drips = Plan.drips3(1, s1, 1) assert(#drips == 2 * #s1)
-- Reveal time field: 0 at a splat centre, grows with distance, every point of the unit egg wet before the span ends; drips earlier.
local span = Plan.Coat.span
assert(near(Plan.revealTime(s1[1].x, s1[1].y, s1[1].z, s1, drips, span), 0, 1e-6))
local maxT = 0
for ix = -5, 5 do for iy = -5, 5 do for iz = -5, 5 do
    local x, y, z = ix / 10, iy / 10, iz / 10
    if x * x + y * y + z * z <= .27 then
        local t = Plan.revealTime(x, y, z, s1, drips, span)
        assert(t >= 0 and t <= span - Plan.Coat.soft + 1e-9) maxT = math.max(maxT, t)
    end
end end end
assert(maxT > span * .5, "the far side of the egg is painted late, not at once: " .. maxT)
local dr = drips[1]
local tDrip = Plan.revealTime(dr.x, dr.y - dr.len * .6, dr.z, s1, drips, span)
local tBeside = Plan.revealTime(dr.x + .2, dr.y - dr.len * .6, dr.z, s1, drips, span)
assert(tDrip < tBeside, "a drip streak runs ahead of the flood under its splat")
assert(Plan.coatAlpha(0, -1) == 0 and Plan.coatAlpha(0, Plan.Coat.soft) == 1 and Plan.wetEdge(.5) == 1 and Plan.wetEdge(0) == 0 and Plan.wetEdge(1) == 0)

-- Projection: the egg centre lands on HatchFxPlan.Center.egg; points behind the camera are nil.
local ex, ey, ez = Plan.eggCameraSpace()
local px, py = Plan.project(ex, ey, ez, Plan.Camera.fov, Plan.ScreenWidthPx, Plan.ScreenHeightPx)
assert(near(px, Plan.Camera.eggPx[1], .01) and near(py, Plan.Camera.eggPx[2], .01), "egg centre projects to (412, 130)")
assert(Plan.project(0, 0, 1, 30, 824, 402) == nil)
local pps = Plan.pxPerStud()
assert(near(pps * Plan.BucketX, 265, 12), "buckets hover about 265 px from the egg, over their chips (HatchTimeline.BucketX)")
assert(pps * Plan.EggHeight >= 180 and pps * Plan.EggHeight <= 260, "egg about 180..260 px tall")

-- Budget per device (docs/105 bytes; docs/87 phone rate): one image at most 256 KiB, phone cheaper than desktop, sprites capped.
for _, device in {"desktop", "tablet", "phone"} do
    local bu = Plan.budget(device)
    assert(bu.bake == 128 or bu.bake == 256)
    assert(Plan.imageKiB(bu.bake) <= Plan.MaxImageKiB, "one EditableImage under 256 KiB")
    assert(bu.writes >= 6 and bu.writes <= 20 and Plan.sprites(bu) <= 60, "writes per second and sprite pool bounded")
end
assert(Plan.budget("phone").bake < Plan.budget("desktop").bake and Plan.sprites(Plan.budget("phone")) < Plan.sprites(Plan.budget("desktop")))
assert(Plan.budget("zzz").bake == Plan.budget("desktop").bake)
assert(Plan.Cues.swoosh == "pickup_lo" and Plan.Cues.splashLeft == "pickup" and Plan.Cues.splashRight == "pickup_hi", "no new sounds")

-- Bake: reveal maps + composite on a small synthetic egg (UV fallback, no position map), then with a position map.
local size = 32
local map1 = Bake.revealMap(size, nil, Plan.seed("egg-1"), 1, 1)
local map2 = Bake.revealMap(size, nil, Plan.seed("egg-1"), -1, 2)
assert(#map1 == size * size and #map2 == size * size)
local prev = -1
for i = 0, 20 do
    local c = Bake.coverage(map1, span * i / 20) assert(c >= prev - 1e-9, "coverage never shrinks") prev = c
end
assert(Bake.coverage(map1, -1) == 0 and Bake.coverage(map1, span * .25) < .9 and near(Bake.coverage(map1, span), 1, 1e-9), "coat 1 floods the whole egg by the end of its span")
local same = Bake.revealMap(size, nil, Plan.seed("egg-1"), 1, 1)
for i = 1, #map1 do assert(same[i] == map1[i], "deterministic reveal map") end
-- a position map: every texel at a point on a sphere of radius .45, so the 3D splats drive the reveal
local pos = buffer.create(size * size * 4)
for i = 0, size * size - 1 do
    local u, v = (i % size + .5) / size, (i // size + .5) / size
    local th, ph = u * 2 * math.pi, v * math.pi
    local x, y, z = .45 * math.sin(ph) * math.cos(th), .45 * math.cos(ph), .45 * math.sin(ph) * math.sin(th)
    buffer.writeu8(pos, i * 4, math.floor((x + 1) * 127.5 + .5)) buffer.writeu8(pos, i * 4 + 1, math.floor((y + 1) * 127.5 + .5))
    buffer.writeu8(pos, i * 4 + 2, math.floor((z + 1) * 127.5 + .5)) buffer.writeu8(pos, i * 4 + 3, 255)
end
local m3 = Bake.revealMap(size, pos, Plan.seed("egg-1"), 1, 1)
assert(near(Bake.coverage(m3, span), 1, 1e-9) and Bake.coverage(m3, span * .2) > 0 and Bake.coverage(m3, span * .2) < .8, "3D reveal grows over the span")
local lx, ly, lz = Bake.position(pos, 1, size) assert(math.abs(lx) <= 1 and math.abs(ly) <= 1 and math.abs(lz) <= 1)
-- pattern mask (LowPolyPattern, same ids as EggGenetics) + composite
local weights = table.create(size * size, 1)
local mask = Pattern.compute("03_round_spots", Pattern.seed("egg|03_round_spots"), weights, .6, false, nil, pos, size)
local share = Bake.accentShare(mask) assert(share > .05 and share < .5, "spots cover a sensible share: " .. share)
local shade = Bake.shade(nil, size)
local out = buffer.create(size * size * 4)
local cream, base, accent = {1, .957, .84}, {.2, .4, .9}, {.05, .05, .05}
local function px(i) local o = (i - 1) * 4 return buffer.readu8(out, o), buffer.readu8(out, o + 1), buffer.readu8(out, o + 2), buffer.readu8(out, o + 3) end
Bake.composite(size, shade, mask, m3, map2, -1, -1, cream, base, accent, out)
for i = 1, size * size, 7 do local rr, gg, bb, aa = px(i) assert(rr == 255 and gg == 244 and bb == 214 and aa == 255, "cream before any impact") end
Bake.composite(size, shade, mask, m3, map2, 99, -1, cream, base, accent, out)
for i = 1, size * size, 5 do local rr, gg, bb = px(i) assert(rr == 51 and gg == 102 and bb == 230, "base coat everywhere after coat 1") end
Bake.composite(size, shade, mask, m3, map2, 99, 99, cream, base, accent, out)
local painted, kept = 0, 0
for i = 1, size * size do
    local rr, gg, bb = px(i)
    if mask[i] >= .999 then assert(rr == 13 and gg == 13 and bb == 13, "accent only where the pattern is") painted += 1
    elseif mask[i] <= .001 then assert(rr == 51 and gg == 102 and bb == 230, "base colour stays off the pattern") kept += 1 end
end
assert(painted > 0 and kept > 0)
Bake.composite(size, shade, nil, m3, map2, 99, 99, cream, base, accent, out)
for i = 1, size * size, 5 do local rr = px(i) assert(rr == 51, "a plain egg: the accent coat paints nothing") end
-- half way through coat 1: a mix of cream and base, with a bright wet edge somewhere
Bake.composite(size, shade, mask, m3, map2, span * .4, -1, cream, base, accent, out)
local sawCream, sawBase, sawEdge = false, false, false
for i = 1, size * size do local rr, gg = px(i) if rr == 255 and gg == 244 then sawCream = true elseif rr == 51 then sawBase = true elseif rr > 51 and gg > 102 and rr < 255 then sawEdge = true end end
assert(sawCream and sawBase and sawEdge, "partial coat: cream, base and a wet edge between them")
local again = buffer.create(size * size * 4)
Bake.composite(size, shade, mask, m3, map2, span * .4, -1, cream, base, accent, again)
assert(buffer.tostring(again) == buffer.tostring(out), "deterministic bytes")
-- shading from a source texture keeps facets: darker source texel -> darker paint
local src = buffer.create(size * size * 4)
for i = 0, size * size - 1 do local v = if i % 2 == 0 then 200 else 120 buffer.writeu8(src, i * 4, v) buffer.writeu8(src, i * 4 + 1, v) buffer.writeu8(src, i * 4 + 2, v) buffer.writeu8(src, i * 4 + 3, 255) end
local sh = Bake.shade(src, size) assert(sh[1] > 1 and sh[2] < 1 and sh[1] <= 1.25 and sh[2] >= .55)
assert(Bake.key(1, 256, "03_round_spots", 60, "blue", "black", true) ~= Bake.key(1, 256, "03_round_spots", 60, "blue", "black", false))

-- HatchTimeline v2 state: same rules (pending hold, fast-forward after the tap gate, Reduced Motion), the v2 build-up.
local sv = T.useV2(T.new(true, nil, nil, true), true)
assert(sv.durs.build == Plan.Build and sv.durs.paint.v2 == true and near(sv.durs.paint.leftImpact, P.leftImpact))
for _ = 1, 600 do T.step(sv, 1 / 60) end
assert(near(sv.t, P.leftStart) and sv.idle > 9, "holds at the first bucket while pending")
T.supply(sv, 3, false)
assert(not sv.pending and sv.durs.build == Plan.Build and sv.v2, "supply keeps the v2 beat sheet")
T.step(sv, 1) assert(T.tap(sv) == "fastforward" and near(sv.t, Plan.Build))
local ps = T.paintState(sv.durs, P.leftImpact + .2)
assert(ps.left.impacted and ps.left.wash > 0 and ps.left.wash < 1 and not ps.right.impacted and near(ps.left.since, b.impact + .2) and ps.left.k > 0 and ps.left.k < 1)
assert(T.paintState(sv.durs, P.endsAt).left.wash == 1 and T.paintState(sv.durs, P.endsAt).pattern == 1)
assert(T.paintState(sv.durs, P.patternAt - .01).pattern == 0 and T.paintState(sv.durs, P.patternAt + .01).patternShown)
local cues = T.cues(sv.durs, 3, false, "hatch_reveal_rare")
assert(cues[1].name == "pickup_lo" and near(cues[1].t, P.leftStart) and cues[2].name == "pickup" and near(cues[2].t, P.leftImpact) and cues[4].name == "pickup_hi" and near(cues[4].t, P.rightImpact))
local nr = 0 for _, c in cues do assert(Sfx.Sounds[c.name], c.name) if c.name == "hatch_rattle" then nr += 1 assert(c.t >= P.endsAt and c.t <= Plan.Build) end end
assert(nr >= 4)
assert(T.eggClock(sv.durs, P.endsAt - .01) < .62 and near(T.eggClock(sv.durs, Plan.Build), T.EggClock), "cracks only after the condition beat")
local rv = T.useV2(T.new(false), true)
assert(rv.durs.build == 0 and rv.durs.paint.endsAt == 0 and T.paintState(rv.durs, 0).left.wash == 1, "Reduce Motion: finished egg at once")
local v1 = T.new(true) assert(v1.durs.build == T.Motion.build and not v1.v2 and v1.durs.paint.v2 == nil, "v1 untouched")
assert(T.durations(true, 5, false, true).readyAt == Plan.Build + T.Motion.burst + T.Motion.settle + .5 and T.durations(true, 1, true, true).build == Plan.Build)
print("Hatch v2 checks passed: beat sheet, bucket/stream/crown/drip/squash/gloss curves, deterministic splats, reveal field to 100%, composite coats, budget, timeline state")
'''


def script():
    return ('local Plan=' + module('src/shared/HatchV2Plan.luau') + '\n'
            'local RS=' + module('src/shared/RevealSkip.luau') + '\n'
            'local script={Parent={RevealSkip=RS,HatchV2Plan=Plan}}\nlocal function require(x) return x end\n'
            'local Bake=' + module('src/shared/HatchPaintBake.luau') + '\n'
            'local Pattern=' + module('src/shared/LowPolyPattern.luau') + '\n'
            'local T=' + module('src/shared/HatchTimeline.luau') + '\n'
            'local Sfx=' + module('src/shared/Sfx.luau') + '\n' + BODY)


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def check_wiring():
    config = read('src/shared/Config.luau')
    assert re.search(r'^    HatchV2 = false,', config, re.M), 'Config.HatchV2 ships false'
    server = read('src/server/Bootstrap.server.luau')
    assert 'if Config.HatchV2 then task.spawn(function() require(script.Parent.ImportedResources).loadHatchV2() end) end' in server, 'loader guarded by the flag'
    imp = read('src/server/ImportedResources.luau')
    assert 'function Import.loadHatchV2' in imp and 'HatchV2Assets' in imp and 'InsertService:LoadAsset' in imp and 'HatchV2MeshFailed' in imp
    assets = read('src/shared/HatchV2Assets.luau')
    ids = re.findall(r'assetId = "(\d+)"', assets)
    assert ids == ['80664439797104', '81905342774801'], ids
    assert 'PLACEHOLDER' in assets and 'Placeholder = {bucket = true}' in assets, 'the barrel is marked as a placeholder bucket'
    registry = read('docs/77-asset-registry.md')
    for i in ids:
        assert i in registry, f'{i} missing in docs/77'
    assert 'hatch_v2_bucket_placeholder' in registry and 'PLACEHOLDER' in registry
    seq = read('src/client/HatchSequence.luau')
    for needle in ('if Config.HatchV2 == true then EggV2.create(fx.back, fx.front, motion) else nil', 'Timeline.useV2(state, true)',
                   'EggV2.setGenes(v2, g, a.eggId, base, accent, plain)', 'EggV2.burst(v2) a.eggView.Visible = true', 'EggV2.stop(v2)',
                   'EggV2.setCondition(v2, id)', 'if not motion then EggV2.finish(v2) end', 'Timeline.new(motion, 1, false, a.result == nil)'):
        assert needle in seq, needle
    assert seq.count('if v2 then') >= 5
    view = read('src/client/HatchEggV2.luau')
    for needle in ('ViewportFrame', 'CreateEditableImage(', 'CreateEditableImageAsync', 'CreateEditableMeshAsync', 'Pattern.rasterize', 'Pattern.compute',
                   'Bake.composite', 'Bake.revealMap', 'WritePixelsBuffer', 'Overlays.apply(egg, h.condition)', 'mesh:Destroy()', 'img:Destroy()',
                   'return nil end', 'h.mode = "tint"', 'Plan.budget(device)', 'if not h.motion then return end', 'Fx.setCell'):
        assert needle in view, needle
    code = '\n'.join(l for l in view.splitlines() if not l.lstrip().startswith('--'))
    assert 'Instance.new("ParticleEmitter")' not in code and 'Instance.new("Beam")' not in code, 'ViewportFrames do not draw emitters or beams: the splash is 2D sprites'
    assert 'UICorner' in view and 'UIGradient' in view, 'drip streaks are gradient frames'
    assert view.count('Instance.new("Part")') == 0 and 'SpecialMesh' not in view, 'no primitive shapes in the v2 egg scene'
    assert 'PLACEHOLDER' in view, 'the stand-in bucket is marked'
    boot = read('src/client/Bootstrap.client.luau')
    assert 'eggId=str("NextChestId"),' in boot
    locals_ = len(re.findall(r'^local ', boot, re.M))
    assert locals_ <= 193, f'Bootstrap locals grew to {locals_} (limit 200, was 193): new code belongs in modules'
    assert 'HatchEggV2' not in boot and 'require(Shared.HatchV2' not in boot, 'Bootstrap never requires the v2 modules; HatchSequence owns the v2 egg'
    tl = read('src/shared/HatchTimeline.luau')
    assert 'require(script.Parent.HatchV2Plan)' in tl and 'function T.useV2' in tl and 'p.window or T.Paint.window' in tl
    doc = read('docs/114-hatch-redesign.md')
    for word in ('Beat sheet', 'generate_mesh', 'Reduce Motion', 'Fallback chain', 'docs/105', 'PLACEHOLDER', 'evidence/2026-10-16-hatch-v2'):
        assert word in doc, word
    kanban = read('docs/07-kanban.md')
    assert '| BD-397 | Review / test |' in kanban and 'docs/114' in kanban.split('| BD-397 |')[1].split('\n')[0]
    print('Wiring checks passed: flag off, guarded loader, placeholder bucket registered, v1 fallback, no Bootstrap growth, doc and Kanban row')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'hatch_v2.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
    check_wiring()
