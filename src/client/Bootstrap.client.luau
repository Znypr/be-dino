--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local Lighting = game:GetService("Lighting")
local Input = game:GetService("UserInputService")
local Http = game:GetService("HttpService")
local player = Players.LocalPlayer
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Theme = require(Shared.UITheme)
local Preview = require(Shared.DinosaurPreview)
local ModelPreview = require(Shared.ModelPreview)
local C = Theme.Colors
local remotes = ReplicatedStorage:WaitForChild("BeDinoRemotes")
local startRun = remotes:WaitForChild("RequestStartRun") :: RemoteEvent
local endRun = remotes:WaitForChild("RequestEndRun") :: RemoteEvent
local equip = remotes:WaitForChild("EquipSpecies") :: RemoteEvent
local hatch = remotes:WaitForChild("ClaimChest") :: RemoteEvent
local fuse = remotes:WaitForChild("MutateSpecies") :: RemoteEvent
local gui = Instance.new("ScreenGui")
gui.Name,gui.ResetOnSpawn,gui.ZIndexBehavior = "BeDinoUI",false,Enum.ZIndexBehavior.Sibling
gui.Parent = player:WaitForChild("PlayerGui")
local blur = Instance.new("BlurEffect")
blur.Name,blur.Size,blur.Parent = "BeDinoModalBlur",0,Lighting
local motion = true
local active = ""
local selected = "compy"
local seenTutorial = false
local lastGrowth = 0
local function num(id: string): number return player:GetAttribute(id) or 0 end
local function str(id: string,fallback: string?): string return player:GetAttribute(id) or fallback or "" end
local function copies(id: string): (number,number)
    local prefix = ({compy="Compy",triceratops="Triceratops",tyrannosaurus="Tyrannosaurus"})[id]
    return num(prefix.."Copies"),num(prefix.."Gold")
end
local function label(parent: Instance,text: string,x: number,y: number,w: number,h: number,size: number,color: Color3?): TextLabel
    local t = Instance.new("TextLabel")
    t.BackgroundTransparency,t.Position,t.Size = 1,UDim2.fromOffset(x,y),UDim2.fromOffset(w,h)
    t.Font,t.TextSize,t.Text,t.TextColor3 = Enum.Font.FredokaOne,size,text,color or C.text
    t.TextStrokeTransparency,t.TextStrokeColor3 = 0,C.outline
    t.TextWrapped,t.ZIndex,t.Parent = true,if parent:IsA("GuiObject") then parent.ZIndex+1 else 1,parent
    local outline = Instance.new("UIStroke")
    outline.ApplyStrokeMode,outline.Color,outline.Thickness,outline.Parent = Enum.ApplyStrokeMode.Contextual,C.outline,2,t
    return t
end
local function box(parent: Instance,x: number,y: number,w: number,h: number,color: Color3,z: number): Frame
    local b = Instance.new("Frame")
    b.Position,b.Size,b.BackgroundColor3,b.ZIndex,b.Parent = UDim2.fromOffset(x,y),UDim2.fromOffset(w,h),color,z,parent
    Theme.decorate(b,5)
    return b
end
local function button(parent: Instance,text: string,x: number,y: number,w: number,h: number,color: Color3,callback): TextButton
    local b = Instance.new("TextButton")
    b.Position,b.Size,b.BackgroundColor3 = UDim2.fromOffset(x,y),UDim2.fromOffset(w,h),color
    b.Text,b.TextColor3,b.TextSize,b.ZIndex,b.Parent = text,C.text,23,if parent:IsA("GuiObject") then parent.ZIndex+2 else 2,parent
    Theme.decorate(b,4)
    b.Activated:Connect(callback)
    return b
end
local function art(parent: GuiObject,id: string,x: number,y: number,size: number)
    local icon = Theme.icon(parent,id)
    if icon then icon.Position,icon.Size = UDim2.fromOffset(x,y),UDim2.fromOffset(size,size) end
