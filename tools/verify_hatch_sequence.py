"""Execute the pure hatch-sequence logic (src/shared/HatchTimeline.luau) with the pinned Luau runtime:
phase durations (about 3 s build-up in full motion, short fade in Reduced Motion), tap gating and
fast-forward, Skip all, the skip rules (Shiny/BIG/mutations never skipped), curve bounds (rattle grows,
reveal overshoot settles at 1), particle caps by rarity, the tap-hint copy, odds line and Sfx cue hooks.
Drawing (Instances, tweens, particles) is Studio-only; see docs/86.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
local function near(a, b, e) return math.abs(a - b) <= (e or 1e-6) end

-- Durations: ~3 s build-up, burst, settle, tap allowed only once the reveal has settled.
local m, r = T.durations(true), T.durations(false)
assert(m.build >= 3.4 and m.build <= 3.8, "build-up is about 3.6 s: two paint buckets, then rattle and crack")
assert(m.readyAt > m.build and m.readyAt <= 5, "tap becomes available shortly after the reveal")
assert(r.build == 0 and r.readyAt <= .8, "reduced motion is a short fade")
assert(T.phase(m, 0) == "build" and T.phase(m, m.build - .01) == "build" and T.phase(m, m.build) == "burst")
assert(T.phase(m, m.build + m.burst) == "settle" and T.phase(m, m.readyAt) == "ready")

-- Tap gating: ignored right after the click that started it, fast-forward once, ignored in burst/settle, advance when ready.
local s = T.new(true)
assert(T.tap(s) == "ignore", "the tap that opened the egg cannot skip it")
T.step(s, .6) assert(T.phase(s.durs, s.t) == "build")
assert(T.tap(s) == "fastforward" and near(s.t, m.build) and s.fastForwarded)
assert(T.tap(s) == "ignore", "no second fast-forward, taps during burst/settle are ignored")
T.step(s, m.burst + m.settle - .05) assert(T.tap(s) == "ignore")
T.step(s, .1) assert(T.phase(s.durs, s.t) == "ready")
assert(T.tap(s) == "advance" and s.done and T.tap(s) == "ignore", "advance fires exactly once")
-- Natural flow without any tap reaches ready at readyAt and waits for the player (no auto advance).
s = T.new(true) for _ = 1, 600 do T.step(s, 1 / 60) end
assert(T.phase(s.durs, s.t) == "ready" and not s.done, "waits for a tap")
-- Reduced motion: same tap-to-continue flow.
s = T.new(false) assert(T.tap(s) == "ignore")
T.step(s, r.readyAt + .01) assert(T.tap(s) == "advance")
-- BD-444: "Egg N of M" counter and the skip button copy.
do
    local b = T.newBatch()
    local i, n = T.batchStep(b, 14) assert(i == 1 and n == 15 and T.counterText(i, n) == "Egg 1 of 15")
    i, n = T.batchStep(b, 13) assert(i == 2 and n == 15)
    i, n = T.batchRefine(b, 12) assert(i == 2 and n == 14, "refine keeps the egg number")
    i, n = T.batchStep(b, 11) assert(i == 3 and n == 14)
    i, n = T.batchStep(b, 3) assert(i == 1 and n == 4, "a gap starts a new party")
    i, n = T.batchStep(b, 0) assert(i == 1 and n == 1 and T.counterText(i, n) == "", "single egg shows no counter")
    assert(T.SkipText == "Skip the rest" and #T.SkipText <= 16)
end
-- Skip all.
s = T.new(true) T.step(s, 1) assert(T.skipAll(s) == "fastforward" and near(s.t, m.build) and not s.done)
s = T.new(true) T.step(s, m.readyAt + .1) assert(T.skipAll(s) == "advance" and s.done)
s = T.new(true) T.step(s, m.build + .1) assert(T.skipAll(s) == "ignore")

-- Skip rules: chosen rarities skip, Shiny/BIG/mutations/Rainbow/Astra never; Skip all skips every rarity but not notable ones.
assert(T.shouldSkip({1, 2}, 1, {}, false) and T.shouldSkip({1, 2}, 2, {}, false) and not T.shouldSkip({1, 2}, 3, {}, false))
assert(not T.shouldSkip({1, 2}, 1, {shiny = true}, false) and not T.shouldSkip({1, 2}, 1, {big = true}, false))
assert(not T.shouldSkip({1, 2}, 1, {eventMutationId = "gold_rush"}, false))
assert(not T.shouldSkip({}, 1, {}, false), "nothing selected, nothing skipped")
for rarity = 1, 5 do
    assert(T.shouldSkip({}, rarity, {}, true), "Skip all covers every rarity")
    assert(not T.shouldSkip({}, rarity, {shiny = true}, true) and not T.shouldSkip({}, rarity, {big = true}, true))
    assert(not T.shouldSkip({}, rarity, {eventMutationId = "x"}, true) and not T.shouldSkip({}, rarity, {genes = {conditionId = "rainbow"}}, true))
end

-- Failed (Cracked) egg: same ~3 s build-up, then a splat; same tap flow and skip rules as any egg.
local f, fr = T.durations(true, 1, true), T.durations(false, 1, true)
assert(f.build == m.build and f.build >= 3.4 and f.build <= 3.8, "failed egg has the same build-up")
assert(f.burst > 0 and f.settle >= .8 and f.readyAt > f.build + f.burst and f.readyAt <= 5.5, "splat burst and settle, then ready")
assert(T.durations(true, 5, true).readyAt == f.readyAt, "no Legendary hold for a failed egg")
assert(fr.build == 0 and fr.readyAt == r.readyAt, "reduced motion failed egg is the short fade")
assert(T.durations(true, 5).readyAt == T.durations(true, 5, nil).readyAt, "normal eggs unchanged")
s = T.new(true, 1, true)
assert(T.tap(s) == "ignore", "the opening tap cannot skip a failed egg")
T.step(s, .6) assert(T.tap(s) == "fastforward" and near(s.t, f.build))
T.step(s, f.burst + f.settle - .05) assert(T.tap(s) == "ignore", "taps ignored during the splat")
T.step(s, .1) assert(T.phase(s.durs, s.t) == "ready" and T.tap(s) == "advance" and s.done, "failed egg counts in the tap flow")
s = T.new(true, 1, true) T.step(s, 1) assert(T.skipAll(s) == "fastforward")
s = T.new(true, 1, true) T.step(s, f.readyAt + .1) assert(T.skipAll(s) == "advance")
s = T.new(false, 1, true) T.step(s, fr.readyAt + .01) assert(T.tap(s) == "advance")
-- Skip rules do not look at hatch success: a failed egg of a skipped rarity keeps its quick path, notable ones are never skipped.
assert(T.shouldSkip({1}, 1, {genes = {conditionId = "cracked", hatchSuccess = false}}, false))
assert(not T.shouldSkip({1}, 3, {genes = {conditionId = "cracked", hatchSuccess = false}}, false))
assert(T.shouldSkip({}, 2, {genes = {conditionId = "cracked", hatchSuccess = false}}, true))
-- Splat curves are bounded: shells bounce but never sink below the floor, yolk squashes then rests, puddle spreads to 1.
for _, side in {-1, 1} do
    local lastX = -1
    for i = 0, 300 do
        local dx, dy, rot = T.shell(i / 100, side, 84)
        assert(dy <= 84.001 and dy >= -170 and math.abs(dx) <= 150 and math.abs(rot) <= 400.001)
        assert(side * dx >= lastX - 1e-6, "shell drifts outward") lastX = side * dx
    end
    local _, endY = T.shell(3, side, 84) assert(near(endY, 84, .01), "shell comes to rest on the floor")
end
local sawUp, sawBounce, prevY = false, false, 0
for i = 0, 200 do
    local y = T.bounceY(i / 100, -170, 900, 84, .38)
    if y < -10 then sawUp = true end
    if i > 30 and y < prevY - .001 and prevY > 70 then sawBounce = true end
    prevY = y
end
assert(sawUp and sawBounce, "shells pop up and bounce at least once")
local y0, sx0, sy0 = T.yolk(0) assert(y0 == -70 and sy0 > 1 and sx0 < 1, "yolk falls stretched")
local _, sxL, syL = T.yolk(T.SplatDrop) assert(sxL > 1.4 and syL < .65, "yolk squashes on landing")
local ysxEnd, ysyEnd
do local _, a1, b1 = T.yolk(4) ysxEnd, ysyEnd = a1, b1 end
assert(near(ysxEnd, 1, .01) and near(ysyEnd, 1, .01), "yolk settles")
local pw0, ph0 = T.puddle(T.SplatDrop - .01) assert(pw0 == 0 and ph0 == 0, "no puddle before the landing")
local pwMax = 0 for i = 0, 300 do local pw, ph = T.puddle(i / 100) pwMax = math.max(pwMax, pw) assert(pw >= 0 and pw < 1.3 and ph >= 0 and ph < 1.3) end
local pwEnd = T.puddle(4) assert(near(pwEnd, 1, .02) and pwMax > 1, "puddle spreads with a little overshoot, then rests")
for i = 1, 2 do
    local dy, alpha = T.drip(T.SplatDrop + .5 + (i - 1) * .3 + .3, i) assert(dy and alpha and dy > 0 and alpha > 0 and alpha < 1)
    assert(T.drip(0, i) == nil and T.drip(5, i) == nil, "drips only show for a moment")
end
local b1, b1y = T.bump(0) assert(b1 > 1.02 and b1 < 1.06 and math.abs(b1y) < 6)
local b2 = T.bump(1) assert(near(b2, 1, .001), "camera bump decays")
local sc0, tr0 = T.splatPulse(T.SplatDrop + .45) assert(sc0 > 2 and tr0 == 1)
assert(T.crumbCount(true) == T.CrumbMax and T.CrumbMax <= 12 and T.crumbCount(false) == 0 and T.MaxParticles >= T.CrumbMax)
-- Cues: build-up like any egg, burst cue, no reveal sting.
local fc = T.cues(f, 1, true, "hatch_reveal_common")
local nb = 0 for _, c in fc do if c.name == "hatch_rattle" then nb += 1 end assert(c.t <= f.readyAt) end
assert(nb >= 4, "failed egg rattles like a normal egg")
-- Copy is built from config, never hardcoded: Cracked hatchChance .2 reads "1 time in 5".
assert(T.FailTitle == "Oops! Splat!" and T.FailSub == "This cracked egg did not hatch")
assert(T.failChance(.2) == "Cracked eggs hatch 1 time in 5" and T.failChance(.25) == "Cracked eggs hatch 1 time in 4")
assert(T.failChance(.4) == "Cracked eggs hatch 40% of the time" and T.failChance(1) == "" and T.failChance(nil) == "" and T.failChance(0) == "")
for _, text in {T.FailTitle, T.FailSub, T.failChance(.2)} do assert(not string.find(string.lower(text), "fail") and #text <= 40, "short and friendly: " .. text) end

-- Curves.
local prev = -1
for i = 0, 20 do
    local v = T.intensity(i / 20) assert(v >= prev and v >= 0 and v <= 1) prev = v
end
assert(T.intensity(0) == 0 and near(T.intensity(1), 1) and T.intensity(.5) < .3, "rattle eases in")
assert(near(T.zoom(0), 1) and T.zoom(1) > 1.15 and T.zoom(1) < 1.4 and T.cameraZoom(1) < 1.08 and T.cameraZoom(1) > 1.02)
assert(T.glow(0) == 0 and near(T.glow(1), 1))
local maxRot, maxDx, maxDy, maxSx = 0, 0, 0, 0
for i = 0, 3000 do
    local rot, dx, dy = T.rattle(i / 1000, 1)
    local sx = T.shakeOffset(i / 1000, 1)
    maxRot, maxDx, maxDy, maxSx = math.max(maxRot, math.abs(rot)), math.max(maxDx, math.abs(dx)), math.max(maxDy, math.abs(dy)), math.max(maxSx, math.abs(sx))
end
assert(maxRot > 5 and maxRot <= 8 and maxDx <= 5 and maxDy <= 3 and maxSx <= 2.4, "bounded rattle and shake")
local r0, d0, y0 = T.rattle(1.234, 0) assert(r0 == 0 and d0 == 0 and y0 == 0, "no jitter at zero intensity")
assert(near(T.revealScale(0), .25) and T.revealScale(1) == 1 and T.revealScale(2) == 1)
local peak = 0 for i = 0, 100 do peak = math.max(peak, T.revealScale(i / 100)) end
assert(peak > 1.02 and peak < 1.05, "slight overshoot, then settle at 1: " .. peak)
assert(T.easeOut(0) == 0 and T.easeOut(1) == 1)

-- Particles: scale with rarity, hard cap, none without motion or on a cracked egg.
local last = 0
for rarity = 1, 5 do
    local n = T.particleCount(rarity, false, false, true, false) assert(n >= last and n <= T.MaxParticles) last = n
    assert(T.particleCount(rarity, true, true, true, false) >= n and T.particleCount(rarity, true, true, true, false) <= T.MaxParticles)
    assert(T.particleCount(rarity, true, true, false, false) == 0 and T.particleCount(rarity, true, true, true, true) == 0)
end
assert(T.particleCount(9, true, true, true, false) == T.MaxParticles and T.MaxParticles <= 32)

-- BD-437 reveal ladder: anticipation, camera punch and dino pop step up with rarity; Reduce Motion / failed eggs unchanged.
do
    local prevA, prevP, prevPeak = -1, 0, 0
    for rr = 1, 5 do
        local a = T.anticipation(rr)
        assert(a >= prevA and a <= .5, "anticipation grows, at most .5 s") prevA = a
        assert(T.durations(true, rr).build == m.build + a and T.durations(true, rr, true).build == m.build, "failed egg: no anticipation")
        assert(T.durations(false, rr).build == 0, "Reduce Motion: no anticipation")
        local pu = T.escalation(rr, true).punch assert(pu > prevP) prevP = pu
        local peak = 0 for i = 0, 200 do peak = math.max(peak, T.revealScale(i / 200, rr)) end
        assert(peak > prevPeak and peak < 1.07 and T.revealScale(1, rr) == 1 and near(T.revealScale(0, rr), .25), "pop grows, bounded, settles at 1: " .. peak)
        prevPeak = peak
    end
    assert(T.anticipation(nil) == 0 and T.anticipation(1) == 0 and T.anticipation(5) > T.anticipation(3))
    -- A 15-egg hatch party in increasing rarity (illustrative mix: 7 Common, 4 Uncommon, 2 Rare, 1 Epic, 1 Legendary), natural flow, no taps.
    local mix, total, plain = {1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 4, 5}, 0, 0
    assert(#mix == 15)
    for _, rr in mix do total += T.durations(true, rr).readyAt plain += T.durations(true, 1).readyAt end
    assert(total - plain < 3 and total < 85, "party stays reasonable: " .. total .. " s (anticipation adds " .. (total - plain) .. " s)")
    print("BD-437 ladder: 15-egg party " .. string.format("%.2f", total) .. " s, +" .. string.format("%.2f", total - plain) .. " s vs all-Common")
end

-- Rarity escalation, extra pools and the BIG stamp.
assert(T.durations(true, 5).readyAt > T.durations(true, 1).readyAt and T.durations(true, 5).build == m.build + T.anticipation(5), "Legendary holds longer (BD-437: build-up plus anticipation)")
assert(T.durations(false, 5).readyAt == r.readyAt)
local e1, e3, e4, e5 = T.escalation(1, true), T.escalation(3, true), T.escalation(4, true), T.escalation(5, true)
assert(not e1.shock and e3.shock and not e3.arcs and e4.arcs and e4.shakeScale > 1 and not e4.fireworks and e5.fireworks and e5.punch > e1.punch)
local er = T.escalation(5, false) assert(not er.shock and not er.arcs and not er.fireworks and er.shakeScale == 1)
assert(T.orbitCount(5, true, false) <= T.OrbitMax and T.orbitCount(1, true, false) < T.orbitCount(5, true, false) and T.orbitCount(5, false, false) == 0)
assert(T.MaxParticles + T.OrbitMax + T.FireworkMax + T.RainMax <= 80, "bounded pools")
assert(T.stamp(-1) == 1 and T.stamp(0) > 1.1 and T.stamp(0) <= 1.13 and T.stamp(.25) == 1 and T.stamp(.1) < T.stamp(0))

-- Copy.
assert(T.hint(3) == "Tap for next egg (3 left)" and T.hint(1) == "Tap for next egg (1 left)" and T.hint(0) == "Done")
assert(T.remaining(false, 4, 9) == 0 and T.remaining(true, 0, 0) == 1 and T.remaining(true, 2, 5) == 7)
assert(T.pct(26) == "26%" and T.pct(12.5) == "12.5%" and T.pct(.04) == "0.04%" and T.pct(100 * 7 / 100) == "7%")
local weights = {{speciesId = "a", weight = 26}, {speciesId = "b", weight = 74}}
assert(near(T.speciesPct(weights, "a"), 26) and T.speciesPct(weights, "zzz") == nil and T.speciesPct(nil, "a") == nil)
assert(T.oddsLine("Rare", 12.5) == "Rare \u{2022} 12.5% of eggs" and T.oddsLine("Rare", nil) == "Rare")

-- BD-170/171: pending start (Open animates at once), paint buckets, trait tiers, remapped cues.
local P = m.paint
assert(P.leftStart > 0 and P.leftStart < P.leftImpact and P.leftImpact < P.leftEnd and P.leftEnd <= P.rightStart, "left bucket first")
assert(P.rightStart < P.rightImpact and P.rightImpact < P.rightEnd and P.rightEnd < P.patternAt and P.patternAt < P.patternEnd and P.patternEnd == P.endsAt, "right bucket second, then the pattern (BD-220)")
assert(P.endsAt < m.build - 1.2, "rattle and cracks still get >= 1.2 s after the pattern")
assert(P.leftEnd - P.leftStart <= 1 and P.rightEnd - P.rightStart <= 1, "each bucket is quick (<= 1 s)")
assert(r.paint.endsAt == 0 and f.paint.endsAt == P.endsAt and T.durations(true, 5).paint.endsAt == P.endsAt, "same paint plan for failed and Legendary eggs; none in Reduced Motion")
-- Pending: t holds at the first bucket until the result arrives; the visual clock keeps running.
local ps = T.new(true, nil, nil, true)
for _ = 1, 600 do T.step(ps, 1 / 60) end
assert(near(ps.t, P.leftStart, 1e-6) and ps.idle > 9 and T.phase(ps.durs, ps.t) == "build", "holds at the first bucket while pending")
assert(T.tap(ps) == "ignore" and T.skipAll(ps) == "ignore" and not ps.done and not ps.fastForwarded, "taps cannot skip an egg that has no result yet")
assert(T.visualT(ps) > 9, "egg keeps wobbling while waiting")
T.supply(ps, 5, false)
assert(not ps.pending and ps.durs.readyAt == T.durations(true, 5, false).readyAt and ps.durs.build == m.build + T.anticipation(5), "supply swaps in the real timing, build length unchanged")
T.step(ps, .5) assert(ps.t > P.leftStart, "runs on after supply")
local pr = T.new(false, nil, nil, true) T.step(pr, 1) assert(pr.t == 0 and pr.idle == 1, "Reduced Motion also waits for the result")
local ns = T.new(true) T.step(ns, 1) assert(near(ns.t, 1) and ns.idle == 0, "a normal egg never idles")
-- Egg clock and build progress: wobble below the first crack while painting, then up to EggClock across the cracks.
assert(T.eggClock(m, 0) == 0 and near(T.eggClock(m, P.endsAt), T.WobbleClock) and near(T.eggClock(m, m.build), T.EggClock) and T.eggClock(r, 0) == T.EggClock)
local lastClock = -1
for i = 0, 360 do
    local c = T.eggClock(m, i / 100) assert(c >= lastClock - 1e-9, "egg clock never runs backwards") lastClock = c
    if i / 100 < P.endsAt then assert(c < .62, "no rattle beat or crack before the buckets are done") end
end
assert(T.buildProgress(m, 0) == 0 and T.buildProgress(m, P.endsAt) == 0 and near(T.buildProgress(m, m.build), 1))
-- Bucket pose: arrives from the side, tilts toward the egg at impact, leaves; bounded.
for _, side in {-1, 1} do
    local x0, _, _, a0 = T.bucketPose(0, side) assert(math.abs(x0) >= 300 and a0 == 0, "starts off to the side, hidden")
    local xi, yi, ri, ai = T.bucketPose(T.Paint.impact, side)
    assert(math.sign(xi) == side and near(math.abs(xi), T.BucketX, 1e-6) and ai == 1, "hovers beside the egg at impact, right above its chip")
    assert(math.sign(ri) == -side and math.abs(ri) >= 40 and math.abs(ri) <= 70, "tilts toward the egg (left bucket clockwise) to pour")
    assert(yi < 0, "above the egg")
    local xe, _, re, ae = T.bucketPose(1, side) assert(math.abs(xe) >= 300 and ae < .05 and near(re, 0, 1e-6), "leaves and fades")
    for i = 0, 100 do local x, y, rot, a = T.bucketPose(i / 100, side) assert(math.abs(x) <= 390 and math.abs(y) <= 100 and math.abs(rot) <= 70.001 and a >= 0 and a <= 1) end
end
-- Paint state: wash is 0 before the impact and grows to 1, per bucket.
local ps0, psA, psB = T.paintState(m, 0), T.paintState(m, P.leftImpact + .01), T.paintState(m, P.rightImpact + .5)
assert(not ps0.left.impacted and ps0.left.wash == 0 and ps0.right.wash == 0)
assert(psA.left.impacted and psA.left.wash > 0 and psA.left.wash < .5 and not psA.right.impacted and psA.right.wash == 0, "colour first, pattern still hidden")
assert(psB.left.wash == 1 and psB.right.wash == 1)
-- BD-220: the pattern fades in only after both buckets.
local psC = T.paintState(m, P.patternAt - .01) assert(psC.right.wash > .9 and psC.pattern == 0 and not psC.patternShown, "pattern still hidden right after the second splash")
local pp = T.paintState(m, P.patternAt + T.Paint.patternWash / 2) assert(pp.patternShown and pp.pattern > 0 and pp.pattern < 1)
assert(T.paintState(m, P.patternEnd + .01).pattern == 1 and T.paintState(r, 0).pattern == 1, "pattern fully shown at the end; Reduced Motion at once")
local rp = T.paintState(r, 0) assert(rp.left.wash == 1 and rp.right.wash == 1, "Reduced Motion shows the final look at once")
-- Splash and droplets: bounded, fade out.
local sc0, st0 = T.splash(0) local sc1, st1 = T.splash(.5)
assert(sc0 > .3 and st0 == 0 and sc1 > 1.9 and st1 == 1 and select(2, T.splash(-1)) == 1)
assert(T.PaintMax == 20 and T.MaxParticles + T.OrbitMax + T.FireworkMax + T.RainMax + T.PaintMax <= 100, "bounded pools")
for _, side in {-1, 1} do
    for i = 1, 10 do
        for k = 0, 70 do
            local dx, dy, tr = T.drop(i, 10, k / 100, side)
            assert(math.abs(dx) <= 200 and dy >= -130 and dy <= 260 and tr >= 0 and tr <= 1, "droplet bounds")
        end
        local _, _, gone = T.drop(i, 10, .75, side) assert(gone == 1)
    end
end
-- Trait tiers: Cream/Blue Common ... Black Mythic; a two-colour egg shows the rarer tier; Plain pattern is Common.
local colors = {{id = "white", name = "Cream", weight = 5000}, {id = "blue", name = "Blue", weight = 2600}, {id = "green", name = "Green", weight = 1200},
    {id = "teal", name = "Teal", weight = 400}, {id = "pink", name = "Pink", weight = 500}, {id = "gold", name = "Amber", weight = 250},
    {id = "violet", name = "Purple", weight = 45}, {id = "red", name = "Red", weight = 4}, {id = "black", name = "Black", weight = 1}}
local function color(a, b) return T.colorReveal(colors, {primaryColorId = a, secondaryColorId = b or a}) end
assert(color("white").tierName == "Common" and color("blue").tierName == "Common" and color("green").tierName == "Uncommon")
assert(color("pink").tierName == "Rare" and color("violet").tierName == "Epic" and color("red").tierName == "Legendary" and color("black").tierName == "Mythic")
-- BD-220: one colour per chip, never "A + B"; the right bucket gets the secondary colour with its own tier.
assert(color("blue").name == "Blue" and color("blue", "black").name == "Blue" and color("blue", "black").tierName == "Common", "left chip = primary colour only")
local second = T.colorReveal(colors, {primaryColorId = "blue", secondaryColorId = "black"}, "secondary")
assert(second.name == "Black" and second.tierName == "Mythic", "right chip = secondary colour and its tier")
assert(T.colorReveal(colors, {primaryColorId = "green", secondaryColorId = "nope"}, "secondary").name == "Green", "missing secondary falls back to the primary")
for _, row in colors do assert(not string.find(color(row.id, "black").name, "+", 1, true)) end
assert(T.colorReveal(colors, {primaryColorId = "nope"}) == nil and T.colorReveal(nil, {}) == nil and T.colorReveal(colors, nil) == nil)
local lastTier = 0 for _, id in {"white", "green", "pink", "violet", "red", "black"} do local t = color(id).tier assert(t > lastTier, "rarer colours never get a lower tier") lastTier = t end
assert(T.tier(nil) == 1 and T.tier(100) == 1 and T.tier(0) == 6 and T.tier(25) == 1 and T.tier(24.9) == 2)
local patternNames = {["03_round_spots"] = "Round Spots"}
local patternList = {"01_blank", "02_emerald_islands", "03_round_spots", "04_bold_patches", "05_horizontal_bands", "06_wavy_stripes", "07_diamond_scales", "08_freckles"}
local pat = T.patternReveal(patternList, "03_round_spots", function(id) return patternNames[id] or tostring(id) end)
assert(pat.name == "Round Spots" and pat.tierName == "Uncommon" and not pat.plain and near(pat.pct, 12.5))
local plain = T.patternReveal(patternList, "01_blank", function(id) return tostring(id) end)
assert(plain.plain and plain.name == "Plain" and plain.tierName == "Common" and T.patternReveal(patternList, nil, tostring).plain)
assert(T.paintLine(color("black")) == "Black \u{2022} Mythic" and T.paintLine(pat) == "Round Spots \u{2022} Uncommon")
assert(T.patternLabel(pat) == "Round Spots" and T.patternLabel(plain) == "No pattern" and T.patternLabel(nil) == "")
assert(T.detailLine(color("green"), pat, "Colour bonus +2% growth") == "Green \u{2022} Round Spots \u{2022} Colour bonus +2% growth", "bonus once, on the final card")
assert(T.detailLine(color("green"), pat, nil) == "Green \u{2022} Round Spots" and T.detailLine(nil, pat, nil) == "")
-- BD-223: condition chip from the first frame; Cracked gets a short hatch hint; Normal shows nothing.
assert(T.conditionChip({id = "cracked", name = "Cracked", hatchChance = .2}) == "Cracked \u{2022} hatches 1 in 5")
assert(T.conditionChip({id = "dirty", name = "Dirty", hatchChance = 1}) == "Dirty" and T.conditionChip({id = "rainbow", name = "Rainbow"}) == "Rainbow")
assert(T.conditionChip({id = "normal", name = "Normal", hatchChance = 1}) == nil and T.conditionChip(nil) == nil)
assert(T.hatchHint(.3) == "hatches 30%" and T.hatchHint(1) == "" and T.hatchHint(nil) == "")
for _, c in {"Cracked \u{2022} hatches 1 in 5", "Rainbow", "Astra"} do assert(#c <= 28 and not string.find(c, "\n"), "one short line") end
local q = {{id = "a", genes = {conditionId = "dirty"}}, {id = "b", genes = {conditionId = "cracked"}}}
assert(T.queueCondition(q, "b") == "cracked" and T.queueCondition(q, "zzz") == "dirty" and T.queueCondition({}, "a") == nil and T.queueCondition(nil, "a") == nil)
assert(T.queueCondition({{id = "a", genes = "bad"}}, "a") == nil)
-- Cues: four paint cues sit in the bucket windows, rattle and cracks after them; only existing Sfx names.
do
    local cues = T.cues(m, 1, false, Sfx.revealName(1))
    assert(cues[1].name == "pickup_lo" and near(cues[1].t, P.leftStart) and cues[2].name == "pickup" and near(cues[2].t, P.leftImpact), "left bucket: swoosh then splash")
    assert(cues[3].name == "pickup_lo" and near(cues[3].t, P.rightStart) and cues[4].name == "pickup_hi" and near(cues[4].t, P.rightImpact), "right bucket: swoosh then splash")
    for _, c in cues do
        if c.name == "hatch_rattle" or c.name == "hatch_crack_stage" then assert(c.t >= P.endsAt and c.t <= m.build, "rattle and cracks come after the buckets") end
        assert(Sfx.Sounds[c.name], "unknown Sfx hook " .. c.name)
    end
    for _, c in T.cues(r, 1, false, "hatch_reveal_common") do assert(c.name ~= "pickup_lo" and c.name ~= "pickup" and c.name ~= "pickup_hi", "no bucket cues in Reduced Motion") end
end

-- Sfx cues: time ordered, inside the sequence, named hooks only.
for rarity = 1, 5 do
    local cues = T.cues(m, rarity, false, Sfx.revealName(rarity))
    local seen, lastT = {}, -1
    for _, c in cues do
        assert(c.t >= lastT and c.t >= 0 and c.t <= m.readyAt, "ordered inside the sequence") lastT = c.t
        assert(Sfx.Sounds[c.name], "unknown Sfx hook " .. c.name) seen[c.name] = (seen[c.name] or 0) + 1
    end
    assert(seen.hatch_rattle >= 4 and seen.hatch_crack_stage == 3 and seen.hatch_burst == 1 and seen[Sfx.revealName(rarity)] == 1)
end
for _, c in T.cues(m, 1, true, "hatch_reveal_common") do assert(c.name ~= "hatch_reveal_common", "no reveal sting for a cracked egg") end
for _, c in T.cues(r, 3, false, Sfx.revealName(3)) do assert(c.name ~= "hatch_rattle" and c.name ~= "hatch_crack_stage", "no rattle or crack cues in Reduced Motion") end
for rarity = 1, 5 do
    local name = Sfx.revealName(rarity) assert(Sfx.Sounds[name] and Sfx.normalizeId(Sfx.Sounds[name].id) ~= nil, "every reveal hook maps to a bound uploaded sound (2026-10-15 pack)")
end
assert(Sfx.revealName(nil) == "hatch_reveal_common" and Sfx.revealName(9) == "hatch_reveal_legendary")
for _, name in {"hatch_rattle", "hatch_burst"} do assert(Sfx.Sounds[name].id == "", "no sound exists yet for " .. name) end
assert(Sfx.normalizeId(Sfx.Sounds.hatch_crack_stage.id) ~= nil, "crack stage reuses the uploaded crack sound")
print("Hatch sequence checks passed: ~3.6 s build-up with paint buckets, pending start, tap gating, skip rules, failed-egg splat, curves, particle caps, copy, Sfx cues")
'''


def script():
    return ('local RS=' + module('src/shared/RevealSkip.luau') + '\n'
            'local V2=' + module('src/shared/HatchV2Plan.luau') + '\n'
            'local script={Parent={RevealSkip=RS,HatchV2Plan=V2}}\nlocal function require(x) return x end\n'
            'local T=' + module('src/shared/HatchTimeline.luau') + '\n'
            'local Sfx=' + module('src/shared/Sfx.luau') + '\n' + BODY)


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def check_wiring():
    """Source-level wiring for BD-170 / BD-171 / BD-174 (Instances cannot run in plain Luau; Studio checks drawing)."""
    import re
    boot = read('src/client/Bootstrap.client.luau')
    seq = read('src/client/HatchSequence.luau')
    pres = read('src/shared/HatchPresentation.luau')
    appearance = read('src/shared/EggAppearance.luau')
    traits = read('src/client/PreviewTraits.luau')
    # BD-170: Open starts the screen at once, Next egg stays in the sequence, the answer is supplied to the running screen.
    assert 'if (hatchState.next :: any)() then open("hatch") end' in boot, 'Open / Next egg open the hatch screen immediately'
    assert boot.count('if (hatchState.next :: any)() then open("hatch") end') >= 2, 'both Open and Next egg use the immediate path'
    assert 'task.defer(waiting.supply)' in boot and 'hatchState.pending' in boot, 'the server answer is handed to the waiting screen'
    assert 'EggCounter' in seq and 'Timeline.batchStep' in seq and 'Timeline.SkipText' in seq and 'UDim2.fromOffset(176, 48)' in seq, 'BD-444 counter + skip button (>= 44 px)'
    assert 'finishBatch()' in boot and 'EggsLogic.afterReveal(skipAllReveals,remainingAfter)=="continue"' in boot, 'only the end of the batch leaves'
    assert 'open("eggs") end -- never leave an egg wobbling forever' in boot, 'a lost answer never strands the player'
    hatch_block = boot[boot.index('elseif name=="hatch" then'):boot.index('elseif name=="exit" then')]
    assert 'HatchPresentation.add(body,nil,' in hatch_block, 'the egg is built without genes: plain and colourless at the start'
    assert hatch_block.index('HatchPresentation.add') < hatch_block.index('Preview.add(body,id'), 'no dinosaur view before the answer exists'
    assert 'condition.name' not in hatch_block and 'conditionId' not in hatch_block, 'BD-174: no condition text on the dinosaur reveal'
    assert 'Timeline.new(motion, 1, false, a.result == nil)' in seq, 'the sequence starts pending when no result is known'
    assert 'if state.pending then return end' in seq, 'taps are ignored until the answer arrives'
    # BD-171: paint buckets drive the egg and use only existing Sfx names through HatchTimeline.cues.
    for needle in ('Timeline.paintState(durs, t)', 'Timeline.bucketPose', 'a.paint.color(', 'a.paint.second(', 'a.paint.pattern(', 'a.paint.finish()',
                   'Timeline.patternLabel(', 'a.paint.setCondition(id)', 'setCondition(a.eggCondition)', 'Timeline.conditionChip(', 'FxPlan.Chips'):
        assert needle in seq, needle
    # BD-220: chips show ONE colour each (left primary, right secondary), never the pattern, never a bonus line.
    assert 'a.secondReveal or a.colorReveal' in seq and 'bonusText' not in seq and 'CHIP_CENTERS' not in seq
    assert 'secondReveal=if geneticsOk then HatchTimeline.colorReveal(ProgressionConfig.EggColors,genes,"secondary")' in boot
    assert 'HatchTimeline.detailLine(colorReveal,patternReveal,colorReveal.bonusText)' in boot, 'colour bonus once on the final card'
    # BD-223: the hatching egg shows its condition from the first frame, kept through the splashes.
    assert 'eggCondition=HatchTimeline.queueCondition(queue(),str("NextChestId"))' in boot
    assert 'function paint.setCondition' in pres and 'Overlays.describe(conditionId)' in pres and 'condition.ImageTransparency=shell.ImageTransparency' in pres
    assert 'function paint.second' in pres
    assert 'ModelPreview.add(holder,"egg")' in pres and 'is never shown' in pres, 'BD-170: the primitive/cube egg is never displayed'
    assert re.search(r'view\.ImageTransparency,view\.Visible=1,false', pres), 'the real 3D egg stays hidden until the pattern splash'
    assert 'Theme.ImageIds.egg or shellImage' in pres, 'the plain Blender egg image is the starting egg'
    # BD-174: condition overlay only for eggs.
    assert 'showCondition==true' in appearance and 'Overlays.apply(shell,genes.conditionId)' in appearance
    assert 'Appearance.apply(lowPoly or view, traits.genes, isEgg == true)' in traits  # BD-345: a held low-poly model is tinted directly; eggs stay on the view path
    calls = {}
    for path in ('src/client/Bootstrap.client.luau', 'src/client/EggsScreen.luau', 'src/client/PreviewTraits.luau', 'src/client/ResourceVisuals.client.luau',
                 'src/shared/DinosaurPreview.luau', 'src/shared/HatchPresentation.luau'):
        for line in read(path).splitlines():
            m = re.search(r"(?:Appearance|EggAppearance)\.apply\((.*)", line)
            if m:
                calls.setdefault(path, []).append(m.group(1).split(" end")[0].rstrip())
    egg_files = {'src/shared/HatchPresentation.luau': 'genes,true', 'src/client/Bootstrap.client.luau': 'EggGenetics.neutral(row.id),true'}
    for path, args in calls.items():
        for arg in (a.rstrip(')') for a in args):
            if path in egg_files:
                assert arg.endswith(',true') or arg.endswith('true'), f'egg call must pass showCondition in {path}: {arg}'
            elif path.endswith('PreviewTraits.luau'):
                assert 'isEgg==true' in arg.replace(' ', '')
            else:
                assert not arg.endswith('true'), f'dinosaur call must not show the condition in {path}: {arg}'
    assert 'Overlays.describe(genes.conditionId)' in read('src/client/EggPicture.luau'), 'egg cards keep the condition look'
    for path in ('src/client/DinoIndexPanels.luau', 'src/client/DinoDetails.luau'):
        assert 'PreviewTraits.add(view, {' in read(path) or 'PreviewTraits.add(preview, {' in read(path)
        assert ', true)' not in re.sub(r'\{[^}]*\}', '', ''.join(l for l in read(path).splitlines() if 'PreviewTraits.add' in l)), f'no condition on dinosaur previews in {path}'
    details = read('src/shared/FusionSelection.luau')
    assert 'label = "Condition"' not in details, 'BD-174: Dino Details has no condition row'
    print('Wiring checks passed: Open/Next egg stay in the sequence, plain egg first, paint buckets, no cube egg, condition only on eggs')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'hatch.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
    check_wiring()
