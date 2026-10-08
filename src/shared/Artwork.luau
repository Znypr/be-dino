--!strict
local Assets = require(script.Parent.ArtworkAssets)
local Layout = require(script.Parent.ArtworkLayout)
local Art = {}
local function layer(parent: GuiObject, key: string, position: Vector2, size: number, z: number): ImageLabel?
    local uri = Assets[key]
    if not uri or uri == "" then return nil end
    local image = Instance.new("ImageLabel")
    image.Name, image.Image = key, uri
    image.BackgroundTransparency, image.ScaleType = 1, Enum.ScaleType.Fit
    image.AnchorPoint, image.Position = Vector2.new(.5,.5), UDim2.fromScale(position.X,position.Y)
    image.Size, image.ZIndex, image.Parent = UDim2.fromScale(size,size), z, parent
    return image
end
function Art.build(parent: GuiObject, id: string, native): Frame?
    local aura = string.match(id, "^aura_(%w+)$")
    local potion = string.match(id, "^potion_(%w+)$")
    if not aura and not potion and id ~= "catches" and id ~= "mutation_gold" and id ~= "mutation_diamond" then return nil end
    local root = Instance.new("Frame")
    root.Name,root.BackgroundTransparency,root.Size = "Artwork_"..id,1,UDim2.fromOffset(42,42)
    root.ZIndex,root.Parent = parent.ZIndex+1,parent
    local function fallback(key: string, position: Vector2?, size: number?)
        local icon = native(root,key)
        if icon then
            icon.AnchorPoint = Vector2.new(.5,.5)
            icon.Position,icon.Size = UDim2.fromScale((position or Vector2.new(.5,.5)).X,(position or Vector2.new(.5,.5)).Y),UDim2.fromScale(size or .88,size or .88)
            icon.ZIndex = root.ZIndex+2
        end
        return icon
    end
    if aura then
        -- Each ring remains independent; place another centerpiece or viewport above it.
        local key = "aura_"..aura.."_ring"
        if Assets[key] and Assets[key] ~= "" then
            for _, region in {{0,Layout.ringSplitY,1},{Layout.ringSplitY,1-Layout.ringSplitY,4}} do
                local clip = Instance.new("Frame")
                clip.Name,clip.BackgroundTransparency,clip.ClipsDescendants = "RingClip",1,true
                clip.Position,clip.Size = UDim2.fromScale(0,region[1]),UDim2.fromScale(1,region[2])
                clip.ZIndex,clip.Parent = root.ZIndex+region[3],root
                local image = layer(clip,key,Vector2.new(Layout.ringPosition.X,(Layout.ringPosition.Y-region[1])/region[2]),Layout.ringSize,clip.ZIndex)
                if image then image.Size=UDim2.fromScale(Layout.ringSize,Layout.ringSize/region[2]) end
            end
        else fallback("aura") end
        if not layer(root,"fossil_centerpiece",Layout.centerpiecePosition,Layout.centerpieceSize,root.ZIndex+2) then fallback("dinos",Layout.centerpiecePosition,.5) end
    elseif potion then
        local bottle = layer(root,"potion_"..potion.."_base",Layout.bottlePosition,Layout.bottleSize,root.ZIndex+1)
        if bottle then fallback(if potion == "growth" then "leaf" else "speed",Layout.symbolPosition,Layout.symbolSize) else fallback(potion) end
    elseif id == "catches" then
        for _, stamp in Layout.catches do
            local image = layer(root,"catches_mark",Vector2.new(stamp[1],stamp[2]),Layout.catchesSize,root.ZIndex+1)
            if image then image.Rotation = stamp[3] else
                local icon = fallback("dinos",Vector2.new(stamp[1],stamp[2]),.38)
                if icon then icon.Rotation = stamp[3] end
            end
        end
    else
        if not layer(root,id,Vector2.new(.5,.5),Layout.mutationSize,root.ZIndex+1) then fallback(if id == "mutation_gold" then "fusion" else "amber") end
    end
    return root
end
return Art
