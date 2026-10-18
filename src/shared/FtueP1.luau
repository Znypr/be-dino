--!strict
-- First-time-player P1/P2 fixes (docs/112 audit, BD-369..381). Pure: no Instances, services or remotes, so it can be tested
-- offline (tools/verify_ftue_p1.py). Plain words for 7 to 10 year olds (docs/72): "egg" for the thing, "nest" only for nests.
local P = {}

-- BD-369 Eggs screen -------------------------------------------------------------------------------------------------------
P.NestLine = "Lucky nests open one at a time."
P.EmptyStatus = "Go find eggs on the island!"
P.EmptyButton = "Explore"
P.CrackedHint = "Some eggs can crack!"
P.CrackedHintSafeEggs = 2 -- the first two eggs are never Cracked (FtueRules.SafeEggs); the hint starts after them
P.CrackedHintWindow = 5 -- ... and stops once the player has seen it work for this many more eggs

-- "Eggs waiting: N" counts EVERY unopened egg, including the one on the card, so a READY card never sits beside "0".
-- Returns nil when there is nothing to count (the label is hidden instead of showing 0).
function P.waitingText(active: number, banked: number): string?
    local total = math.max(0, math.floor(active)) + math.max(0, math.floor(banked))
    if total <= 0 then return nil end
    return "Eggs waiting: " .. tostring(total)
end

-- Hatched eggs are estimated from the collection copies (one starter Compy is not an egg). The card egg may be Cracked
-- only after the safe first eggs; show the hint on the cards after them for a short while.
function P.crackedHintShown(collectionCopies: number, hasCardEgg: boolean): boolean
    if not hasCardEgg then return false end
    local hatched = math.max(0, math.floor(collectionCopies) - 1)
    return hatched >= P.CrackedHintSafeEggs and hatched < P.CrackedHintSafeEggs + P.CrackedHintWindow
end

-- BD-371 hatch end buttons -------------------------------------------------------------------------------------------------
-- After an egg is shown: what real buttons are drawn. remaining = eggs still to open after this one.
-- "next" opens the next egg, "done" goes back to the Eggs screen, "again" starts another run to find more eggs.
function P.hatchButtons(failed: boolean, remaining: number): {string}
    if remaining > 0 then
        return if failed then {"next"} else {}
    end
    return if failed then {"done", "again"} else {"done"}
end
P.ButtonText = {next = "NEXT EGG", done = "DONE", again = "TRY AGAIN"}
P.ButtonColors = {next = {93, 237, 31}, done = {93, 237, 31}, again = {255, 210, 43}} -- accent green / gold
P.ButtonTextColor = {13, 15, 20} -- dark text on a bright button

local function channel(v: number): number
    local c = v / 255
    return if c <= 0.03928 then c / 12.92 else ((c + 0.055) / 1.055) ^ 2.4
end
local function luminance(rgb: {number}): number
    return 0.2126 * channel(rgb[1]) + 0.7152 * channel(rgb[2]) + 0.0722 * channel(rgb[3])
end
-- WCAG contrast ratio between two {r, g, b} colours (0..255).
function P.contrast(a: {number}, b: {number}): number
    local la, lb = luminance(a), luminance(b)
    if la < lb then la, lb = lb, la end
    return (la + 0.05) / (lb + 0.05)
end

-- BD-445 (docs/132) shop day one: the CONDITIONS tab stays hidden until account level 3 (it is a late-game odds upgrade); a
-- player with 0 crystals gets a one-line hint on the other tabs. No prices or odds change.
P.ConditionsTabLevel = 3
P.NoCrystalsHint = "Play a run to earn crystals!"
function P.shopTabs(level: number): {string}
    local tabs = {"auras", "trails", "eggs"}
    if level >= P.ConditionsTabLevel then table.insert(tabs, "conditions") end
    table.insert(tabs, "crystals")
    return tabs
end
function P.noCrystalsHintShown(crystals: number, tab: string): boolean
    return crystals <= 0 and tab ~= "crystals"
end

-- BD-447 (docs/132): the Fast travel perk entry stays hidden in the first minutes (level 1 = the first run or two); it shows from
-- account level 2, or at once if the player already owns it. Walking stays the default.
P.FastTravelLevel = 2
function P.fastTravelEntryShown(level: number, owned: boolean): boolean
    return owned or level >= P.FastTravelLevel
end

-- BD-372 shop day one ------------------------------------------------------------------------------------------------------
-- The condition upgrade button. enabled=false draws a grey button with the reason; a green action never sits over a lock.
function P.upgradeButton(upgrade: any, level: number, crystals: number): (string, boolean)
    if upgrade == nil then return "MAX LEVEL", false end
    if level < upgrade.requiredLevel then return "Reach level " .. tostring(upgrade.requiredLevel), false end
    if crystals < upgrade.price then return "Need " .. tostring(upgrade.price) .. " Crystals", false end
    return "UPGRADE: " .. tostring(upgrade.price) .. " CRYSTALS", true
