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
local claimChest = remotes:WaitForChild("ClaimChest") :: RemoteEvent
local testGrantChests = remotes:WaitForChild("TestGrantChests") :: RemoteEvent
local mutateSpecies = remotes:WaitForChild("MutateSpecies") :: RemoteEvent
local testSetMutationCopies = remotes:WaitForChild("TestSetMutationCopies") :: RemoteEvent

local gui = Instance.new("ScreenGui")
gui.Name = "PrototypeHUD"
gui.ResetOnSpawn = false
gui.Parent = player:WaitForChild("PlayerGui")

local panel = Instance.new("TextLabel")
panel.Position = UDim2.new(0.5, 0, 0, 12)
panel.AnchorPoint = Vector2.new(0.5, 0)
panel.Size = UDim2.new(0.94, 0, 0, 174)
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
limit.MaxSize = Vector2.new(760, 184)
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

local chestPanel = Instance.new("Frame")
chestPanel.Name = "ChestPanel"
chestPanel.AnchorPoint = Vector2.new(1, 0.5)
chestPanel.Position = UDim2.new(1, -18, 0.5, 0)
chestPanel.Size = UDim2.fromOffset(260, 250)
chestPanel.BackgroundColor3 = Color3.fromRGB(55, 43, 31)
chestPanel.BackgroundTransparency = 0.08
chestPanel.Parent = gui
local chestCorner = Instance.new("UICorner")
chestCorner.CornerRadius = UDim.new(0, 12)
chestCorner.Parent = chestPanel

local chestTitle = Instance.new("TextLabel")
chestTitle.BackgroundTransparency = 1
chestTitle.Position = UDim2.fromOffset(10, 8)
chestTitle.Size = UDim2.new(1, -20, 0, 30)
chestTitle.Text = "CHEST QUEUE"
chestTitle.TextColor3 = Color3.fromRGB(245, 241, 222)
chestTitle.Font = Enum.Font.GothamBold
chestTitle.TextSize = 18
chestTitle.Parent = chestPanel

local chestInfo = Instance.new("TextLabel")
chestInfo.BackgroundTransparency = 1
chestInfo.Position = UDim2.fromOffset(10, 42)
chestInfo.Size = UDim2.new(1, -20, 0, 78)
chestInfo.TextColor3 = Color3.fromRGB(245, 241, 222)
chestInfo.Font = Enum.Font.GothamMedium
chestInfo.TextSize = 14
chestInfo.TextWrapped = true
chestInfo.Parent = chestPanel

local function chestButton(y: number, textValue: string): TextButton
    local button = Instance.new("TextButton")
    button.Position = UDim2.fromOffset(10, y)
    button.Size = UDim2.new(1, -20, 0, 38)
    button.BackgroundColor3 = Color3.fromRGB(102, 76, 46)
    button.TextColor3 = Color3.fromRGB(255, 255, 255)
    button.Font = Enum.Font.GothamBold
    button.TextSize = 13
    button.Text = textValue
    button.Parent = chestPanel
    local c = Instance.new("UICorner")
    c.CornerRadius = UDim.new(0, 8)
    c.Parent = button
    return button
end

local claimButton = chestButton(124, "CLAIM NEXT CHEST")
local retryClaimButton = chestButton(166, "RETRY LAST CLAIM")
local chestGrantButton = chestButton(208, "TEST ADD 7 CHESTS")

claimButton.Activated:Connect(function()
    local chestId = player:GetAttribute("NextChestId")
    if typeof(chestId) == "string" and chestId ~= "" then
        claimChest:FireServer(chestId, HttpService:GenerateGUID(false))
    end
end)

retryClaimButton.Activated:Connect(function()
    local chestId = player:GetAttribute("LastClaimedChestId")
    if typeof(chestId) == "string" and chestId ~= "" then
        claimChest:FireServer(chestId, HttpService:GenerateGUID(false))
    end
end)

chestGrantButton.Activated:Connect(function()
    if player:GetAttribute("ProfileState") == "Loaded" then
        testGrantChests:FireServer()
    end
end)

