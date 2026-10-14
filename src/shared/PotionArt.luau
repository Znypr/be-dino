--!strict
-- Native vector potion icons (docs/68). No image assets and no symbol on the glass:
-- the effect family sets the bottle SHAPE and liquid colour, the rarity sets cork, trim, glow and pip count.
local PotionArt = {}
PotionArt.Rarities = {"Common","Uncommon","Rare","Epic","Legendary"}
PotionArt.RarityColor = {
    Common=Color3.fromRGB(176,188,200), Uncommon=Color3.fromRGB(93,237,31), Rare=Color3.fromRGB(46,206,255),
    Epic=Color3.fromRGB(194,86,255), Legendary=Color3.fromRGB(255,210,43),
}
-- body = {x,y,w,h}, neck = {x,w,top,height}, corner = body corner radius (scale), all fractions of the 42x42 root.
PotionArt.Shapes = {
    speed={body={.30,.34,.40,.52}, neck={.40,.20,.14,.22}, corner=.5, liquid=Color3.fromRGB(64,214,255)}, -- tall slim flask, cyan
    growth={body={.18,.42,.64,.46}, neck={.38,.24,.20,.24}, corner=1, liquid=Color3.fromRGB(98,236,112)}, -- round flask, green
    loot={body={.16,.48,.68,.38}, neck={.30,.40,.30,.20}, corner=.3, liquid=Color3.fromRGB(255,170,48)}, -- wide squat jar, amber
}
local function frame(parent: GuiObject, name: string, x: number, y: number, w: number, h: number, color: Color3, z: number, corner: number?, transparency: number?)
    local f = Instance.new("Frame")
    f.Name, f.BackgroundColor3, f.BorderSizePixel, f.ZIndex = name, color, 0, z
    f.BackgroundTransparency = transparency or 0
    f.Position, f.Size = UDim2.fromScale(x,y), UDim2.fromScale(w,h)
    if corner then
        local c = Instance.new("UICorner")
        c.CornerRadius, c.Parent = UDim.new(corner,0), f
    end
    f.Parent = parent
    return f
end
local function stroke(parent: GuiObject, color: Color3, thickness: number)
    local s = Instance.new("UIStroke")
    s.Color, s.Thickness, s.Parent = color, thickness, parent
    return s
end
function PotionArt.rarityIndex(rarity: string): number
    return table.find(PotionArt.Rarities, rarity) or 1
end
function PotionArt.build(root: GuiObject, kind: string, rarity: string)
    local shape = PotionArt.Shapes[kind] or PotionArt.Shapes.speed
    local tier = PotionArt.rarityIndex(rarity)
    local trim = PotionArt.RarityColor[rarity] or PotionArt.RarityColor.Common
    local z = root.ZIndex + 1
    -- Glow plate: invisible for Common, strengthening each tier; Epic/Legendary get a bright rim.
    local glow = frame(root, "RarityGlow", .02, .02, .96, .96, trim, z, .3, if tier == 1 then 1 else 0.9 - tier * .1)
    if tier >= 4 then stroke(glow, trim, tier - 2) end
    local b, n = shape.body, shape.neck
    local neck = frame(root, "Neck", n[1], n[3], n[2], n[4] + .06, Color3.fromRGB(214,238,246), z + 1, .2, .25)
    local body = frame(root, "Glass", b[1], b[2], b[3], b[4], Color3.fromRGB(214,238,246), z + 1, shape.corner, .25)
    stroke(body, trim, if tier >= 3 then 2 else 1)
    -- Liquid fills the lower 65% of the body, clipped by matching corners.
    frame(body, "Liquid", .06, .35, .88, .59, shape.liquid, z + 2, shape.corner, .05)
    frame(body, "Shine", .14, .14, .12, .3, Color3.new(1,1,1), z + 3, 1, .45)
    frame(root, "Cork", n[1] - .02, n[3] - .06, n[2] + .04, .1, trim, z + 3, .35)
    -- Pips (1 per tier) make rarity readable without colour.
    for i = 1, tier do
        frame(root, "Pip", .5 + (i - (tier + 1) / 2) * .11 - .03, .92, .06, .06, trim, z + 3, 1)
    end
    return neck
end
return PotionArt