end
local shade = Instance.new("TextButton")
shade.Name,shade.Text,shade.Size = "ModalScrim","",UDim2.fromScale(1,1)
shade.BackgroundColor3,shade.BackgroundTransparency,shade.Visible,shade.AutoButtonColor = Color3.new(0,0,0),.42,false,false
shade.ZIndex,shade.Parent = 20,gui
local panel = box(shade,0,0,860,520,C.panel,21)
panel.AnchorPoint,panel.Position = Vector2.new(.5,.5),UDim2.fromScale(.5,.5)
panel.Active=true
Theme.texture(panel,860,520)
local scale = Instance.new("UIScale")
scale.Parent = panel
local header = box(panel,4,4,852,78,C.blue,22)
Theme.texture(header,852,78)
local heading = label(header,"Dino Index",22,4,730,68,40)
heading.TextXAlignment = Enum.TextXAlignment.Left
local body = Instance.new("Frame")
body.Position,body.Size,body.BackgroundTransparency,body.ZIndex,body.Parent = UDim2.fromOffset(18,98),UDim2.fromOffset(824,402),1,23,panel
local modalVersion=0
local function close()
    modalVersion+=1
    local version=modalVersion
    active=""
    TweenService:Create(scale,TweenInfo.new(if motion then .13 else 0),{Scale=scale.Scale*.92}):Play()
    task.delay(if motion then .13 else 0,function() if modalVersion==version then shade.Visible=false end end)
    TweenService:Create(blur,TweenInfo.new(if motion then .15 else 0),{Size=0}):Play()
end
button(header,"X",778,8,62,62,C.red,close)
shade.Activated:Connect(close)
local toast = box(gui,0,0,440,56,C.card,50)
toast.AnchorPoint,toast.Position,toast.Visible = Vector2.new(.5,0),UDim2.new(.5,0,0,80),false
local toastScale=Instance.new("UIScale") toastScale.Parent=toast
local toastText = label(toast,"",10,5,420,46,22)
local toastSerial = 0
local function notify(text: string,color: Color3?)
    toastSerial+=1
    local serial=toastSerial
    toast.BackgroundColor3,toastText.Text,toast.Visible = color or C.card,text,true
    task.delay(3,function() if serial==toastSerial then toast.Visible=false end end)
end
local function viewportScale(): number
    local camera=workspace.CurrentCamera
    local size=if camera then camera.ViewportSize else Vector2.new(1280,720)
    return math.max(.24,math.min(1,(size.X-28)/860,(size.Y-64)/520))
end
local function celebrate()
    if not motion then return end
    for i=1,24 do
        local confetti=Instance.new("Frame")
        confetti.Size,confetti.Position=UDim2.fromOffset(9,16),UDim2.fromScale(.5,.42)
        confetti.BackgroundColor3,confetti.BorderSizePixel,confetti.Rotation,confetti.ZIndex,confetti.Parent=({C.gold,C.accent,C.blue,C.purple})[i%4+1],0,i*17,45,gui
        TweenService:Create(confetti,TweenInfo.new(.9,Enum.EasingStyle.Quad,Enum.EasingDirection.Out),{Position=UDim2.fromScale(.15+(i%8)*.1,.7+(i%3)*.06),Rotation=i*65,BackgroundTransparency=1}):Play()
        task.delay(1,function() confetti:Destroy() end)
    end
end
local render
local function open(name: string)
    modalVersion+=1
    active=name
    body:ClearAllChildren()
    shade.Visible=true
    scale.Scale=viewportScale()*(if motion then .86 else 1)
    TweenService:Create(scale,TweenInfo.new(if motion then .24 else 0,Enum.EasingStyle.Back,Enum.EasingDirection.Out),{Scale=viewportScale()}):Play()
    TweenService:Create(blur,TweenInfo.new(if motion then .18 else 0),{Size=12}):Play()
    render(name)
end
local function hero(parent: GuiObject,id: string,x: number,y: number,w: number,h: number,gold: boolean?)
    local view=Preview.add(parent,id,gold==true)
    view.Position,view.Size = UDim2.fromOffset(x,y),UDim2.fromOffset(w,h)
    return view
end
local rarityColors={C.accent,C.blue,C.gold}
local rarityNames={"Common","Rare","Legendary"}
local function speciesIndex(id: string): number return table.find(Config.SpeciesOrder,id) or 1 end
local function meter(parent: GuiObject,x: number,y: number,w: number,value: number,maxValue: number,color: Color3,text: string)
    local b=box(parent,x,y,w,34,C.outline,parent.ZIndex+1)
    local fill=Instance.new("Frame")
    fill.Size,fill.BorderSizePixel,fill.BackgroundColor3,fill.ZIndex,fill.Parent=UDim2.new(math.clamp(value/maxValue,0,1),0,1,0),0,color,b.ZIndex+1,b
    label(b,text,0,0,w,34,20)
end
local function queue()
    local ok,data=pcall(function() return Http:JSONDecode(str("ChestQueueJson","[]")) end)
    return if ok and typeof(data)=="table" then data else {}