local mutationPanel = Instance.new("Frame")
mutationPanel.Name = "MutationPanel"
mutationPanel.AnchorPoint = Vector2.new(0.5, 1)
mutationPanel.Position = UDim2.new(0.5, 0, 1, -18)
mutationPanel.Size = UDim2.fromOffset(520, 150)
mutationPanel.BackgroundColor3 = Color3.fromRGB(65, 52, 24)
mutationPanel.BackgroundTransparency = 0.06
mutationPanel.Parent = gui
local mutationCorner = Instance.new("UICorner")
mutationCorner.CornerRadius = UDim.new(0, 12)
mutationCorner.Parent = mutationPanel

local mutationInfo = Instance.new("TextLabel")
mutationInfo.BackgroundTransparency = 1
mutationInfo.Position = UDim2.fromOffset(10, 6)
mutationInfo.Size = UDim2.new(1, -20, 0, 42)
mutationInfo.TextColor3 = Color3.fromRGB(255, 235, 153)
mutationInfo.Font = Enum.Font.GothamBold
mutationInfo.TextSize = 14
mutationInfo.TextWrapped = true
mutationInfo.Parent = mutationPanel

local lastMutationToken = ""
local function smallMutationButton(x: number, width: number, textValue: string): TextButton
    local button = Instance.new("TextButton")
    button.Position = UDim2.fromOffset(x, 52)
    button.Size = UDim2.fromOffset(width, 38)
    button.BackgroundColor3 = Color3.fromRGB(118, 88, 36)
    button.TextColor3 = Color3.fromRGB(255, 255, 255)
    button.Font = Enum.Font.GothamBold
    button.TextSize = 13
    button.Text = textValue
    button.Parent = mutationPanel
    local c = Instance.new("UICorner")
    c.CornerRadius = UDim.new(0, 8)
    c.Parent = button
    return button
end

local set49 = smallMutationButton(10, 80, "SET 49")
local set50 = smallMutationButton(96, 80, "SET 50")
local set51 = smallMutationButton(182, 80, "SET 51")
local mutateButton = smallMutationButton(268, 116, "MUTATE GOLD")
local retryMutationButton = smallMutationButton(390, 120, "RETRY SAME")

set49.Activated:Connect(function() testSetMutationCopies:FireServer(49) end)
set50.Activated:Connect(function() testSetMutationCopies:FireServer(50) end)
set51.Activated:Connect(function() testSetMutationCopies:FireServer(51) end)
mutateButton.Activated:Connect(function()
    lastMutationToken = HttpService:GenerateGUID(false)
    mutateSpecies:FireServer("compy", "gold", lastMutationToken)
end)
retryMutationButton.Activated:Connect(function()
    if lastMutationToken ~= "" then
        mutateSpecies:FireServer("compy", "gold", lastMutationToken)
    end
end)

local mutationHelp = Instance.new("TextLabel")
mutationHelp.BackgroundTransparency = 1
mutationHelp.Position = UDim2.fromOffset(10, 96)
mutationHelp.Size = UDim2.new(1, -20, 0, 48)
mutationHelp.TextColor3 = Color3.fromRGB(245, 241, 222)
mutationHelp.Font = Enum.Font.GothamMedium
mutationHelp.TextSize = 12
mutationHelp.TextWrapped = true
mutationHelp.Text = "Test helpers overwrite Compy base/Gold counts. Use a fresh private test experience."
mutationHelp.Parent = mutationPanel

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

