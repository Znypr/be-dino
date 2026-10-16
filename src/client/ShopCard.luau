--!strict
-- BD-267: shared look for shop cards. Applies ShopCardState.look: sold out / locked cards turn grey and quiet,
-- owned cards get a soft tint, and the button is disabled when it cannot be used. Styling only; callers keep
-- their own layout and text.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared.UITheme)
local State = require(Shared.ShopCardState)
local C = Theme.Colors
local Card = {}
Card.SoldOutColor = Color3.fromRGB(70, 72, 82)
Card.CalmText = Color3.fromRGB(190, 195, 205)

function Card.cardColor(base: Color3, look): Color3
    if look.kind == State.SoldOut or look.kind == State.Locked then return Card.SoldOutColor:Lerp(base, .12) end
    if look.kind == State.Owned then return base:Lerp(C.panel, .35) end
    return base
end

function Card.captionColor(look): Color3
    return if look.tone == "calm" then Card.CalmText else C.gold
end

function Card.styleButton(button: TextButton, look, activeColor: Color3)
    button.Text = look.buttonText
    button.Active = look.active
    button.AutoButtonColor = look.active
    button.BackgroundColor3 = if look.active then activeColor else Card.SoldOutColor
    button.TextTransparency = if look.active then 0 else .25
end

return Card
