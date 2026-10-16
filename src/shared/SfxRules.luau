--!strict
-- BD-339/341/342: pure sound rules (no Roblox services): voice limiter, priority ducking, hatch sound stack, dedupe and
-- deterministic pitch jitter. Sfx.luau applies them; asset ids are NOT touched here. OFFLINE only: nobody has listened.
local R = {}

-- Higher number = more important (docs/110 section 2): reveal > fusion > level > run end > shop > weather > pickup > click.
R.Priority = {
    hatch_reveal_legendary = 100, hatch_reveal_epic = 100, hatch_reveal_rare = 100, hatch_reveal_uncommon = 100,
    hatch_reveal_common = 100, hatch_legendary = 100, hatch_rare = 100, hatch_common = 100, shiny_bang = 95, big_thud = 95,
    fusion_reveal = 90, level_up = 80, run_end = 70, shop_buy = 50, shop_refresh = 50, hatch_burst = 45,
    weather_start = 40, hatch_crack = 30, hatch_crack_stage = 30, hatch_rattle = 30, run_start = 30,
    pickup = 20, pickup_hi = 20, pickup_lo = 20, ui_click = 10,
}
R.DefaultPriority = 30
R.MaxVoices = 2
R.ImportantPriority = 70 -- may replace a quieter/older cue instead of being dropped, and ducks everything lower
R.DuckFactor = .6 -- others play at 60% (ducked by 40%) while an important cue lasts
R.DefaultLen = 1 -- seconds, for cues without `len`

function R.priority(name: string): number
    return R.Priority[name] or R.DefaultPriority
end
function R.isImportant(name: string): boolean
    return R.priority(name) >= R.ImportantPriority
end

-- active = list of {name, endsAt, startedAt, volume}. Returns "play" | "drop" | "replace", and the index to replace.
function R.limit(active: {any}, name: string, now: number): (string, number?)
    local live = {}
    for i, v in active do if v.endsAt > now then table.insert(live, i) end end
    if #live < R.MaxVoices then return "play", nil end
    if not R.isImportant(name) then return "drop", nil end
    local p = R.priority(name)
    local worst: number? = nil
    for _, i in live do
        local v = active[i]
        local better = worst == nil
        if not better then
            local w = active[worst :: number]
            local pv, pw = R.priority(v.name), R.priority(w.name)
            better = pv < pw or (pv == pw and (v.volume < w.volume or (v.volume == w.volume and v.startedAt < w.startedAt)))
        end
        if better then worst = i end
    end
    if worst ~= nil and R.priority(active[worst].name) <= p then return "replace", worst end
    return "drop", nil
end

-- Volume multiplier for an already playing cue while `incoming` plays (1 = untouched).
function R.duck(incoming: string, other: string): number
    if R.isImportant(incoming) and R.priority(other) < R.priority(incoming) then return R.DuckFactor end
    return 1
end

-- BD-342: the same cue twice inside its window is one cue (a level-up that coincides with a nest open).
R.DedupeWindow = {level_up = .8}
function R.deduped(name: string, last: number?, now: number): boolean
    local w = R.DedupeWindow[name]
    return w ~= nil and last ~= nil and now - last < w
end

-- Aliases reuse REGISTERED cues (no new asset): a soft crystal reward tick behind a cooldown.
R.Aliases = {crystal_reward = {cue = "pickup_hi", volume = .6, cooldown = 1.5}, egg_found = {cue = "pickup_hi", volume = .45, cooldown = 2}} -- egg_found: BD-367 soft "you found an egg" tick

-- Pitch jitter +-4%, deterministic per cue name and repeat count; reveal stings keep their pitch (rarity escalation).
R.Jitter = .04
R.JitterNames = {
    pickup = true, pickup_hi = true, pickup_lo = true, ui_click = true, hatch_crack = true, hatch_crack_stage = true,
    shop_buy = true, shop_refresh = true, level_up = true, run_end = true,
}
function R.jitter(name: string, n: number): number
    if not R.JitterNames[name] then return 1 end
    local h = 5381
    for i = 1, #name do h = (h * 33 + string.byte(name, i)) % 2147483647 end
    h = (h * 1103515245 + (n + 1) * 12345 + 7919) % 2147483647
    h = (h * 1103515245 + 12345) % 2147483647
    return 1 + ((h % 2001) / 1000 - 1) * R.Jitter
end

-- BD-437 reveal ladder: Epic and Legendary stack a second REGISTERED cue under the main sting (no new asset). volume and rate are
-- multipliers on that cue's registered numbers; delay is seconds after the main sting. Common..Rare stay a single sting.
R.RevealLayers = {
    hatch_reveal_epic = {{cue = "hatch_reveal_rare", volume = .55, rate = 1, delay = .16}},
    hatch_reveal_legendary = {{cue = "fusion_reveal", volume = .6, rate = 1, delay = .2}},
}
function R.layers(revealName: string): {any}
    return R.RevealLayers[revealName] or {}
end

-- BD-341 hatch stack per species rarity 1..5: stage cracks kept, chime on the opening. Escalates with rarity.
R.HatchStack = {
    {stages = 1, chime = false}, {stages = 2, chime = false}, {stages = 3, chime = true}, {stages = 3, chime = true}, {stages = 3, chime = true},
}
R.HatchStagger = .3 -- minimum seconds between audible hatch cues (0.25-0.4 s)
function R.hatchStack(rarity: number?): any
    return R.HatchStack[math.clamp(math.floor(rarity or 1), 1, #R.HatchStack)]
end
-- Takes HatchTimeline cues ({t, name}, any order); drops silent/redundant hatch_* cues, thins stage cracks per rarity and
-- staggers hatch_* cues so crack, stage and reveal never start together. Non-hatch cues (paint) pass through unchanged.
function R.hatchCues(cues: {any}, rarity: number?): {any}
    local sorted = table.clone(cues)
    table.sort(sorted, function(a, b) return a.t < b.t end)
    local stack = R.hatchStack(rarity)
    local out, stages, lastT = {}, 0, -1e9
    for _, c in sorted do
        local n = c.name
        if n == "hatch_rattle" then continue end
        if n == "hatch_crack_stage" then
            stages += 1
            if stages > stack.stages then continue end
        end
        if string.sub(n, 1, 6) == "hatch_" then
            local t = math.max(c.t, lastT + R.HatchStagger)
            if n == "hatch_burst" and t - c.t > R.HatchStagger then continue end
            lastT = t
            table.insert(out, {t = t, name = n})
        else
            table.insert(out, c)
        end
    end
    table.sort(out, function(a, b) return a.t < b.t end)
    return out
end
return R
