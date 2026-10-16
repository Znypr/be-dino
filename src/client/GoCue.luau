--!strict
-- BD-442 (docs/132): the single "go" cue for a new player at the cave hub. A soft pulsing glow ring plus the short label
-- "TAP TO GO!" on the EXPLORE ISLAND button, only until the first run starts (decisions: FtueRules.goCueShown). Reduce Motion
-- (Theme.MotionEnabled false): the ring stays, still, and the label stays. Pure UI code, no art asset.
local TweenService = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Rules = require(Shared:WaitForChild("FtueRules"))
local Theme = require(Shared:WaitForChild("UITheme"))
local RunService = game:GetService("RunService")
local Players = game:GetService("Players")

local Cue = {}

-- action = the EXPLORE ISLAND button; hasFoundEgg() and menuOpen() come from the caller. Updates itself 4 times a second.
function Cue.attach(action: TextButton, hasFoundEgg: () -> boolean, menuOpen: () -> boolean)
    local runStarted = false
    local ring = Instance.new("UIStroke")
    ring.Name, ring.Color, ring.Thickness, ring.Transparency, ring.Enabled = "GoCueRing", Color3.fromRGB(255, 240, 150), 5, 0.2, false
    ring.ApplyStrokeMode, ring.Parent = Enum.ApplyStrokeMode.Border, action
    local tag = Instance.new("TextLabel")
    tag.Name, tag.BackgroundTransparency, tag.AnchorPoint = "GoCueLabel", 1, Vector2.new(0.5, 1)
    tag.Position, tag.Size, tag.Text, tag.Visible = UDim2.new(0.5, 0, 0, -4), UDim2.new(1, 0, 0, 30), Rules.GoCueText, false
    tag.Font, tag.TextScaled, tag.TextColor3, tag.ZIndex = Enum.Font.FredokaOne, true, Color3.fromRGB(255, 240, 150), action.ZIndex + 1
    local limit = Instance.new("UITextSizeConstraint") limit.MinTextSize, limit.MaxTextSize, limit.Parent = 14, 24, tag
    Theme.TextStyle.apply(tag)
    tag.Parent = action
    local tween: Tween? = nil
    local function update()
        local character = Players.LocalPlayer.Character
        local runState = if character then character:GetAttribute("RunState") else nil
        if runState == "Active" then runStarted = true end
        local shown = Rules.goCueShown({ runState = runState, runStarted = runStarted, hasFoundEgg = hasFoundEgg(), menuOpen = menuOpen() })
        ring.Enabled, tag.Visible = shown, shown
        if shown and Theme.MotionEnabled then
            if not tween then
                local t = TweenService:Create(ring, TweenInfo.new(0.9, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true), { Transparency = 0.75 })
                tween = t
                t:Play()
            end
        elseif tween then
            (tween :: Tween):Cancel()
            tween = nil
            ring.Transparency = 0.2
        end
    end
    local elapsed = 0
    RunService.Heartbeat:Connect(function(dt)
        elapsed += dt
        if elapsed < 0.25 then return end
        elapsed = 0
        update()
    end)
end

return Cue
