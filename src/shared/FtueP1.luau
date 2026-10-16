--!strict
-- First-time-player P1/P2 fixes (docs/112 audit, BD-369..381). Pure: no Instances, services or remotes, so it can be tested
-- offline (tools/verify_ftue_p1.py). Plain words for 7 to 10 year olds (docs/72): "egg" for the thing, "nest" only for nests.
local P = {}

-- BD-369 Eggs screen -------------------------------------------------------------------------------------------------------
P.NestLine = "Nest eggs are lucky! Nests open one at a time."
P.EmptyStatus = "Go find eggs on the island!"
P.EmptyButton = "EXPLORE ISLAND"
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
P.ConditionsHeader = "Your first 2 eggs are safe: they are never Cracked."

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
function P.foundToast(eggs: number, mutationName: string?): (string, string?)
    local n = math.max(1, math.floor(eggs))
    if mutationName and mutationName ~= "" then
        local text = if n == 1 then "You found a " .. mutationName .. " egg!" else string.format("You found %d eggs!", n)
        return text, "A weather egg! Hatch it at Home"
    end
    return if n == 1 then "You found an egg!" else string.format("You found %d eggs!", n), nil
end
-- Toasts ride the top centre, clear of the Crystals / XP plate (top right) and the HUD bars.
P.ToastTopY = 4

-- BD-379 world text ---------------------------------------------------------------------------------------------------------
-- Floating "+2.8" style text is hidden while a menu or confirm window is open.
function P.worldTextAllowed(modalOpen: boolean): boolean
    return not modalOpen
end

return P
