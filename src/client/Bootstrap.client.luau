--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local player = Players.LocalPlayer
player.CameraMode = Enum.CameraMode.Classic
player.CameraMaxZoomDistance = Config.CameraMaxZoom

local remotes = ReplicatedStorage:WaitForChild("BeDinoRemotes")
local requestEndRun = remotes:WaitForChild("RequestEndRun") :: RemoteEvent

local gui = Instance.new("ScreenGui")
gui.Name = "PrototypeHUD"
gui.ResetOnSpawn = false
gui.Parent = player:WaitForChild("PlayerGui")

local panel = Instance.new("TextLabel")
panel.Position = UDim2.new(0.5, 0, 0, 12)
panel.AnchorPoint = Vector2.new(0.5, 0)
panel.Size = UDim2.new(0.94, 0, 0, 142)
panel.BackgroundColor3 = Color3.fromRGB(32, 49, 42)
panel.BackgroundTransparency = 0.12
panel.TextColor3 = Color3.fromRGB(249, 243, 218)
panel.Font = Enum.Font.GothamMedium
panel.TextSize = 15
panel.TextWrapped = true
panel.Parent = gui
local corner = Instance.new("UICorner")
corner.CornerRadius = UDim.new(0, 12)
corner.Parent = panel
local limit = Instance.new("UISizeConstraint")
limit.MaxSize = Vector2.new(720, 150)
limit.Parent = panel

local endButton = Instance.new("TextButton")
endButton.Name = "EndRun"
endButton.AnchorPoint = Vector2.new(1, 1)
endButton.Position = UDim2.new(1, -20, 1, -20)
endButton.Size = UDim2.fromOffset(150, 52)
endButton.BackgroundColor3 = Color3.fromRGB(143, 78, 61)
endButton.TextColor3 = Color3.fromRGB(255, 247, 230)
endButton.Font = Enum.Font.GothamBold
endButton.TextSize = 16
endButton.Text = "END RUN"
endButton.Parent = gui
local buttonCorner = Instance.new("UICorner")
buttonCorner.CornerRadius = UDim.new(0, 12)
buttonCorner.Parent = endButton

endButton.Activated:Connect(function()
    requestEndRun:FireServer()
end)

local connections: {RBXScriptConnection} = {}
local currentCharacter: Model? = nil
local currentHumanoid: Humanoid? = nil

local function onCharacter(character: Model)
    for _, connection in connections do connection:Disconnect() end
    table.clear(connections)
    currentCharacter = character
    currentHumanoid = nil
    local humanoid = character:WaitForChild("Humanoid", 10) :: Humanoid?
    if not humanoid or player.Character ~= character then return end
    currentHumanoid = humanoid
    humanoid:SetStateEnabled(Enum.HumanoidStateType.Jumping, false)
    local camera = workspace.CurrentCamera
    if camera then
        camera.CameraType = Enum.CameraType.Custom
        camera.CameraSubject = humanoid
    end
end
player.CharacterAdded:Connect(onCharacter)
if player.Character then task.spawn(onCharacter, player.Character) end

local function numberAttr(name: string): number
    local value = player:GetAttribute(name)
    return if typeof(value) == "number" then value else 0
end

local elapsed = 0
RunService.Heartbeat:Connect(function(dt)
    elapsed += dt
    if elapsed < 0.1 then return end
    elapsed = 0

    local profileValue = player:GetAttribute("ProfileState")
    local profileState = if typeof(profileValue) == "string" then profileValue else "Starting"
    local rewardValue = player:GetAttribute("LastRewardText")
    local probeValue = player:GetAttribute("LastSettlementProbe")
    local rewardText = if typeof(rewardValue) == "string" and rewardValue ~= "" then rewardValue else "none yet"
    local probeText = if typeof(probeValue) == "string" and probeValue ~= "" then probeValue else "not run yet"
    local collectionText = string.format(
        "Owned: Compy %d  •  Triceratops %d  •  T-Rex %d  •  Pending chests %d",
        numberAttr("CompyCopies"),
        numberAttr("TriceratopsCopies"),
        numberAttr("TyrannosaurusCopies"),
        numberAttr("PendingChestGrants")
    )

    local character = currentCharacter
    local humanoid = currentHumanoid
    if not character or player.Character ~= character or not humanoid then
        panel.Text = string.format(
            "BE DINO!  •  PERSISTENCE TEST\nProfile: %s  •  Idempotency: %s\n%s\nLast reward: %s",
            profileState, probeText, collectionText, rewardText
        )
        endButton.Active = false
        endButton.AutoButtonColor = false
        endButton.Text = "END RUN"
        return
    end

    local scaleValue = character:GetAttribute("VisualScale")
    local scale = if typeof(scaleValue) == "number" then scaleValue else 1
    player.CameraMinZoomDistance = Config.CameraMinZoom * scale
    humanoid.CameraOffset = Vector3.new(0, (scale - 1) * 2, 0)

    local scoreValue = character:GetAttribute("GrowthScore")
    local catchValue = character:GetAttribute("CatchScore")
    local score = if typeof(scoreValue) == "number" then scoreValue else 0
    local catches = if typeof(catchValue) == "number" then catchValue else 0
    local now = workspace:GetServerTimeNow()
    local protectionValue = character:GetAttribute("SpawnProtectionEndsAt")
    local protectionEnd = if typeof(protectionValue) == "number" then protectionValue else 0
    local protectionRemaining = math.max(0, protectionEnd - now)
    local status = if protectionRemaining > 0 then string.format("SAFE %.1fs", protectionRemaining) else "PVP ACTIVE"

    panel.Text = string.format(
        "BE DINO!  •  PERSISTENCE TEST\nGrowth %d  •  Catches %d  •  Size %.2fx  •  %s\nProfile: %s  •  Idempotency: %s\n%s\nLast reward: %s",
        score, catches, scale, status, profileState, probeText, collectionText, rewardText
    )

    local state = character:GetAttribute("RunState")
    local canEnd = state == "Active" and profileState == "Loaded"
    endButton.Active = canEnd
    endButton.AutoButtonColor = canEnd
    local exitValue = character:GetAttribute("ExitChannelEndsAt")
    local exitEnd = if typeof(exitValue) == "number" then exitValue else 0
    local exitRemaining = math.max(0, exitEnd - now)
    if exitRemaining > 0 then
        endButton.Text = string.format("STAY STILL %.1fs", exitRemaining)
    else
        endButton.Text = "END RUN"
    end
end)
