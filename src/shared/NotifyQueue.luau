--!strict
-- BD-066 notification queue (docs/65). Pure and dependency-free: the caller passes the clock, so
-- tests drive it with fake time. Decides WHICH cards are visible; the client only draws them.
-- Rules: at most 3 visible; major 3 > warning 2 > good/info 1; same `key` merges into one card
-- with a counter; info cards at most one per 1.5 s; a repeat of an expired key within 5 s is
-- dropped for info; at most 8 waiting (lowest priority, oldest dropped); major cards wait while the
-- hatch reveal or a menu is open (`blocked`) and may bump the oldest visible info/good card.
local Q = {}

Q.MaxVisible = 3
Q.MaxWaiting = 8
Q.InfoGap = 1.5
Q.KeyGap = 5
Q.Priority = {info = 1, good = 1, warning = 2, major = 3} :: {[string]: number}
-- A card is 440 px wide: long copy is cut at a word boundary with "..." so it never runs past the card.
Q.MaxText = 30
Q.MaxBody = 44
Q.Duration = {info = 2.5, good = 3, warning = 4, major = 4.5} :: {[string]: number}

export type Card = {text: string, body: string?, kind: string, key: string?, icon: string?, tint: string?,
    amount: number?, format: string?, live: boolean?, count: number, seq: number, shownAt: number?, expiresAt: number?}

-- Merging into an existing card: counters (`amount` + `format`, e.g. "+%d Crystals") add up,
-- anything else shows the newest text with an x2, x3 badge.
local function merge(card: Card, input: any)
    card.count += 1
    local amount = card.amount
    if amount ~= nil and typeof(input.amount) == "number" then
        amount += input.amount :: number
        card.amount = amount
        card.text = string.format(card.format or "%d", amount)
    else
        card.text = input.text
    end
    card.body = input.body
end

export type State = {visible: {Card}, waiting: {Card}, keyShownAt: {[string]: number}, lastInfoAt: number,
    seq: number, stats: {shown: number, merged: number, dropped: number}}

function Q.new(): State
    return {visible = {} :: {Card}, waiting = {} :: {Card}, keyShownAt = {} :: {[string]: number},
        lastInfoAt = -math.huge, seq = 0, stats = {shown = 0, merged = 0, dropped = 0}} :: State
end

function Q.clip(value: string, max: number): string
    if #value <= max then return value end
    local cut = string.sub(value, 1, max - 3)
    local word = string.match(cut, "^(.*)%s+%S*$")
    if word and #word >= max // 2 then cut = word end
    return string.gsub(cut, "[%s%p]+$", "") .. "..."
end

local function kindOf(kind: any): string
    return if typeof(kind) == "string" and Q.Priority[kind] then kind else "info"
end

local function findKey(list: {Card}, key: string?): Card?
    if key == nil then return nil end
    for _, card in list do if card.key == key then return card end end
    return nil
end

-- Returns "queued" | "merged" | "dropped".
function Q.push(q: State, now: number, input: any): string
    if typeof(input) ~= "table" or typeof(input.text) ~= "string" or input.text == "" then return "dropped" end
    input = {text = Q.clip(input.text, Q.MaxText), body = if typeof(input.body) == "string" then Q.clip(input.body, Q.MaxBody) else nil,
        kind = input.kind, key = input.key, icon = input.icon, tint = input.tint, amount = input.amount, format = input.format, live = input.live == true}
    local kind = kindOf(input.kind)
    local key = if typeof(input.key) == "string" then input.key else nil
    local live = findKey(q.visible, key)
    if live then
        merge(live, input)
        live.expiresAt = now + Q.Duration[live.kind]
        q.stats.merged += 1
        return "merged"
    end
    local waiting = findKey(q.waiting, key)
    if waiting then
        merge(waiting, input)
        q.stats.merged += 1
        return "merged"
    end
    if key and Q.Priority[kind] == 1 and q.keyShownAt[key] and now - q.keyShownAt[key] < Q.KeyGap then
        q.stats.dropped += 1
        return "dropped"
    end
    q.seq += 1
    table.insert(q.waiting, {text = input.text, body = input.body, kind = kind, key = key, icon = input.icon,
        tint = input.tint, amount = if typeof(input.amount) == "number" then input.amount else nil,
        format = if typeof(input.format) == "string" then input.format else nil, live = input.live, count = 1, seq = q.seq})
    if #q.waiting > Q.MaxWaiting then
        local worst = 1
        for i, card in q.waiting do
            local w = q.waiting[worst]
            if Q.Priority[card.kind] < Q.Priority[w.kind] then worst = i end
        end
        local removed = table.remove(q.waiting, worst)
        q.stats.dropped += 1
        if removed and removed.seq == q.seq then return "dropped" end
    end
    return "queued"
