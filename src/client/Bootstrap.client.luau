--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local HttpService = game:GetService("HttpService")
local UserInputService = game:GetService("UserInputService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local player = Players.LocalPlayer
player.CameraMode = Enum.CameraMode.Classic
player.CameraMaxZoomDistance = Config.CameraMaxZoom

local remotes = ReplicatedStorage:WaitForChild("BeDinoRemotes")
local requestEndRun = remotes:WaitForChild("RequestEndRun") :: RemoteEvent
local equipSpecies = remotes:WaitForChild("EquipSpecies") :: RemoteEvent
local claimChest = remotes:WaitForChild("ClaimChest") :: RemoteEvent
local mutateSpecies = remotes:WaitForChild("MutateSpecies") :: RemoteEvent

local gui = Instance.new("ScreenGui")
gui.Name = "CoreUI"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = false
gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
gui.Parent = player:WaitForChild("PlayerGui")

local function rounded(instance: GuiObject, radius: number)
    local corner = Instance.new("UICorner")
    corner.CornerRadius = UDim.new(0, radius)
    corner.Parent = instance
end

local function scaleForViewport(): number
    local camera = workspace.CurrentCamera
    local size = if camera then camera.ViewportSize else Vector2.new(1280, 720)
    return math.clamp(math.min(size.X / 1100, size.Y / 620), 0.68, 1.08)
end

local function addScale(instance: GuiObject): UIScale
    local scale = Instance.new("UIScale")
    scale.Scale = scaleForViewport()
    scale.Parent = instance
    return scale
end

local function makeButton(parent: Instance, textValue: string, width: number): TextButton
    local button = Instance.new("TextButton")
    button.Size = UDim2.fromOffset(width, 44)
    button.BackgroundColor3 = Color3.fromRGB(54, 74, 63)
    button.TextColor3 = Color3.fromRGB(250, 246, 224)
    button.Font = Enum.Font.GothamBold
    button.TextSize = 14
    button.Text = textValue
    button.AutoButtonColor = true
    button.Parent = parent
    rounded(button, 10)
    return button
end

local hud = Instance.new("Frame")
hud.AnchorPoint = Vector2.new(0.5, 0)
hud.Position = UDim2.new(0.5, 0, 0, 12)
hud.Size = UDim2.fromOffset(520, 72)
hud.BackgroundColor3 = Color3.fromRGB(28, 45, 38)
hud.BackgroundTransparency = 0.08
hud.Parent = gui
rounded(hud, 14)
local hudScale = addScale(hud)

local title = Instance.new("TextLabel")
title.BackgroundTransparency = 1
title.Position = UDim2.fromOffset(14, 8)
title.Size = UDim2.fromOffset(120, 24)
title.Text = "BE DINO!"
title.TextColor3 = Color3.fromRGB(247, 236, 177)
title.Font = Enum.Font.GothamBold
title.TextSize = 18
title.TextXAlignment = Enum.TextXAlignment.Left
title.Parent = hud

local hudStats = Instance.new("TextLabel")
hudStats.BackgroundTransparency = 1
hudStats.Position = UDim2.fromOffset(14, 34)
hudStats.Size = UDim2.new(1, -28, 0, 28)
hudStats.TextColor3 = Color3.fromRGB(238, 242, 232)
hudStats.Font = Enum.Font.GothamMedium
hudStats.TextSize = 14
hudStats.TextXAlignment = Enum.TextXAlignment.Left
hudStats.Parent = hud

local nav = Instance.new("Frame")
nav.AnchorPoint = Vector2.new(0.5, 1)
nav.Position = UDim2.new(0.5, 0, 1, -16)
nav.Size = UDim2.fromOffset(514, 54)
nav.BackgroundColor3 = Color3.fromRGB(26, 38, 34)
nav.BackgroundTransparency = 0.05
nav.Parent = gui
rounded(nav, 14)
local navScale = addScale(nav)
local navLayout = Instance.new("UIListLayout")
navLayout.FillDirection = Enum.FillDirection.Horizontal
navLayout.HorizontalAlignment = Enum.HorizontalAlignment.Center
navLayout.VerticalAlignment = Enum.VerticalAlignment.Center
navLayout.Padding = UDim.new(0, 8)
navLayout.Parent = nav

local homeButton = makeButton(nav, "HOME", 108)
local collectionButton = makeButton(nav, "DINOS", 108)
local chestButton = makeButton(nav, "CHESTS", 108)
local endButton = makeButton(nav, "END RUN", 150)
endButton.BackgroundColor3 = Color3.fromRGB(133, 72, 57)

local modalShade = Instance.new("Frame")
modalShade.Size = UDim2.fromScale(1, 1)
modalShade.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
modalShade.BackgroundTransparency = 0.5
modalShade.Visible = false
modalShade.ZIndex = 10
modalShade.Parent = gui

local panel = Instance.new("Frame")
panel.AnchorPoint = Vector2.new(0.5, 0.5)
panel.Position = UDim2.fromScale(0.5, 0.5)
panel.Size = UDim2.fromOffset(570, 380)
panel.BackgroundColor3 = Color3.fromRGB(31, 43, 38)
panel.ZIndex = 11
panel.Parent = modalShade
rounded(panel, 16)
local panelScale = addScale(panel)

local panelTitle = Instance.new("TextLabel")
panelTitle.BackgroundTransparency = 1
panelTitle.Position = UDim2.fromOffset(18, 12)
panelTitle.Size = UDim2.new(1, -88, 0, 34)
panelTitle.TextColor3 = Color3.fromRGB(247, 236, 177)
panelTitle.Font = Enum.Font.GothamBold
panelTitle.TextSize = 22
panelTitle.TextXAlignment = Enum.TextXAlignment.Left
panelTitle.ZIndex = 12
panelTitle.Parent = panel

local closeButton = Instance.new("TextButton")
closeButton.AnchorPoint = Vector2.new(1, 0)
closeButton.Position = UDim2.new(1, -12, 0, 12)
closeButton.Size = UDim2.fromOffset(54, 36)
closeButton.BackgroundColor3 = Color3.fromRGB(66, 78, 71)
closeButton.TextColor3 = Color3.new(1, 1, 1)
closeButton.Text = "X"
closeButton.Font = Enum.Font.GothamBold
closeButton.TextSize = 16
closeButton.ZIndex = 12
closeButton.Parent = panel
rounded(closeButton, 9)

local content = Instance.new("Frame")
content.BackgroundTransparency = 1
content.Position = UDim2.fromOffset(18, 58)
content.Size = UDim2.new(1, -36, 1, -76)
content.ZIndex = 12
content.Parent = panel

local activeView = ""
local viewChildren: {Instance} = {}

local function clearView()
    for _, child in viewChildren do
        child:Destroy()
    end
    table.clear(viewChildren)
end

local function track<T>(instance: T): T
    table.insert(viewChildren, instance :: any)
    return instance
end

local function numberAttr(name: string): number
    local value = player:GetAttribute(name)
    return if typeof(value) == "number" then value else 0
end

local function stringAttr(name: string, fallback: string): string
    local value = player:GetAttribute(name)
    return if typeof(value) == "string" and value ~= "" then value else fallback
end

local function counts(speciesId: string): (number, number)
    if speciesId == "compy" then return numberAttr("CompyCopies"), numberAttr("CompyGold") end
    if speciesId == "triceratops" then return numberAttr("TriceratopsCopies"), numberAttr("TriceratopsGold") end
    if speciesId == "tyrannosaurus" then return numberAttr("TyrannosaurusCopies"), numberAttr("TyrannosaurusGold") end
    return 0, 0
end

local function openModal(viewName: string)
    activeView = viewName
    modalShade.Visible = true
end

local function closeModal()
    activeView = ""
    modalShade.Visible = false
    clearView()
end
closeButton.Activated:Connect(closeModal)

local function textLine(parent: Instance, textValue: string, y: number, height: number, size: number, bold: boolean?): TextLabel
    local label = Instance.new("TextLabel")
    label.BackgroundTransparency = 1
    label.Position = UDim2.fromOffset(0, y)
    label.Size = UDim2.new(1, 0, 0, height)
    label.Text = textValue
    label.TextColor3 = Color3.fromRGB(236, 240, 230)
    label.Font = if bold then Enum.Font.GothamBold else Enum.Font.GothamMedium
    label.TextSize = size
    label.TextWrapped = true
    label.TextXAlignment = Enum.TextXAlignment.Left
    label.TextYAlignment = Enum.TextYAlignment.Top
    label.ZIndex = 12
    label.Parent = parent
    return label
end

local function renderHome()
    clearView()
    panelTitle.Text = "HOME"
    local equipped = stringAttr("EquippedSpeciesId", "compy")
    local display = Config.SpeciesDisplayNames[equipped] or equipped
    track(textLine(content, "Equipped: " .. display, 4, 28, 18, true))
    track(textLine(content, "Grow by collecting food. Bigger dinosaurs can eat smaller ones.", 42, 50, 15, false))
    track(textLine(content, "End your run to bank dinosaur copies and any earned chests.", 100, 50, 15, false))
    track(textLine(content, "Collect 50 base copies of a dinosaur to create one Gold copy.", 158, 50, 15, false))
    local queue = numberAttr("ActiveChestCount")
    local overflow = numberAttr("PendingChestGrants")
    track(textLine(content, string.format("Chest queue: %d active, %d overflow", queue, overflow), 224, 30, 15, true))
end

local function renderCollection()
    clearView()
    panelTitle.Text = "DINOSAURS"
    local equipped = stringAttr("EquippedSpeciesId", "compy")
    local y = 0
    for _, speciesId in Config.SpeciesOrder do
        local base, gold = counts(speciesId)
        local owned = base + gold > 0
        local row = track(Instance.new("Frame"))
        row.Position = UDim2.fromOffset(0, y)
        row.Size = UDim2.new(1, 0, 0, 78)
        row.BackgroundColor3 = Color3.fromRGB(44, 59, 51)
        row.ZIndex = 12
        row.Parent = content
        rounded(row, 10)

        local display = Config.SpeciesDisplayNames[speciesId] or speciesId
        local name = Instance.new("TextLabel")
        name.BackgroundTransparency = 1
        name.Position = UDim2.fromOffset(12, 8)
        name.Size = UDim2.new(1, -220, 0, 24)
        name.Text = display .. (if equipped == speciesId then "  •  EQUIPPED" else "")
        name.TextColor3 = if owned then Color3.fromRGB(246, 238, 194) else Color3.fromRGB(156, 163, 157)
        name.Font = Enum.Font.GothamBold
        name.TextSize = 15
        name.TextXAlignment = Enum.TextXAlignment.Left
        name.ZIndex = 13
        name.Parent = row

        local countLabel = Instance.new("TextLabel")
        countLabel.BackgroundTransparency = 1
        countLabel.Position = UDim2.fromOffset(12, 38)
        countLabel.Size = UDim2.new(1, -220, 0, 24)
        countLabel.Text = string.format("%s base  •  %s Gold", tostring(base), tostring(gold))
        countLabel.TextColor3 = Color3.fromRGB(219, 226, 215)
        countLabel.Font = Enum.Font.GothamMedium
        countLabel.TextSize = 14
        countLabel.TextXAlignment = Enum.TextXAlignment.Left
        countLabel.ZIndex = 13
        countLabel.Parent = row

        local equip = Instance.new("TextButton")
        equip.AnchorPoint = Vector2.new(1, 0)
        equip.Position = UDim2.new(1, -10, 0, 8)
        equip.Size = UDim2.fromOffset(104, 28)
        equip.Text = if equipped == speciesId then "EQUIPPED" elseif owned then "EQUIP" else "LOCKED"
        equip.BackgroundColor3 = if owned then Color3.fromRGB(63, 91, 72) else Color3.fromRGB(66, 66, 66)
        equip.TextColor3 = Color3.new(1, 1, 1)
        equip.Font = Enum.Font.GothamBold
        equip.TextSize = 12
        equip.Active = owned and equipped ~= speciesId
        equip.AutoButtonColor = equip.Active
        equip.ZIndex = 13
        equip.Parent = row
        rounded(equip, 7)
        equip.Activated:Connect(function()
            if equip.Active then
                equipSpecies:FireServer(speciesId, HttpService:GenerateGUID(false))
            end
        end)

        local mutate = Instance.new("TextButton")
        mutate.AnchorPoint = Vector2.new(1, 0)
        mutate.Position = UDim2.new(1, -10, 0, 42)
        mutate.Size = UDim2.fromOffset(104, 28)
        mutate.Text = if base >= Config.GoldMutationCost then "MAKE GOLD" else string.format("%d / %d", base, Config.GoldMutationCost)
        mutate.BackgroundColor3 = if base >= Config.GoldMutationCost then Color3.fromRGB(153, 115, 35) else Color3.fromRGB(77, 72, 54)
        mutate.TextColor3 = Color3.fromRGB(255, 243, 194)
        mutate.Font = Enum.Font.GothamBold
        mutate.TextSize = 12
        mutate.Active = base >= Config.GoldMutationCost
        mutate.AutoButtonColor = mutate.Active
        mutate.ZIndex = 13
        mutate.Parent = row
        rounded(mutate, 7)
        mutate.Activated:Connect(function()
            if mutate.Active then
                mutateSpecies:FireServer(speciesId, "gold", HttpService:GenerateGUID(false))
            end
        end)

        y += 86
    end
end

local function parseChestQueue()
    local raw = player:GetAttribute("ChestQueueJson")
    if typeof(raw) ~= "string" or raw == "" then return {} end
    local ok, result = pcall(function()
        return HttpService:JSONDecode(raw)
    end)
    if not ok or typeof(result) ~= "table" then return {} end
    return result
end

local function renderChests()
    clearView()
    panelTitle.Text = "CHESTS"
    local queue = parseChestQueue()
    local now = workspace:GetServerTimeNow()
    local y = 0
    for slot = 1, Config.ChestQueueCapacity do
        local entry = queue[slot]
        local row = track(Instance.new("Frame"))
        row.Position = UDim2.fromOffset(0, y)
        row.Size = UDim2.new(1, -132, 0, 48)
        row.BackgroundColor3 = Color3.fromRGB(61, 52, 39)
        row.ZIndex = 12
        row.Parent = content
        rounded(row, 8)

        local label = Instance.new("TextLabel")
        label.BackgroundTransparency = 1
        label.Size = UDim2.new(1, -20, 1, 0)
        label.Position = UDim2.fromOffset(10, 0)
        label.TextColor3 = Color3.fromRGB(246, 232, 186)
        label.Font = Enum.Font.GothamBold
        label.TextSize = 14
        label.TextXAlignment = Enum.TextXAlignment.Left
        label.ZIndex = 13
        label.Parent = row
        if typeof(entry) == "table" and typeof(entry.readyAt) == "number" then
            local remaining = math.max(0, entry.readyAt - now)
            label.Text = string.format("Slot %d   %s", slot, if remaining <= 0 then "READY" else string.format("%.0fs", remaining))
        else
            label.Text = string.format("Slot %d   EMPTY", slot)
        end
        y += 54
    end

    local overflow = track(textLine(content, "Overflow: " .. tostring(numberAttr("PendingChestGrants")), 276, 24, 14, true))
    overflow.Size = UDim2.new(1, -132, 0, 24)

    local claim = track(Instance.new("TextButton"))
    claim.AnchorPoint = Vector2.new(1, 0)
    claim.Position = UDim2.new(1, 0, 0, 0)
    claim.Size = UDim2.fromOffset(120, 50)
    claim.BackgroundColor3 = Color3.fromRGB(142, 102, 42)
    claim.TextColor3 = Color3.fromRGB(255, 247, 219)
    claim.Font = Enum.Font.GothamBold
    claim.TextSize = 13
    claim.Text = "CLAIM NEXT"
    claim.ZIndex = 13
    claim.Parent = content
    rounded(claim, 9)

    local nextId = stringAttr("NextChestId", "")
    local nextReadyAt = numberAttr("NextChestReadyAt")
    local canClaim = nextId ~= "" and workspace:GetServerTimeNow() >= nextReadyAt
    claim.Active = canClaim
    claim.AutoButtonColor = canClaim
    if not canClaim then claim.Text = if nextId == "" then "NO CHEST" else "NOT READY" end
    claim.Activated:Connect(function()
        if canClaim then
            claimChest:FireServer(nextId, HttpService:GenerateGUID(false))
        end
    end)

    local reward = track(textLine(content, "Last reward: " .. stringAttr("LastChestRewardText", "none"), 64, 58, 13, false))
    reward.Position = UDim2.new(1, -120, 0, 64)
    reward.Size = UDim2.fromOffset(120, 58)
    reward.TextXAlignment = Enum.TextXAlignment.Center
end

homeButton.Activated:Connect(function() openModal("home") renderHome() end)
collectionButton.Activated:Connect(function() openModal("collection") renderCollection() end)
chestButton.Activated:Connect(function() openModal("chests") renderChests() end)

endButton.Activated:Connect(function()
    requestEndRun:FireServer()
end)

local tutorialShade = Instance.new("Frame")
tutorialShade.Size = UDim2.fromScale(1, 1)
tutorialShade.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
tutorialShade.BackgroundTransparency = 0.42
tutorialShade.Visible = false
tutorialShade.ZIndex = 20
tutorialShade.Parent = gui

local tutorial = Instance.new("Frame")
tutorial.AnchorPoint = Vector2.new(0.5, 0.5)
tutorial.Position = UDim2.fromScale(0.5, 0.5)
tutorial.Size = UDim2.fromOffset(500, 330)
tutorial.BackgroundColor3 = Color3.fromRGB(34, 50, 42)
tutorial.ZIndex = 21
tutorial.Parent = tutorialShade
rounded(tutorial, 16)
local tutorialScale = addScale(tutorial)

local tutorialTitle = Instance.new("TextLabel")
tutorialTitle.BackgroundTransparency = 1
tutorialTitle.Position = UDim2.fromOffset(22, 20)
tutorialTitle.Size = UDim2.new(1, -44, 0, 34)
tutorialTitle.Text = "HOW TO PLAY"
tutorialTitle.TextColor3 = Color3.fromRGB(247, 236, 177)
tutorialTitle.Font = Enum.Font.GothamBold
tutorialTitle.TextSize = 24
tutorialTitle.ZIndex = 22
tutorialTitle.Parent = tutorial

local tutorialText = Instance.new("TextLabel")
tutorialText.BackgroundTransparency = 1
tutorialText.Position = UDim2.fromOffset(28, 70)
tutorialText.Size = UDim2.new(1, -56, 0, 180)
tutorialText.Text = "1. Eat food to grow bigger.\n\n2. Bigger dinos can eat smaller dinos.\n\n3. End your run to bank dinosaur copies and chests.\n\n4. Collect duplicates, equip new dinos, and make Gold copies."
tutorialText.TextColor3 = Color3.fromRGB(237, 242, 231)
tutorialText.Font = Enum.Font.GothamMedium
tutorialText.TextSize = 16
tutorialText.TextWrapped = true
tutorialText.TextXAlignment = Enum.TextXAlignment.Left
tutorialText.TextYAlignment = Enum.TextYAlignment.Top
tutorialText.ZIndex = 22
tutorialText.Parent = tutorial

local gotIt = Instance.new("TextButton")
gotIt.AnchorPoint = Vector2.new(0.5, 1)
gotIt.Position = UDim2.new(0.5, 0, 1, -18)
gotIt.Size = UDim2.fromOffset(180, 48)
gotIt.BackgroundColor3 = Color3.fromRGB(70, 113, 77)
gotIt.TextColor3 = Color3.new(1, 1, 1)
gotIt.Font = Enum.Font.GothamBold
gotIt.TextSize = 15
gotIt.Text = "GOT IT"
gotIt.ZIndex = 22
gotIt.Parent = tutorial
rounded(gotIt, 10)

local tutorialDismissed = false
gotIt.Activated:Connect(function()
    tutorialDismissed = true
    tutorialShade.Visible = false
end)

local summaryShade = Instance.new("Frame")
summaryShade.Size = UDim2.fromScale(1, 1)
summaryShade.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
summaryShade.BackgroundTransparency = 0.48
summaryShade.Visible = false
summaryShade.ZIndex = 30
summaryShade.Parent = gui

local summary = Instance.new("Frame")
summary.AnchorPoint = Vector2.new(0.5, 0.5)
summary.Position = UDim2.fromScale(0.5, 0.5)
summary.Size = UDim2.fromOffset(460, 250)
summary.BackgroundColor3 = Color3.fromRGB(33, 47, 40)
summary.ZIndex = 31
summary.Parent = summaryShade
rounded(summary, 16)
local summaryScale = addScale(summary)

local summaryText = Instance.new("TextLabel")
summaryText.BackgroundTransparency = 1
summaryText.Position = UDim2.fromOffset(24, 20)
summaryText.Size = UDim2.new(1, -48, 1, -40)
summaryText.TextColor3 = Color3.fromRGB(244, 241, 218)
summaryText.Font = Enum.Font.GothamMedium
summaryText.TextSize = 16
summaryText.TextWrapped = true
summaryText.ZIndex = 32
summaryText.Parent = summary

local lastSummaryAt = 0
local function showSummary()
    local endAt = numberAttr("LastRunEndAt")
    if endAt <= 0 or endAt == lastSummaryAt then return end
    lastSummaryAt = endAt
    local reason = stringAttr("LastRunEndReason", "Run ended")
    local catches = numberAttr("LastRunCatchScore")
    local growth = numberAttr("LastRunGrowthScore")
    local reward = stringAttr("LastRewardText", "saving reward...")
    summaryText.Text = string.format(
        "RUN COMPLETE\n\nReason: %s\nGrowth: %d   •   Catches: %d\n\nReward: %s\n\nA new run will start automatically.",
        reason, growth, catches, reward
    )
    summaryShade.Visible = true
    task.delay(3.5, function()
        if lastSummaryAt == endAt then summaryShade.Visible = false end
    end)
end

local currentCharacter: Model? = nil
local currentHumanoid: Humanoid? = nil
local function onCharacter(character: Model)
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

local function refreshScales()
    local value = scaleForViewport()
    hudScale.Scale = value
    navScale.Scale = value
    panelScale.Scale = value
    tutorialScale.Scale = value
    summaryScale.Scale = value
end

local camera = workspace.CurrentCamera
if camera then camera:GetPropertyChangedSignal("ViewportSize"):Connect(refreshScales) end
refreshScales()

local elapsed = 0
RunService.Heartbeat:Connect(function(dt)
    elapsed += dt
    if elapsed < 0.12 then return end
    elapsed = 0

    local profile = stringAttr("ProfileState", "Loading")
    if profile == "Loaded" and not tutorialDismissed and not tutorialShade.Visible then
        tutorialShade.Visible = true
    end

    local character = currentCharacter
    local humanoid = currentHumanoid
    if character and player.Character == character and humanoid then
        local scaleValue = character:GetAttribute("VisualScale")
        local visualScale = if typeof(scaleValue) == "number" then scaleValue else 1
        player.CameraMinZoomDistance = Config.CameraMinZoom * visualScale
        humanoid.CameraOffset = Vector3.new(0, (visualScale - 1) * 2, 0)

        local growth = character:GetAttribute("GrowthScore")
        local catches = character:GetAttribute("CatchScore")
        local protection = character:GetAttribute("SpawnProtectionEndsAt")
        local safeRemaining = math.max(0, (if typeof(protection) == "number" then protection else 0) - workspace:GetServerTimeNow())
        local safety = if safeRemaining > 0 then string.format("SAFE %.0fs", safeRemaining) else "PVP"
        hudStats.Text = string.format(
            "Growth %d   •   Catches %d   •   %.2fx   •   %s",
            if typeof(growth) == "number" then growth else 0,
            if typeof(catches) == "number" then catches else 0,
            visualScale,
            safety
        )

        local state = character:GetAttribute("RunState")
        local exitEnd = character:GetAttribute("ExitChannelEndsAt")
        local exitRemaining = math.max(0, (if typeof(exitEnd) == "number" then exitEnd else 0) - workspace:GetServerTimeNow())
        endButton.Active = state == "Active" and profile == "Loaded"
        endButton.AutoButtonColor = endButton.Active
        endButton.Text = if exitRemaining > 0 then string.format("STAY STILL %.1fs", exitRemaining) else "END RUN"
    else
        hudStats.Text = if profile == "Loaded" then "Preparing next run..." else "Profile: " .. profile
        endButton.Active = false
        endButton.AutoButtonColor = false
        endButton.Text = "END RUN"
    end

    if activeView == "home" then renderHome()
    elseif activeView == "collection" then renderCollection()
    elseif activeView == "chests" then renderChests()
    end

    showSummary()
end)

player:GetAttributeChangedSignal("LastRunEndAt"):Connect(showSummary)

-- Keyboard convenience only; all core actions remain reachable by touch.
UserInputService.InputBegan:Connect(function(input, processed)
    if processed then return end
    if input.KeyCode == Enum.KeyCode.C then
        openModal("collection")
        renderCollection()
    elseif input.KeyCode == Enum.KeyCode.B then
        openModal("chests")
        renderChests()
    end
end)

print("[Be Dino] Core UI client ready")
