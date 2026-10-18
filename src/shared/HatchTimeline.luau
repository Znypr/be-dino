--!strict
-- Hatch sequence logic: pure timing, curves, tap gating and skip rules (no Instances, no time source).
-- The client module HatchSequence.luau only draws; everything testable lives here
-- (tools/verify_hatch_sequence.py). Presentation only: the server-committed outcome is never read or changed.
local RevealSkip = require(script.Parent.RevealSkip)
local V2 = require(script.Parent.HatchV2Plan) -- BD-397 (docs/118): the v2 beat sheet; only used when a state is created with v2 = true
local T = {}

-- Seconds. Full motion: ~3.6 s build-up (two paint-bucket splashes, then rattle/crack), burst, dino reveal, then wait for a tap.
-- BD-220: the egg starts colourless but already shows its condition (BD-223); the left bucket pours the primary colour, the right
-- bucket the secondary colour, then the pattern fades in on the egg with its own small label. Rattle and cracks follow.
T.Motion = {build = 3.6, burst = .6, settle = .8, tapGate = .5}
-- Reduced Motion (Theme.MotionEnabled false): no shake/zoom/particles, a short fade, same tap flow.
T.Reduced = {build = 0, burst = 0, settle = .45, tapGate = .15}
-- A failed (Cracked) egg: same ~3 s build-up, then a SPLAT instead of a dinosaur (shell halves bounce, yolk plops into a puddle).
T.Splat = {build = 3.6, burst = .7, settle = 1.0, tapGate = .5}
T.CrumbMax = 10 -- tiny shell crumbs of the splat (pooled; they reuse the sparkle pool)
T.MaxParticles = 28
T.OrbitMax = 12 -- twinkling sparkles orbiting the dinosaur after the reveal
T.FireworkMax = 24 -- Legendary gold fireworks: 3 bursts of 8
T.RainMax = 14 -- Shiny gold sparkle rain
T.CrackBeats = {.21, .46, .71} -- fractions of the build-up where the three crack stages start (HatchPresentation)
T.EggClock = 3.2 -- HatchPresentation.update() time at the end of the build-up
T.PaintMax = 20 -- paint droplets (two buckets x 10, pooled)
-- Paint buckets (BD-171). Each bucket slides in, tilts, splashes at `impact` (fraction of its window) and leaves; both are quick.
T.Paint = {leftStart = .35, rightStart = 1.1, window = .75, impact = .6, wash = .35, patternDelay = .05, patternWash = .4}
T.WobbleClock = .5 -- egg clock while painting (below the first rattle beat and crack stage, so no cracks show yet)

-- Legendary holds the reveal longer (+.5 s settle) before the tap prompt; the build-up stays the same length.
function T.paintPlan(motion: boolean)
    if not motion then
        return {leftStart = 0, leftImpact = 0, leftEnd = 0, rightStart = 0, rightImpact = 0, rightEnd = 0, patternAt = 0, patternEnd = 0, endsAt = 0}
    end
    local p = T.Paint
    local rightEnd = p.rightStart + p.window
    local patternAt = rightEnd + p.patternDelay
    return {leftStart = p.leftStart, leftImpact = p.leftStart + p.window * p.impact, leftEnd = p.leftStart + p.window,
        rightStart = p.rightStart, rightImpact = p.rightStart + p.window * p.impact, rightEnd = rightEnd,
        patternAt = patternAt, patternEnd = patternAt + p.patternWash, endsAt = patternAt + p.patternWash}
