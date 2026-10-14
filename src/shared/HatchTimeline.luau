--!strict
-- Hatch sequence logic: pure timing, curves, tap gating and skip rules (no Instances, no time source).
-- The client module HatchSequence.luau only draws; everything testable lives here
-- (tools/verify_hatch_sequence.py). Presentation only: the server-committed outcome is never read or changed.
local RevealSkip = require(script.Parent.RevealSkip)
local T = {}

-- Seconds. Full motion: ~3 s rattle/crack build-up, burst, dino reveal, then wait for a tap.
T.Motion = {build = 3.0, burst = .6, settle = .8, tapGate = .5}
-- Reduced Motion (Theme.MotionEnabled false): no shake/zoom/particles, a short fade, same tap flow.
T.Reduced = {build = 0, burst = 0, settle = .45, tapGate = .15}
T.MaxParticles = 28
T.OrbitMax = 12 -- twinkling sparkles orbiting the dinosaur after the reveal
T.FireworkMax = 24 -- Legendary gold fireworks: 3 bursts of 8
T.RainMax = 14 -- Shiny gold sparkle rain
T.CrackBeats = {.21, .46, .71} -- fractions of the build-up where the three crack stages start (HatchPresentation)
T.EggClock = 3.2 -- HatchPresentation.update() time at the end of the build-up

-- Legendary holds the reveal longer (+.5 s settle) before the tap prompt; the build-up stays about 3 s.
function T.durations(motion: boolean, rarity: number?)
    local d = if motion then T.Motion else T.Reduced
    local settle = d.settle + (if motion and (rarity or 1) >= 5 then .5 else 0)
    return {build = d.build, burst = d.burst, settle = settle, revealAt = d.build, readyAt = d.build + d.burst + settle,
        tapGate = d.tapGate}
end

function T.phase(durs, t: number): string
    if t < durs.build then return "build" end
    if t < durs.build + durs.burst then return "burst" end
    if t < durs.readyAt then return "settle" end
    return "ready"
end

-- State machine: {t, fastForwarded, done}. All transitions are pure.
function T.new(motion: boolean, rarity: number?)
    return {t = 0, durs = T.durations(motion, rarity), fastForwarded = false, done = false, motion = motion}
end
function T.step(state, dt: number)
    if state.done then return state end
    state.t += math.max(0, dt)
    return state
end
-- "advance" (next egg / done), "fastforward" (jump the build-up to the burst) or "ignore".
function T.tapAction(state): string
    if state.done then return "ignore" end
    local phase = T.phase(state.durs, state.t)
    if phase == "ready" then return "advance" end
    if phase == "build" and not state.fastForwarded and state.t >= state.durs.tapGate then return "fastforward" end
    return "ignore"
end
function T.tap(state): string
    local action = T.tapAction(state)
    if action == "fastforward" then
        state.t, state.fastForwarded = state.durs.build, true
    elseif action == "advance" then
        state.done = true
    end
    return action
end
-- Skip all: fast-forward a running build-up; an already revealed egg moves on at once.
function T.skipAll(state): string
    if state.done then return "ignore" end
    local phase = T.phase(state.durs, state.t)
    if phase == "build" then
        state.t, state.fastForwarded = state.durs.build, true
        return "fastforward"
    elseif phase == "ready" then
        state.done = true
        return "advance"
    end
    return "ignore"
end

-- Reveal skipping: the player's chosen rarities, or every rarity after "Skip all". Shiny, BIG, event
-- mutations and Rainbow/Astra are never skipped (RevealSkip.isNotable).
function T.shouldSkip(selection: any, rarity: number, outcome: any, skipAll: boolean): boolean
    return RevealSkip.shouldSkip(if skipAll then RevealSkip.Rarities else selection, rarity, outcome)
end

-- Tap hint copy. remaining = eggs still to open after this one.
function T.hint(remaining: number): string
    if remaining > 0 then return "Tap for next egg (" .. tostring(remaining) .. " left)" end
    return "Done"
end
-- Remaining eggs after this one; `more` is whether another egg can be claimed right now.
function T.remaining(more: boolean, active: number, waiting: number): number
    if not more then return 0 end
    return math.max(1, math.floor(active + waiting))
end

