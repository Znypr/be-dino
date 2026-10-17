--!strict
-- BD-075 (docs/66 section 18): the pure rules behind the objectives panel (client/ObjectivesPanel.luau). No Instances, services, remotes or
-- clock reads. It only turns the SERVER view (ObjectiveAction {action="view"}) into what the panel draws: which (at most 3) objectives to show,
-- the folded one-liner, the "New tasks soon" words, the claim button state and the child-friendly answers to a claim. It never computes a reward,
-- a window or a progress value: every number it shows is a field of the server view. Copy follows docs/72 (short, plain, no "5m 0s" and no "1.25x").
-- Exercised by tools/verify_objectives_panel.py.
local Rules = {}

Rules.Title = "TASKS"
Rules.MaxShown = 3 -- docs/66 s6: three active objectives in the open panel
Rules.PollSeconds = 20 -- while visible, ask the server for a fresh view this often (the limiter allows 10 requests per 10 s)
Rules.MaxName = 40 -- characters a catalogue name may have so a row fits two lines of the 300 px panel at 15 px
Rules.SecondSpeciesId = "T8" -- tutorial "Collect a second species": the one row that would double the Goals panel PLAY line (docs/66 s16)

local function whole(n: any): number
    return math.max(0, math.floor(tonumber(n) or 0))
end

-- Short -> "Hatch 3 eggs"; the client only ever shows catalogue text that came through the server view.
local function describe(row: any, group: string): any
    local goal = math.max(1, whole(row.goal))
    local progress = math.min(whole(row.progress), goal)
    local reward = if type(row.reward) == "table" then row.reward else {}
    return {
        id = row.id, name = tostring(row.name or ""), group = group, carried = row.carried == true,
        progress = progress, goal = goal, fraction = progress / goal,
        reward = {crystals = whole(reward.crystals), xp = whole(reward.xp)},
        claimable = row.claimed ~= true and (row.done == true or progress >= goal),
    }
end

