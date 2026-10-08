--!strict
local Theme=require(script.Parent.UITheme)
local Fragments=require(script.Parent.HatchFragments)
local geneticsModule=script.Parent:FindFirstChild("EggGenetics")
local Genetics=if geneticsModule then require(geneticsModule) else nil
local ContentProvider=game:GetService("ContentProvider")
local RunService=game:GetService("RunService")
local ModelPreview=require(script.Parent.ModelPreview)
local Appearance=require(script.Parent.EggAppearance)
local Hatch={}
local shellImage="rbxassetid://95856282289615"
local crackImage="rbxassetid://126956807167774"
local crunchId="rbxassetid://9120490790"
local chimeId="rbxassetid://9116394545"
local canvas=460
local unit=canvas/512
local trajectories={{12,-195,-28},{-175,-85,-105},{175,-100,110},{-135,-10,-150},{15,30,75},{145,-20,160},{-8,45,-40}}
function Hatch.add(parent: GuiObject,genes,rarityColor: Color3?,assets: {shell: string,cracks: string}?)
    local shellAsset=if assets then assets.shell else Theme.ImageIds.egg or shellImage
    local cracksAsset=if assets then assets.cracks else crackImage
    local color=rarityColor or Theme.Colors.gold
    local root=Instance.new("Frame")
    root.Name,root.BackgroundTransparency,root.Size,root.ZIndex,root.Parent="PremiumHatchEgg",1,UDim2.fromOffset(304,260),parent.ZIndex+1,parent
    local stage=Instance.new("Frame")
    stage.Name,stage.BackgroundTransparency,stage.AnchorPoint="EggLayers",1,Vector2.new(.5,.5)
    stage.Position,stage.Size,stage.ZIndex,stage.Parent=UDim2.fromScale(.5,.5),UDim2.fromOffset(canvas,canvas),root.ZIndex,root
    local scale=Instance.new("UIScale") scale.Parent=stage
    local tint=if genes and Genetics and Genetics.valid(genes) then Genetics.tint(genes) else Color3.new(1,1,1)
    local function image(parentObject: GuiObject,id: string,z: number)
        local result=Instance.new("ImageLabel")
        result.BorderSizePixel=0
        result.Image,result.BackgroundTransparency,result.Size,result.ScaleType=id,1,UDim2.fromScale(1,1),Enum.ScaleType.Stretch
        result.ZIndex,result.Parent=z,parentObject
        return result
    end
    local fallback=ModelPreview.add(root,"egg")
    fallback.Name="NativeHatchFallback"
    fallback.ZIndex=root.ZIndex+2
    Appearance.apply(fallback,genes)
    local authored=fallback:FindFirstChild("AuthoredBody",true)~=nil
    root:SetAttribute("ArtworkFallback",true)
    root:SetAttribute("ArtworkLoadState","Loading")
    local shell=image(stage,shellAsset,stage.ZIndex+2)
    shell.Name,shell.ImageColor3="PorcelainShell",tint
    shell.Visible=false
    local crackStages={}
    for i,region in {{210,107,95,128,.68},{151,224,210,83,1.48},{151,306,210,80,2.28}} do
        local mask=Instance.new("Frame")
        mask.Name,mask.BackgroundTransparency="CrackStage"..i,1
        mask.Position,mask.Size=UDim2.fromOffset(region[1]*unit,region[2]*unit),UDim2.fromOffset(region[3]*unit,0)
        mask.ZIndex,mask.Parent=stage.ZIndex+3,stage
        local cracks=image(mask,cracksAsset,mask.ZIndex)
        cracks.ImageRectOffset,cracks.ImageRectSize=Vector2.new(region[1],region[2]),Vector2.new(region[3],1)
        cracks.Visible=false
        table.insert(crackStages,{mask=mask,image=cracks,width=region[3],height=region[4],start=region[5]})
    end
    local halo=Instance.new("Frame")
    halo.Name,halo.BackgroundColor3,halo.BackgroundTransparency="HatchHalo",color,1
    halo.AnchorPoint,halo.Position,halo.Size=Vector2.new(.5,.5),UDim2.fromScale(.5,.5),UDim2.fromOffset(160,160)
    halo.ZIndex,halo.Parent=root.ZIndex,root
    local corner=Instance.new("UICorner") corner.CornerRadius=UDim.new(1,0) corner.Parent=halo
    local haloScale=Instance.new("UIScale") haloScale.Parent=halo
    local sounds={}
    local function sound(id: string,volume: number,pitch: number)
        local s=Instance.new("Sound")
        s.SoundId,s.Volume,s.PlaybackSpeed,s.Parent=id,volume,pitch,root
        table.insert(sounds,s)
        return s
    end
    local tap=sound(crunchId,.16,1.5)
    local crunch=sound(crunchId,.38,1)
    local chime=sound(chimeId,.24,1)
    task.spawn(function()
        local failed=shellAsset=="" or cracksAsset==""
        local images={shell}
        for _,step in crackStages do table.insert(images,step.image) end
        local ok=pcall(function() ContentProvider:PreloadAsync(images,function(_,status)
            if status~=Enum.AssetFetchStatus.Success then failed=true end
        end) end)
        if not root.Parent or root:GetAttribute("Opening") then return end
        local native=authored or not ok or failed
        root:SetAttribute("ArtworkFallback",native)
        root:SetAttribute("ArtworkLoadState",if native then "Unavailable" else "Loaded")
        fallback.Visible=native
        shell.Visible=not native
        task.spawn(function() pcall(function() ContentProvider:PreloadAsync({crunch,chime}) end) end)
    end)
    local pieces={}
    -- Cropped strips approximate jagged alpha masks without editing the bitmap.
    for index,polygon in Fragments.Polygons do
        if not Theme.MotionEnabled then break end
        local minX,minY,maxX,maxY=512,512,0,0
        for _,point in polygon do minX=math.min(minX,point[1]) minY=math.min(minY,point[2]) maxX=math.max(maxX,point[1]) maxY=math.max(maxY,point[2]) end
        local home=Vector2.new((minX+maxX)*.5*unit,(minY+maxY)*.5*unit)
        local group=Instance.new("CanvasGroup")
        group.Name,group.BackgroundTransparency,group.AnchorPoint="ShellFragment"..index,1,Vector2.new(.5,.5)
        group.Size,group.Position,group.Visible=UDim2.fromOffset((maxX-minX)*unit,(maxY-minY)*unit),UDim2.fromOffset(home.X,home.Y),false
        group.ZIndex,group.Parent=stage.ZIndex+4,stage
        local strips={}
        for y=107,383,4 do
            for _,span in Fragments.spans(polygon,y+2) do
                local left,right=span[1],span[2]
                local strip=image(group,shellAsset,group.ZIndex)
                strip.ImageColor3=tint
                -- Guard overlap avoids one-pixel seams when the phone UI scales.
                strip.ImageRectOffset,strip.ImageRectSize=Vector2.new(left,y),Vector2.new(right-left,6)
                strip.Position,strip.Size=UDim2.fromOffset((left-minX)*unit,(y-minY)*unit),UDim2.fromOffset((right-left)*unit,6*unit)
                table.insert(strips,strip)
            end
        end
        table.insert(pieces,{group=group,strips=strips,home=home})
    end
    local opening=false
    local lastTap=0
    local flight: RBXScriptConnection?=nil
    root.Destroying:Connect(function()
        if flight then flight:Disconnect() flight=nil end
        for _,s in sounds do if s.Parent==root then s:Stop() end end
    end)
    local function update(t: number)
        if opening or not root.Parent then return end
        local wobble=0
        for i,beat in {.62,1.42,2.22} do
            local age=t-beat
            if age>=0 and age<.32 then wobble+=math.sin(age*45)*math.exp(-age*10)*(2+i*1.6) end
            if t>=beat and lastTap<i then lastTap=i if Theme.HatchSoundEnabled~=false then tap:Play() end end
        end
        if t>=2.75 and t<3.12 then wobble=0 end
        if t>=3.12 then wobble=math.sin((t-3.12)*38)*5 end
        stage.Rotation=if Theme.MotionEnabled then wobble else 0
        scale.Scale=if Theme.MotionEnabled then 1+math.abs(wobble)*.004 else 1
        for _,step in crackStages do
            local height=math.floor(step.height*math.clamp((t-step.start)/.48,0,1))
            step.mask.Size=UDim2.fromOffset(step.width*unit,height*unit)
            step.image.ImageRectSize=Vector2.new(step.width,math.max(1,height))
            step.image.Visible=height>0 and root:GetAttribute("ArtworkFallback")~=true
        end
        halo.BackgroundTransparency=if Theme.MotionEnabled then 1-math.clamp((t-2.3)/1.1,0,1)*.12 else 1
        haloScale.Scale=1+math.clamp(t-2.7,0,.7)*.15
    end
    local function split(success: boolean?)
        if opening or not root.Parent then return end
        opening=true
        root:SetAttribute("Opening",true)
        if Theme.HatchSoundEnabled~=false then
            crunch.Parent=parent crunch:Play() game:GetService("Debris"):AddItem(crunch,2)
            if success~=false then chime.Parent=parent chime:Play() game:GetService("Debris"):AddItem(chime,3) end
        end
        if not Theme.MotionEnabled then root:Destroy() return end
        stage.Rotation=0 scale.Scale=1 shell.Visible=false fallback.Visible=false
        for _,step in crackStages do step.mask.Visible=false end
        for _,piece in pieces do piece.group.Visible=root:GetAttribute("ArtworkFallback")~=true end
        local ring=Instance.new("UIStroke") ring.Color,ring.Thickness,ring.Transparency,ring.Parent=color,2,.15,halo
        Theme.animate(halo,.48,{BackgroundTransparency=1})
        Theme.animate(haloScale,.48,{Scale=1.7})
        Theme.animate(ring,.48,{Transparency=1})
        if success~=false then
            for i=1,8 do
                local angle=i*math.pi/4
                local ray=Instance.new("Frame")
                ray.Name,ray.BorderSizePixel,ray.BackgroundColor3="RevealRay",0,color
                ray.AnchorPoint,ray.Size,ray.Rotation=Vector2.new(.5,.5),UDim2.fromOffset(3,18),i*45-90
                ray.Position,ray.ZIndex,ray.Parent=UDim2.new(.5,math.cos(angle)*62,.5,math.sin(angle)*62),root.ZIndex,root
                Theme.animate(ray,.38,{Position=UDim2.new(.5,math.cos(angle)*130,.5,math.sin(angle)*130),BackgroundTransparency=1})
            end
        end
        local started=os.clock()
        local accumulated=0
        flight=RunService.Heartbeat:Connect(function(dt)
            accumulated+=dt if accumulated<1/30 then return end accumulated=0
            local t=os.clock()-started
            if t>=.72 or not root.Parent or not Theme.MotionEnabled then
                if flight then flight:Disconnect() flight=nil end
                root:Destroy() return
            end
            for index,piece in pieces do
                local velocity=trajectories[index]
                local time=math.max(0,t-(if index==1 then 0 else .065))
                piece.group.Position=UDim2.fromOffset(piece.home.X+velocity[1]*time,piece.home.Y+velocity[2]*time+240*time*time)
                piece.group.Rotation=velocity[3]*time
                local fade=math.clamp((time-.22)/.4,0,1)
                piece.group.GroupTransparency=fade
            end
        end)
    end
    return root,update,split
end
return Hatch
