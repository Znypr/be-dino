--!strict
-- BD-1017 (docs/180 option A, owner 2026-10-18: "the shop interactions should be like messages with buttons to click, like E to interact"):
-- the pure rules of the stall message bubble. Behind Config.ShopPromptBubbleEnabled (the client module HubPromptBubble does nothing with the flag off).
-- No Instances, no services. The client builds the look; this module decides WHAT is said, WHICH stall shows, WHEN it shows and whether the words fit.
--   * the words (stall name, one warm line, key button) per stall and per input type (keyboard, phone, gamepad)
--   * the key label per input type ("E" on a keyboard, the button name on a gamepad, none on a phone: the whole bubble is the button)
--   * one bubble at a time: the nearest stall
--   * hidden while a window is open, while the stall cannot open, for a moment after a press and after a window closes
--   * the two sizes (big, and a smaller one on short screens) and a fit check for the words (children read these, docs/72: text at least 14 px)
local Copy = require(script.Parent.HubSignCopy)
local Walk = require(script.Parent.HubWalkUpRules)

local Rules = {}
Rules.ReturnDelay = 0.3 -- seconds after a window closes before the bubble comes back
Rules.PressHide = 0.3 -- seconds the bubble stays hidden after a press (a blocked press shows it again after this)
Rules.RangeSlack = 3 -- studs: the engine decided "in range"; this only protects the ordering from a small measuring difference
Rules.FadeIn, Rules.FadeOut, Rules.Squash, Rules.SquashSeconds = 0.15, 0.1, 0.92, 0.08
Rules.ShortScreen = 480 -- screens lower than this (pixels) get the smaller bubble
Rules.AverageEm = 0.55 -- FredokaOne letters are about half an em wide; 0.55 errs on the wide side so a fit check is safe
Rules.MinText = 14 -- docs/72 and docs/114 s4.4
Rules.MinTap = 44 -- docs/72: the whole bubble is the tap target

local function finite(n: any): boolean return typeof(n) == "number" and n == n and n ~= math.huge and n ~= -math.huge end

-- ---- input type ---------------------------------------------------------------------------------------------------------------
-- "Keyboard" | "Touch" | "Gamepad". `name` is the name of an Enum.UserInputType or Enum.ProximityPromptInputType (the last input the player used, so a
-- touch laptop that is being typed on shows the key and one that is being tapped shows "Tap to open"). Anything unknown counts as a keyboard.
function Rules.inputKind(name: any): string
    if typeof(name) ~= "string" then return "Keyboard" end
    if name == "Touch" then return "Touch" end
    if name == "Gamepad" or string.sub(name, 1, 7) == "Gamepad" then return "Gamepad" end
    return "Keyboard"
end

local GAMEPAD_LABELS: {[string]: string} = {
    ButtonA = "A", ButtonB = "B", ButtonX = "X", ButtonY = "Y", ButtonL1 = "L1", ButtonR1 = "R1", ButtonL2 = "L2", ButtonR2 = "R2",
}
-- The short name on the key chip. keyLabel = what the engine says for the keyboard key (UserInputService:GetStringForKeyCode, "" or nil = unknown).
-- Keyboard: that label upper-cased (1 to 3 letters), else the key name from the rules. Gamepad: the button name ("X"). Touch: nil (there is no key).
function Rules.keyLabel(kind: any, keyName: any, engineLabel: any): string?
    if kind == "Touch" then return nil end
    if kind == "Gamepad" then
        return if typeof(keyName) == "string" and GAMEPAD_LABELS[keyName] then GAMEPAD_LABELS[keyName] else GAMEPAD_LABELS[Walk.PromptGamepadBubble]
    end
    if typeof(engineLabel) == "string" and #engineLabel >= 1 and #engineLabel <= 3 and not engineLabel:find("[^%w]") then return string.upper(engineLabel) end
    return if typeof(keyName) == "string" and #keyName >= 1 and #keyName <= 3 then string.upper(keyName) else Walk.PromptKeyBubble
end

-- What the bubble says. Returns {title, line, keyLabel, buttonText} or nil for a station that has no bubble copy.
-- station: "nests" | "potions" | "fusion" | "style" | "index" | "heart". kind: from inputKind. keyName: the prompt's key (KeyCode name).
function Rules.words(station: any, kind: any, keyName: any, engineLabel: any): {title: string, line: string, keyLabel: string?, buttonText: string}?
    local title, line = Copy.bubbleTitle(station), Copy.bubbleLine(station)
    if title == nil or line == nil then return nil end
    local k = Rules.inputKind(kind)
    return {title = title, line = line, keyLabel = Rules.keyLabel(k, keyName, engineLabel), buttonText = if k == "Touch" then "Tap to open" else "Open"}