end
-- BD-437: a slightly longer rattle before the burst of rarer eggs (anticipation). Seconds added to the build-up; none for a failed egg,
-- an unknown rarity or Reduce Motion. A 15-egg party adds well under 2 s in total (tools/verify_hatch_sequence.py).
T.Anticipation = {0, 0, .15, .3, .5}
function T.anticipation(rarity: number?): number
    if rarity == nil then return 0 end
    return T.Anticipation[math.clamp(math.floor(rarity), 1, #T.Anticipation)]
end
-- v2 (BD-397, docs/118): the longer paint beat sheet of HatchV2Plan replaces the build-up and the paint plan; burst, settle,
-- tap gate, skip rules, Reduced Motion and the failed-egg splat are unchanged.
function T.durations(motion: boolean, rarity: number?, failed: boolean?, v2: boolean?)
    local d = if not motion then T.Reduced elseif failed then T.Splat else T.Motion
    local settle = d.settle + (if motion and not failed and (rarity or 1) >= 5 then .5 else 0)
    local build = (if v2 and motion then V2.Build else d.build) + (if motion and not failed then T.anticipation(rarity) else 0)
    return {build = build, burst = d.burst, settle = settle, revealAt = build, readyAt = build + d.burst + settle,
        tapGate = d.tapGate, paint = if v2 and motion then V2.paintPlan() else T.paintPlan(motion)}
end

function T.phase(durs, t: number): string
    if t < durs.build then return "build" end
    if t < durs.build + durs.burst then return "burst" end
    if t < durs.readyAt then return "settle" end
    return "ready"
end

-- State machine: {t, idle, pending, fastForwarded, done}. All transitions are pure.
-- pending = the server result (species, colours, pattern) has not arrived yet: the egg keeps wobbling (idle grows, t holds
-- at the first bucket) so Open starts the animation at once without waiting for the network (BD-170).
function T.new(motion: boolean, rarity: number?, failed: boolean?, pending: boolean?)
    return {t = 0, idle = 0, pending = pending == true, durs = T.durations(motion, rarity, failed), fastForwarded = false, done = false, motion = motion, v2 = false}
end
-- BD-397: switch a fresh state to the v2 beat sheet (before any step). Keeps the pending hold and every rule.
function T.useV2(state, on: boolean)
    state.v2 = on == true
    state.durs = T.durations(state.motion, nil, nil, state.v2)
    return state
end
-- The result arrived: use the real timing (the build-up length never depends on rarity or failure).
function T.supply(state, rarity: number?, failed: boolean?)
    state.durs = T.durations(state.motion, rarity, failed, state.v2)
    state.pending = false
    return state
end
function T.holdAt(state): number
    return if state.motion then state.durs.paint.leftStart else 0
end
function T.step(state, dt: number)
    if state.done then return state end
    dt = math.max(0, dt)
    if state.pending then
        local room = math.max(0, T.holdAt(state) - state.t)
        state.t += math.min(dt, room)
        state.idle += dt - math.min(dt, room)
    else
        state.t += dt
    end
    return state
end
-- Visual clock for idle wobble: keeps moving while the sequence is waiting for the result.
function T.visualT(state): number return state.t + state.idle end
-- "advance" (next egg / done), "fastforward" (jump the build-up to the burst) or "ignore".
function T.tapAction(state): string
    if state.done or state.pending then return "ignore" end
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
    if state.done or state.pending then return "ignore" end
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

-- Reveal skipping: the player's chosen rarities, or every rarity but Legendary after "Skip all" (BD-1057). Shiny, BIG, event
-- mutations, Rainbow/Astra and secrets are never skipped (RevealSkip.isNotable).
function T.shouldSkip(selection: any, rarity: number, outcome: any, skipAll: boolean): boolean
    return RevealSkip.shouldSkip(if skipAll then RevealSkip.OpenAllRarities else selection, rarity, outcome)
end

-- Tap hint copy. remaining = eggs still to open after this one.
function T.hint(remaining: number): string
    if remaining > 0 then return "Tap for next egg (" .. tostring(remaining) .. " left)" end
    return "Done"
end
-- BD-444 (docs/132): "Egg 3 of 15" counter over the WHOLE reveal session. `T.session` is plain module state {index, total, left, at}.
-- One session = the eggs of one hatch party (Open ... last egg / Skip the rest). Every claimed egg counts once, shown or skipped
-- quickly; the copies of one egg never count. The session ends only through T.batchReset (end of party) or after IdleReset seconds.
T.IdleReset = 90
function T.newBatch() return {left = nil, index = 0, total = 0, at = nil} end
T.session = T.newBatch()
function T.batchReset(batch: any) batch.left, batch.index, batch.total, batch.at = nil, 0, 0, nil end
-- A claimed egg arrived with `remaining` eggs still to come. `now` (seconds, optional) only drops a forgotten old session.
function T.batchStep(batch: any, remaining: number, now: number?): (number, number)
    if now and batch.at and now - batch.at > T.IdleReset then T.batchReset(batch) end
    batch.index += 1
    batch.total = math.max(batch.total, batch.index + remaining)
    batch.left, batch.at = remaining, now
    return batch.index, batch.total
end
-- The egg counts arrive a moment after the result (BD-380): re-count the eggs left, keep the egg number.
function T.batchRefine(batch: any, remaining: number): (number, number)
    batch.left = remaining
    batch.total = math.max(batch.index + remaining, batch.index)
    return batch.index, batch.total
end
function T.counterText(index: number, total: number): string
    if total < 2 then return "" end
    return "Egg " .. tostring(index) .. " of " .. tostring(total)
end
-- "Skip all" button copy (kid words, docs/72).
T.SkipText = "Skip the rest"

-- Remaining eggs after this one; `more` is whether another egg can be claimed right now. `buffered` (BD-380) = eggs of the
-- current hatch page: already credited and out of the queue, so active and waiting do not count them but they are still to open.
function T.remaining(more: boolean, active: number, waiting: number, buffered: number?): number
    if not more then return 0 end
    return math.max(1, math.floor(active + waiting + (buffered or 0)))
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
function T.revealScale(p: number, rarity: number?): number
    local x = clamp01(p)
    if x >= 1 then return 1 end
    local c1 = 1.0 + .1 * (math.clamp(rarity or 1, 1, 5) - 1) -- BD-437: rarer dinos pop a little further past 1 (peak below 1.07). BD-327: peak about 1.03 (was 1.1): the dino no longer crosses the panel edge at the pop
    local c3 = c1 + 1
    local back = 1 + c3 * (x - 1) ^ 3 + c1 * (x - 1) ^ 2
    return .25 + .75 * back
end
function T.easeOut(p: number): number
    local x = 1 - clamp01(p)
    return 1 - x * x * x
end

-- Rattle/crack progress 0..1: starts once both paint buckets are done and runs to the burst.
function T.buildProgress(durs, t: number): number
    local from = durs.paint.endsAt
    if durs.build <= from then return 1 end
    return clamp01((t - from) / (durs.build - from))
end
-- Time (seconds) of a point given as a fraction of the rattle/crack part of the build-up.
function T.crackTime(durs, fraction: number): number
    return durs.paint.endsAt + clamp01(fraction) * math.max(0, durs.build - durs.paint.endsAt)
end
-- HatchPresentation.update() clock: a slow wobble while painting, then the three crack stages across the rest of the build-up.
function T.eggClock(durs, t: number): number
    if durs.build <= 0 then return T.EggClock end
    local from = durs.paint.endsAt
    if t < from then return T.WobbleClock * clamp01(t / math.max(from, 1e-6)) end
    return T.WobbleClock + (T.EggClock - T.WobbleClock) * T.buildProgress(durs, t)
end

-- Paint buckets (BD-171/220). side: -1 left bucket (primary colour), +1 right bucket (secondary colour). k = 0..1 over the window.
-- Returns x offset from the egg centre (px), y offset (px), rotation (degrees, positive = clockwise) and alpha 0..1.
T.BucketX = 265 -- hover distance from the egg centre; each colour chip sits right under its bucket (HatchFxPlan.Chips)
function T.bucketPose(k: number, side: number): (number, number, number, number)
    k = clamp01(k)
    local arrive = T.easeOut(k / .35)
    local leave = clamp01((k - .8) / .2)
    local tilt = clamp01((k - .3) / .3)
    local back = clamp01((k - .68) / .17)
    local x = side * (T.BucketX + 120 * (1 - arrive) + 120 * leave * leave)
    local y = -78 + 10 * math.sin(k * math.pi) - 14 * tilt
    local rot = -side * 64 * tilt * (1 - back)
    return x, y, rot, if k <= 0 then 0 else 1 - leave
end
-- Where each bucket is in its window at time t, and how far its colour has washed over the egg (0..1).
function T.paintState(durs, t: number)
    local p = durs.paint
    local window = if p.endsAt > 0 then (p.window or T.Paint.window) else 0 -- v2 plans carry their own window / wash lengths
    local wash, patternWash = p.wash or T.Paint.wash, p.patternWash or T.Paint.patternWash
    local function bucket(start: number, impactAt: number)
        if window <= 0 then return {k = 1, impacted = true, wash = 1, sinceImpact = 99, since = 99} end
        local since = t - impactAt
        return {k = clamp01((t - start) / window), impacted = since >= 0, wash = if since <= 0 then 0 else T.easeOut(since / wash), sinceImpact = since, since = t - start}
    end
    local pattern = if window <= 0 then 1 elseif t <= p.patternAt then 0 else T.easeOut((t - p.patternAt) / patternWash)
    return {left = bucket(p.leftStart, p.leftImpact), right = bucket(p.rightStart, p.rightImpact), pattern = pattern,
        patternShown = window <= 0 or t >= p.patternAt}
end
-- Splash ring: s = seconds since the bucket hit the egg. Returns scale and transparency (1 = invisible).
function T.splash(s: number): (number, number)
    if s < 0 then return 0, 1 end
    local k = clamp01(s / .5)
    return .35 + 1.7 * T.easeOut(k), k
end
-- Paint droplet i of n, s seconds after impact, thrown up and out, leaning toward the bucket's side (-1 left, +1 right).
-- Returns dx, dy (px from the splash point) and transparency (1 = gone).
function T.drop(i: number, n: number, s: number, side: number): (number, number, number)
    if s < 0 or s >= .7 then return 0, 0, 1 end
    local a = (-.1 - .8 * ((i - 1) / math.max(1, n - 1))) * math.pi -- fan over the upper half
    local speed = 110 + (i * 37) % 90
    return math.cos(a) * speed * s + side * 50 * s, math.sin(a) * speed * s + 380 * s * s, clamp01((s - .3) / .4)
end

-- Trait rarity tiers for the paint reveal. Chance = percent of eggs; PROVISIONAL cut-offs, tuned so Cream/Blue are Common and Black is Mythic.
T.TierNames = {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"}
T.TierFloors = {25, 10, 2, .3, .03, 0}
function T.tier(pct: number?): number
    if pct == nil then return 1 end
    for i, floor in T.TierFloors do if pct >= floor then return i end end
    return #T.TierNames
end
-- colors = Config.EggColors rows {id, name, weight}; genes = {primaryColorId, secondaryColorId}. Returns nil without a known colour.
-- BD-220: ONE colour per reveal (one chip per bucket). which = "secondary" for the right bucket; a one-colour egg shows its
-- primary colour on both chips.
function T.colorReveal(colors: any, genes: any, which: string?)
    if typeof(colors) ~= "table" or typeof(genes) ~= "table" then return nil end
    local total = 0
    for _, row in colors do total += row.weight end
    local function find(id: any)
        for _, row in colors do if row.id == id then return row end end
        return nil
    end
    local a = find(genes.primaryColorId)
    if not a or total <= 0 then return nil end
    local row = if which == "secondary" then (find(genes.secondaryColorId) or a) else a
    local pct = 100 * row.weight / total
    -- BD-1036: a colour row that declares its rarity shows exactly that tier (the equal-split ladder puts Pink and Teal at 1.6%, which
    -- the percent cut-offs below would call Epic); rows without a rarity fall back to the cut-offs.
    local tier = (if type(row.rarity) == "string" then table.find(T.TierNames, row.rarity) else nil) or T.tier(pct)
    -- BD-1069: `rgb` is the colour's OWN palette rgb (EggColors), never the shell tint after blending or Dirty: the chip swatch and the paint bucket use exactly it.
    return {name = row.name, pct = pct, tier = tier, tierName = T.TierNames[tier], rgb = row.rgb, id = row.id}
end
-- BD-1069: the exact rgb a reveal names, as 0..255 numbers; nil when the reveal carries none (the caller keeps its fallback colour).
function T.revealRgb(reveal: any): {number}?
    if typeof(reveal) ~= "table" or typeof(reveal.rgb) ~= "table" then return nil end
    local rgb = reveal.rgb
    if type(rgb[1]) ~= "number" or type(rgb[2]) ~= "number" or type(rgb[3]) ~= "number" then return nil end
    return {rgb[1], rgb[2], rgb[3]}
end
-- BD-1073: why "Skip the rest" stops on this egg, for the reveal card (the egg's own Rainbow / Astra look is gone once it hatched, and Shiny / BIG /
-- event dinosaurs always stop it too). info = {conditionId, shiny, big, mutationName, failed}. Returns the short title, or nil when nothing makes it stop.
T.StopLine = "Skip stops here"
function T.stopReason(info: any): string?
    if typeof(info) ~= "table" or info.failed == true then return nil end
    if info.conditionId == "rainbow" then return "Rainbow egg!" end
    if info.conditionId == "astra" then return "Astra egg!" end
    if info.shiny == true then return "Shiny!" end
    if info.big == true then return "BIG!" end
    if type(info.mutationName) == "string" and info.mutationName ~= "" then return info.mutationName .. "!" end
    return nil
end
-- patterns = ordered pattern ids (uniform odds); nameOf(id) -> display name. The blank pattern is "Plain" (Common).
function T.patternReveal(patterns: any, patternId: string?, nameOf: (string?) -> string)
    local count = if typeof(patterns) == "table" then #patterns else 0
    if patternId == nil or patternId == "" or string.find(patternId, "blank", 1, true) then
        local blank = if typeof(patterns) == "table" and typeof((patterns :: any).info) == "table" and patternId then (patterns :: any).info[patternId] else nil
        return {name = "Plain", pct = if blank then blank.pct else 100, tier = 1, tierName = T.TierNames[1], plain = true}
    end
    -- BD-1033: the ordered id list may carry `.info[id] = {name, rarity, pct}` (EggGenetics.Patterns): real chance and the declared
    -- tier. Without it (older callers, harnesses) the pattern is treated as one of `count` equally likely ones.
    local info = if typeof(patterns) == "table" and typeof((patterns :: any).info) == "table" then (patterns :: any).info[patternId] else nil
    local pct = if info then info.pct elseif count > 0 then 100 / count else nil
    local tier = (if info then table.find(T.TierNames, info.rarity) else nil) or T.tier(pct)
    return {name = nameOf(patternId), pct = pct, tier = tier, tierName = T.TierNames[tier], plain = false}
end
function T.paintLine(reveal: any): string
    return reveal.name .. " \u{2022} " .. reveal.tierName
end
-- Final reveal card detail line: primary colour, pattern and (shown once, BD-220) the colour growth bonus.
function T.detailLine(colorReveal: any, patternReveal: any, bonusText: string?): string
    if not colorReveal or not patternReveal then return "" end
    local s = colorReveal.name .. " \u{2022} " .. patternReveal.name
    if bonusText and bonusText ~= "" then s ..= " \u{2022} " .. bonusText end
    return s
end
-- Pattern label on the egg after the buckets (BD-220), one short line.
function T.patternLabel(reveal: any): string
    if not reveal then return "" end
    return if reveal.plain then "No pattern" else reveal.name
end

-- BD-223: condition chip shown from the first frame of the hatch. nil for a Normal egg. Cracked adds its hatch chance.
function T.hatchHint(hatchChance: number?): string
    if hatchChance == nil or hatchChance <= 0 or hatchChance >= 1 then return "" end
    local n = 1 / hatchChance
    local r = math.floor(n + .5)
    if r >= 2 and math.abs(n - r) < .02 then return "hatches 1 in " .. r end
    return "hatches " .. T.pct(100 * hatchChance)
end
function T.conditionChip(condition: any): string?
    if typeof(condition) ~= "table" or type(condition.name) ~= "string" or condition.id == nil or condition.id == "normal" then return nil end
    local hint = T.hatchHint(condition.hatchChance)
    return condition.name .. (if hint ~= "" then " \u{2022} " .. hint else "")
end
-- Condition id of the egg about to open, from the client queue (ChestQueueJson), before the server answer arrives.
function T.queueCondition(queue: any, nextId: string?): string?
    if typeof(queue) ~= "table" then return nil end
    local entry = nil
    for _, item in queue do if typeof(item) == "table" and item.id == nextId then entry = item break end end
    entry = entry or queue[1]
    if typeof(entry) ~= "table" or typeof(entry.genes) ~= "table" or typeof(entry.genes.conditionId) ~= "string" then return nil end
    return entry.genes.conditionId
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
T.Punch = {.035, .05, .065, .085, .11} -- BD-437: camera push-in released at the burst, one step per rarity (was .045 / .06 / .09)
-- Rarity escalation flags (all false without motion): shockwave Rare+, energy arcs and stronger shake Epic+, fireworks Legendary.
function T.escalation(rarity: number, motion: boolean)
    local r = math.clamp(rarity, 1, 5)
    return {shock = motion and r >= 3, arcs = motion and r >= 4, fireworks = motion and r >= 5,
        shakeScale = if motion and r >= 4 then 1 + .35 * (r - 3) else 1, punch = T.Punch[r]}
end
-- BIG "stamp": starts 35% oversize and slams to 1 in .25 s.
function T.stamp(s: number): number
    if s < 0 or s >= .25 then return 1 end
    return 1 + .12 * (1 - s / .25) ^ 2 -- BD-327b: was .35, a BIG dino crossed the top edge of the panel at the stamp (seen in Studio)
end
function T.burstStrength(rarity: number): number return .18 + .08 * math.clamp(rarity, 1, 5) end -- screen flash alpha

-- Failed-egg splat curves. s = seconds since the burst. Pure and bounded (tools/verify_hatch_sequence.py).
T.SplatDrop = .22 -- the yolk reaches the puddle this long after the burst
-- Vertical offset of a bouncing body: launched with v0 (negative = up), gravity g, resting `floor` px below the start.
function T.bounceY(s: number, v0: number, g: number, floor: number, e: number): number
    if s <= 0 then return 0 end
    local pos, vel = 0, v0
    for _ = 1, 4 do
        local fall = (-vel + math.sqrt(vel * vel + 2 * g * (floor - pos))) / g
        if s < fall then return pos + vel * s + .5 * g * s * s end
        s -= fall
        vel = -(vel + g * fall) * e
        pos = floor
        if vel > -8 then return floor end
        local up = -2 * vel / g
        if s < up then return floor + vel * s + .5 * g * s * s end
        s -= up
    end
    return floor
end
-- One shell half (side -1 left, +1 right): dx, dy (px from the egg centre), rotation (deg). Pops up, tumbles, falls, bounces.
function T.shell(s: number, side: number, fall: number): (number, number, number)
    local dx = side * (22 + 128 * T.easeOut(s / .8))
    return dx, T.bounceY(s, -170, 900, fall, .38), side * 400 * T.easeOut(s / .85)
end
-- Yolk: dy above its resting place, squash and stretch scales. Falls stretched, lands squashed, then wobbles to rest.
function T.yolk(s: number): (number, number, number)
    local d = T.SplatDrop
    if s < d then
        local k = math.max(0, s / d)
        return -70 * (1 - k * k), .86, 1.2
    end
    local u = s - d
    local amp = math.exp(-5 * u)
    local osc = math.cos(16 * u)
    local hop = if u < .28 then -20 * math.sin(math.pi * u / .28) else 0
    return hop, 1 + .55 * amp * osc, 1 - .42 * amp * osc
end
local function backOut(x: number): number
    x = clamp01(x)
    return math.max(0, 1 + 2.2 * (x - 1) ^ 3 + 1.2 * (x - 1) ^ 2)
end
-- Egg-white puddle spreading from the landing: width and height scale (0 before the landing, wobbles at the end).
function T.puddle(s: number): (number, number)
    local k = (s - T.SplatDrop) / .5
    if k <= 0 then return 0, 0 end
    local wob = 1 + .025 * math.sin((s - T.SplatDrop) * 11) * math.exp(-(s - T.SplatDrop) * 1.6)
    return backOut(k) * wob, backOut(k - .1) * (2 - wob)
end
-- Drip i (1..2): nil while inactive, else dy (px) and alpha. Starts after the puddle has spread.
function T.drip(s: number, i: number): (number?, number?)
    local k = (s - T.SplatDrop - .5 - (i - 1) * .3) / .6
    if k < 0 or k >= 1 then return nil, nil end
    return 44 * k * k, 1 - k ^ 1.5
end
-- Camera bump: panel scale and a small downward nudge (px), both decaying to 0.
function T.bump(s: number): (number, number)
    if s < 0 then return 1, 0 end
    local d = math.exp(-9 * s)
    return 1 + .032 * d, 5 * math.exp(-8 * s) * math.cos(22 * s) * -1
end
-- Cartoon splat pulse: expanding soft ring. Returns scale and ring transparency (1 = invisible).
function T.splatPulse(s: number): (number, number)
    local k = clamp01((s - T.SplatDrop) / .45)
    return .3 + 2.2 * T.easeOut(k), if s < T.SplatDrop then 1 else k
end
function T.crumbCount(motion: boolean): number return if motion then T.CrumbMax else 0 end

-- Failed-egg copy (docs/72: short and friendly). The chance line is built from the real config value (Cracked hatchChance).
T.FailTitle = "Oops! Splat!"
T.FailSub = "This cracked egg did not hatch"
function T.failChance(hatchChance: number?): string
    if hatchChance == nil or hatchChance <= 0 or hatchChance >= 1 then return "" end
    local n = 1 / hatchChance
    local r = math.floor(n + .5)
    if r >= 2 and math.abs(n - r) < .02 then return "Cracked eggs hatch 1 time in " .. r end
    return "Cracked eggs hatch " .. T.pct(100 * hatchChance) .. " of the time"
end

-- Odds line: base chance of one purchased egg (docs/85); FusionSelection.pct formatting.
function T.pct(p: number): string
    local s = string.format(if p > 0 and p < 0.1 then "%.3f" else "%.2f", p) -- BD-1032: a Legendary is 0.004% of eggs, "%.2f" would show 0%
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
        -- Paint buckets reuse existing Sfx names (no new sounds): swoosh = pickup_lo, primary splash = pickup, secondary splash = pickup_hi.
        local p = durs.paint
        if p.endsAt > 0 then
            table.insert(cues, {t = p.leftStart, name = "pickup_lo"})
            table.insert(cues, {t = p.leftImpact, name = "pickup"})
            table.insert(cues, {t = p.rightStart, name = "pickup_lo"})
            table.insert(cues, {t = p.rightImpact, name = "pickup_hi"})
        end
        for _, b in T.RattleBeats do table.insert(cues, {t = T.crackTime(durs, b / 3), name = "hatch_rattle"}) end
        for _, f in T.CrackBeats do table.insert(cues, {t = T.crackTime(durs, f), name = "hatch_crack_stage"}) end
    end
    table.insert(cues, {t = build, name = "hatch_burst"})
    if not failed then table.insert(cues, {t = build + .12, name = revealName}) end
    table.sort(cues, function(a, b) return a.t < b.t end)
    return cues
end

return T
