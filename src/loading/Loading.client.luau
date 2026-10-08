--!strict
-- Runs before character spawning, including when profile loading cannot finish.
local ReplicatedFirst = game:GetService("ReplicatedFirst")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local player = Players.LocalPlayer
local gui = Instance.new("ScreenGui")
gui.Name = "StartupUI"
gui.IgnoreGuiInset = true
gui.ResetOnSpawn = false
gui.DisplayOrder = 100
gui.Parent = player:WaitForChild("PlayerGui")
local background = Instance.new("CanvasGroup")
background.Size = UDim2.fromScale(1, 1)
background.BackgroundColor3 = Color3.fromRGB(18, 40, 49)
background.Parent = gui
local message = Instance.new("TextLabel")
message.AnchorPoint = Vector2.new(0.5, 0.5)
message.Position = UDim2.fromScale(0.5, 0.5)
message.Size = UDim2.new(0.8, 0, 0.55, 0)
message.BackgroundTransparency = 1
message.TextColor3 = Color3.fromRGB(239, 247, 228)
message.Font = Enum.Font.GothamBold
message.TextSize = 22
message.TextWrapped = true
message.Text = "BE DINO!\n\nPreparing your island..."
message.Parent = background
local track=Instance.new("Frame")
track.AnchorPoint,track.Position,track.Size=Vector2.new(.5,0),UDim2.fromScale(.5,.76),UDim2.new(.6,0,0,8)
track.BackgroundColor3,track.BorderSizePixel,track.ZIndex,track.Parent=Color3.fromRGB(36,68,77),0,4,background
local fill=Instance.new("Frame")
fill.Size,fill.BackgroundColor3,fill.BorderSizePixel,fill.ZIndex,fill.Parent=UDim2.fromScale(.15,1),Color3.fromRGB(93,237,31),0,5,track
local progressTween: Tween?=nil
local lastStage=0
ReplicatedFirst:RemoveDefaultLoadingScreen()
task.spawn(function()
    local shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared", 10)
    local module = if shared then shared:FindFirstChild("UITheme") else nil
    if not module then return end
    local ok, theme = pcall(require, module)
    if not ok or theme.BackgroundImageId == "" then return end
    local image = Instance.new("ImageLabel")
    image.Size = UDim2.fromScale(1,1)
    image.ScaleType = Enum.ScaleType.Crop
    image.Image = theme.BackgroundImageId
    image.BackgroundTransparency = 1
    image.ZIndex = 1
    image.Parent = background
    local shade = Instance.new("Frame")
    shade.Size = UDim2.fromScale(1,1)
    shade.BackgroundColor3 = Color3.fromRGB(10,26,36)
    shade.BackgroundTransparency = .35
    shade.ZIndex = 2
    shade.Parent = background
    message.ZIndex = 3
end)
local started = os.clock()
local failures = {
    LoadFailed = "Your saved data could not load. Rejoin to retry. In a published Studio test, enable Studio API access under Game Settings > Security.",
    SessionBusy = "Your previous session is still closing. Wait a moment, then rejoin.",
    SchemaError = "Your save needs a version update. Please report this to Znypr.",
    LeaseLost = "Your save session changed. Rejoin before continuing.",
    SaveFailed = "Saving is unavailable. Rejoin before continuing.",
}
local connection: RBXScriptConnection?
connection = RunService.Heartbeat:Connect(function()
    local state = player:GetAttribute("ProfileState")
    local character = player.Character
    local mainUI=player.PlayerGui:FindFirstChild("BeDinoUI")
    local ready=state == "Loaded" and character and character:GetAttribute("DinoAttached") and mainUI and mainUI:GetAttribute("Ready")
    local stage=if ready then 3 elseif state=="Loaded" then 2 else 1
    if stage~=lastStage then
        lastStage=stage
        if progressTween then progressTween:Cancel() end
        progressTween=TweenService:Create(fill,TweenInfo.new(.2),{Size=UDim2.fromScale(({.2,.65,1})[stage],1)})
        progressTween:Play()
    end
    if ready then
        if connection then connection:Disconnect() end
        local fade=TweenService:Create(background,TweenInfo.new(.2),{GroupTransparency=1})
        fade.Completed:Once(function() gui:Destroy() end)
        fade:Play()
        return
    end
    local reason = failures[state :: any]
    if reason then
        message.Text = "CAN'T START YET\n\n" .. reason
    elseif player:GetAttribute("CharacterState") == "SpawnFailed" then
        message.Text = "CHARACTER COULD NOT SPAWN\n\nRejoin to retry. Check Studio Output for the character loading error."
    elseif os.clock() - started > 20 then
        message.Text = "TAKING LONGER THAN EXPECTED\n\nStatus: " .. tostring(state or "Server starting")
            .. "\nIf this does not finish, rejoin and check Studio Output. Your existing save has not been replaced."
    else
        message.Text = "BE DINO!\n\n" .. (if state == "Loaded" then "Preparing your dinosaur..." else "Loading your collection...")
    end
end)
