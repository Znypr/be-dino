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
    return {title = title, line = line, keyLabel = Rules.keyLabel(k, keyName, engineLabel), buttonText = Rules.buttonWords(station, k)}
end

-- The words on the big button. A stall opens a window ("Open"); the Heart does not open anything, it shows your dino off (BD-1129, docs/205 picture 432: the Heart
-- button said "Open"). On a phone the whole bubble is the button, so it says what a tap does.
function Rules.buttonWords(station: any, kind: any): string
    local touch = kind == "Touch"
    if station == "heart" then return if touch then "Tap to show off" else "Show off" end
    return if touch then "Tap to open" else "Open"
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

-- ---- where on the screen (BD-1128) ---------------------------------------------------------------------------------------------------
-- Studio round 8 (docs/205 picture 421) at 516 x 481: the bubble was a 3D billboard over the stall, and every billboard is drawn UNDER the HUD, so the rail and
-- the weather plate hid its name and cut its key button. LEAD decision (owner delegated 2026-10-16): the bubble is now drawn in a screen layer ABOVE the HUD and
-- ALSO placed clear of the HUD pieces, never over them, because on top of the HUD it would otherwise cover a button the player needs (the rail, Home, LEAP).
-- This pure rule does the placing; the client only gives it the projected point of the stall and the HUD rectangles (px of the same canvas).
-- To overturn: put the BillboardGui back (HubPromptBubble.show) and delete the placing. The bubble stays the same size at every distance.
Rules.Gap = 6 -- px kept free between the bubble and a HUD piece
Rules.Edge = 4 -- px kept free at the screen edge
-- Attributes of the HUD canvas (HudV2.layout, Bootstrap). HARD pieces are buttons and plates the bubble must never cover. SOFT pieces (the build badge and the
-- Studio-only notice, two lines of small text, and the "Back to the middle" chip) are kept clear too, but only while a spot exists that also clears the hard ones:
-- in a very small window the bubble may lie over a soft piece rather than over the rail or Home.
Rules.HardRects = {"RailRect", "TimersRect", "ActionRect", "HudRect", "WalletBlockRect", "FeedbackRect", "AdminRect"}
Rules.SoftRects = {"BadgeRect", "NoticeRect", "ChipRect"}

export type Rect = {x: number, y: number, w: number, h: number}

local function overlapArea(a: Rect, b: Rect): number
    local w = math.min(a.x + a.w, b.x + b.w) - math.max(a.x, b.x)
    local h = math.min(a.y + a.h, b.y + b.h) - math.max(a.y, b.y)
    return if w > 0 and h > 0 then w * h else 0
end

