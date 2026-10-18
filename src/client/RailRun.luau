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

-- How many buttons the rail lays out.
function M.count(buttons: {Instance}): number
    local n = 0
    for _, b in buttons do if not M.hidden(b) then n += 1 end end
    return n
end

-- The slot of button number `i` among `positions` (a hidden button keeps the first slot: it is not shown).
function M.position(buttons: {Instance}, i: number, positions: {any}): any
    local rank = 0
    for j = 1, i do if not M.hidden(buttons[j]) then rank += 1 end end
    return positions[math.max(rank, 1)]
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