end

-- Every stall that gets a bubble: the five menu stalls (in layout order) and the Heart.
function Rules.stations(): {string}
    local out = {}
    for _, s in Walk.stations() do out[#out + 1] = s.id end
    out[#out + 1] = "heart"
    return out
end

-- ---- size and fit ----------------------------------------------------------------------------------------------------------------
-- Pixel layout. The bubble is a world billboard (pixels on screen, it does not scale with the menu). Big on tall screens, smaller on short ones
-- (a 640 x 360 phone view); the target never drops under 96 px wide, and the text never under 14 px.
function Rules.layout(viewportHeight: any): {w: number, h: number, pad: number, titleSize: number, lineSize: number, buttonSize: number, titleY: number, titleH: number, lineY: number, lineH: number, buttonY: number, buttonH: number, innerW: number, small: boolean}
    if finite(viewportHeight) and (viewportHeight :: number) < Rules.ShortScreen then
        return {w = 220, h = 100, pad = 8, titleSize = 18, lineSize = 14, buttonSize = 18, titleY = 6, titleH = 22, lineY = 28, lineH = 18, buttonY = 50, buttonH = 40, innerW = 204, small = true}
    end
    return {w = 248, h = 116, pad = 10, titleSize = 20, lineSize = 16, buttonSize = 20, titleY = 8, titleH = 24, lineY = 34, lineH = 22, buttonY = 62, buttonH = 44, innerW = 228, small = false}
end

function Rules.textWidth(text: any, size: any): number
    if typeof(text) ~= "string" or not finite(size) then return math.huge end
    return #text * (size :: number) * Rules.AverageEm
end

-- true when every word of the bubble for `station` fits one line in `layout` (the line at its own size, the title, the button words).
function Rules.fits(station: any, kind: any, layout: any): boolean
    local words = Rules.words(station, kind, nil, nil)
    if words == nil or typeof(layout) ~= "table" then return false end
    local chip = if words.keyLabel then 36 + 8 else 0 -- the key chip and its gap before the button words
    return Rules.textWidth(words.title, layout.titleSize) <= layout.innerW
        and Rules.textWidth(words.line, layout.lineSize) <= layout.innerW
        and Rules.textWidth(words.buttonText, layout.buttonSize) + chip <= layout.innerW - 16
        and layout.lineSize >= Rules.MinText and layout.titleSize >= Rules.MinText and layout.buttonSize >= Rules.MinText
        and layout.w >= 96 and layout.h >= Rules.MinTap
end

-- ---- which bubble, and when ----------------------------------------------------------------------------------------------------------
-- candidates: {{id = station id, distance = studs from the player to the prompt, range = its walk-up distance (optional)}}. Returns the nearest id
-- that is inside its range (plus a small slack), or nil. A tie goes to the first listed. Junk entries are skipped.
function Rules.nearest(candidates: any): string?
    if typeof(candidates) ~= "table" then return nil end
    local best: string? = nil
    local bestDistance = math.huge
    for _, c in candidates do
        if typeof(c) == "table" and typeof(c.id) == "string" and finite(c.distance) and (c.distance :: number) >= 0 then
            local range = if finite(c.range) then c.range else Walk.PromptDistance
            if (c.distance :: number) <= (range :: number) + Rules.RangeSlack and (c.distance :: number) < bestDistance then
                best, bestDistance = c.id :: string, c.distance :: number
            end
        end
    end
    return best
end

function Rules.newState(): any
    return {wasWindowOpen = false, windowClosedAt = -math.huge, pressedAt = -math.huge}
end

-- A press happened (key, tap or button): hide the bubble for a moment. If the press opened a window the window rule keeps it hidden; if it
-- closed one or did nothing, the bubble returns when the moment is over.
function Rules.pressed(state: any, now: number)
    state.pressedAt = now
end

-- The bubble to show right now (a station id) or nil. input = {candidates, canShow, windowOpen}.
--   windowOpen: any shop or menu window is on screen -> hidden (a tap could fall through), and it comes back ReturnDelay after the window closes.
--   canShow: the stall can open now (at home, no hub trip) -> else hidden (never a dead button).
function Rules.step(state: any, input: any, now: number): string?
    if typeof(input) ~= "table" then return nil end
    if input.windowOpen == true then
        state.wasWindowOpen = true
        return nil
    end
    if state.wasWindowOpen then
        state.wasWindowOpen = false
        state.windowClosedAt = now
    end
    if input.canShow ~= true then return nil end
    if now - state.windowClosedAt < Rules.ReturnDelay then return nil end
    if now - state.pressedAt < Rules.PressHide then return nil end
    return Rules.nearest(input.candidates)
end

return Rules