local function cleanRects(list: any): {Rect}
    local out: {Rect} = {}
    if typeof(list) ~= "table" then return out end
    for _, r in list do
        if typeof(r) == "table" and finite(r.x) and finite(r.y) and finite(r.w) and finite(r.h) and r.w > 0 and r.h > 0 then
            out[#out + 1] = {x = r.x, y = r.y, w = r.w, h = r.h}
        end
    end
    return out
end

-- p = {w, h = the canvas in px, point = {x, y} where the stall is on that canvas, size = {w, h} of the bubble, blockers = {Rect} the hard HUD pieces,
-- soft = {Rect} the soft ones}. The bubble is centred on the point, then slid onto the screen and off every blocker (kept Rules.Gap away): of the spots that are
-- free it takes the one nearest the point. Returns {x, y (top-left), clear = true when it touches no hard piece (and no soft one unless softCovered)}.
-- If no free spot exists (a tiny window) it takes the spot that covers the least of the hard pieces, and clear is false; `layoutFor` below tries the smaller
-- bubble first, so that is rare.
function Rules.place(p: any): {x: number, y: number, clear: boolean, softCovered: boolean}
    local W, H = if typeof(p) == "table" and finite(p.w) then p.w :: number else 0, if typeof(p) == "table" and finite(p.h) then p.h :: number else 0
    local size = if typeof(p) == "table" and typeof(p.size) == "table" then p.size else {w = 0, h = 0}
    local bw, bh = if finite(size.w) then size.w :: number else 0, if finite(size.h) then size.h :: number else 0
    local point = if typeof(p) == "table" and typeof(p.point) == "table" then p.point else {x = W / 2, y = H / 2}
    local px, py = if finite(point.x) then point.x :: number else W / 2, if finite(point.y) then point.y :: number else H / 2
    local hard = cleanRects(if typeof(p) == "table" then p.blockers else nil)
    local soft = cleanRects(if typeof(p) == "table" then p.soft else nil)
    local edge = Rules.Edge
    local maxX, maxY = math.max(edge, W - edge - bw), math.max(edge, H - edge - bh)
    local function clampX(x: number): number return math.max(edge, math.min(maxX, x)) end
    local function clampY(y: number): number return math.max(edge, math.min(maxY, y)) end
    local wantX, wantY = clampX(px - bw / 2), clampY(py - bh / 2)

    local function search(blockers: {Rect}): (number, number, number)
        local xs, ys = {wantX}, {wantY}
        for _, b in blockers do
            table.insert(xs, clampX(b.x - Rules.Gap - bw))
            table.insert(xs, clampX(b.x + b.w + Rules.Gap))
            table.insert(ys, clampY(b.y - Rules.Gap - bh))
            table.insert(ys, clampY(b.y + b.h + Rules.Gap))
        end
        -- the same value twice (a clamped edge) is looked at once
        local function unique(list: {number}): {number}
            local seen, out = {}, {}
            for _, v in list do
                local key = math.floor(v * 100 + 0.5)
                if not seen[key] then seen[key] = true table.insert(out, v) end
            end
            return out
        end
        xs, ys = unique(xs), unique(ys)
        local bestX, bestY, bestTouch, bestDistance = wantX, wantY, math.huge, math.huge
        local function touches(x: number, y: number): number
            local total = 0
            local r: Rect = {x = x - Rules.Gap + 1e-6, y = y - Rules.Gap + 1e-6, w = bw + 2 * Rules.Gap - 2e-6, h = bh + 2 * Rules.Gap - 2e-6}
            for _, b in blockers do
                total += overlapArea(r, b)
                if total > bestTouch + 1e-6 then break end -- it cannot win any more
            end
            return total
        end
        for _, x in xs do
            for _, y in ys do
                local touch = touches(x, y)
                local d = (x - wantX) ^ 2 + (y - wantY) ^ 2
                if touch < bestTouch - 1e-6 or (math.abs(touch - bestTouch) <= 1e-6 and d < bestDistance) then
                    bestX, bestY, bestTouch, bestDistance = x, y, touch, d
                end
            end
        end
        return bestX, bestY, bestTouch
    end

    local all: {Rect} = table.clone(hard)
    for _, s in soft do table.insert(all, s) end
    local x, y, touch = search(all)
    if touch <= 1e-6 then return {x = x, y = y, clear = true, softCovered = false} end
    if #soft > 0 then
        x, y, touch = search(hard)
        if touch <= 1e-6 then return {x = x, y = y, clear = true, softCovered = true} end
    end
    return {x = x, y = y, clear = false, softCovered = #soft > 0}
end

-- The layout to build (Rules.layout by screen height) and whether the HUD leaves it a free spot, trying the smaller bubble when the big one has none (a narrow
-- window). Returns {layout, clear}. hard and soft as in `place`.
function Rules.layoutFor(canvasW: any, canvasH: any, hard: any, soft: any): (any, boolean)
    local big = Rules.layout(canvasH)
    local W, H = if finite(canvasW) then canvasW :: number else 0, if finite(canvasH) then canvasH :: number else 0
    local function fits(layout: any): boolean
        if W <= 0 or H <= 0 then return true end
        return Rules.place({w = W, h = H, point = {x = W / 2, y = H / 2}, size = {w = layout.w, h = layout.h}, blockers = hard, soft = soft}).clear
    end
    if fits(big) then return big, true end
    if not big.small then
        local small = Rules.layout(0)
        if fits(small) then return small, true end
        return small, false
    end
    return big, false
end

-- Reads one attribute value of the HUD canvas: a Roblox Rect (Min, Max) or a table with Min and Max. Anything else is nil.
function Rules.rectOf(v: any): Rect?
    if typeof(v) ~= "Rect" and typeof(v) ~= "table" then return nil end
    local lo, hi = (v :: any).Min, (v :: any).Max
    if lo == nil or hi == nil or not finite(lo.X) or not finite(lo.Y) or not finite(hi.X) or not finite(hi.Y) then return nil end
    if hi.X <= lo.X or hi.Y <= lo.Y then return nil end
    return {x = lo.X, y = lo.Y, w = hi.X - lo.X, h = hi.Y - lo.Y}
end

-- Eases the shown spot toward the wanted one so a switch between free spots (the camera turns, a HUD piece appears) glides instead of jumping. Reduce Motion
-- (motion = false) jumps at once. dt = seconds since the last frame.
Rules.FollowRate = 16
function Rules.follow(current: any, target: any, dt: any, motion: any): {x: number, y: number}
    if typeof(target) ~= "table" or not finite(target.x) or not finite(target.y) then return {x = 0, y = 0} end
    if motion ~= true or typeof(current) ~= "table" or not finite(current.x) or not finite(current.y) or not finite(dt) then return {x = target.x, y = target.y} end
    local k = 1 - math.exp(-Rules.FollowRate * math.max(0, math.min(dt :: number, 0.25)))
    return {x = current.x + (target.x - current.x) * k, y = current.y + (target.y - current.y) * k}
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
