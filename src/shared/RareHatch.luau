--!strict
-- BD-428 (owner 2026-10-16): a rare hatch is a HUGE celebration for the hatcher and a short announcement for everyone.
-- Pure rules, no Roblox services, so tests drive them with a fake clock. The SERVER decides from the settled hatch outcome
-- (ProfileRepository.publishHatch -> RareHatchService); the client only draws what it is told.
-- Rare = a Legendary species (tier 5), a Shiny, or an event mutation. A Cracked (failed) egg is never rare.
-- Announcements are rate limited: eggs of one hatcher are coalesced for Window seconds and only the BEST one is announced,
-- then that hatcher is quiet for Cooldown seconds (a 15-egg reveal takes about 75 s); the whole server has a small global cap.
local R = {}

R.LegendaryTier = 5
R.Window = 3 -- seconds: rare eggs inside one window collapse into the best one
R.Cooldown = 45 -- seconds a hatcher stays quiet after an announcement
R.GlobalMax = 4 -- announcements per GlobalWindow seconds across the whole server
R.GlobalWindow = 10
R.MaxName = 20 -- display names are cut to this many characters
R.Celebrate = table.freeze({gap = 4}) -- the hatcher's own celebrations are at least this many seconds apart (client)

-- score: higher is better. Legendary + Shiny beats Shiny beats Legendary beats a mutation alone.
function R.classify(outcome: any, speciesRarity: number?): {kind: string, score: number, shiny: boolean, legendary: boolean, mutation: boolean}?
    if type(outcome) ~= "table" or outcome.failed == true then return nil end
    local shiny = outcome.shiny == true
    local legendary = (speciesRarity or 0) >= R.LegendaryTier
    local mutation = type(outcome.eventMutationId) == "string" and outcome.eventMutationId ~= ""
    if not (shiny or legendary or mutation) then return nil end
    local score = (if legendary then 4 else 0) + (if shiny then 5 else 0) + (if mutation then 2 else 0)
    local kind = if shiny then "shiny" elseif legendary then "legendary" else "mutation"
    return {kind = kind, score = score, shiny = shiny, legendary = legendary, mutation = mutation}
end

-- Display names come from Roblox (already filtered by Roblox); still drop control characters and cut the length.
function R.cleanName(name: any): string
    local s = if type(name) == "string" then name else ""
    s = string.gsub(s, "[%c]", "")
    s = string.gsub(s, "^%s+", "")
    s = string.gsub(s, "%s+$", "")
    if #s > R.MaxName then s = string.sub(s, 1, R.MaxName) end
    if s == "" then s = "A player" end
    return s
end

-- Short kid-friendly text. speciesName is the display name ("T-Rex"). Example: "Sam hatched a Shiny T-Rex!"
function R.text(playerName: string, info: {shiny: boolean, legendary: boolean, mutation: boolean}, speciesName: string): string
    local label = if info.shiny then "Shiny " elseif info.mutation then "Mutant " elseif info.legendary then "Legendary " else ""
    return string.format("%s hatched a %s%s!", R.cleanName(playerName), label, speciesName)
end

-- Own celebration line.
function R.ownText(info: {shiny: boolean, legendary: boolean, mutation: boolean}, speciesName: string): string
    local label = if info.shiny then "Shiny " elseif info.mutation then "Mutant " elseif info.legendary then "Legendary " else ""
    return string.format("You hatched a %s%s!", label, speciesName)
end

-- Client plan: how big the celebration is for the Effects setting (full / lite / off) and Reduce Motion (calm).
-- Off and Calm keep a banner and the sound but no confetti; Lite draws fewer pieces. Counts are capped for phones.
-- BD-430 / BD-433: `pop` = how many star pops (the starPop Blender flipbook) flank the own banner: two at Full, one at Lite, none at Off or
-- Calm. The client draws them ONLY while the starPop slot holds a real upload, so an empty slot keeps exactly the banner and confetti.
R.Confetti = table.freeze({full = 36, lite = 14, off = 0})
R.Pop = table.freeze({full = 2, lite = 1, off = 0})
R.PopLife = 0.9 -- seconds one star pop plays (16 frames, played once)
R.PopSize = 64 -- px
function R.plan(effects: string, calm: boolean, kind: string): {confetti: number, banner: boolean, sound: string, pop: number}
    local n = R.Confetti[effects]
    if n == nil then n = R.Confetti.full end
    local pop = R.Pop[effects]
    if pop == nil then pop = R.Pop.full end
    if calm then n, pop = 0, 0 end
    return {confetti = n, banner = true, sound = "shiny_bang", pop = pop}
end

export type State = {
    pending: {[number]: {score: number, info: any, text: string, flushAt: number}},
    quietUntil: {[number]: number},
    seen: {[string]: boolean},
    seenCount: number,
    sent: {number},
    stats: {offered: number, announced: number, merged: number, dropped: number},
}

function R.newState(): State
    return {pending = {}, quietUntil = {}, seen = {}, seenCount = 0, sent = {}, stats = {offered = 0, announced = 0, merged = 0, dropped = 0}}
end

-- A hatcher offers a rare egg. Returns the flush time (seconds, clock) when a NEW window opened (the caller schedules flush at
-- that time), or nil when the egg merged into an open window or was dropped (duplicate egg id, hatcher is quiet).
function R.offer(state: State, userId: number, eggId: string, info: any, text: string, now: number): number?
    state.stats.offered += 1
    if state.seen[eggId] then state.stats.dropped += 1 return nil end
    if state.seenCount > 400 then state.seen = {} state.seenCount = 0 end
    state.seen[eggId] = true
    state.seenCount += 1
    local open = state.pending[userId]
    if open then
        state.stats.merged += 1
        if info.score > open.score then open.score = info.score open.info = info open.text = text end
        return nil
    end
    if (state.quietUntil[userId] or 0) > now then state.stats.dropped += 1 return nil end
    state.pending[userId] = {score = info.score, info = info, text = text, flushAt = now + R.Window}
    return now + R.Window
end

-- Close the hatcher's window. Returns {text, info} to announce, or nil (global cap, or nothing pending).
function R.flush(state: State, userId: number, now: number): {text: string, info: any}?
    local open = state.pending[userId]
    state.pending[userId] = nil
    if not open then return nil end
    local keep = {}
    for _, t in state.sent do if now - t < R.GlobalWindow then table.insert(keep, t) end end
    state.sent = keep
    if #keep >= R.GlobalMax then state.stats.dropped += 1 return nil end
    table.insert(state.sent, now)
    state.quietUntil[userId] = now + R.Cooldown
    state.stats.announced += 1
    return {text = open.text, info = open.info}
end

function R.forget(state: State, userId: number)
    state.pending[userId] = nil
    state.quietUntil[userId] = nil
end

return R
