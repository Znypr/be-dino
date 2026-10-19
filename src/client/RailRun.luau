--!strict
-- BD-1105 (owner 2026-10-18, picture 115): in a run the HUD rail shows four buttons (Dinos, Eggs, Fusion, Shop) that all just say "At home". They cannot
-- do anything in a run, so they are hidden there (HubTravelClientRules.hiddenInRun; with Config.CaveHub off nothing is hidden). POTIONS and SETTINGS stay.
-- The rail is laid out again for the buttons that are left (TouchLayout.compute gets their number, each one takes the next free slot), so there is no empty
-- space. Hiding is immediate (no fade): the buttons are not shown for one frame at the start of a run. At home they are all back, in their old slots.
-- Bootstrap's scales() asks count() and position(); attach() makes it run again when the run state changes (it listens to the "RailRun" attribute of the gui).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Rules = require(Shared:WaitForChild("HubTravelClientRules"))

local M = {}
local player = Players.LocalPlayer

local function runState(): any
    local character = player.Character
    return if character then character:GetAttribute("RunState") else nil
end

function M.hidden(button: Instance): boolean
    return Rules.hiddenInRun(button:GetAttribute("Destination"), Config.CaveHub, runState())
end

function M.anyHidden(buttons: {Instance}): boolean
    for _, b in buttons do if M.hidden(b) then return true end end
    return false
end

-- BD-1116 (Config.HudRailWordsEnabled): the SETTINGS button is the small gear of the rail with words. It is not one of the (at most five) word buttons: it takes the
-- layout's gear slot and is never counted. Flag off: nothing is a gear.
function M.isGear(button: Instance): boolean
    return Config.HudRailWordsEnabled == true and button:GetAttribute("Destination") == "settings"
end

-- How many buttons the rail lays out (with words: the word buttons; TouchLayout.compute adds one back when it falls back to the old rail).
function M.count(buttons: {Instance}): number
    local n = 0
    for _, b in buttons do if not M.hidden(b) and not M.isGear(b) then n += 1 end end
    return n
end

-- The slot of button number `i` among `positions` (a hidden button keeps the first slot: it is not shown). `folded` (rail with words): the gear is not in the
-- list, it has a slot of its own (M.place). A rail with words that did not fit the window falls back to the old rail: Settings is an ordinary button again.
function M.position(buttons: {Instance}, i: number, positions: {any}, folded: boolean?): any
    local rank = 0
    for j = 1, i do if not M.hidden(buttons[j]) and not (folded == true and M.isGear(buttons[j])) then rank += 1 end end
    return positions[math.max(rank, 1)]
end

-- Bootstrap's scales() used to place every rail button itself; the loop lives here now (BD-1116, to keep Bootstrap small). `layout` is the TouchLayout result.
-- A button gets its slot, the size of a cell, then its icon and its word. The gear (rail with words) gets the layout's gear slot and cell: icon only.
function M.place(buttons: {GuiObject}, layout: any)
    local rail = layout.rail
    for i, b in buttons do
        local gear = M.isGear(b) and rail.gear ~= nil
        local cell = if gear then rail.gearCell else rail.button
        local at = if gear then rail.gear else M.position(buttons, i, rail.positions, rail.gear ~= nil)
        b.Position, b.Size = UDim2.fromOffset(at.x, at.y), UDim2.fromOffset(cell.w, cell.h)
        for _, child in b:GetChildren() do
            if child:IsA("TextLabel") then
                child.Position, child.Size, child.TextSize = UDim2.fromOffset(cell.labelX, cell.labelY), UDim2.fromOffset(cell.labelW, cell.labelH), cell.textSize
                child.Visible = not cell.iconOnly -- BD-333: narrow phones show the icon only (BD-1116: never with the words rail, except the gear)
                child.TextScaled = not layout.touch -- BD-333: phones: real >= 14 px, no shrink
                local limit = child:FindFirstChildOfClass("UITextSizeConstraint") or Instance.new("UITextSizeConstraint")
                limit.MaxTextSize, limit.Parent = cell.textSize, child
            elseif child:IsA("GuiObject") and child.Name ~= "ActiveTab" and child.Name ~= "IndexDot" then
                child.Position, child.Size = UDim2.fromOffset(cell.iconX, cell.iconY), UDim2.fromOffset(cell.icon, cell.icon)
            end
        end
    end
end

function M.attach(gui: Instance, buttons: {GuiObject})
    local serial = 0
    local function refresh()
        for _, b in buttons do
            if M.hidden(b) then b.Visible = false end -- showing again is the job of FtueRail (it also knows the first-run menu)
        end
        serial += 1
        gui:SetAttribute("RailRun", serial) -- Bootstrap lays the rail out again
    end
    local function watch(character: Model)
        character:GetAttributeChangedSignal("RunState"):Connect(refresh)
        refresh()
    end
    player.CharacterAdded:Connect(watch)
    if player.Character then watch(player.Character) end
end

return M
