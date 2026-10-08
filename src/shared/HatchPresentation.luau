--!strict
-- Matched 512px Blender layers keep shell fractures attached during motion.
local Theme=require(script.Parent.UITheme)
local geneticsModule=script.Parent:FindFirstChild("EggGenetics")
local Genetics=if geneticsModule then require(geneticsModule) else nil
local ContentProvider=game:GetService("ContentProvider")
local Hatch={}
local shellImage="rbxassetid://95856282289615"
local crackImage="rbxassetid://126956807167774"
function Hatch.add(parent: GuiObject,genes)
    local root=Instance.new("Frame")
    root.Name,root.BackgroundTransparency,root.Size,root.ZIndex,root.Parent="PremiumHatchEgg",1,UDim2.fromOffset(304,260),parent.ZIndex+1,parent
    local stage=Instance.new("Frame")
    stage.Name,stage.BackgroundTransparency,stage.AnchorPoint="EggLayers",1,Vector2.new(.5,.5)
    stage.Position,stage.Size,stage.ZIndex,stage.Parent=UDim2.fromScale(.5,.5),UDim2.fromOffset(420,420),root.ZIndex,root
    local scale=Instance.new("UIScale") scale.Parent=stage
    local tint=if genes and Genetics and Genetics.valid(genes) then Genetics.tint(genes) else Color3.new(1,1,1)
    local halves={}
    local cracks={}
    for side=0,1 do
        local group=Instance.new("Frame")
        group.Name,group.BackgroundTransparency="ShellHalf"..side,1
        group.Size,group.Position,group.ZIndex,group.Parent=UDim2.fromScale(.5,1),UDim2.fromScale(side*.5,0),stage.ZIndex,stage
        for layer,id in {shellImage,crackImage} do
            local image=Instance.new("ImageLabel")
            image.Name=if layer==1 then "PorcelainShell" else "BranchingFractures"
            image.Image,image.ImageRectOffset,image.ImageRectSize=id,Vector2.new(side*256,0),Vector2.new(256,512)
            image.Size,image.BackgroundTransparency,image.ScaleType=UDim2.fromScale(1,1),1,Enum.ScaleType.Stretch
            image.ImageColor3=if layer==1 then tint else Color3.new(1,1,1)
            image.ImageTransparency=if layer==1 then 0 else 1
            image.ZIndex,image.Parent=group.ZIndex+layer,group
            if layer==2 then table.insert(cracks,image) end
        end
        table.insert(halves,group)
    end
    task.spawn(function() pcall(function() ContentProvider:PreloadAsync({shellImage,crackImage}) end) end)
    local opening=false
    local function update(t: number)
        if opening or not root.Parent then return end
        if Theme.MotionEnabled then
            stage.Rotation=math.sin(t*(9+t*4))*math.min(8,t*3)
            scale.Scale=1+math.sin(t*12)*.012*math.min(1,t)
        else stage.Rotation=0 scale.Scale=1 end
        local visibility=math.clamp((t-1.55)/1.1,0,1)
        for _,image in cracks do image.ImageTransparency=1-visibility end
    end
    local function split()
        if opening or not root.Parent then return end
        opening=true stage.Rotation=0
        for side,half in halves do
            local direction=if side==1 then -1 else 1
            Theme.animate(half,.24,{Position=UDim2.fromScale((side-1)*.5+direction*.17,.07),Rotation=direction*18})
            for _,image in half:GetChildren() do
                if image:IsA("ImageLabel") then Theme.animate(image,.24,{ImageTransparency=1}) end
            end
        end
        task.delay(if Theme.MotionEnabled then .25 else 0,function() root:Destroy() end)
    end
    return root,update,split
end
return Hatch
