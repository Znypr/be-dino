--!strict
-- Trailer clip director (docs/133). DEV ONLY: does nothing unless RunService:IsStudio() AND Config.DemoDirectorEnabled (false in every
-- committed build, pinned by release_profiles.py). Plays a shot list (tools/demo/shots/*.json) on this client: camera moves, HUD hide,
-- letterbox, title cards and lower-thirds, and Studio demo triggers through the server's DemoTrigger RemoteFunction (src/server/DemoTriggerService.luau, which is itself
-- unreachable unless unpublished Studio + Config.DemoDirectorEnabled). It changes no shipped gameplay.
-- Start: set the StringValue Players.LocalPlayer.BeDinoDemoShot.Value to the shot list JSON (tools/demo/run_shot.py prints the snippet).
local RunService = game:GetService("RunService")
if not RunService:IsStudio() then return end
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
if Config.DemoDirectorEnabled ~= true then return end

local Players = game:GetService("Players")
local HttpService = game:GetService("HttpService")
local StarterGui = game:GetService("StarterGui")
local TweenService = game:GetService("TweenService")
local Theme = require(Shared:WaitForChild("UITheme"))
local Shots = require(Shared:WaitForChild("DemoShots"))
local C = Theme.Colors
local player = Players.LocalPlayer

local slot = Instance.new("StringValue")
slot.Name = "BeDinoDemoShot"
slot.Parent = player

local gui = Instance.new("ScreenGui")
gui.Name, gui.ResetOnSpawn, gui.DisplayOrder, gui.IgnoreGuiInset = "BeDinoDemoDirector", false, 999, true
gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
gui.Parent = player:WaitForChild("PlayerGui")

local function bar(name: string, anchorY: number): Frame
    local f = Instance.new("Frame")
    f.Name, f.BackgroundColor3, f.BorderSizePixel = name, Color3.new(0, 0, 0), 0
    f.AnchorPoint, f.Position, f.Size = Vector2.new(0, anchorY), UDim2.fromScale(0, anchorY), UDim2.fromScale(1, 0)
    f.Parent = gui
    return f
end
local topBar, bottomBar = bar("LetterTop", 0), bar("LetterBottom", 1)

local function styled(label: TextLabel, size: number)
    label.Font, label.TextSize, label.TextColor3 = Enum.Font.FredokaOne, size, C.text
    label.TextStrokeColor3, label.TextStrokeTransparency = C.outline, 0
    label.BackgroundTransparency, label.TextWrapped = 1, true
end

local title = Instance.new("TextLabel")
title.Name, title.AnchorPoint, title.Visible = "TitleCard", Vector2.new(0.5, 0.5), false
styled(title, 64)
title.TextColor3 = C.gold
title.Parent = gui
local lower = Instance.new("TextLabel")
lower.Name, lower.AnchorPoint, lower.Visible, lower.TextXAlignment = "LowerThird", Vector2.new(0, 1), false, Enum.TextXAlignment.Left
styled(lower, 36)
lower.Parent = gui

-- Full-screen black cover (shot.blackout): hides respawns and teleports between ability shots.
local cover = Instance.new("Frame")
cover.Name, cover.BackgroundColor3, cover.BorderSizePixel, cover.Size, cover.Visible, cover.ZIndex = "BlackCover", Color3.new(0, 0, 0), 0, UDim2.fromScale(1, 1), false, 0
cover.Parent = gui
title.ZIndex, lower.ZIndex = 5, 5
topBar.ZIndex, bottomBar.ZIndex = 3, 3

-- Chrome hiding (list.hideChrome): everything in the main game UI except the modal layer (the hatch screen lives in ModalScrim) and
-- toasts, so a clip shows the world or the hatch modal only: no menu buttons, goals, build badge, "Skip all". Enforced every frame
-- because the game's own scripts flip those frames back on.
local chromeKeep = {ModalScrim = true, Toasts = true, RevealFlash = true}
local chromeOn = false
local function enforceChrome()
    local main = player.PlayerGui:FindFirstChild("BeDinoUI")
    if not main then return end
    for _, child in main:GetChildren() do
        if child:IsA("GuiObject") and not chromeKeep[child.Name] then child.Visible = false end
    end
    local skip = main:FindFirstDescendant("SkipAll")
    if skip and skip:IsA("GuiObject") then skip.Visible = false end
end

local hiddenGuis: {ScreenGui} = {}
local function setHud(visible: boolean)
    if visible then
        for _, g in hiddenGuis do g.Enabled = true end
        hiddenGuis = {}
        pcall(function() StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.All, true) end)
    else
        for _, g in player.PlayerGui:GetChildren() do
            if g:IsA("ScreenGui") and g ~= gui and g.Enabled and g.Name ~= "BeDinoUI" then
                g.Enabled = false
                table.insert(hiddenGuis, g)
            end
        end
        pcall(function() StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.All, false) end)
    end
end

local function layout(aspect: string)
    local safe = Shots.SafeInsets[aspect]
    title.Position, title.Size = UDim2.fromScale(0.5, 0.5), UDim2.fromScale(1 - safe.x * 2, 0.3)
    lower.Position, lower.Size = UDim2.fromScale(safe.x, 1 - safe.y), UDim2.fromScale(1 - safe.x * 2, 0.1)
    title.TextSize = if aspect == "9:16" then 56 else 72
end

local function fadeBars(on: boolean, seconds: number)
    local size = UDim2.fromScale(1, if on then 0.11 else 0)
    TweenService:Create(topBar, TweenInfo.new(seconds, Enum.EasingStyle.Sine), {Size = size}):Play()
    TweenService:Create(bottomBar, TweenInfo.new(seconds, Enum.EasingStyle.Sine), {Size = size}):Play()
end

local function spotPosition(id: string): Vector3?
    local ok, layoutModule = pcall(function() return require(Shared:WaitForChild("CaveHubLayout")) end)
    if not ok then return nil end
    local item = (layoutModule :: any).get().byId[id]
    if not item then return nil end
    return Vector3.new(item.x, (layoutModule :: any).FloorY + 3, item.z + (layoutModule :: any).CenterZ)
end

-- Scripted input (move / jump): applied after the default control script each frame so it wins over the (idle) real controls.
local scripted = {moveX = 0, moveZ = 0, moveUntil = 0, jumpUntil = 0}
RunService:BindToRenderStep("BeDinoDemoInput", Enum.RenderPriority.Input.Value + 1, function()
    local c = player.Character
    local hum = if c then c:FindFirstChildOfClass("Humanoid") else nil
    if not hum then return end
    local now = os.clock()
    if now < scripted.moveUntil then hum:Move(Vector3.new(scripted.moveX, 0, scripted.moveZ), false) end
    if now < scripted.jumpUntil then hum.Jump = true end
end)

local function groundPoint(x: number, z: number): Vector3?
    local params = RaycastParams.new()
    params.IgnoreWater = true
    local hit = workspace:Raycast(Vector3.new(x, 400, z), Vector3.new(0, -800, 0), params)
    return if hit then hit.Position + Vector3.new(0, 4, 0) else nil
end

local function remoteEvent(name: string): RemoteEvent?
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    local found = folder and folder:FindFirstChild(name)
    if found and found:IsA("RemoteEvent") then return found end
    warn("[DemoDirector] remote event missing (is Config.ClassMovementEnabled on in this build?): " .. name)
    return nil
end

local function fire(trig: any)
    if trig.kind == "remote" then
        local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
        local remote = folder and folder:FindFirstChild(trig.remote)
        if remote and remote:IsA("RemoteFunction") then
            for _ = 1, trig.repeatCount or 1 do
                local args = trig.args or {}
                local ok, result, status = pcall(function() return (remote :: RemoteFunction):InvokeServer(table.unpack(args)) end)
                if not ok or result ~= true then warn("[DemoDirector] " .. tostring(trig.remote) .. " refused: " .. tostring(if ok then status else result)) end
                task.wait(trig.gap or 0.3)
            end
        else
            warn("[DemoDirector] remote missing or not enabled (needs unpublished Studio + Config.DemoDirectorEnabled): " .. tostring(trig.remote))
        end
    elseif trig.kind == "teleport" then
        local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
        local pos = if trig.ground and trig.pos then groundPoint(trig.pos[1], trig.pos[3]) elseif trig.pos then Vector3.new(trig.pos[1], trig.pos[2], trig.pos[3]) else spotPosition(trig.spot)
        if root and pos then
            local face = if trig.face then Vector3.new(trig.face[1], 0, trig.face[2]) else nil
            local part = root :: BasePart
            part.CFrame = if face then CFrame.lookAt(pos, pos + face) else CFrame.new(pos)
            part.AssemblyLinearVelocity = Vector3.zero
        end
    elseif trig.kind == "move" then
        scripted.moveX, scripted.moveZ, scripted.moveUntil = trig.dir[1], trig.dir[2], os.clock() + trig.seconds
    elseif trig.kind == "jump" then
        scripted.jumpUntil = os.clock() + 0.15
    elseif trig.kind == "glide" then -- the real client behaviour of holding jump in the air: one boolean to the server, released afterwards
        local glide = remoteEvent("ClassGlide")
        if glide then
            glide:FireServer(true)
            task.wait(trig.seconds)
            glide:FireServer(false)
        end
    elseif trig.kind == "dash" then -- same request the jump input sends for a Water dino; the real client script applies the answer
        local dash = remoteEvent("ClassDash")
        if dash then dash:FireServer() end
    elseif trig.kind == "closeModal" then
        player:SetAttribute("DemoCloseModal", true)
    elseif trig.kind == "startHatch" then
        for _ = 1, trig.repeatCount or 1 do -- one press opens the first egg; each repeat taps "next egg" like a player would
            player:SetAttribute("DemoStartHatch", true)
            task.wait(trig.gap or 5)
        end
    elseif trig.kind == "hud" then
        setHud(trig.visible)
    elseif trig.kind == "note" then
        print("[DemoDirector] " .. tostring(trig.text))
    end
end

local running = false
local function play(list: any)
    running = true
    player:SetAttribute("DemoSkipTutorial", true) -- no welcome modal over the clip
    chromeOn = list.hideChrome == true
    local cam = workspace.CurrentCamera
    local lastSubject: {number}? = nil
    local prevType, prevSubject = cam.CameraType, cam.CameraSubject
    layout(list.aspect)
    if list.hideHud ~= false then setHud(false) end
    if list.letterbox ~= false then fadeBars(true, 0.6) end
    cam.CameraType = Enum.CameraType.Scriptable
    for _, shot in list.shots do
        if shot.title then title.Text, title.Visible = shot.title, true else title.Visible = false end
        if shot.lowerThird then lower.Text, lower.Visible = shot.lowerThird, true else lower.Visible = false end
        local blackout = shot.blackout or 0
        cover.BackgroundTransparency, cover.Visible = 0, blackout > 0
        local coverLifted = blackout <= 0
        local started = os.clock()
        local fired: {[number]: boolean} = {}
        while true do
            local elapsed = os.clock() - started
            if elapsed >= shot.duration then break end
            for i, trig in shot.triggers or {} do
                if not fired[i] and elapsed >= trig.at then
                    fired[i] = true
                    task.spawn(fire, trig)
                end
            end
            if not coverLifted and elapsed >= blackout then
                coverLifted = true
                title.Visible = false -- a title card belongs to the black part only
                TweenService:Create(cover, TweenInfo.new(0.5), {BackgroundTransparency = 1}):Play()
                task.delay(0.55, function() cover.Visible = false end)
            end
            if chromeOn then enforceChrome() end
            local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
            if root then lastSubject = {(root :: BasePart).Position.X, (root :: BasePart).Position.Y, (root :: BasePart).Position.Z} end
            local p, l = Shots.cameraPose(shot.camera, elapsed / shot.duration, lastSubject)
            cam.CFrame = CFrame.lookAt(Vector3.new(p[1], p[2], p[3]), Vector3.new(l[1], l[2], l[3]))
            RunService.RenderStepped:Wait()
        end
    end
    title.Visible, lower.Visible, cover.Visible, chromeOn = false, false, false, false
    scripted.moveUntil, scripted.jumpUntil = 0, 0
    fadeBars(false, 0.6)
    task.wait(0.6)
    setHud(true)
    cam.CameraType, cam.CameraSubject = prevType, prevSubject
    running = false
end

slot.Changed:Connect(function(value: string)
    if running or value == "" then return end
    local ok, list = pcall(function() return HttpService:JSONDecode(value) end)
    if not ok then warn("[DemoDirector] bad JSON: " .. tostring(list)) return end
    local err = Shots.validate(list)
    if err then warn("[DemoDirector] invalid shot list: " .. err) return end
    task.spawn(play, list)
    slot.Value = ""
end)
print("[DemoDirector] ready (Studio, Config.DemoDirectorEnabled): set Players.LocalPlayer.BeDinoDemoShot.Value to a shot list JSON")