-- view: the table from ObjectiveAction view (never mutated). opts.playGoalActive: the Goals panel PLAY line ("play new dinos") is on screen
-- and not finished; while it is, an UNFINISHED "second species" task is not shown, so the two never nag about the same thing at once.
-- A finished one is shown (to claim): that is a reward moment, not a nudge. Returns at most Rules.MaxShown rows, best first:
-- claimable rows (tutorial, carried, short, daily), then the tutorial row, then short and daily taken in turns (closest to done first).
function Rules.select(view: any, opts: any?): {any}
    local o: any = if type(opts) == "table" then opts else {}
    local playActive = o.playGoalActive == true
    local max = math.min(whole(o.max ~= nil and o.max or Rules.MaxShown), 6)
    if type(view) ~= "table" then return {} end
    local function keep(row: any): boolean
        if type(row) ~= "table" or row.claimed == true or type(row.id) ~= "string" then return false end
        local finished = row.done == true or whole(row.progress) >= whole(row.goal)
        return not (playActive and row.id == Rules.SecondSpeciesId and not finished)
    end
    local tutorial, carry, short, daily = {}, {}, {}, {}
    if type(view.tutorial) == "table" and keep(view.tutorial) then table.insert(tutorial, describe(view.tutorial, "tutorial")) end
    for _, group in {{view.carry, carry, "carry"}, {view.short, short, "short"}, {view.daily, daily, "daily"}} do
        if type(group[1]) == "table" then
            for _, row in group[1] do
                if keep(row) then table.insert(group[2], describe(row, group[3])) end
            end
        end
    end
    local function byProgress(a: any, b: any): boolean return a.fraction > b.fraction end
    -- table.sort is not stable: sort by (fraction desc, original order).
    local function sorted(list: {any}): {any}
        for i, r in list do r.order = i end
        table.sort(list, function(a, b) if a.fraction ~= b.fraction then return byProgress(a, b) end return a.order < b.order end)
        return list
    end
    local out: {any} = {}
    local seen: {[string]: boolean} = {}
    local function add(row: any)
        if #out < max and not seen[row.id] then seen[row.id] = true table.insert(out, row) end
    end
    for _, list in {tutorial, carry, short, daily} do
        for _, row in list do if row.claimable then add(row) end end
    end
    for _, row in tutorial do add(row) end
    short, daily = sorted(short), sorted(daily)
    for i = 1, math.max(#short, #daily, #carry) do
        if short[i] then add(short[i]) end
        if daily[i] then add(daily[i]) end
        if carry[i] then add(carry[i]) end
    end
    return out
end

function Rules.claimableCount(rows: {any}): number
    local n = 0
    for _, r in rows do if r.claimable then n += 1 end end
    return n
end

-- "3/10". Whole numbers only.
function Rules.progressText(row: any): string
    return string.format("%d/%d", whole(row.progress), math.max(1, whole(row.goal)))
end

-- "+10 crystals" (and " +5 XP" when the catalogue gives XP). Shown on the row's button while it is claimable.
function Rules.rewardText(reward: any): string
    local r = if type(reward) == "table" then reward else {}
    local text = string.format("+%d crystals", whole(r.crystals))
    if whole(r.xp) > 0 then text ..= string.format(" +%d XP", whole(r.xp)) end
    return text
end

-- The folded one-liner: the nearest objective plus a progress chip. Nothing to show -> a calm line, no chip.
function Rules.folded(rows: {any}): any
    local first = rows[1]
    if first == nil then return {text = "All done!", chip = "", claimable = false, empty = true} end
    local more = Rules.claimableCount(rows)
    return {text = first.name, chip = if first.claimable then "Done!" else Rules.progressText(first), claimable = more > 0, empty = false, claimableCount = more,
        tutorial = first.group == "tutorial" and not first.claimable}
end

-- docs/72: round and drop zeros, never "5m 0s". Under a minute (or unknown) it is just "soon".
function Rules.resetText(seconds: any): string
    local s = tonumber(seconds)
    if s == nil or s ~= s or s <= 60 then return "New tasks soon" end
    local minutes = math.ceil(s / 60)
    if minutes < 60 then return string.format("New tasks in %d min", minutes) end
    return string.format("New tasks in %d h", math.ceil(s / 3600))
end

-- Which group's countdown to show: the soonest of the groups that have a visible (unfinished or claimable) row; the tutorial has no clock.
-- view = server view, rows = Rules.select(view). Returns seconds or nil (only tutorial rows shown).
function Rules.resetSeconds(view: any, rows: {any}): number?
    if type(view) ~= "table" then return nil end
    local best: number? = nil
    for _, r in rows do
        local key = if r.group == "short" then "shortResetsIn" elseif r.group == "daily" then "dailyResetsIn" elseif r.group == "carry" then "shortResetsIn" else nil
        local v = if key then tonumber(view[key]) else nil
        if v ~= nil and (best == nil or v < best) then best = v end
    end
    return best
end

-- Answer to a claim. status/reason come from ObjectiveAction ({ok=true,status} or {ok=false,reason}); nil = the call itself failed.
local REASON_TEXT: {[string]: string} = {
    claimed = "Got it!", claimed_capped = "Got it! That is the most for today.",
    duplicate = "Already got it!", already_claimed = "Already got it!",
    not_done = "Not done yet", not_active = "Gone! New tasks soon",
    rate_limited = "Slow down a little", save_failed = "Try again", lease_lost = "Try again", error = "Try again",
}
function Rules.claimMessage(code: any): string
    return REASON_TEXT[tostring(code)] or "Try again later"
end

-- A claim token stays the same across a retry only while the answer says "nothing was decided" (so a lost answer never double-pays, and a
-- definite answer frees the id for a new token).
local RETRY: {[string]: boolean} = {rate_limited = true, save_failed = true, lease_lost = true, error = true}
function Rules.keepToken(code: any): boolean
    return RETRY[tostring(code)] == true
end

-- The claim succeeded (the server paid, now or earlier).
local PAID: {[string]: boolean} = {claimed = true, claimed_capped = true, duplicate = true, already_claimed = true}
function Rules.paid(code: any): boolean
    return PAID[tostring(code)] == true
end

-- Button state of one row: "claim" (green, tappable), "wait" (claim sent, answer not back), "none" (progress bar only).
function Rules.buttonState(row: any, busy: boolean): string
    if row.claimable ~= true then return "none" end
    return if busy then "wait" else "claim"
end

-- BD-076 (docs/66 s19): the one-line goal ("NextGoal") shows the TOP objective when the priority table in NextGoal.pick says so.
-- Everything here is pure: the words, and a CONSERVATIVE width estimate so the line never relies on the engine cutting a word in half.
-- The estimate is an em-fraction table for the HUD font (FredokaOne) plus 8 % slack; Studio measuring with TextService stays on BD-078.
Rules.GoalReadyText = {"Done! Claim at the objectives panel", "Done! Claim in Tasks", "Done! Claim it", "Done!"} -- longest first; the first that fits is shown
local MIN_FONT = 14 -- = PhoneScale.MinText (checked by tools/verify_objectives_panel.py): the line is never drawn smaller
local EM_SMALL, EM_MID, EM_WIDE = 0.30, 0.44, 0.84
local function em(ch: string): number
    if ch == " " then return 0.28 end
    if string.find(ch, "^[%.,:;!'|]$") then return 0.30 end
    if ch == "/" then return 0.42 end
    if string.find(ch, "^[ilj]$") then return EM_SMALL end
    if string.find(ch, "^[tfr]$") then return EM_MID end
    if string.find(ch, "^[mwMW]$") then return EM_WIDE end
    if string.find(ch, "^%d$") then return 0.60 end
    if string.find(ch, "^%u$") then return 0.68 end
    return 0.58
end
-- Estimated on-screen width, in the same px as `fontPx` (a design-space size when the label sits under a UIScale).
function Rules.textWidth(text: string, fontPx: number): number
    local total = 0
    for i = 1, #text do total += em(string.sub(text, i, i)) end
    return total * fontPx * 1.08
end

-- fit = {width = px the label has, font = px (the smallest size the line is drawn at), prefix = the words the HUD puts in front ("Goal  " on a
-- desktop, "" on a phone)}.
function Rules.fitsLine(text: string, fit: any): boolean
    local font = math.max(MIN_FONT, tonumber(fit.font) or MIN_FONT)
    local prefix = if type(fit.prefix) == "string" then fit.prefix else ""
    return Rules.textWidth(prefix .. text, font) <= (tonumber(fit.width) or 0)
end

local DANGLING: {[string]: boolean} = {}
for _, word in {"a", "an", "the", "to", "of", "in", "for", "your", "any", "or", "toward", "with"} do DANGLING[word] = true end

-- Words of the top row for the goal line, or nil when there is nothing to show. rows = Rules.select(...) (finished first, T8 already
-- filtered against the PLAY line). A finished row says where to claim; an unfinished one says "Name: 1/3" (just the name for a one-step task). Over-long names lose WHOLE words
-- from the end (and a dangling "a" / "toward"), then "..." marks the cut; never a word cut in half.
function Rules.goalLine(rows: {any}, fit: any): any?
    local first = rows[1]
    if type(first) ~= "table" or type(fit) ~= "table" then return nil end
    if first.claimable then
        local chosen = Rules.GoalReadyText[#Rules.GoalReadyText]
        for _, candidate in Rules.GoalReadyText do
            if Rules.fitsLine(candidate, fit) then chosen = candidate break end
        end
        return {kind = "objective", text = chosen, claimable = true, ready = true, fraction = 1, id = first.id}
    end
    -- "0/1" says nothing, so a one-step task shows only its name; a counted task keeps its count ("Hatch 10 eggs: 3/10").
    local progress = if math.max(1, whole(first.goal)) > 1 then Rules.progressText(first) else ""
    local joiner, tail = if progress ~= "" then ": " else "", if progress ~= "" then " " .. progress else ""
    local name = tostring(first.name or "")
    local text: string? = nil
    if name ~= "" and Rules.fitsLine(name .. joiner .. progress, fit) then
        text = name .. joiner .. progress
    else
        local words = {}
        for word in string.gmatch(name, "%S+") do table.insert(words, word) end
        for n = #words - 1, 1, -1 do
            local keep = n
            while keep > 1 and DANGLING[string.lower(words[keep])] do keep -= 1 end
            local candidate = table.concat(words, " ", 1, keep) .. "..." .. tail
            if Rules.fitsLine(candidate, fit) then text = candidate break end
        end
    end
    if text == nil then
        local fallback = if progress ~= "" then "Task " .. progress else "Next task"
        text = if Rules.fitsLine(fallback, fit) then fallback elseif progress ~= "" then progress else "Task"
    end
    return {kind = "objective", text = text, claimable = false, ready = false, fraction = first.fraction, id = first.id}
end

-- BD-561 (docs/109 section 9): the four optional icons of the panel. Pure geometry: the panel passes the numbers in and draws what comes back.
-- Every slot is read through Theme.ImageIds (AssetSlots.Images); an EMPTY id means "draw nothing and reserve no space", so with all four empty none
-- of the functions below is called and the panel is exactly the one without icons. Sizes are the docs/109 s9 sizes (never above 44 px).
Rules.Slots = {chevron = "objective_chevron", arrow = "objective_arrow", crystal = "notify_crystal", star = "notify_star"} :: {[string]: string}
Rules.IconPx = {chevron = 24, arrow = 28, crystal = 20, star = 24, row = 20} :: {[string]: number} -- row = the gem and the star on a task row's prize line
Rules.IconGap = 4
Rules.ChipW = 56 -- the progress chip of the folded line (ObjectivesPanel)
Rules.MinTitle = 72 -- folded: the arrow or the star is left out when the task name would get less than this many px

-- Longest whole-word start of `text` that fits `width` px at `font` px ("Equip a dino in the Index" -> "Equip a dino..."), never a word cut in half and
-- never ending on a dangling "a" / "the". If not even "...": the first word alone when it fits, else nil (the caller picks a fallback).
function Rules.fitWords(text: string, width: number, font: number): string?
    if Rules.textWidth(text, font) <= width then return text end
    local words = {}
    for word in string.gmatch(text, "%S+") do table.insert(words, word) end
    for n = #words - 1, 1, -1 do
        local keep = n
        while keep > 1 and DANGLING[string.lower(words[keep])] do keep -= 1 end
        local candidate = table.concat(words, " ", 1, keep) .. "..."
        if Rules.textWidth(candidate, font) <= width then return candidate end
    end
    if #words >= 1 and Rules.textWidth(words[1], font) <= width then return words[1] end
    return nil
end

-- Lines the text needs when wrapped at whole words in `width` px (math.huge when one word alone is wider than the line).
function Rules.wrapLines(text: string, width: number, font: number): number
    local lines, current = 1, 0
    local space = Rules.textWidth(" ", font)
    for word in string.gmatch(text, "%S+") do
        local w = Rules.textWidth(word, font)
        if w > width then return math.huge end
        if current > 0 and current + space + w > width then lines += 1 current = w else current = if current > 0 then current + space + w else w end
    end
    return lines
end

-- Header geometry. width = panel width; has = {chevron, arrow, star, chip, open} (booleans: that piece is wanted now AND its art exists).
-- Folded: [trophy][arrow?] title [star?][chip][chevron?]; open: [trophy] title ... words [chevron]. The chevron always keeps its place, then the chip;
-- the arrow (tutorial task first) or the star (Done chip) is dropped when the title would get less than MinTitle px.
-- Returns x (px from the panel's left edge) of each piece that is shown, plus titleX / titleW and, open, waitInset (px from the right edge).
function Rules.headerLayout(width: number, has: any): any
    local P, gap = Rules.IconPx, Rules.IconGap
    local out: any = {titleX = 42}
    local right = width - 8
    if has.chevron then out.chevronX = right - P.chevron right = out.chevronX - gap end
    if has.open then
        out.waitInset = if has.chevron then width - right else 10
        out.titleW = math.max(0, 0.38 * width - 42)
        out.waitW = math.max(0, 0.62 * width - out.waitInset)
        return out
    end
    if has.chip then out.chipX = right - Rules.ChipW right = out.chipX - gap end
    local left = out.titleX
    if has.star and has.chip then
        if right - gap - P.star - left >= Rules.MinTitle then out.starX = right - P.star right = out.starX - gap end
    elseif has.arrow then
        if right - (left + P.arrow + gap) >= Rules.MinTitle then out.arrowX = left left += P.arrow + gap end
    end
    out.titleX, out.titleW = left, math.max(0, right - left)
    return out
end

-- "+10" (the gem follows) instead of "+10 crystals"; XP, when the catalogue gives any, stays words in front: "+5 XP +10".
function Rules.rewardWords(reward: any, gem: boolean): string
    if not gem then return Rules.rewardText(reward) end
    local r = if type(reward) == "table" then reward else {}
    local text = string.format("+%d", whole(r.crystals))
    if whole(r.xp) > 0 then text = string.format("+%d XP ", whole(r.xp)) .. text end
    return text
end

-- The prize line of a task row, in a span of `span` px starting at x = 0. claimable: left aligned under the name, [star?] "+10" [gem];
-- otherwise right aligned: "+10" [gem] at the end of the span. want = {star, gem}. Nothing that does not fit is drawn: the star goes first, then the gem
-- (the words "+10 crystals" come back), so the line is always readable. Returns {words, text = {x, w}, star = x?, gem = x?}.
function Rules.prizeLayout(reward: any, span: number, claimable: boolean, want: any): any
    local R, gap = Rules.IconPx.row, Rules.IconGap
    local full = Rules.rewardText(reward)
    local plain = {words = full, text = {x = 0, w = span}}
    local wantGem = want.gem == true
    local wantStar = want.star == true and claimable
    if not wantGem and not wantStar then return plain end
    if not claimable then
        local words = Rules.rewardWords(reward, true)
        local avail = span - R - 2
        if Rules.textWidth(words, MIN_FONT) <= avail then return {words = words, text = {x = 0, w = avail}, gem = span - R} end
        return plain
    end
    local tries = if wantStar then {true, false} else {false}
    for _, useStar in tries do
        local x = if useStar then R + gap else 0
        local out: any = {star = if useStar then 0 else nil}
        if wantGem then
            local words = Rules.rewardWords(reward, true)
            local w = math.ceil(Rules.textWidth(words, MIN_FONT))
            if x + w + 2 + R <= span then
                out.words, out.text, out.gem = words, {x = x, w = w}, x + w + 2
                return out
            end
        elseif x + math.ceil(Rules.textWidth(full, MIN_FONT)) <= span then
            out.words, out.text = full, {x = x, w = span - x}
            return out
        end
    end
    return plain
end

-- True when a string follows the docs/72 copy rules (used by tools/verify_objectives_panel.py on every string this module can produce).
function Rules.copyOk(text: string): boolean
    if string.find(text, "%d+%s*m%s+%d+%s*s") or string.find(text, "%d+%s*h%s+%d+%s*m") then return false end -- "5m 0s", "2h 0m"
    if string.find(text, "%d%.?%d*x%f[%W]") then return false end -- "1.25x"
    for _, banned in {"window", "token", "transform", "ledger", "idle", "resets in", "cooldown", "PROVISIONAL"} do
        if string.find(string.lower(text), string.lower(banned), 1, true) then return false end
    end
    return true
end

return Rules
