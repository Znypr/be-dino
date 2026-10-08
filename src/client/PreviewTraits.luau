--!strict
local TweenService = game:GetService("TweenService")
local Theme = require(game:GetService("ReplicatedStorage").Shared.UITheme)
local PreviewTraits = {}
function PreviewTraits.add(view: ViewportFrame, traits)
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
    if Theme.MotionEnabled then
        TweenService:Create(shine,TweenInfo.new(1.6,Enum.EasingStyle.Sine,Enum.EasingDirection.InOut,-1,true),{
            Position=UDim2.fromScale(.65,.5),Rotation=100,ImageTransparency=.65,
        }):Play()
    end
end
return PreviewTraits