local function goldForSpecies(speciesId: string): number
    if speciesId == "compy" then return numberAttr("CompyGold") end
    if speciesId == "triceratops" then return numberAttr("TriceratopsGold") end
    if speciesId == "tyrannosaurus" then return numberAttr("TyrannosaurusGold") end
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
    local chestStatus = stringAttr("LastChestClaimStatus", "none")
    local chestGrantStatus = stringAttr("LastChestTestGrantStatus", "not used")
    local chestReward = stringAttr("LastChestRewardText", "none")
    local activeChests = numberAttr("ActiveChestCount")
    local overflowChests = numberAttr("PendingChestGrants")
    local nextReadyAt = numberAttr("NextChestReadyAt")
    local nextChestId = stringAttr("NextChestId", "")
    local serverNow = workspace:GetServerTimeNow()
    local remaining = math.max(0, nextReadyAt - serverNow)
    local nextState = if nextChestId == "" then "EMPTY"
        elseif remaining <= 0 then "READY"
        else string.format("%.1fs", remaining)

    chestInfo.Text = string.format(
        "Active %d / %d  •  Overflow %d\nNext: %s\nClaim: %s  •  Reward: %s",
        activeChests, Config.ChestQueueCapacity, overflowChests, nextState, chestStatus, chestReward
    )
    local ready = nextChestId ~= "" and remaining <= 0 and profileState == "Loaded"
    claimButton.Active = ready
    claimButton.AutoButtonColor = ready
    retryClaimButton.Active = stringAttr("LastClaimedChestId", "") ~= "" and profileState == "Loaded"
    retryClaimButton.AutoButtonColor = retryClaimButton.Active
    chestGrantButton.Visible = Config.ChestTestGrantEnabled
    chestGrantButton.Active = Config.ChestTestGrantEnabled and profileState == "Loaded"
    chestGrantButton.AutoButtonColor = chestGrantButton.Active
    chestGrantButton.Text = "TEST ADD 7 CHESTS (" .. chestGrantStatus .. ")"

    for speciesId, button in speciesButtons do
        local count = countForSpecies(speciesId)
        local displayName = Config.SpeciesDisplayNames[speciesId] or speciesId
        local stateText = if equipped == speciesId then "EQUIPPED" elseif count > 0 then "OWNED" else "LOCKED"
        button.Text = string.format(
            "%s | %d base / %d Gold | %s",
            displayName, count, goldForSpecies(speciesId), stateText
        )
        button.Active = profileState == "Loaded"
        button.AutoButtonColor = profileState == "Loaded"
    end

    local mutationStatus = stringAttr("LastMutationStatus", "none")
    local setupStatus = stringAttr("LastMutationSetupStatus", "not used")
    mutationInfo.Text = string.format(
        "GOLD MUTATION  •  Compy %d base / %d Gold  •  %s  •  Setup: %s",
        numberAttr("CompyCopies"), numberAttr("CompyGold"), mutationStatus, setupStatus
    )
    mutateButton.Active = profileState == "Loaded"
    mutateButton.AutoButtonColor = mutateButton.Active
    retryMutationButton.Active = profileState == "Loaded" and lastMutationToken ~= ""
    retryMutationButton.AutoButtonColor = retryMutationButton.Active

    local testCount = countForSpecies(Config.CollectionTestGrantSpeciesId)
    grantButton.Visible = Config.CollectionTestGrantEnabled
    grantButton.Text = if testCount > 0 then "TEST TRICERATOPS GRANT USED" else "TEST UNLOCK TRICERATOPS"
    grantButton.Active = Config.CollectionTestGrantEnabled and profileState == "Loaded" and testCount == 0
    grantButton.AutoButtonColor = grantButton.Active

    local collectionText = string.format(
        "Owned: Compy %d+%dG  •  Triceratops %d+%dG  •  T-Rex %d+%dG",
        numberAttr("CompyCopies"), numberAttr("CompyGold"),
        numberAttr("TriceratopsCopies"), numberAttr("TriceratopsGold"),
        numberAttr("TyrannosaurusCopies"), numberAttr("TyrannosaurusGold")
    )

    local character = currentCharacter
    local humanoid = currentHumanoid
    if not character or player.Character ~= character or not humanoid then
        panel.Text = string.format(
            "BE DINO!  •  GOLD MUTATION TEST\nProfile: %s  •  Equipped: %s  •  Equip result: %s\n%s\nTest grant: %s",
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
        "BE DINO!  •  GOLD MUTATION TEST\nGrowth %d  •  Catches %d  •  Size %.2fx  •  %s\nProfile: %s  •  Equipped: %s  •  Equip result: %s\n%s\nTest grant: %s",
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
