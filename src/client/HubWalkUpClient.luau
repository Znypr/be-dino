--!strict
-- BD-289 first part (docs/104 s8): walking up to a station sign. Each menu station gets an invisible anchor at its sign with
-- a ProximityPrompt (hold 0, 10 studs, a 96 px tap target on phones) and a pad dwell (0.5 s on the pad opens the station
-- once). Both end in the same ctx.open / ctx.openFusion the rail uses. Leaving a pad closes nothing. Decisions live in the
-- pure HubWalkUpRules (tools/verify_cave_gate.py). The moss-trail guide beam is NOT built here (BD-289 stays open for it).
-- attach() returns nil at once while Config.CaveHub is false.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local ProximityPromptService = game:GetService("ProximityPromptService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Layout = require(Shared:WaitForChild("CaveHubLayout"))
local Rules = require(Shared:WaitForChild("HubWalkUpRules"))

local Client = {}
local TAP = 96 -- px: the prompt button (docs/104 s8)

-- ctx = {gui, open, openFusion}; isBusy() = a hub trip is running. Returns {note = function(station)} or nil.
function Client.attach(ctx: any, isBusy: () -> boolean): any?
    if Config.CaveHub ~= true then return nil end
    local player = Players.LocalPlayer
    local state = Rules.newState()

    local function canOpen(): boolean
        local character = player.Character
        if not character or character:GetAttribute("RunState") ~= "Sanctuary" or isBusy() then return false end
        local scrim = ctx.gui:FindFirstChild("ModalScrim")
        return not (scrim and scrim:IsA("GuiObject") and scrim.Visible)
    end
    local function openStation(station: string)
        local destination = Rules.destination(station)
        if destination == nil then return end
        if destination == "fusion" then ctx.openFusion() else ctx.open(destination) end
    end

    local folder = Instance.new("Folder")
    folder.Name = "HubWalkUpPrompts"
    for _, s in Rules.stations() do
        local anchor = Instance.new("Part")
        anchor.Name, anchor.Anchored, anchor.CanCollide, anchor.CanTouch, anchor.CanQuery, anchor.Transparency = "Prompt_" .. s.id, true, false, false, false, 1
        anchor.Size = Vector3.new(1, 1, 1)
        anchor.Position = Vector3.new(s.signX, Layout.FloorY + Rules.PromptHeight, s.signZ + Layout.CenterZ)
        local prompt = Instance.new("ProximityPrompt")
        prompt.Name, prompt.ActionText, prompt.ObjectText = "Walk up", s.sign, ""
        prompt.HoldDuration, prompt.MaxActivationDistance, prompt.RequiresLineOfSight = 0, Rules.PromptDistance, false
        prompt.Style = Enum.ProximityPromptStyle.Custom
        prompt:SetAttribute("HubWalkUp", true)
        prompt.Triggered:Connect(function()
            if Rules.trigger(state, s.id, canOpen(), os.clock()) then openStation(s.id) end
        end)
        prompt.Parent = anchor
        anchor.Parent = folder
    end
    folder.Parent = workspace

    -- The prompt face: one big round button (phones tap it; keyboards still use the prompt key as usual).
    ProximityPromptService.PromptShown:Connect(function(prompt: ProximityPrompt)
        if prompt:GetAttribute("HubWalkUp") ~= true then return end
        local board = Instance.new("BillboardGui")
        board.Name, board.Adornee, board.Size, board.AlwaysOnTop = "HubWalkUpFace", prompt.Parent :: Instance, UDim2.fromOffset(TAP, TAP), true
        board.StudsOffset = Vector3.new(0, 2, 0)
        local button = Instance.new("TextButton")
        button.Size, button.BackgroundColor3, button.Text, button.Font, button.TextSize = UDim2.fromScale(1, 1), Color3.fromRGB(255, 200, 70), prompt.ActionText, Enum.Font.FredokaOne, 22
        button.TextColor3, button.TextWrapped = Color3.fromRGB(40, 28, 70), true
        local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(1, 0) corner.Parent = button
        local stroke = Instance.new("UIStroke") stroke.Thickness, stroke.Color = 3, Color3.fromRGB(40, 28, 70) stroke.Parent = button
        button.Parent = board
        button.Activated:Connect(function()
            prompt:InputHoldBegin()
            prompt:InputHoldEnd()
        end)
        board.Parent = player:WaitForChild("PlayerGui")
        prompt.PromptHidden:Once(function() board:Destroy() end)
    end)

    RunService.Heartbeat:Connect(function()
        local character = player.Character
        local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
        local pad: string? = nil
        if root and root:IsA("BasePart") and character:GetAttribute("RunState") == "Sanctuary" then
            pad = Rules.padAt(root.Position.X, root.Position.Z)
        end
        local station = Rules.step(state, pad, canOpen(), os.clock())
        if station then openStation(station) end
    end)

    return {note = function(station: string) Rules.note(state, station, os.clock()) end}
end

return Client