end

local function nextWaiting(q: State, blocked: boolean): number?
    local best = nil
    for i, card in q.waiting do
        -- BD-257: a `live` major (caught in the run, e.g. a mutation egg) is never held back by an open menu: it would show late or never.
        if not (blocked and card.kind == "major" and not card.live) then
            local b = if best then q.waiting[best] else nil
            if b == nil or Q.Priority[card.kind] > Q.Priority[b.kind] then best = i end
        end
    end
    return best
end

-- Expires and promotes cards. Returns true when the visible list changed.
function Q.update(q: State, now: number, blocked: boolean?): boolean
    local changed = false
    for i = #q.visible, 1, -1 do
        if (q.visible[i].expiresAt or 0) <= now then table.remove(q.visible, i) changed = true end
    end
    while true do
        local index = nextWaiting(q, blocked == true)
        if index == nil then break end
        local card = q.waiting[index]
        local priority = Q.Priority[card.kind]
        if priority == 1 and now - q.lastInfoAt < Q.InfoGap then break end
        if #q.visible >= Q.MaxVisible then
            if card.kind ~= "major" then break end
            local bump = nil
            for i, shown in q.visible do if Q.Priority[shown.kind] == 1 then bump = i break end end
            if bump == nil then break end
            table.remove(q.visible, bump)
        end
        table.remove(q.waiting, index)
        card.shownAt, card.expiresAt = now, now + Q.Duration[card.kind]
        if priority == 1 then q.lastInfoAt = now end
        if card.key then q.keyShownAt[card.key] = now end
        table.insert(q.visible, card)
        q.stats.shown += 1
        changed = true
    end
    return changed
end

-- Tap: dismiss the newest visible card.
function Q.dismissTop(q: State): boolean
    if #q.visible == 0 then return false end
    table.remove(q.visible, #q.visible)
    return true
end

-- Hatch batches: per-egg reveals are the feedback, so one summary card at the end.
-- entries: {{rarity=number, name=string, failed=boolean?, shiny=boolean?, big=boolean?}}
function Q.hatchSummary(entries: {any}, rarityNames: {string}): any
    local hatched, failed, best = 0, 0, nil :: any
    for _, entry in entries do
        if entry.failed then failed += 1 else
            hatched += 1
            local score = (entry.rarity or 1) * 4 + (if entry.shiny then 2 else 0) + (if entry.big then 1 else 0)
            if best == nil or score > best.score then best = {score = score, entry = entry} end
        end
    end
    if #entries < 2 then return nil end
    local text = if hatched == 1 then "1 dino hatched" else string.format("%d dinos hatched", hatched)
    local body = nil
    if best then
        local e = best.entry
        local tags = (if e.shiny then "Shiny " else "") .. (if e.big then "BIG " else "")
        body = "Best: " .. tags .. (rarityNames[e.rarity or 1] or "") .. " " .. tostring(e.name)
    elseif failed > 0 then
        body = "The cracked eggs crumbled"
    end
    local rarity = if best then best.entry.rarity or 1 else 1
    return {text = text, body = body, kind = if rarity >= 4 or (best and best.entry.shiny) then "major" else "good",
        key = "hatch_summary", icon = "egg", tint = rarityNames[rarity]}
end

-- BD-1000: the title slot holds Q.MaxText (30) characters; the old "Something went wrong. Try again" was 31 and showed as "Something went wrong. Try...".
Q.GenericError = "Oops! Please try again"
-- Server status codes -> short child-friendly copy (docs/72). Unknown codes never show raw text.
Q.StatusText = {
    insufficient_crystals = "Not enough Crystals",
    not_owned = "You don't own that yet",
    already_owned = "You already have that",
    locked = "Locked for now",
    level_locked = "Reach a higher level first",
    sold_out = "Sold out! Check back soon",
    not_offered = "Not in the shop right now",
    stale_window = "Shop changed. Try again",
    window_required = "Shop changed. Try again",
    inventory_full = "Your bag is full",
    queue_full = "Hatch some eggs first",
    max_level = "Already at the top level",
    replace_confirmation_required = "Tap again to replace it",
    disabled = "Not available yet",
    random_items_unavailable = "Not available yet",
    profile_not_loaded = "Still loading. Try again",
    save_failed = "Could not save. Try again",
    lease_lost = "Please rejoin the game",
    bank_full = "Hatch eggs to make room",
    not_ready = "That nest is still incubating",
    nest_pending = "That nest is still incubating",
    next_run = "Your new dino starts next game",
    already_equipped = "Already equipped", -- BD-1000: a calm note, never an error
}
function Q.statusText(status: any): string
    return if typeof(status) == "string" and Q.StatusText[status] then Q.StatusText[status] else Q.GenericError
end

return Q