end
-- The line under the button. Never repeats or contradicts the button.
function P.upgradeHint(upgrade: any, level: number): string
    if upgrade == nil then return "Top level reached" end
    if level < upgrade.requiredLevel then return "Keep playing to level up!" end
    return "Ready to buy!"
end
-- (BD-365: the "first eggs are safe" line is OddsCopy.safeEggsLine, shown only while it is true.)

-- BD-374 Settings > Controls -----------------------------------------------------------------------------------------------
-- Two short lines of keys (desktop) or touch controls (phone). Read from the real input code in Bootstrap
-- (E leap, B eggs, C dinos, Esc close) and CombatHud (F bite, only while fighting is on).
function P.controlsLines(touch: boolean, combat: boolean): {string}
    if touch then
        return {"Move: left stick  •  Look: drag the screen", "Jump and LEAP: tap the buttons"}
    end
    return {
        "Move: W A S D  •  Jump: Space  •  Leap: E",
        if combat then "Look: right-click drag  •  Bite: F  •  Eggs: B" else "Look: right-click drag  •  Eggs: B  •  Dinos: C",
    }
end

-- BD-375 go home -----------------------------------------------------------------------------------------------------------
P.HomeConfirmTitle = "Go home?"
P.HomeConfirmButton = "GO HOME"
P.HomeToast = "Going home..."

-- BD-376 plain words for the buff line and Index counts --------------------------------------------------------------------
P.BuffWord = {growth = "Growth", speed = "Speed", loot = "Eggs"}
P.MinTextSize = 14
-- "1 Base • 2 Gold": only the tiers the player has; plain "Not found yet" never shows here (the caller handles unowned).
function P.indexCount(base: number, gold: number, diamond: number): string
    local parts = {}
    for _, pair in {{base, "Base"}, {gold, "Gold"}, {diamond, "Diamond"}} do
        local n = pair[1] :: number
        if n > 0 then table.insert(parts, string.format("%d %s", n, pair[2] :: string)) end
    end
    return if #parts == 0 then "0 Base" else table.concat(parts, "  •  ")
end

-- BD-378 egg-found toast ---------------------------------------------------------------------------------------------------
-- ONE toast for every egg that landed in a tick. Returns text (<= NotifyQueue.MaxText 30) and a body (<= 44).
-- BD-508: `mutations` is a weather name ("Ember", one egg) or a count per weather name ({Ember = 2, Frost = 1}) for the eggs of this
-- tick. Several eggs of one kind: "You found 7 eggs!" + "2 Ember eggs! Hatch them at Home". Mixed kinds: the most common one + "and more".
P.FoundBodyTail = " Hatch them at Home"
P.FoundBodyOne = "A weather egg! Hatch it at Home"
local function article(name: string): string
    return if string.find(string.sub(name, 1, 1), "[AEIOUaeiou]") then "an" else "a"
end
local function withTail(head: string): string
    local full = head .. P.FoundBodyTail
    return if #full <= 44 then full else head -- a long name drops the tail rather than being cut mid-word
end
function P.foundToast(eggs: number, mutations: (string | {[string]: number})?): (string, string?)
    local n = math.max(1, math.floor(eggs))
    local counts: {[string]: number} = {}
    if typeof(mutations) == "string" then
        if mutations ~= "" then counts[mutations] = 1 end
    elseif typeof(mutations) == "table" then
        for name, k in mutations do
            if typeof(name) == "string" and name ~= "" and typeof(k) == "number" and k >= 1 then counts[name] = math.floor(k) end
        end
    end
    local kinds, total, best, bestCount = 0, 0, "", 0
    for name, k in counts do
        kinds += 1
        total += k
        if k > bestCount or (k == bestCount and name < best) then best, bestCount = name, k end
    end
    if kinds == 0 then
        return if n == 1 then "You found an egg!" else string.format("You found %d eggs!", n), nil
    end
    if n == 1 then
        return "You found " .. article(best) .. " " .. best .. " egg!", P.FoundBodyOne
    end
    local text = string.format("You found %d eggs!", n)
    local shown = math.min(bestCount, n) -- never claim more weather eggs than eggs
    local head: string
    if kinds > 1 then
        head = string.format("%d %s %s and more!", shown, best, if shown == 1 then "egg" else "eggs")
    elseif shown == 1 then
        head = string.upper(string.sub(article(best), 1, 1)) .. string.sub(article(best), 2) .. " " .. best .. " egg!"
    else
        head = string.format("%d %s eggs!", shown, best)
    end
    return text, withTail(head)
end
-- Toasts ride the top centre, clear of the Crystals / XP plate (top right) and the HUD bars.
P.ToastTopY = 4

-- BD-379 world text ---------------------------------------------------------------------------------------------------------
-- Floating "+2.8" style text is hidden while a menu or confirm window is open.
function P.worldTextAllowed(modalOpen: boolean): boolean
    return not modalOpen
end

return P
