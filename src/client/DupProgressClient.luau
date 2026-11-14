--!strict
-- BD-1170 part A (docs/227): the client half of "a duplicate shows progress". Behind Config.DupProgressEnabled (default false, on
-- only in the playtest profile): with the flag off every function returns at once, no thread, no remote call, no Instance.
--   * hatch reveal: one small line under the colour line, "3 of 6 for Gold!" / "Ready for Gold!" (count AFTER this hatch)
--   * Index species page: one row of progress bars (Gold, and Emerald / Diamond once the player owns Gold / Emerald copies);
--     a tap opens the Fusion Menu on that species and step
-- Text and existing UI pieces only (no new art, no sound). Every word, the count rule (the Fusion Menu's own
-- FusionSelection.ineligibility) and the hatch counting are in the pure Shared/DupProgress (tools/verify_dup_progress.py).
-- The copy list is the FusionAction "list" answer the Fusion Menu, the goal line and the Index already read; nothing is written.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config) :: any
local Dup = require(Shared.DupProgress)
local Theme = require(Shared.UITheme)
local PrivateState = require(script.Parent.PrivateState)
local C = Theme.Colors

local Client = {}
Client.PageLimit, Client.MaxPages = 200, 10 -- a longer list than this is not counted at all (no line is better than a wrong number)
Client.Line = {x = 152, y = 338, w = 520, h = 20, text = 16, hintDrop = 6} -- under the colour line (316..344), above the tap hint (moved hintDrop px down)

local tracker: any = nil
local dirty, scheduled = true, false
local current: any = nil -- the hatch line on screen: {label, speciesId, supplied}

local function on(): boolean return Config.DupProgressEnabled == true end

local function fetch(): any
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    local fn = folder and folder:FindFirstChild("FusionAction")
    if not fn or not fn:IsA("RemoteFunction") then return nil end
    local all, cursor, pages = {}, nil, 0
    repeat
        local ok, response = pcall(function() return (fn :: RemoteFunction):InvokeServer({action = "list", cursor = cursor, limit = Client.PageLimit}) end)
        if not ok or type(response) ~= "table" or response.ok ~= true or type(response.dinosaurs) ~= "table" then return nil end
        for _, d in response.dinosaurs do table.insert(all, d) end
        cursor = response.nextCursor
        pages += 1
    until cursor == nil or pages >= Client.MaxPages
    if cursor ~= nil then return nil end
    return all
end

local function setLine(entry: any, have: number?)
    local label: TextLabel = entry.label
    if not label.Parent then return end
    local line = Dup.hatchLine(have)
    entry.has = line ~= nil
    if not line then label.Text = "" return end
    label.Text, label.TextColor3 = line.text, if line.ready then C.accent else C.text
    local hint: GuiObject? = entry.hint
    if hint and not entry.dropped then -- the "Tap for next egg" label moves a few pixels down, once, so the two never touch
        entry.dropped = true
        hint.Position += UDim2.fromOffset(0, Client.Line.hintDrop)
    end
end

local poke: () -> ()
poke = function()
    if scheduled or not tracker then return end
    scheduled = true
    task.delay(Dup.QuietSeconds + .2, function()
        scheduled = false
        if not dirty then return end
        local buffered = PrivateState.num("BufferedRevealCount")
        if not Dup.quiet(tracker, os.clock(), buffered) then
            -- still hatching: a later hatch event or a change of the buffered count pokes again; only the plain time wait re-checks itself
            if buffered == 0 and tracker.requested == nil then poke() end
            return
        end
        local token = Dup.request(tracker)
        local dinos = fetch()
        if Dup.arrived(tracker, token, dinos, PrivateState.num("BufferedRevealCount")) then
            dirty = false
            -- the list holds the egg on screen: the line now shows the server's own count
            if current and current.supplied and not current.failed then
                setLine(current, Dup.have(tracker, current.speciesId))
                if current.revealed then Client.show(current, 0) end
            end
        end
    end)
end

-- Called once at start-up (DinoIndexScreens.attach): reads the copy list while nothing hatches and keeps it fresh.
function Client.start()
    if not on() or tracker then return end
    tracker = Dup.tracker()
    for _, name in {"ProfileRevision", "BufferedRevealCount"} do
        PrivateState.onChanged(name, function() if name == "ProfileRevision" then dirty = true end poke() end)
    end
    poke()
end