end
local refreshEggs
render=function(name: string)
    if name=="home" then
        heading.Text,header.BackgroundColor3="Sanctuary",C.accent
        local heroCard=box(body,0,0,290,330,C.card,24)
        local id=str("EquippedSpeciesId","compy")
        hero(heroCard,id,0,12,290,238)
        label(heroCard,Config.SpeciesDisplayNames[id],0,250,290,42,30)
        label(heroCard,"Equipped dinosaur",0,296,290,26,18,C.accent)
        label(body,"Ready for an adventure?",320,0,495,58,32)
        label(body,"Eat small food clusters, jump mountain paths and avoid bigger dinosaurs.",330,74,474,85,22)
        label(body,"Bank catches and reward eggs by returning to your sanctuary.",330,170,474,75,22,C.gold)
        button(body,"EXPLORE ISLAND",340,280,460,68,C.accent,function()
            local character=player.Character
            if character and character:GetAttribute("RunState")=="Sanctuary" then startRun:FireServer() close()
            else close() notify("You are already exploring",C.blue) end
        end)
        art(body,"home",316,284,64)
    elseif name=="collection" then
        heading.Text,header.BackgroundColor3="Dino Index",C.blue
        local unlocked=0
        for i,id in Config.SpeciesOrder do
            local base,gold=copies(id)
            if base+gold>0 then unlocked+=1 end
            local card=box(body,(i-1)*276,0,264,328,rarityColors[i],24)
            Theme.texture(card,264,328)
            label(card,Config.SpeciesDisplayNames[id],4,8,256,35,27)
            label(card,rarityNames[i],4,44,256,25,18)
            hero(card,id,0,72,264,174,gold>0 and base==0)
            label(card,if base+gold>0 then string.format("%d copies  •  %d Gold",base,gold) else "Not discovered",5,246,254,25,18)
            button(card,"VIEW DINO",12,281,240,38,C.card,function() selected=id open("detail") end)
        end
        meter(body,0,356,600,unlocked,3,C.accent,string.format("Discovered: %d / 3",unlocked))
        button(body,"GOLD FUSION",624,350,200,44,C.gold,function() open("fusion") end)
    elseif name=="detail" then
        local index=speciesIndex(selected)
        local base,gold=copies(selected)
        heading.Text,header.BackgroundColor3=Config.SpeciesDisplayNames[selected],rarityColors[index]
        local stage=box(body,0,0,380,360,rarityColors[index],24)
        hero(stage,selected,0,20,380,280,gold>0 and base==0)
        label(stage,rarityNames[index],0,302,380,42,30)
        label(body,"YOUR COLLECTION",414,0,400,42,28)
        label(body,string.format("Base copies: %d\nGold copies: %d",base,gold),414,62,400,92,25)
        label(body,"Gold is cosmetic. Combine 50 base copies to unlock it.",414,173,400,76,22,C.gold)
        local equipped=str("EquippedSpeciesId","compy")==selected
        button(body,if equipped then "EQUIPPED" elseif base+gold==0 then "LOCKED" else "EQUIP",426,273,372,52,if base+gold>0 then C.accent else C.card,function()
            if base+gold<=0 then notify("Hatch reward eggs to discover this dino") return end
            if not equipped then equip:FireServer(selected,Http:GenerateGUID(false)) end
        end)
        button(body,"BACK TO INDEX",426,341,372,45,C.blue,function() open("collection") end)
    elseif name=="fusion" then
        heading.Text,header.BackgroundColor3="Gold Fusion",C.purple
        local base=copies(selected)
        hero(body,selected,14,0,360,300,true)
        label(body,"MAKE IT GOLD",388,0,420,54,36,C.gold)
        label(body,"Turn 50 base copies into one Gold dinosaur. This consumes the base copies.",392,76,420,106,24)
        meter(body,400,214,400,base,Config.GoldMutationCost,C.gold,string.format("%d / %d copies",base,Config.GoldMutationCost))
        button(body,"FUSE SELECTED DINO",400,277,400,56,if base>=Config.GoldMutationCost then C.accent else C.card,function()
            if base<Config.GoldMutationCost then notify("You need 50 base copies",C.red) return end
            open("fusionConfirm")
        end)
        button(body,"CHOOSE DINO",70,332,264,47,C.blue,function() open("collection") end)
    elseif name=="fusionConfirm" then
        heading.Text,header.BackgroundColor3="Confirm Gold Fusion",C.gold
        art(body,"fusion",26,35,230)
        label(body,"Use 50 copies?",280,12,510,64,36)
        label(body,"You will receive 1 Gold "..Config.SpeciesDisplayNames[selected]..". Your other dinosaurs stay in your collection.",280,100,510,115,24)
        button(body,"CONFIRM FUSION",280,264,510,64,C.accent,function() fuse:FireServer(selected,"gold",Http:GenerateGUID(false)) open("fusion") end)
        button(body,"CANCEL",280,340,510,44,C.red,function() open("fusion") end)
    elseif name=="eggs" then
        heading.Text,header.BackgroundColor3="Growing Eggs",C.gold
        local entries=queue()
        local timers={}
        for slot=1,Config.ChestQueueCapacity do
            local entry=entries[slot]
            local card=box(body,(slot-1)*166,0,156,280,if entry then C.card else C.outline,24)
            label(card,"Slot "..slot,0,8,156,30,22)
            if entry then
                local view=ModelPreview.add(card,"egg")
                view.Position,view.Size=UDim2.fromOffset(0,48),UDim2.fromOffset(156,160)
            else art(card,"egg",26,74,104) end
            timers[slot]=label(card,if entry then "Growing..." else "Empty",3,222,150,40,22,if entry then C.gold else Color3.fromRGB(156,156,174))
        end
        refreshEggs=function()
            for i,timer in timers do
                local entry=entries[i]
                if entry and typeof(entry.readyAt)=="number" then
                    local remaining=math.max(0,entry.readyAt-workspace:GetServerTimeNow())
                    timer.Text=if remaining<=0 then "READY!" else string.format("%dm %02ds",remaining//60,remaining%60)
                end
            end
        end
        refreshEggs()
        button(body,"HATCH NEXT EGG",0,310,400,64,C.accent,function()
            local id=str("NextChestId")
            if id=="" then notify("Return from a run to earn reward eggs") return end
            if workspace:GetServerTimeNow()<num("NextChestReadyAt") then notify("This egg is still growing",C.gold) return end
            hatch:FireServer(id,Http:GenerateGUID(false))
        end)
        label(body,"Eggs grow in order, even while offline.\nWaiting for a nest slot: "..num("PendingChestGrants"),420,302,400,88,21)
    elseif name=="hatch" then
        heading.Text,header.BackgroundColor3="You hatched a dinosaur!",C.gold
        celebrate()
        local reward=str("LastChestRewardText","New dinosaur")
        local id=string.match(reward,"x (%w+)") or "compy"
        if not Config.SpeciesDisplayNames[id] then id="compy" end
        hero(body,id,160,-12,504,260)
        label(body,reward,80,240,660,58,36,C.gold)
        button(body,"VIEW COLLECTION",212,322,400,64,C.accent,function() open("collection") end)
    elseif name=="exit" then
        heading.Text,header.BackgroundColor3="Return to Sanctuary?",C.red
        art(body,"home",36,28,214)
        label(body,"Bank this run",300,12,500,54,36,C.gold)
        label(body,"Stay still for "..Config.ExitChannelSeconds.." seconds to return safely. Moving cancels the return.",300,91,500,104,24)
        button(body,"RETURN & BANK",300,242,500,68,C.accent,function() endRun:FireServer() close() notify("Returning... stay still",C.gold) end)
        button(body,"KEEP EXPLORING",300,329,500,48,C.blue,close)
    elseif name=="results" then
        heading.Text,header.BackgroundColor3="Run Complete!",C.gold
        art(body,"trophy",24,42,240)
        label(body,"Growth  "..num("LastRunGrowthScore"),300,18,500,60,34,C.accent)
        label(body,"Catches  "..num("LastRunCatchScore"),300,93,500,60,34,C.blue)
        label(body,str("LastRewardText","Saving rewards..."),290,168,510,100,24,C.gold)
        label(body,"Your next adventure starts from the sanctuary.",30,302,760,40,21)
        button(body,"BACK TO SANCTUARY",212,348,400,48,C.accent,function() open("home") end)
    elseif name=="settings" then
        heading.Text,header.BackgroundColor3="Settings",C.purple
        label(body,"Popup effects",24,24,410,56,30)
        button(body,if motion then "ON" else "OFF",560,24,230,56,if motion then C.accent else C.card,function() motion=not motion Theme.MotionEnabled=motion open("settings") end)
        label(body,"Camera distance",24,114,410,56,30)
        button(body,"RESET CAMERA",470,114,320,56,C.blue,function() player.CameraMaxZoomDistance=Config.CameraMaxZoom notify("Camera reset",C.blue) end)
        button(body,"HOW TO PLAY",24,238,370,64,C.gold,function() open("tutorial") end)
        button(body,"FOOD GUIDE",424,238,366,64,C.accent,function() open("food") end)
        label(body,"Settings apply on this device for this session.",24,342,766,40,18)
    elseif name=="food" then
        heading.Text,header.BackgroundColor3="Food & Growth",C.accent
        local types={{"Berries","leaf",1,C.accent},{"Fruit","leaf",4,C.gold},{"Eggs","egg",15,C.blue},{"Crystals","amber",50,C.purple}}
        for i,food in types do
            local card=box(body,(i-1)*208,0,196,286,food[4],24)
            art(card,food[2],28,30,140)
            label(card,food[1],0,180,196,42,26)
            label(card,"+"..food[3].." Growth",0,226,196,42,26)
        end
        label(body,"Look for small clusters across the island. Rare crystals are worth the most growth.",18,316,788,72,23)
    elseif name=="tutorial" then
        heading.Text,header.BackgroundColor3="Welcome to Be Dino!",C.blue
        local steps={{"1","EAT & GROW","Find small food clusters across the island."},{"2","JUMP & EXPLORE","Space on desktop. Jump button on mobile."},{"3","BANK & HATCH","Return to sanctuary to bank catches and eggs."}}
        for i,step in steps do
            local card=box(body,(i-1)*276,0,264,278,C.card,24)
            label(card,step[1],12,12,240,80,64,rarityColors[i])
            label(card,step[2],10,110,244,46,25,rarityColors[i])
            label(card,step[3],16,176,232,84,22)
        end
        button(body,"LET'S PLAY",212,324,400,62,C.accent,function() seenTutorial=true open("home") end)
    end
end
local previewNotice=label(gui,"STUDIO PREVIEW • progress is not saved",0,0,390,25,14,C.gold)
previewNotice.AnchorPoint,previewNotice.Position=Vector2.new(.5,0),UDim2.new(.5,0,0,8)
previewNotice.Visible=player:GetAttribute("ProfileMode")=="Studio preview (not saved)"
player:GetAttributeChangedSignal("ProfileMode"):Connect(function() previewNotice.Visible=player:GetAttribute("ProfileMode")=="Studio preview (not saved)" end)
local rail=box(gui,14,0,148,320,C.panel,2)
rail.AnchorPoint,rail.Position=Vector2.new(0,.5),UDim2.new(0,14,.5,0)
local railScale=Instance.new("UIScale") railScale.Parent=rail
for i,entry in {{"DINOS","dinos","collection",C.blue},{"EGGS","egg","eggs",C.gold},{"GOLD","fusion","fusion",C.purple},{"HOME","home","home",C.accent},{"SETTINGS","shield","settings",C.card}} do
    local b=button(rail,entry[1],7,7+(i-1)*62,134,54,entry[4],function() open(entry[3]) end)
    b.TextSize=20
    art(b,entry[2],5,6,40)
    b.TextXAlignment=Enum.TextXAlignment.Right
end
local hud=box(gui,0,0,390,94,C.panel,2)
hud.AnchorPoint,hud.Position=Vector2.new(0,1),UDim2.new(0,18,1,-18)
local hudScale=Instance.new("UIScale") hudScale.Parent=hud
art(hud,"amber",8,12,64)
local growthLabel=label(hud,"0 GROWTH",82,3,290,42,30,C.accent)
local catchLabel=label(hud,"0 catches  •  Sanctuary",82,47,290,34,20)
local action=button(gui,"EXPLORE",0,0,244,60,C.accent,function()
    local character=player.Character
    if character and character:GetAttribute("RunState")=="Active" then open("exit")
    elseif character and character:GetAttribute("RunState")=="Sanctuary" then startRun:FireServer() close() end
end)
action.AnchorPoint,action.Position=Vector2.new(1,1),UDim2.new(1,-20,1,-22)
local actionScale=action:FindFirstChildOfClass("UIScale") :: UIScale
local function scales()
    scale.Scale=viewportScale()
    local camera=workspace.CurrentCamera
    local size=if camera then camera.ViewportSize else Vector2.new(1280,720)
    local small=math.clamp(math.min(size.X/1000,size.Y/700),.5,1)
    railScale.Scale,hudScale.Scale,actionScale.Scale=small,small,small
    action:SetAttribute("UIScaleBase",small)
    toastScale.Scale=math.min(1,(size.X-20)/440)
end
local function characterAdded(character: Model)
    local humanoid=character:WaitForChild("Humanoid",10) :: Humanoid?
    if not humanoid or player.Character~=character then return end
    local camera=workspace.CurrentCamera
    if camera then camera.CameraType,camera.CameraSubject=Enum.CameraType.Custom,humanoid end
    humanoid:SetStateEnabled(Enum.HumanoidStateType.Jumping,true)
    lastGrowth=0
end
player.CameraMaxZoomDistance=Config.CameraMaxZoom
player.CharacterAdded:Connect(characterAdded)
if player.Character then task.spawn(characterAdded,player.Character) end
if workspace.CurrentCamera then workspace.CurrentCamera:GetPropertyChangedSignal("ViewportSize"):Connect(scales) end
scales()
local elapsed=0
local exitPending=false
RunService.Heartbeat:Connect(function(dt)
    elapsed+=dt
    if elapsed<.15 then return end elapsed=0
    local character=player.Character
    local state=if character then character:GetAttribute("RunState") else "Loading"
    local growth=if character then character:GetAttribute("GrowthScore") or 0 else 0
    local catches=if character then character:GetAttribute("CatchScore") or 0 else 0
    growthLabel.Text=string.format("%d GROWTH",growth)
    catchLabel.Text=string.format("%d catches  •  %s",catches,if state=="Sanctuary" then "Safe sanctuary" else "Island")
    action.Text=if state=="Sanctuary" then "EXPLORE ISLAND" elseif state=="Active" then "RETURN HOME" else "SAVING..."
    action.BackgroundColor3=if state=="Active" then C.red else C.accent
    if character then
        local visualScale=character:GetAttribute("VisualScale") or 1
        player.CameraMinZoomDistance=Config.CameraMinZoom*visualScale
        local humanoid=character:FindFirstChildOfClass("Humanoid")
        if humanoid then humanoid.CameraOffset=Vector3.new(0,(visualScale-1)*2,0) end
        local deadline=character:GetAttribute("ExitChannelEndsAt") or 0
        local remaining=deadline-workspace:GetServerTimeNow()
        if remaining>0 then action.Text=string.format("STAY STILL %.1fs",remaining) exitPending=true
        elseif exitPending then exitPending=false if state=="Active" then notify("Return cancelled: you moved",C.red) end end
    end
    if growth>lastGrowth and state=="Active" then
        notify("+"..(growth-lastGrowth).." Growth!",C.accent)
        if motion then
            hudScale.Scale*=1.06
            TweenService:Create(hudScale,TweenInfo.new(.2,Enum.EasingStyle.Back),{Scale=railScale.Scale}):Play()
        end
    end
    lastGrowth=growth
    if active=="eggs" and refreshEggs then refreshEggs() end
    if player:GetAttribute("ProfileState")=="Loaded" and state=="Sanctuary" and not seenTutorial then seenTutorial=true open("tutorial") end
end)
for _,attribute in {"EquippedSpeciesId","CompyCopies","CompyGold","TriceratopsCopies","TriceratopsGold","TyrannosaurusCopies","TyrannosaurusGold","ChestQueueJson"} do
    player:GetAttributeChangedSignal(attribute):Connect(function()
        if table.find({"collection","detail","fusion","eggs"},active) then body:ClearAllChildren() render(active) end
    end)
end
player:GetAttributeChangedSignal("LastClaimedChestId"):Connect(function() task.defer(function() open("hatch") end) end)
player:GetAttributeChangedSignal("LastRunEndAt"):Connect(function() open("results") end)
player:GetAttributeChangedSignal("LastRewardText"):Connect(function() if active=="results" then body:ClearAllChildren() render(active) end end)
for _,attribute in {"LastEquipStatus","LastMutationStatus","LastChestClaimStatus"} do
    player:GetAttributeChangedSignal(attribute):Connect(function()
        local status=str(attribute)
        if status=="equipped" or status=="mutated" or status=="claimed" then notify("Success!",C.accent)
        elseif status~="" and status~="duplicate" then notify(status:gsub("_"," "),C.red) end
    end)
end
Input.InputBegan:Connect(function(input,processed)
    if processed then return end
    if input.KeyCode==Enum.KeyCode.Escape then close()
    elseif input.KeyCode==Enum.KeyCode.C then open("collection")
    elseif input.KeyCode==Enum.KeyCode.B then open("eggs") end
end)
