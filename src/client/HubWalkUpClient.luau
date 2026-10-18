--!strict
-- BD-289 (docs/104 s8, OWNER 2026-10-16): each menu station gets an invisible anchor at its sign with a ProximityPrompt
-- (hold 0, 10 studs, key G, a 96 px tap target on phones). The shop opens ONLY when the player presses it, never by walking up.
-- Fast travel (HubTravelClient) opens the menu itself because the player chose it. Rules: pure HubWalkUpRules.
-- attach() returns nil at once while Config.CaveHub is false.
local Players = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")
local ContextActionService = game:GetService("ContextActionService")
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
    local function openName(): string -- the rail destination on screen now ("" none): the Fusion menu has its own window, every other screen is Bootstrap's
        local fusion = require(script.Parent:WaitForChild("FusionMenu"))
        if fusion.isOpen() then return "fusion" end
        return if ctx.current then ctx.current() else ""
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
        prompt.Name, prompt.ActionText, prompt.ObjectText = "Open", "Open " .. s.sign, ""
        prompt.KeyboardKeyCode, prompt.GamepadKeyCode = Enum.KeyCode[Rules.PromptKey], Enum.KeyCode.ButtonL1
        prompt.HoldDuration, prompt.MaxActivationDistance, prompt.RequiresLineOfSight = 0, Rules.PromptDistance, false
        prompt.Style = Enum.ProximityPromptStyle.Custom
        prompt:SetAttribute("HubWalkUp", true)
        prompt.Triggered:Connect(function()
            local action = Rules.press(state, s.id, canOpen(), openName(), os.clock())
            if action == "open" then openStation(s.id)
            elseif action == "close" then -- BD-1074: the same key that opened the screen closes it
                if Rules.destination(s.id) == "fusion" then require(script.Parent:WaitForChild("FusionMenu")).closeFromKey() else ctx.close() end
            end
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
        button.Size, button.BackgroundColor3, button.Text, button.Font, button.TextSize = UDim2.fromScale(1, 1), Color3.fromRGB(255, 200, 70), Rules.PromptButtonText, Enum.Font.FredokaOne, 22
        button.TextColor3, button.TextWrapped = Color3.fromRGB(40, 28, 70), true
        local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(1, 0) corner.Parent = button
        local stroke = Instance.new("UIStroke") stroke.Thickness, stroke.Color = 3, Color3.fromRGB(40, 28, 70) stroke.Parent = button
        button.Parent = board
        button.Activated:Connect(function()
            prompt:InputHoldBegin()
            prompt:InputHoldEnd()
        end)
        local hint = Instance.new("TextLabel")
        hint.Size, hint.Position, hint.BackgroundTransparency = UDim2.fromOffset(TAP, 22), UDim2.fromOffset(0, TAP + 2), 1
        hint.Font, hint.TextSize, hint.Text, hint.TextColor3 = Enum.Font.FredokaOne, 18, "[" .. Rules.PromptKey .. "]", Color3.fromRGB(255, 240, 205)
        hint.TextStrokeTransparency = 0.3
        hint.Visible = UserInputService.KeyboardEnabled
        hint.Parent = board
        board.Parent = player:WaitForChild("PlayerGui")
        local actionName = "HubOpen_" .. prompt.Parent.Name
        ContextActionService:BindAction(actionName, function(_, state)
            if state == Enum.UserInputState.Begin then prompt:InputHoldBegin() prompt:InputHoldEnd() end
            return Enum.ContextActionResult.Sink
        end, false, prompt.KeyboardKeyCode, prompt.GamepadKeyCode)
        prompt.PromptHidden:Once(function()
            ContextActionService:UnbindAction(actionName)
            board:Destroy()
        end)
    end)

    return {note = function(station: string) Rules.note(state, station, os.clock()) end}
end

return Client
