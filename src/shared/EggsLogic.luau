--!strict
-- Combined Eggs screen logic (owner 2026-10-15): pure state machines, no Instances, no time source.
-- Nest slots row, the single "Next egg" card and the auto-open (per rarity) rules.
-- The auto-open choice is a UI preference: the server never trusts it and still credits every egg
-- through the normal claim path. src/client/EggsScreen.luau only draws; tools/verify_eggs_screen.py tests this.
local RevealSkip = require(script.Parent.RevealSkip)
local Copy = require(script.Parent.FtueP1)
local L = {}

-- Five nest slots (capacity), index = queue order. nests are NestQueue.project() results.
-- state: "ready" | "opening" (the incubating one, shows the timer) | "queued" | "empty".
function L.nestSlots(nests: {any}, capacity: number, now: number)
    local slots = {}
    for i = 1, capacity do
        local nest = nests[i]
        if not nest then
            slots[i] = {state = "empty", text = "Empty"}
        elseif nest.state == "ready" then
            slots[i] = {state = "ready", text = "READY", id = nest.id}
        elseif nest.state == "incubating" then
            slots[i] = {state = "opening", remaining = math.max(0, (nest.readyAt or now) - now), id = nest.id}
        else
            slots[i] = {state = "queued", text = "Queued", id = nest.id}
        end
    end
    return slots
end

function L.nestHeader(nests: {any}, capacity: number): string
    return string.format("Nests %d/%d", math.min(#nests, capacity), capacity)
end

-- BD-259 / BD-369: the "Eggs waiting" number = EVERY unopened egg, the one on the card included (a READY card must never sit
-- beside "0"): the eggs in the line (ActiveChestCount) plus the banked ones (QueuedEggsWaiting). 31 run eggs read 31.
function L.waitingTotal(active: number, banked: number, hasCard: boolean): number
    return math.max(0, math.floor(banked)) + math.max(0, math.floor(active))
end

-- Single next-egg card. entry = ChestQueueJson entry or nil; waiting = QueuedEggsWaiting.
-- kind: "empty" (nothing waiting), "banked" (eggs not yet in the line), "growing", "ready".
function L.card(entry: any, nextId: string?, readyAt: number, now: number, waiting: number)
    if nextId == nil or nextId == "" then
        return {kind = if waiting > 0 then "banked" else "empty", canOpen = false, waiting = waiting}
    end
    local at = if entry and typeof(entry.readyAt) == "number" then entry.readyAt else readyAt
    local remaining = math.max(0, at - now)
    return {kind = if remaining <= 0 then "ready" else "growing", canOpen = remaining <= 0, remaining = remaining, waiting = waiting}
end

function L.cardCopy(card: any): (string, string)
    if card.kind == "ready" then return "READY!", "OPEN" end
    if card.kind == "growing" then return "Growing...", "GROWING" end
    if card.kind == "banked" then return "Eggs are on the way", "WAIT" end
    return Copy.EmptyStatus, Copy.EmptyButton
end

-- Auto-open per rarity. selection = the stored rarity list (RevealSkip format).
-- When requiresPass and the player lacks the pass: rows are locked and the setting is ignored.
function L.locked(requiresPass: boolean, ownsPass: boolean): boolean
    return requiresPass == true and ownsPass ~= true
end
function L.effective(selection: any, requiresPass: boolean, ownsPass: boolean): {number}
    if L.locked(requiresPass, ownsPass) then return {} end
    return RevealSkip.normalize(selection)
end
-- Never auto-opens Shiny, BIG, event mutations, Rainbow/Astra (RevealSkip.isNotable). openAll = the optional
-- "Open all" convenience (every rarity, same never-skip rules).
function L.shouldAutoOpen(selection: any, requiresPass: boolean, ownsPass: boolean, rarity: number, outcome: any, openAll: boolean): boolean
    local list = if openAll and not L.locked(requiresPass, ownsPass) then RevealSkip.Rarities else L.effective(selection, requiresPass, ownsPass)
    return RevealSkip.shouldSkip(list, rarity, outcome)
end

-- "Auto-opened" summary lines: a header, then counts per rarity with the best find first.
function L.summaryLines(summary: any): {string}
    local lines = {string.format("Auto-opened: %d", summary.total)}
    local parts = {}
    for rarity = #RevealSkip.Names, 1, -1 do
        local count = summary.byRarity[rarity] or 0
        if count > 0 then table.insert(parts, string.format("%d %s", count, RevealSkip.Names[rarity])) end
    end
    if summary.failed > 0 then table.insert(parts, string.format("%d cracked", summary.failed)) end
    if #parts > 0 then table.insert(lines, table.concat(parts, "  |  ")) end
    return lines
end

-- Run end: the player is never forced into hatching; the run summary may offer "Open eggs".
function L.afterRun(): string
    return "results"
end
-- After one reveal (BD-170): Next egg ALWAYS stays inside the opening sequence while eggs remain; only the end of the
-- batch (or the player closing the screen) goes back to the Eggs screen. skipAll no longer changes that.
function L.afterReveal(skipAll: boolean, remaining: number): string
    if remaining > 0 then return "continue" end
    return "eggs"
end

return L
