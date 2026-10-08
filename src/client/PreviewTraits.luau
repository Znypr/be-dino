--!strict
local RunService = game:GetService("RunService")
local Theme = require(game:GetService("ReplicatedStorage").Shared.UITheme)
local Appearance = require(game:GetService("ReplicatedStorage").Shared.EggAppearance)
local PreviewTraits = {}
function PreviewTraits.add(view: ViewportFrame, traits)
    if traits and traits.genes then Appearance.apply(view,traits.genes) end
    if not traits or not (traits.shiny or traits.big) then return end
    local badge = Instance.new("TextLabel")
    badge.Name = "TraitBadge"
    badge.BackgroundTransparency, badge.Size, badge.Position = 1, UDim2.new(1,0,0,26), UDim2.new(0,0,1,-26)
    badge.Font, badge.TextSize, badge.TextColor3 = Enum.Font.FredokaOne, 18, Theme.Colors.gold
    badge.TextScaled=true
    badge.Text = (if traits.shiny then "SHINY" else "") .. (if traits.shiny and traits.big then " + " else "") .. (if traits.big then "BIG" else "")
    badge.ZIndex, badge.Parent = view.ZIndex + 2, view
    if not traits.shiny then return end
    local shine = Instance.new("ImageLabel")
    shine.Name, shine.Image = "ShinyPreviewGlint", "rbxasset://textures/particles/sparkles_main.dds"
    shine.BackgroundTransparency, shine.ImageColor3 = 1, Color3.fromRGB(255,244,160)
    shine.Size, shine.Position, shine.ZIndex, shine.Parent = UDim2.fromScale(.23,.3), UDim2.fromScale(.15,.14), view.ZIndex+1, view
    local elapsed, accumulated=0,0
    local connection=RunService.Heartbeat:Connect(function(dt)
        if not Theme.MotionEnabled then shine.ImageTransparency=.3 return end
        local ancestor: Instance?=view
        while ancestor do
            if ancestor:IsA("GuiObject") and not ancestor.Visible then return end
            if ancestor:IsA("ScreenGui") and not ancestor.Enabled then return end
            ancestor=ancestor.Parent
        end
        elapsed+=dt accumulated+=dt
        if accumulated<1/20 then return end
        accumulated=0
        local phase=(1-math.cos(elapsed*math.pi/1.6))*.5
        shine.Position=UDim2.fromScale(.15+.5*phase,.14+.36*phase)
        shine.Rotation=100*phase
        shine.ImageTransparency=.65*phase
    end)
    view.Destroying:Connect(function() connection:Disconnect() end)
end
return PreviewTraits
