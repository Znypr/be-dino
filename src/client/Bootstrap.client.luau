--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local player = Players.LocalPlayer
player.CameraMode = Enum.CameraMode.Classic
player.CameraMaxZoomDistance = Config.CameraMaxZoom

local gui = Instance.new("ScreenGui")
gui.Name = "PrototypeHUD"
gui.ResetOnSpawn = false
gui.Parent = player:WaitForChild("PlayerGui")
local panel = Instance.new("TextLabel")
panel.Position = UDim2.new(0.5, 0, 0, 12)
panel.AnchorPoint = Vector2.new(0.5, 0)
panel.Size = UDim2.new(0.9, 0, 0, 88)
panel.BackgroundColor3 = Color3.fromRGB(32, 49, 42)
panel.BackgroundTransparency = 0.12
panel.TextColor3 = Color3.fromRGB(249, 243, 218)
panel.Font = Enum.Font.GothamMedium
panel.TextSize = 16
panel.TextWrapped = true
panel.Parent = gui
local corner = Instance.new("UICorner")
corner.CornerRadius = UDim.new(0, 12)
corner.Parent = panel
local limit = Instance.new("UISizeConstraint")
limit.MaxSize = Vector2.new(640, 100)
limit.Parent = panel

local scaleConnection: RBXScriptConnection? = nil
local function onCharacter(character: Model)
    if scaleConnection then scaleConnection:Disconnect() end
    local humanoid = character:WaitForChild("Humanoid", 10) :: Humanoid?
    if not humanoid or player.Character ~= character then return end
    humanoid:SetStateEnabled(Enum.HumanoidStateType.Jumping, false)
    local function update()
        local scale = character:GetAttribute("VisualScale") or 1
        player.CameraMinZoomDistance = Config.CameraMinZoom * scale
        humanoid.CameraOffset = Vector3.new(0, (scale - 1) * 2, 0)
        panel.Text = "BE DINO!  •  MOVEMENT PROTOTYPE\nMove: WASD / thumbstick   •   Look: drag / right mouse\nWalk onto a size pad: 1× / 2× / 4×   •   Current: " .. tostring(scale) .. "×"
    end
    scaleConnection = character:GetAttributeChangedSignal("VisualScale"):Connect(update)
    local camera = workspace.CurrentCamera
    if camera then
        camera.CameraType = Enum.CameraType.Custom
        camera.CameraSubject = humanoid
    end
    update()
end
player.CharacterAdded:Connect(onCharacter)
if player.Character then task.spawn(onCharacter, player.Character) end