-- Hatch reveal (HatchSequence) -----------------------------------------------------------------------------------------
-- An egg starts opening: makes the (empty, hidden) line and tells the counter. Returns nil while the flag is off.
function Client.hatchPlay(body: GuiObject): any
    if not on() then return nil end
    Client.start()
    Dup.opened(tracker, os.clock())
    local L = Client.Line
    local label = Instance.new("TextLabel")
    label.Name, label.BackgroundTransparency, label.Position, label.Size = "DupProgressLine", 1, UDim2.fromOffset(L.x, L.y), UDim2.fromOffset(L.w, L.h)
    label.Font, label.TextSize, label.Text, label.TextColor3 = Enum.Font.FredokaOne, L.text, "", C.text
    label.TextTransparency, label.TextStrokeTransparency, label.TextStrokeColor3 = 1, 1, C.outline
    label.ZIndex, label.Parent = body.ZIndex + 6, body
    current = {label = label, supplied = false, has = false, revealed = false, failed = false}
    return current
end

-- The server answer is here: the egg's species, whether it failed, the words on the name label ("2x Compy" = 2 copies) and the
-- "Tap for next egg" label.
function Client.hatchResult(entry: any, speciesId: string?, failed: boolean, nameText: string, hint: GuiObject?)
    if not entry or type(speciesId) ~= "string" then return end
    entry.speciesId, entry.supplied, entry.failed, entry.hint = speciesId, true, failed, hint
    local have = Dup.hatched(tracker, speciesId, if failed then 0 else Dup.copiesFromName(nameText), os.clock())
    dirty = true
    poke()
    setLine(entry, if failed then nil else have)
end

-- The dinosaur is revealed: the line fades in with the other lines (opacity only, so Reduce Motion needs nothing).
function Client.show(entry: any, delay: number)
    if not entry or not entry.has then return end
    task.delay(delay, function()
        local label: TextLabel = entry.label
        if not label.Parent then return end
        TweenService:Create(label, TweenInfo.new(.3, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {TextTransparency = 0, TextStrokeTransparency = 0}):Play()
    end)
end
function Client.hatchReveal(entry: any, delay: number)
    if entry then entry.revealed = true end
    Client.show(entry, delay)
end

-- Index species page (DinoIndexPanels) ---------------------------------------------------------------------------------
-- One row of bars at y = top in the My dinos column. dinos = the player's copies (the Index's own list). open(stageId) is called
-- on a tap. Returns the height used (0 = flag off or nothing to show), so the grid starts below it.
function Client.indexRow(parent: GuiObject, dinos: any, speciesId: string, top: number, height: number, open: (string) -> (), rowWidth: number?, left: number?): number
    if not on() then return 0 end
    local steps = Dup.speciesSteps(dinos, speciesId)
    if #steps == 0 then return 0 end
    local W = require(script.Parent.FusionWidgets) :: any
    local width, gap = rowWidth or 516, 8 -- BD-1189: the new detail page passes its panel width and left edge; nil = the old 516 at x 0
    local each = math.floor((width - gap * (#steps - 1)) / #steps)
    local row = Instance.new("Frame")
    row.Name, row.BackgroundTransparency, row.Position, row.Size = "DupProgress", 1, UDim2.fromOffset(left or 0, top), UDim2.fromOffset(width, height)
    row.Parent = parent
    for i, step in steps do
        local bar = W.box(row, UDim2.fromOffset(each, height), UDim2.fromOffset((i - 1) * (each + gap), 0), C.outline, 5)
        bar.Name, bar.ClipsDescendants, bar.ZIndex = "Step_" .. step.stageId, true, parent.ZIndex + 1 -- explicit layers: outline, fill, words, tap
        local fill = Instance.new("Frame")
        fill.Name, fill.BorderSizePixel, fill.Size, fill.ZIndex = "Fill", 0, UDim2.new(step.fraction, 0, 1, 0), bar.ZIndex + 1
        fill.BackgroundColor3 = if step.ready then C.accent else (W.StageColors[step.stageId] or C.gold):Lerp(C.outline, .35)
        fill.Parent = bar
        local words = if #steps == 1 then step.text .. "  " .. step.hint else step.text
        W.label(bar, words, UDim2.new(1, -8, 1, 0), UDim2.fromOffset(4, 0), 20, C.text).ZIndex = bar.ZIndex + 2
        local tap = Instance.new("TextButton") -- the whole bar is the touch target (height = the page's touch size, 44 px or more)
        tap.Name, tap.BackgroundTransparency, tap.Text, tap.Size, tap.ZIndex = "Open", 1, "", UDim2.fromScale(1, 1), bar.ZIndex + 3
        tap.Activated:Connect(function() open(step.stageId) end)
        tap.Parent = bar
    end
    return height + 6
end

-- The tap: the Fusion Menu opens on this species and step (its own Dino filter chip shows it and clears it). openMenu is
-- Bootstrap's openFusion, which says "Fusion is coming soon" when the menu is not there.
function Client.openFusion(speciesId: string, stageId: string, openMenu: () -> ())
    local ok, menu = pcall(require, script.Parent.FusionMenu)
    if ok and type(menu) == "table" and menu.preset then menu.preset(speciesId, stageId) end
    openMenu()
end

return Client
