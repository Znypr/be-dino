--!strict
-- Runs before character spawning, including when profile loading cannot finish.
local ReplicatedFirst = game:GetService("ReplicatedFirst")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local player = Players.LocalPlayer
local gui = Instance.new("ScreenGui")
gui.Name = "StartupUI"
gui.IgnoreGuiInset = true
gui.ResetOnSpawn = false
gui.DisplayOrder = 100
gui.Parent = player:WaitForChild("PlayerGui")
local background = Instance.new("Frame")
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
ReplicatedFirst:RemoveDefaultLoadingScreen()
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
    if state == "Loaded" and character and character:GetAttribute("DinoAttached") then
        if connection then connection:Disconnect() end
        gui:Destroy()
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
