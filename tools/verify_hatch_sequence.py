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
assert(m.build >= 2.8 and m.build <= 3.2, "build-up is about 3 s")
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
assert(peak > 1.02 and peak < 1.12, "slight overshoot, then settle at 1: " .. peak)
assert(T.easeOut(0) == 0 and T.easeOut(1) == 1)

-- Particles: scale with rarity, hard cap, none without motion or on a cracked egg.
local last = 0
for rarity = 1, 5 do
    local n = T.particleCount(rarity, false, false, true, false) assert(n >= last and n <= T.MaxParticles) last = n
    assert(T.particleCount(rarity, true, true, true, false) >= n and T.particleCount(rarity, true, true, true, false) <= T.MaxParticles)
    assert(T.particleCount(rarity, true, true, false, false) == 0 and T.particleCount(rarity, true, true, true, true) == 0)
end
assert(T.particleCount(9, true, true, true, false) == T.MaxParticles and T.MaxParticles <= 32)

-- Rarity escalation, extra pools and the BIG stamp.
assert(T.durations(true, 5).readyAt > T.durations(true, 1).readyAt and T.durations(true, 5).build == m.build, "Legendary holds longer, same build-up")
assert(T.durations(false, 5).readyAt == r.readyAt)
local e1, e3, e4, e5 = T.escalation(1, true), T.escalation(3, true), T.escalation(4, true), T.escalation(5, true)
assert(not e1.shock and e3.shock and not e3.arcs and e4.arcs and e4.shakeScale > 1 and not e4.fireworks and e5.fireworks and e5.punch > e1.punch)
local er = T.escalation(5, false) assert(not er.shock and not er.arcs and not er.fireworks and er.shakeScale == 1)
assert(T.orbitCount(5, true, false) <= T.OrbitMax and T.orbitCount(1, true, false) < T.orbitCount(5, true, false) and T.orbitCount(5, false, false) == 0)
assert(T.MaxParticles + T.OrbitMax + T.FireworkMax + T.RainMax <= 80, "bounded pools")
assert(T.stamp(-1) == 1 and T.stamp(0) > 1.3 and T.stamp(.25) == 1 and T.stamp(.1) < T.stamp(0))

-- Copy.
assert(T.hint(3) == "Tap for next egg (3 left)" and T.hint(1) == "Tap for next egg (1 left)" and T.hint(0) == "Done")
assert(T.remaining(false, 4, 9) == 0 and T.remaining(true, 0, 0) == 1 and T.remaining(true, 2, 5) == 7)
assert(T.pct(26) == "26%" and T.pct(12.5) == "12.5%" and T.pct(.04) == "0.04%" and T.pct(100 * 7 / 100) == "7%")
local weights = {{speciesId = "a", weight = 26}, {speciesId = "b", weight = 74}}
assert(near(T.speciesPct(weights, "a"), 26) and T.speciesPct(weights, "zzz") == nil and T.speciesPct(nil, "a") == nil)
assert(T.oddsLine("Rare", 12.5) == "Rare \u{2022} 12.5% of eggs" and T.oddsLine("Rare", nil) == "Rare")

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
    local name = Sfx.revealName(rarity) assert(Sfx.Sounds[name] and Sfx.Sounds[name].id == "", "reveal hooks stay silent until ids are bound")
end
assert(Sfx.revealName(nil) == "hatch_reveal_common" and Sfx.revealName(9) == "hatch_reveal_legendary")
for _, name in {"hatch_rattle", "hatch_crack_stage", "hatch_burst"} do assert(Sfx.Sounds[name].id == "") end
print("Hatch sequence checks passed: ~3 s build-up, tap gating, skip rules, curves, particle caps, copy, Sfx cues")
'''


def script():
    return ('local RS=' + module('src/shared/RevealSkip.luau') + '\n'
            'local script={Parent={RevealSkip=RS}}\nlocal function require(x) return x end\n'
            'local T=' + module('src/shared/HatchTimeline.luau') + '\n'
            'local Sfx=' + module('src/shared/Sfx.luau') + '\n' + BODY)


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