-- Curves (p = 0..1 progress of the build-up).
local function clamp01(x: number): number return math.clamp(x, 0, 1) end
function T.intensity(p: number): number return clamp01(p) ^ 2.2 end -- rattle gets stronger, eased in
function T.zoom(p: number): number return 1 + .24 * clamp01(p) ^ 1.7 end -- egg push-in
function T.cameraZoom(p: number): number return 1 + .045 * clamp01(p) ^ 1.7 end -- whole panel, slight
function T.glow(p: number): number return clamp01((p - .12) / .88) ^ 1.4 end -- light leaking from the cracks
-- Rattle offsets: rotation (degrees), position (virtual px). Bounded by 12 deg / 8 px at intensity 1.
function T.rattle(t: number, intensity: number): (number, number, number)
    local rot = (math.sin(t * 38) * 5.2 + math.sin(t * 61 + 1.3) * 2.6) * intensity
    local dx = math.sin(t * 47 + .7) * 5 * intensity
    local dy = math.cos(t * 53) * 3 * intensity
    return rot, dx, dy
end
-- Camera/UI shake: smaller than the egg's, +-3 px at full intensity.
function T.shakeOffset(t: number, intensity: number): (number, number)
    return math.sin(t * 71 + .4) * 2.4 * intensity, math.cos(t * 83) * 1.8 * intensity
end
-- Ease-out with overshoot for the dinosaur: from .25 to 1 with ~7% overshoot, settles at exactly 1.
function T.revealScale(p: number): number
    local x = clamp01(p)
    if x >= 1 then return 1 end
    local c1 = 1.4
    local c3 = c1 + 1
    local back = 1 + c3 * (x - 1) ^ 3 + c1 * (x - 1) ^ 2
    return .25 + .75 * back
end
function T.easeOut(p: number): number
    local x = 1 - clamp01(p)
    return 1 - x * x * x
end

-- Particles scale with rarity (1..5); Shiny and BIG add more; none when motion is off or the egg failed.
function T.particleCount(rarity: number, shiny: boolean, big: boolean, motion: boolean, failed: boolean): number
    if not motion or failed then return 0 end
    local n = 8 + 4 * math.clamp(rarity, 1, 5) + (if shiny then 6 else 0) + (if big then 4 else 0)
    return math.min(T.MaxParticles, n)
end
function T.orbitCount(rarity: number, motion: boolean, failed: boolean): number
    if not motion or failed then return 0 end
    return math.min(T.OrbitMax, 4 + 2 * math.clamp(rarity, 1, 5))
end
-- Rarity escalation flags (all false without motion): shockwave Rare+, energy arcs and stronger shake Epic+, fireworks Legendary.
function T.escalation(rarity: number, motion: boolean)
    local r = math.clamp(rarity, 1, 5)
    return {shock = motion and r >= 3, arcs = motion and r >= 4, fireworks = motion and r >= 5,
        shakeScale = if motion and r >= 4 then 1 + .35 * (r - 3) else 1, punch = if r >= 5 then .09 elseif r >= 3 then .06 else .045}
end
-- BIG "stamp": starts 35% oversize and slams to 1 in .25 s.
function T.stamp(s: number): number
    if s < 0 or s >= .25 then return 1 end
    return 1 + .35 * (1 - s / .25) ^ 2
end
function T.burstStrength(rarity: number): number return .18 + .08 * math.clamp(rarity, 1, 5) end -- screen flash alpha

-- Odds line: base chance of one purchased egg (docs/85); FusionSelection.pct formatting.
function T.pct(p: number): string
    local s = string.format("%.2f", p)
    if string.find(s, ".", 1, true) then s = string.gsub(s, "0+$", "") s = string.gsub(s, "%.$", "") end
    return s .. "%"
end
function T.speciesPct(weights: any, speciesId: string): number?
    if typeof(weights) ~= "table" then return nil end
    local total, mine = 0, 0
    for _, row in weights do
        total += row.weight
        if row.speciesId == speciesId then mine = row.weight end
    end
    if total <= 0 or mine <= 0 then return nil end
    return 100 * mine / total
end
function T.oddsLine(rarityName: string, p: number?, pctFormat: ((number) -> string)?): string
    if p == nil then return rarityName end
    return rarityName .. " \u{2022} " .. (pctFormat or T.pct)(p) .. " of eggs"
end

-- Sound cues in time order: {t = seconds, name = Sfx name}. The "reveal" cue name depends on rarity.
T.RattleBeats = {.1, .8, 1.4, 1.9, 2.35, 2.7, 2.9}
function T.cues(durs, rarity: number, failed: boolean, revealName: string)
    local cues = {}
    local build = durs.build
    if build > 0 then
        for _, b in T.RattleBeats do table.insert(cues, {t = build * b / 3, name = "hatch_rattle"}) end
        for _, f in T.CrackBeats do table.insert(cues, {t = build * f, name = "hatch_crack_stage"}) end
    end
    table.insert(cues, {t = build, name = "hatch_burst"})
    if not failed then table.insert(cues, {t = build + .12, name = revealName}) end
    table.sort(cues, function(a, b) return a.t < b.t end)
    return cues
end

return T
