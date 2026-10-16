--!strict
-- BD-368 (docs/112): fewer controls at minute zero. During a run, while the profile has never found an egg, the left menu
-- shows only POTIONS and SETTINGS plus a small MENU chip that opens the rest. The choice is made when the run starts and
-- holds for that run; the menu auto-closes after a few seconds and whenever a new run starts. Buttons keep their layout
-- positions (Bootstrap's scales() still owns them): this module only toggles Visible and places the chip on slot 4.
-- Rules live in Shared/FtueRules (tools/verify_ftue_rules.py). No Instances are created per frame.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Rules = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("FtueRules"))
local Theme = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("UITheme"))

local Rail = {}
local player = Players.LocalPlayer

local function hasFoundEgg(): boolean
    local copies = 0
    local ok, collection = pcall(function() return game:GetService("HttpService"):JSONDecode(player:GetAttribute("CollectionJson") :: string) end)
    if ok then copies = Rules.collectionCopies(collection) end
    return Rules.hasFoundEgg({activeEggs = player:GetAttribute("ActiveChestCount"), waitingEggs = player:GetAttribute("QueuedEggsWaiting"),
        lastRunEggs = player:GetAttribute("LastRunEggCount"), copies = copies})
end

-- rail = the left menu frame; buttons = the six nav buttons in order (each has a "Destination" attribute).
function Rail.attach(rail: Frame, buttons: {TextButton})
    local chip = Instance.new("TextButton")
    chip.Name, chip.Text, chip.Font, chip.TextSize, chip.TextColor3 = "MenuChip", Rules.MenuChipText, Enum.Font.FredokaOne, 20, Theme.Colors.text
    chip.BackgroundColor3, chip.ZIndex, chip.Visible, chip.AutoButtonColor = Theme.Colors.card, rail.ZIndex + 3, false, true
    Theme.decorate(chip, 4)
    chip.Parent = rail

    local strokes: {UIStroke} = {}
    for _, child in rail:GetChildren() do if child:IsA("UIStroke") then table.insert(strokes, child) end end
    local panelTransparency = rail.BackgroundTransparency

    local collapsed, expanded, openedAt, wasActive = false, false, 0, false
    local function apply()
        for _, b in buttons do
            b.Visible = Rules.buttonVisible(tostring(b:GetAttribute("Destination")), collapsed, expanded)
        end
        -- The empty panel is hidden while collapsed so only the three items float at the edge.
        rail.BackgroundTransparency = if collapsed and not expanded then 1 else panelTransparency
        for _, s in strokes do s.Enabled = not (collapsed and not expanded) end
        local slot = buttons[4]
        chip.Visible = Rules.chipVisible(collapsed, expanded) and slot ~= nil
        if slot then chip.Position, chip.Size = slot.Position, slot.Size end
    end
    chip.Activated:Connect(function()
        expanded, openedAt = true, os.clock()
        apply()
    end)
    for _, b in buttons do
        b.Activated:Connect(function() if collapsed and expanded then expanded = false task.defer(apply) end end)
    end

    local elapsed = 0
    RunService.Heartbeat:Connect(function(dt)
        elapsed += dt
        if elapsed < 0.15 then return end
        elapsed = 0
        local character = player.Character
        local active = character ~= nil and character:GetAttribute("RunState") == "Active"
        if active and not wasActive then
            collapsed, expanded = Rules.collapseForRun(true, hasFoundEgg()), false -- auto-close at the start of a run
        elseif not active and wasActive then
            collapsed, expanded = false, false
        end
        wasActive = active
        if expanded and os.clock() - openedAt > Rules.MenuAutoCloseSeconds then expanded = false end
        apply()
    end)
end

return Rail
