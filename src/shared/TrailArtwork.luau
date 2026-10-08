--!strict
-- Shared ribbon preview uses the catalog's real colors and taper, not a fabricated upload.
local Config=require(script.Parent.ProgressionConfig)
local Rules=require(script.Parent.ProgressionRules)
local Art={}
function Art.build(parent: GuiObject,id: string): Frame?
    local item=Rules.item(Config.Trails,id)
    if not item then return nil end
    local root=Instance.new("Frame")
    root.Name,root.BackgroundTransparency,root.Size,root.ZIndex,root.Parent="TrailArtwork_"..id,1,UDim2.fromScale(1,1),parent.ZIndex+1,parent
    for lane=1,2 do for i=1,28 do
        local t=(i-1)/27
        local part=Instance.new("Frame")
        local nextT=i/27
        local x,y=.12+t*.76,.34+(lane-1)*.2+math.sin(t*math.pi*1.5)*.14
        local dx,dy=(nextT-t)*.76,(math.sin(nextT*math.pi*1.5)-math.sin(t*math.pi*1.5))*.14
        part.AnchorPoint,part.Position=Vector2.new(.5,.5),UDim2.fromScale(x,y)
        part.Size=UDim2.fromScale(math.sqrt(dx*dx+dy*dy)*2.2,.045*(1-t*.75))
        part.Rotation=math.deg(math.atan2(dy,dx))
        part.BackgroundColor3=Color3.fromRGB(item.color[1],item.color[2],item.color[3]):Lerp(Color3.fromRGB(item.accent[1],item.accent[2],item.accent[3]),t)
        part.BackgroundTransparency,part.BorderSizePixel,part.ZIndex,part.Parent=t*.7,0,root.ZIndex,root
        local corner=Instance.new("UICorner") corner.CornerRadius,corner.Parent=UDim.new(1,0),part
    end end
    return root
end
return Art
