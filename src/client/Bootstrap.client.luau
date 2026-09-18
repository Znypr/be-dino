--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local HttpService = game:GetService("HttpService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local player = Players.LocalPlayer
player.CameraMode = Enum.CameraMode.Classic
player.CameraMaxZoomDistance = Config.CameraMaxZoom

local remotes = ReplicatedStorage:WaitForChild("BeDinoRemotes")
local requestEndRun = remotes:WaitForChild("RequestEndRun") :: RemoteEvent
local equipSpecies = remotes:WaitForChild("EquipSpecies") :: RemoteEvent
local testGrantSpecies = remotes:WaitForChild("TestGrantSpecies") :: RemoteEvent

local gui = Instance.new("ScreenGui")
gui.Name = "PrototypeHUD"
gui.ResetOnSpawn = false
gui.Parent = player:WaitForChild("PlayerGui")

local panel = Instance.new("TextLabel")
panel.Position = UDim2.new(0.5, 0, 0, 12)
panel.AnchorPoint = Vector2.new(0.5, 0)
panel.Size = UDim2.new(0.94, 0, 0, 150)
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
limit.MaxSize = Vector2.new(720, 160)
limit.Parent = panel

local collection = Instance.new("Frame")
collection.Name = "CollectionPanel"
collection.Position = UDim2.new(0, 18, 0.5, -130)
collection.Size = UDim2.fromOffset(250, 260)
collection.BackgroundColor3 = Color3.fromRGB(31, 42, 55)
collection.BackgroundTransparency = 0.08
collection.Parent = gui
local collectionCorner = Instance.new("UICorner")
collectionCorner.CornerRadius = UDim.new(0, 12)
collectionCorner.Parent = collection

local title = Instance.new("TextLabel")
title.BackgroundTransparency = 1
title.Position = UDim2.fromOffset(10, 8)
title.Size = UDim2.new(1, -20, 0, 30)
title.Text = "COLLECTION"
title.TextColor3 = Color3.fromRGB(245, 241, 222)
title.Font = Enum.Font.GothamBold
title.TextSize = 18
title.Parent = collection

local function makeButton(y: number): TextButton
    local button = Instance.new("TextButton")
    button.Position = UDim2.fromOffset(10, y)
    button.Size = UDim2.new(1, -20, 0, 42)
    button.BackgroundColor3 = Color3.fromRGB(61, 78, 91)
    button.TextColor3 = Color3.fromRGB(255, 255, 255)
    button.Font = Enum.Font.GothamMedium
    button.TextSize = 14
    button.TextWrapped = true
    button.Parent = collection
    local buttonCorner = Instance.new("UICorner")
    buttonCorner.CornerRadius = UDim.new(0, 8)
    buttonCorner.Parent = button
    return button
end

local speciesButtons: {[string]: TextButton} = {}
for index, speciesId in Config.SpeciesOrder do
    local button = makeButton(42 + (index - 1) * 48)
    speciesButtons[speciesId] = button
    button.Activated:Connect(function()
        if player:GetAttribute("ProfileState") ~= "Loaded" then return end
        equipSpecies:FireServer(speciesId, HttpService:GenerateGUID(false))
    end)
end

local grantButton = makeButton(194)
grantButton.BackgroundColor3 = Color3.fromRGB(97, 82, 53)
grantButton.Activated:Connect(function()
    if player:GetAttribute("ProfileState") ~= "Loaded" then return end
    testGrantSpecies:FireServer()
end)

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

local function stringAttr(name: string, fallback: string): string
    local value = player:GetAttribute(name)
    return if typeof(value) == "string" and value ~= "" then value else fallback
end

local function countForSpecies(speciesId: string): number
    if speciesId == "compy" then return numberAttr("CompyCopies") end
    if speciesId == "triceratops" then return numberAttr("TriceratopsCopies") end
    if speciesId == "tyrannosaurus" then return numberAttr("TyrannosaurusCopies") end
    return 0
end

local elapsed = 0
RunService.Heartbeat:Connect(function(dt)
    elapsed += dt
    if elapsed < 0.1 then return end
    elapsed = 0

    local profileState = stringAttr("ProfileState", "Starting")
    local equipped = stringAttr("EquippedSpeciesId", "compy")
    local equipStatus = stringAttr("LastEquipStatus", "none")
    local grantStatus = stringAttr("LastCollectionGrantStatus", "not used")

    for speciesId, button in speciesButtons do
        local count = countForSpecies(speciesId)
        local displayName = Config.SpeciesDisplayNames[speciesId] or speciesId
        local stateText = if equipped == speciesId then "EQUIPPED" elseif count > 0 then "OWNED" else "LOCKED"
        button.Text = string.format("%s  |  %d copies  |  %s", displayName, count, stateText)
        button.Active = profileState == "Loaded"
        button.AutoButtonColor = profileState == "Loaded"
    end

    local testCount = countForSpecies(Config.CollectionTestGrantSpeciesId)
    grantButton.Visible = Config.CollectionTestGrantEnabled
    grantButton.Text = if testCount > 0 then "TEST TRICERATOPS GRANT USED" else "TEST UNLOCK TRICERATOPS"
    grantButton.Active = Config.CollectionTestGrantEnabled and profileState == "Loaded" and testCount == 0
    grantButton.AutoButtonColor = grantButton.Active

    local collectionText = string.format(
        "Owned: Compy %d  •  Triceratops %d  •  T-Rex %d",
        numberAttr("CompyCopies"),
        numberAttr("TriceratopsCopies"),
        numberAttr("TyrannosaurusCopies")
    )

    local character = currentCharacter
    local humanoid = currentHumanoid
    if not character or player.Character ~= character or not humanoid then
        panel.Text = string.format(
            "BE DINO!  •  COLLECTION TEST\nProfile: %s  •  Equipped: %s  •  Equip result: %s\n%s\nTest grant: %s",
            profileState, equipped, equipStatus, collectionText, grantStatus
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
        "BE DINO!  •  COLLECTION TEST\nGrowth %d  •  Catches %d  •  Size %.2fx  •  %s\nProfile: %s  •  Equipped: %s  •  Equip result: %s\n%s\nTest grant: %s",
        score, catches, scale, status, profileState, equipped, equipStatus, collectionText, grantStatus
    )

    local state = character:GetAttribute("RunState")
    local canEnd = state == "Active" and profileState == "Loaded"
    endButton.Active = canEnd
    endButton.AutoButtonColor = canEnd
    local exitValue = character:GetAttribute("ExitChannelEndsAt")
    local exitEnd = if typeof(exitValue) == "number" then exitValue else 0
    local exitRemaining = math.max(0, exitEnd - now)
    endButton.Text = if exitRemaining > 0 then string.format("STAY STILL %.1fs", exitRemaining) else "END RUN"
end)
