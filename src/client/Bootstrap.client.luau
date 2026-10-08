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
local NavigationArtwork = require(Shared.NavigationArtwork)
local Preview = require(Shared.DinosaurPreview)
local ModelPreview = require(Shared.ModelPreview)
local ProgressionConfig=require(Shared.ProgressionConfig)
local ProgressionRules=require(Shared.ProgressionRules)
local EggTraits=require(Shared.EggTraits)
local PreviewTraits=require(script.Parent.PreviewTraits)
local C = Theme.Colors
local remotes = ReplicatedStorage:WaitForChild("BeDinoRemotes")
local startRun = remotes:WaitForChild("RequestStartRun") :: RemoteEvent
local endRun = remotes:WaitForChild("RequestEndRun") :: RemoteEvent
local equip = remotes:WaitForChild("EquipSpecies") :: RemoteEvent
local hatch = remotes:WaitForChild("ClaimChest") :: RemoteEvent
local fuse = remotes:WaitForChild("MutateSpecies") :: RemoteEvent
local shopAction=remotes:WaitForChild("ProgressionAction") :: RemoteEvent
local shopResult=remotes:WaitForChild("ProgressionResult") :: RemoteEvent
local leapRemote=remotes:WaitForChild("RequestLeap") :: RemoteEvent
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
local lastEggCount = 0
local function num(id: string): number return player:GetAttribute(id) or 0 end
local function str(id: string,fallback: string?): string return player:GetAttribute(id) or fallback or "" end
local function copies(id: string): (number,number,number)
    local ok, data = pcall(function() return Http:JSONDecode(str("CollectionJson","{}")) end)
    local entry = if ok and typeof(data)=="table" then data[id] else nil
    return if entry then entry.base or 0 else 0, if entry then entry.gold or 0 else 0, if entry then entry.diamond or 0 else 0
end
local function bestMutation(id: string): string
    local _,gold,diamond = copies(id)
    return if diamond>0 then "diamond" elseif gold>0 then "gold" else "base"
end
local function eventMutation(id: string)
    local ok,data=pcall(function() return Http:JSONDecode(str("CollectionJson","{}")) end)
    return if ok and typeof(data)=="table" then ProgressionRules.eventMutation(data[id]) else nil
end
local fusionTarget = "gold"
local hatchPending = false
local autoHatching = false
local hatchCancelSerial = 0
local function ownedTraits(id: string)
    local ok,data=pcall(function() return Http:JSONDecode(str("CollectionJson","{}")) end)
    return if ok and typeof(data)=="table" then EggTraits.selected(data[id]) else nil
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
    autoHatching=false
    hatchCancelSerial+=1
    modalVersion+=1
    local version=modalVersion
    active=""
    TweenService:Create(scale,TweenInfo.new(if motion then .13 else 0),{Scale=scale.Scale*.92}):Play()
    task.delay(if motion then .13 else 0,function() if modalVersion==version then shade.Visible=false end end)
    TweenService:Create(blur,TweenInfo.new(if motion then .15 else 0),{Size=0}):Play()
end
local closeButton=button(header,"X",770,1,80,76,C.red,close)
closeButton.AnchorPoint,closeButton.Position=Vector2.new(1,0),UDim2.new(1,-2,0,1)
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
    local size=gui.AbsoluteSize
    return math.max(.05,math.min(1,(size.X-40)/860,(size.Y-40)/520))
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
    TweenService:Create(scale,TweenInfo.new(if motion then .24 else 0,Enum.EasingStyle.Quad,Enum.EasingDirection.Out),{Scale=viewportScale()}):Play()
    TweenService:Create(blur,TweenInfo.new(if motion then .18 else 0),{Size=12}):Play()
    render(name)
end
local function hero(parent: GuiObject,id: string,x: number,y: number,w: number,h: number,gold: (boolean | string)?)
    local view=Preview.add(parent,id,gold or "base")
    view.Position,view.Size = UDim2.fromOffset(x,y),UDim2.fromOffset(w,h)
    PreviewTraits.add(view,ownedTraits(id))
    return view
end
local rarityColors={C.accent,C.blue,C.gold}
local rarityNames={"Common","Rare","Legendary"}
local function speciesIndex(id: string): number return Config.SpeciesRarities[id] or 1 end
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
local function hatchNext()
    local id=str("NextChestId")
    if id=="" or workspace:GetServerTimeNow()<num("NextChestReadyAt") then
        autoHatching=false
        open("eggs")
        return
    end
    if hatchPending then return end
    hatchPending=true
    hatch:FireServer(id,Http:GenerateGUID(false))
    task.delay(8,function()
        if hatchPending then hatchPending=false autoHatching=false notify("Hatching did not finish. Please retry.",C.red) end
    end)
end
local function progression()
    local ok,data=pcall(function() return Http:JSONDecode(str("ProgressionJson","{}")) end)
    if not ok or typeof(data)~="table" or typeof(data.auras)~="table" or typeof(data.potions)~="table" or typeof(data.buffs)~="table" then return {crystals=0,auras={},equippedAura="",potions={},buffs={}} end
    return data
end
local chosenAura="meadow"
local cosmeticTab="auras"
local chosenPotion="speed_common"
local pendingShop=nil
local function transact(action,id,replace)
    if pendingShop then notify("Purchase is still processing",C.gold) return end
    local token=Http:GenerateGUID(false)
    pendingShop={token=token,action=action,id=id,replace=replace==true,started=os.clock()}
    shopAction:FireServer(action,id,token,replace==true)
end
shopResult.OnClientEvent:Connect(function(token,ok,status)
    if pendingShop and pendingShop.token==token then pendingShop=nil end
    notify(if ok then "Success!" else tostring(status):gsub("_"," "),if ok then C.accent else C.red)
    if active=="auras" or active=="potions" then body:ClearAllChildren() render(active) end
end)
local refreshEggs
render=function(name: string)
    if name=="home" then
        heading.Text,header.BackgroundColor3="Sanctuary",C.accent
        local heroCard=box(body,0,0,290,330,C.card,24)
        local id=str("EquippedSpeciesId","compy")
        hero(heroCard,id,8,8,274,230,bestMutation(id))
        label(heroCard,Config.SpeciesDisplayNames[id],0,244,290,42,30)
        label(heroCard,"Equipped dinosaur",0,296,290,26,18,C.accent)
        label(body,"Ready for an adventure?",320,0,495,58,32)
        label(body,"Eat small food clusters, jump mountain paths and avoid bigger dinosaurs.",330,74,474,85,22)
        label(body,"Bank catches and reward eggs by returning to your sanctuary.",330,170,474,75,22,C.gold)
        button(body,"EXPLORE ISLAND",340,280,460,68,C.accent,function()
            local character=player.Character
            if character and character:GetAttribute("RunState")=="Sanctuary" then startRun:FireServer() close()
            else close() notify("You are already exploring",C.blue) end
        end)
        
    elseif name=="auras" then
        heading.Text,header.BackgroundColor3="Aura & Trail Shop",C.purple
        local p=progression()
        p.trails=p.trails or {}
        local isTrail=cosmeticTab=="trails"
        local touch=Input.TouchEnabled
        local targetHeight=if touch then math.max(45,45/viewportScale()) else 44
        local tabsHeight=if touch then targetHeight else 40
        local cardsY=tabsHeight+12
        local cardsHeight=if touch then 402-cardsY else 302
        local buyY=if touch then cardsHeight-targetHeight-10 else 247
        for i,tab in {"auras","trails"} do
            button(body,if tab=="auras" then "AURAS" else "TRAILS",(i-1)*170,0,160,tabsHeight,if cosmeticTab==tab then C.blue else C.card,function() cosmeticTab=tab open("auras") end)
        end
        label(body,"Crystals: "..num("Crystals"),355,0,460,40,23,C.gold)
        local owned=if isTrail then p.trails else p.auras
        local equippedId=if isTrail then p.equippedTrail or "" else p.equippedAura
        for i,item in (if isTrail then ProgressionConfig.Trails else ProgressionConfig.Auras) do
            local color=Color3.fromRGB(item.color[1],item.color[2],item.color[3])
            local card=box(body,(i-1)*276,cardsY,264,cardsHeight,color,24)
            label(card,item.name,6,5,252,34,25)
            label(card,item.rarity.." • "..(if isTrail then "Cosmetic" else item.growth.."x Growth"),4,42,256,30,19)
            art(card,(if isTrail then "trail_" else "aura_")..item.id,if touch then 92 else 46,if touch then 70 else 77,if touch then 80 else 172)
            label(card,if owned[item.id] then "Owned" else item.price.." Crystals",4,if touch then buyY-33 else 212,256,27,21,C.gold)
            local equipped=equippedId==item.id
            button(card,if equipped then "UNEQUIP" elseif owned[item.id] then "EQUIP" else "BUY",12,buyY,240,targetHeight,C.card,function()
                if owned[item.id] then transact(if isTrail then "equipTrail" else "equipAura",if equipped then "" else item.id)
                else chosenAura=item.id open("auraConfirm") end
            end)
        end
        if not touch then label(body,"Equipped: "..(if equippedId=="" then "None" else equippedId),0,363,824,35,20) end
    elseif name=="auraConfirm" then
        local isTrail=cosmeticTab=="trails"
        local item=ProgressionRules.item(if isTrail then ProgressionConfig.Trails else ProgressionConfig.Auras,chosenAura)
        heading.Text,header.BackgroundColor3=if isTrail then "Buy Trail?" else "Buy Aura?",C.purple
        art(body,(if isTrail then "trail_" else "aura_")..item.id,30,25,220)
        label(body,item.name.." • "..(if isTrail then "Cosmetic trail" else item.growth.."x eating growth"),290,24,510,70,29)
        label(body,item.price.." Crystals\nBalance after purchase: "..(num("Crystals")-item.price),290,125,510,90,25,C.gold)
        button(body,if isTrail then "BUY TRAIL" else "BUY AURA",290,261,510,57,C.accent,function() transact(if isTrail then "buyTrail" else "buyAura",item.id) open("auras") end)
        button(body,"CANCEL",290,337,510,45,C.red,function() open("auras") end)
    elseif name=="potions" then
        heading.Text,header.BackgroundColor3="Potion Shop",C.accent
        local p=progression()
        label(body,"Crystals: "..num("Crystals").."  •  Select a potion to buy or use",0,0,824,32,21,C.gold)
        for i,item in ProgressionConfig.Potions do
            local x=((i-1)%3)*276 local y=43+math.floor((i-1)/3)*176
            local color=if item.rarity=="Legendary" then C.gold elseif item.rarity=="Rare" then C.blue else C.accent
            local card=box(body,x,y,264,164,C.card,24)
            art(card,"potion_"..item.kind,8,14,76)
            label(card,item.name,88,5,167,32,21,color)
            label(card,item.rarity.." • "..item.multiplier.."x\n"..(item.duration//60).." minutes",86,39,170,50,18)
            label(card,"Owned: "..(p.potions[item.id] or 0),86,88,170,24,17)
            button(card,item.price.." Crystals",8,120,144,34,color,function() chosenPotion=item.id open("potionConfirm") end).TextSize=17
            button(card,"USE",162,120,94,34,C.purple,function()
                chosenPotion=item.id
                local buff=p.buffs[item.kind]
                if buff and buff.expiresAt>workspace:GetServerTimeNow() then open("potionReplace") else transact("usePotion",item.id,false) end
            end).TextSize=18
        end
    elseif name=="potionConfirm" or name=="potionReplace" then
        local item=ProgressionRules.item(ProgressionConfig.Potions,chosenPotion)
        local replacing=name=="potionReplace"
        heading.Text,header.BackgroundColor3=if replacing then "Replace Active Potion?" else "Buy Potion?",C.accent
        art(body,"potion_"..item.kind,30,22,220)
        label(body,item.name.." • "..item.multiplier.."x "..item.kind,290,15,510,62,28)
        label(body,if replacing then "Your current "..item.kind.." potion ends immediately. Its remaining time is lost. Consume 1 potion for a fresh "..(item.duration//60).." minutes?" else (item.duration//60).." minutes • "..item.price.." Crystals\nBalance after purchase: "..(num("Crystals")-item.price),290,101,510,135,24,C.gold)
        button(body,if replacing then "REPLACE & USE" else "BUY POTION",290,263,510,58,C.accent,function()
            transact(if replacing then "usePotion" else "buyPotion",item.id,replacing) open("potions")
        end)
        button(body,"CANCEL",290,339,510,44,C.red,function() open("potions") end)
    elseif name=="collection" then
        heading.Text,header.BackgroundColor3="Dino Index",C.blue
        local unlocked=0
        local list=Instance.new("ScrollingFrame")
        list.Name,list.Size,list.Position="DinoCards",UDim2.fromOffset(824,326),UDim2.fromOffset(0,0)
        list.BackgroundTransparency,list.BorderSizePixel,list.ScrollBarThickness=1,0,6
        list.CanvasSize=UDim2.fromOffset(0,math.ceil(#Config.SpeciesOrder/3)*284)
        list.ZIndex,list.Parent=24,body
        for i,id in Config.SpeciesOrder do
            local base,gold,diamond=copies(id)
            local event=eventMutation(id)
            local rarity=speciesIndex(id)
            if base+gold+diamond>0 or event or ownedTraits(id) then unlocked+=1 end
            local card=box(list,((i-1)%3)*276,math.floor((i-1)/3)*284,264,272,rarityColors[rarity],24)
            Theme.texture(card,264,272)
            label(card,Config.SpeciesDisplayNames[id],4,8,256,35,25)
            label(card,rarityNames[rarity],4,44,256,25,18)
            hero(card,id,7,70,250,128,bestMutation(id))
            label(card,if event then event.name.." mutation" elseif ownedTraits(id) then "Special variant" elseif base+gold+diamond>0 then string.format("%d Base • %d Gold • %d Diamond",base,gold,diamond) else "Not discovered",5,201,254,25,15)
            button(card,"VIEW DINO",12,233,240,30,C.card,function() selected=id open("detail") end)
        end
        meter(body,0,356,600,unlocked,#Config.SpeciesOrder,C.accent,string.format("Discovered: %d / %d",unlocked,#Config.SpeciesOrder))
        button(body,"FUSION",624,350,200,44,C.gold,function() open("fusion") end)
    elseif name=="detail" then
        local index=speciesIndex(selected)
        local base,gold,diamond=copies(selected)
        local event=eventMutation(selected)
        local owned=base+gold+diamond>0 or event~=nil or ownedTraits(selected)~=nil
        heading.Text,header.BackgroundColor3=Config.SpeciesDisplayNames[selected],rarityColors[index]
        local stage=box(body,0,0,380,360,rarityColors[index],24)
        hero(stage,selected,0,20,380,280,bestMutation(selected))
        label(stage,rarityNames[index],0,302,380,42,30)
        label(body,"YOUR COLLECTION",414,0,400,42,28)
        label(body,string.format("Base: %d • Gold: %d\nDiamond: %d",base,gold,diamond),414,62,400,92,25)
        label(body,if event then event.name.." • "..event.growth.."x Growth • "..event.speed.."x Speed" else "Cosmetic fusion: 50 Base → Gold; 50 Gold → Diamond. Highest owned variant equips.",414,173,400,76,22,C.gold)
        local equipped=str("EquippedSpeciesId","compy")==selected
        button(body,if equipped then "EQUIPPED" elseif not owned then "LOCKED" else "EQUIP",426,273,372,52,if owned then C.accent else C.card,function()
            if not owned then notify("Hatch reward eggs to discover this dino") return end
            if not equipped then equip:FireServer(selected,Http:GenerateGUID(false)) end
        end)
        button(body,"BACK TO INDEX",426,341,372,45,C.blue,function() open("collection") end)
    elseif name=="fusion" then
        heading.Text,header.BackgroundColor3="Dinosaur Fusion",C.purple
        local base,gold=copies(selected)
        local diamond=fusionTarget=="diamond"
        local cost=if diamond then Config.DiamondMutationCost else Config.GoldMutationCost
        local owned=if diamond then gold else base
        local source=if diamond then "Gold" else "Base"
        local target=if diamond then "Diamond" else "Gold"
        hero(body,selected,14,0,360,260,fusionTarget)
        art(body,"mutation_"..fusionTarget,142,242,84)
        button(body,"GOLD",388,0,200,42,C.gold,function() fusionTarget="gold" open("fusion") end)
        button(body,"DIAMOND",600,0,200,42,C.blue,function() fusionTarget="diamond" open("fusion") end)
        label(body,"MAKE IT "..string.upper(target),388,56,420,54,30,if diamond then C.blue else C.gold)
        label(body,"Consume "..cost.." "..source.." copies for 1 "..target.." "..Config.SpeciesDisplayNames[selected]..". Cosmetic only.",392,118,420,76,22)
        meter(body,400,214,400,owned,cost,C.gold,string.format("%d / %d %s copies",owned,cost,source))
        button(body,"FUSE SELECTED DINO",400,277,400,56,if owned>=cost then C.accent else C.card,function()
            if owned<cost then notify("You need "..cost.." "..source.." copies",C.red) return end
            open("fusionConfirm")
        end)
        button(body,"CHOOSE DINO",70,342,264,47,C.blue,function() open("collection") end)
    elseif name=="fusionConfirm" then
        local diamond=fusionTarget=="diamond"
        local cost=if diamond then Config.DiamondMutationCost else Config.GoldMutationCost
        local source=if diamond then "Gold" else "Base"
        local target=if diamond then "Diamond" else "Gold"
        heading.Text,header.BackgroundColor3="Confirm "..target.." Fusion",if diamond then C.blue else C.gold
        art(body,"mutation_"..fusionTarget,26,35,230)
        label(body,"Use "..cost.." "..source.." copies?",280,12,510,64,30)
        label(body,"Receive 1 "..target.." "..Config.SpeciesDisplayNames[selected]..". The consumed copies are removed after a successful save.",280,100,510,115,24)
        button(body,"CONFIRM FUSION",280,264,510,64,C.accent,function() fuse:FireServer(selected,fusionTarget,Http:GenerateGUID(false)) open("fusion") end)
        button(body,"CANCEL",280,340,510,44,C.red,function() open("fusion") end)
    elseif name=="eggs" then
        heading.Text,header.BackgroundColor3="Caught Eggs",C.gold
        local entries=queue()
        local timers={}
        for slot=1,Config.ChestQueueCapacity do
            local entry=entries[slot]
            local card=box(body,(slot-1)*166,0,156,280,if entry then C.card else C.outline,24)
            label(card,"Slot "..slot,0,8,156,30,22)
            local view=ModelPreview.add(card,"egg",entry==nil)
            view.Position,view.Size=UDim2.fromOffset(18,65),UDim2.fromOffset(120,120)
            PreviewTraits.add(view,entry)
            if entry then label(card,rarityNames[entry.rarity or 1],0,37,156,24,18,rarityColors[entry.rarity or 1]) end
            local mutation=if entry then ProgressionRules.item(ProgressionConfig.EventMutations,entry.mutationId) else nil
            if mutation then
                local color=Color3.fromRGB(mutation.color[1],mutation.color[2],mutation.color[3])
                for _,part in view:GetDescendants() do if part:IsA("BasePart") then part.Color=part.Color:Lerp(color,.6) end end
                label(card,mutation.name,0,192,156,27,18,color)
            elseif entry and entry.eventId and entry.eventId~="clear" then
                local event=ProgressionRules.item(ProgressionConfig.Weather,entry.eventId)
                label(card,if event then event.name else entry.eventId,0,192,156,27,15,C.gold)
            end
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
        button(body,"HATCH NEXT EGG",0,310,400,math.max(64,45/viewportScale()),C.accent,function()
            local id=str("NextChestId")
            if id=="" then notify("Return from a run to earn reward eggs") return end
            if workspace:GetServerTimeNow()<num("NextChestReadyAt") then notify("This egg is still growing",C.gold) return end
            if hatchPending then return end
            autoHatching=true
            hatchNext()
        end)
        label(body,"Waiting for a nest slot: "..num("PendingChestGrants"),420,302,400,88,21)
    elseif name=="hatch" then
        heading.Text,header.BackgroundColor3="An egg is hatching...",C.gold
        local version=modalVersion
        local reward=str("LastChestRewardText","New dinosaur")
        local id=string.match(reward,"x (%w+)") or "compy"
        if not Config.SpeciesDisplayNames[id] then id="compy" end
        local view=hero(body,id,160,-12,504,260)
        for _,child in view:GetChildren() do if child.Name=="TraitBadge" or child.Name=="ShinyPreviewGlint" then child:Destroy() end end
        PreviewTraits.add(view,{big=player:GetAttribute("LastChestBig"),shiny=player:GetAttribute("LastChestShiny")})
        view.Visible=false
        local eggView=ModelPreview.add(body,"egg")
        eggView.Position,eggView.Size=UDim2.fromOffset(260,0),UDim2.fromOffset(304,260)
        local rewardLabel=label(body,rarityNames[speciesIndex(id)].." egg",80,240,660,58,36,rarityColors[speciesIndex(id)])
        local crack=Instance.new("Frame")
        crack.BackgroundTransparency,crack.Position,crack.Size,crack.ZIndex,crack.Parent=1,UDim2.fromOffset(370,88),UDim2.fromOffset(84,120),eggView.ZIndex+1,body
        local fractures={}
        for i,line in {{34,0,22,44},{28,32,26,-35},{33,70,20,38}} do
            local segment=Instance.new("Frame")
            segment.BackgroundColor3,segment.BorderSizePixel=C.outline,0
            segment.Position,segment.Size,segment.Rotation=UDim2.fromOffset(line[1],line[2]),UDim2.fromOffset(4,line[3]),line[4]
            segment.Visible,segment.ZIndex,segment.Parent=false,crack.ZIndex,crack
            fractures[i]=segment
        end
        local mutation=ProgressionRules.item(ProgressionConfig.EventMutations,str("LastChestEventMutation"))
        if mutation then
            local color=Color3.fromRGB(mutation.color[1],mutation.color[2],mutation.color[3])
            for _,part in view:GetDescendants() do if part:IsA("BasePart") then part.Color=part.Color:Lerp(color,.55) end end
            local perks=label(body,mutation.name.." • "..mutation.growth.."x Growth • "..mutation.speed.."x Speed",80,295,660,25,20,color)
            perks.Visible=false
            task.delay(3.4,function() if perks.Parent and modalVersion==version then perks.Visible=true end end)
        end
        local nextButton=button(body,"NEXT EGG",80,322,320,math.max(64,45/viewportScale()),C.accent,function() autoHatching=true hatchNext() end)
        local collectionButton=button(body,"COLLECTION",424,322,320,math.max(64,45/viewportScale()),C.blue,function() autoHatching=false open("collection") end)
        nextButton.Visible,collectionButton.Visible=false,false
        task.spawn(function()
            local started=os.clock()
            while os.clock()-started<3.4 and modalVersion==version and eggView.Parent do
                local t=os.clock()-started
                if motion then eggView.Rotation=math.sin(t*(8+t*5))*math.min(14,t*5) end
                for i,segment in fractures do segment.Visible=t>1.8+i*.35 end
                task.wait(.03)
            end
            if modalVersion~=version or not view.Parent then return end
            eggView:Destroy() crack:Destroy()
            view.Visible=true rewardLabel.Text=reward heading.Text="You hatched a dinosaur!"
            celebrate()
            task.wait(math.max(0,Config.HatchRevealSeconds-(os.clock()-started)))
            if modalVersion~=version or not view.Parent then return end
            if autoHatching and str("NextChestId")~="" then hatchNext()
            else autoHatching=false nextButton.Visible=true collectionButton.Visible=true end
        end)
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
        label(body,"Growth  "..math.floor(num("LastRunGrowthScore")),300,18,500,60,34,C.accent)
        label(body,"Catches  "..num("LastRunCatchScore"),300,93,500,60,34,C.blue)
        label(body,str("LastRewardText","Saving rewards..."),290,168,510,100,24,C.gold)
        label(body,"Your next adventure starts from the sanctuary.",30,302,760,40,21)
        button(body,"BACK TO SANCTUARY",212,348,400,48,C.accent,function() open("home") end)
    elseif name=="settings" then
        heading.Text,header.BackgroundColor3="Settings",C.purple
        label(body,"Visual effects",24,24,410,56,30)
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
        label(body,"500 raw food points earn 15 catches before weather bonuses. Growth boosts do not multiply catches.",18,316,788,72,23)
    elseif name=="tutorial" then
        heading.Text,header.BackgroundColor3="Welcome to Be Dino!",C.blue
        local steps={{"1","EAT & GROW","Find small food clusters across the island."},{"2","JUMP & EXPLORE","Space to jump, E to leap. Buttons on mobile."},{"3","BANK & HATCH","Return to sanctuary to bank catches and eggs."}}
        for i,step in steps do
            local card=box(body,(i-1)*276,0,264,278,C.card,24)
            label(card,step[1],12,12,240,80,64,rarityColors[i])
            label(card,step[2],10,110,244,46,25,rarityColors[i])
            label(card,step[3],16,176,232,84,22)
        end
        button(body,"LET'S PLAY",212,324,400,62,C.accent,function() seenTutorial=true open("home") end)
    end
end
local buildBadge=label(gui,"BUILD "..Config.Build,0,0,250,24,15,C.blue)
buildBadge.Name,buildBadge.AnchorPoint,buildBadge.Position="BuildBadge",Vector2.new(.5,0),UDim2.new(.5,0,0,36)
local foodDiagnostic=label(gui,"",0,0,450,22,14,C.accent)
foodDiagnostic.AnchorPoint,foodDiagnostic.Position,foodDiagnostic.Visible=Vector2.new(.5,0),UDim2.new(.5,0,0,62),RunService:IsStudio()
local function refreshFoodDiagnostic()
    local status=workspace:GetAttribute("FoodSpawnStatus") or "Starting"
    foodDiagnostic.Text="FOOD: "..tostring(workspace:GetAttribute("FoodCount") or 0).."  •  "..tostring(status)
    foodDiagnostic.TextColor3=if status=="Failed" or status=="No valid ground" then C.red else C.accent
end
workspace:GetAttributeChangedSignal("FoodSpawnStatus"):Connect(refreshFoodDiagnostic)
workspace:GetAttributeChangedSignal("FoodCount"):Connect(refreshFoodDiagnostic)
refreshFoodDiagnostic()
local previewNotice=label(gui,"STUDIO PREVIEW • progress not saved • test currency",0,0,500,25,14,C.gold)
previewNotice.AnchorPoint,previewNotice.Position=Vector2.new(.5,0),UDim2.new(.5,0,0,8)
previewNotice.Visible=player:GetAttribute("ProfileMode")=="Studio preview (not saved)"
player:GetAttributeChangedSignal("ProfileMode"):Connect(function() previewNotice.Visible=player:GetAttribute("ProfileMode")=="Studio preview (not saved)" end)
local rail=box(gui,14,0,186,444,C.panel,2)
rail.AnchorPoint,rail.Position=Vector2.new(0,.5),UDim2.new(0,14,.5,0)
local railScale=Instance.new("UIScale") railScale.Parent=rail
local navigationButtons = {}
for i,entry in {{"DINOS","dinos","collection",C.blue},{"EGGS","egg","eggs",C.gold},{"FUSION","fusion","fusion",C.purple},{"HOME","home","home",C.accent},{"AURAS","aura","auras",C.purple},{"POTIONS","potion","potions",C.accent},{"SETTINGS","shield","settings",C.card}} do
    local b=button(rail,entry[1],7,7+(i-1)*62,172,54,entry[4],function() open(entry[3]) end)
    b.TextSize=20
    art(b,NavigationArtwork[entry[3]] or entry[2],5,6,40)
    b.Text=""
    label(b,entry[1],52,0,114,54,19)
    table.insert(navigationButtons,b)
end
local hud=box(gui,0,0,390,94,C.panel,2)
hud.AnchorPoint,hud.Position=Vector2.new(0,1),UDim2.new(0,18,1,-18)
local hudScale=Instance.new("UIScale") hudScale.Parent=hud
art(hud,"leaf",8,12,64)
local growthLabel=label(hud,"0 GROWTH",82,3,290,42,30,C.accent)
art(hud,"catches",40,48,32)
local catchLabel=label(hud,"0 catches  •  Sanctuary",82,47,290,34,20)
local crystalHUD=box(gui,0,0,260,48,C.panel,2)
crystalHUD.AnchorPoint,crystalHUD.Position=Vector2.new(1,0),UDim2.new(1,-20,0,8)
art(crystalHUD,"amber",6,4,40)
local crystalText=label(crystalHUD,"0 Crystals",50,0,203,48,24,C.gold)
local timers=Instance.new("Frame")
timers.BackgroundTransparency,timers.Size,timers.AnchorPoint,timers.Position,timers.Parent=1,UDim2.fromOffset(286,220),Vector2.new(1,1),UDim2.new(1,-20,1,-100),gui
local timerScale=Instance.new("UIScale") timerScale.Parent=timers
local leapButton=button(timers,"LEAP [E]",0,0,286,60,C.blue,function()
    if shade.Visible then return end
    leapRemote:FireServer()
end)
leapButton.Text=""
art(leapButton,"leap",4,5,48)
local leapText=label(leapButton,"LEAP [E]",56,0,225,60,22)
local weatherTile=box(timers,0,72,286,62,C.panel,2)
local weatherArt=Theme.icon(weatherTile,"weather")
if weatherArt then weatherArt.Position,weatherArt.Size=UDim2.fromOffset(4,7),UDim2.fromOffset(48,48) end
local weatherText=label(weatherTile,"Weather in 10:00",56,0,226,62,20)
local buffsText=label(timers,"",0,145,286,68,16,C.gold)
local function timerText(seconds)
    local value=math.max(0,math.ceil(seconds))
    return string.format("%d:%02d",value//60,value%60)
end
local lastWeather=""
local function refreshProgressionHUD()
    local now=workspace:GetServerTimeNow()
    crystalText.Text=num("Crystals").." Crystals"
    local left=num("LeapReadyAt")-now
    leapText.Text=if left>0 then "LEAP "..timerText(left) else "LEAP [E] • READY"
    leapButton.BackgroundColor3=if left>0 then C.card else C.blue
    local c=player.Character
    leapButton.Active=left<=0 and c~=nil and c:GetAttribute("RunState")=="Active"
    local id=workspace:GetAttribute("WeatherId") or "clear"
    if id~=lastWeather then
        lastWeather=id
        if weatherArt then weatherArt:Destroy() end
        local event=ProgressionRules.item(ProgressionConfig.Weather,id)
        weatherArt=Theme.icon(weatherTile,if event then event.icon or id else "weather")
        if weatherArt then weatherArt.Position,weatherArt.Size=UDim2.fromOffset(4,7),UDim2.fromOffset(48,48) end
        if id~="clear" then notify((workspace:GetAttribute("WeatherName") or id).." started!",C.blue) end
    end
    weatherText.Text=if id=="clear" then "Weather in "..timerText((workspace:GetAttribute("NextWeatherAt") or now)-now) else (workspace:GetAttribute("WeatherName") or id).." "..timerText((workspace:GetAttribute("WeatherEndsAt") or now)-now)
    local p=progression() local lines={}
    for kind,buff in p.buffs do
        if buff.expiresAt>now then table.insert(lines,kind.." potion "..timerText(buff.expiresAt-now)) end
    end
    table.sort(lines)
    table.insert(lines,string.format("Growth %.2fx • Speed %.2fx • Loot %.2fx",num("GrowthMultiplier"),num("SpeedMultiplier"),num("LootMultiplier")))
    buffsText.Text=table.concat(lines,"\n")
    if pendingShop and os.clock()-pendingShop.started>8 then
        -- Retry the same operation token so a delayed result cannot charge twice.
        pendingShop.started=os.clock()
        shopAction:FireServer(pendingShop.action,pendingShop.id,pendingShop.token,pendingShop.replace)
    end
end
local action=button(gui,"EXPLORE",0,0,244,60,C.accent,function()
    local character=player.Character
    if character and character:GetAttribute("RunState")=="Active" then open("exit")
    elseif character and character:GetAttribute("RunState")=="Sanctuary" then startRun:FireServer() close() end
end)
action.AnchorPoint,action.Position=Vector2.new(1,1),UDim2.new(1,-20,1,-22)
local actionScale=action:FindFirstChildOfClass("UIScale") :: UIScale
local function scales()
    scale.Scale=viewportScale()
    closeButton.Size=UDim2.fromOffset(math.max(80,46/viewportScale()),math.max(62,46/viewportScale()))
    local camera=workspace.CurrentCamera
    local size=if camera then camera.ViewportSize else Vector2.new(1280,720)
    local small=math.clamp(math.min(size.X/1000,size.Y/800),.3,1)
    railScale.Scale,hudScale.Scale,actionScale.Scale,timerScale.Scale=small,small,small,small
    hud:SetAttribute("UIScaleBase",small)
    timers.Position=UDim2.new(1,-20,1,if Input.TouchEnabled then -190 else -100)
    action.Position=UDim2.new(1,-20,1,if Input.TouchEnabled then -120 else -22)
    action:SetAttribute("UIScaleBase",small)
    if Input.TouchEnabled then
        -- Keep navigation above the joystick and retain usable touch targets.
        railScale.Scale=math.min(1,(size.X-28)/630)
        rail.AnchorPoint,rail.Position,rail.Size=Vector2.new(.5,0),UDim2.new(.5,0,0,56),UDim2.fromOffset(630,58)
        for i,b in navigationButtons do
            b.Position,b.Size=UDim2.fromOffset(7+(i-1)*88,7),UDim2.fromOffset(82,44)
            for _,child in b:GetChildren() do
                if child:IsA("TextLabel") then
                    child.Position,child.Size,child.TextSize=UDim2.fromOffset(28,0),UDim2.fromOffset(52,44),11
                elseif child:IsA("GuiObject") then
                    child.Position,child.Size=UDim2.fromOffset(3,10),UDim2.fromOffset(24,24)
                end
            end
        end
        hud.AnchorPoint,hud.Position=Vector2.new(0,0),UDim2.new(0,18,0,120)
        previewNotice.Text="STUDIO PREVIEW: UNSAVED"
        previewNotice.Size,previewNotice.AnchorPoint,previewNotice.Position=UDim2.fromOffset(240,25),Vector2.zero,UDim2.fromOffset(18,8)
        timerScale.Scale=math.max(small,44/60)
        timers.AnchorPoint=Vector2.new(1,0)
        timers.Position=UDim2.new(1,-20,0,120)
        foodDiagnostic.Visible=false
        actionScale.Scale=math.max(small,44/60)
        action.AnchorPoint,action.Position=Vector2.new(.5,1),UDim2.new(.5,0,1,-18)
        action:SetAttribute("UIScaleBase",actionScale.Scale)
    else
        previewNotice.Text="STUDIO PREVIEW • progress not saved • test currency"
        previewNotice.Size,previewNotice.AnchorPoint,previewNotice.Position=UDim2.fromOffset(500,25),Vector2.new(.5,0),UDim2.new(.5,0,0,8)
        rail.AnchorPoint,rail.Position,rail.Size=Vector2.new(0,.5),UDim2.new(0,14,.5,0),UDim2.fromOffset(186,444)
        for i,b in navigationButtons do
            b.Position,b.Size=UDim2.fromOffset(7,7+(i-1)*62),UDim2.fromOffset(172,54)
            for _,child in b:GetChildren() do
                if child:IsA("TextLabel") then
                    child.Position,child.Size,child.TextSize=UDim2.fromOffset(52,0),UDim2.fromOffset(114,54),19
                elseif child:IsA("GuiObject") then
                    child.Position,child.Size=UDim2.fromOffset(5,6),UDim2.fromOffset(40,40)
                end
            end
        end
        hud.AnchorPoint,hud.Position=Vector2.new(0,1),UDim2.new(0,18,1,-18)
        timers.AnchorPoint=Vector2.new(1,1)
        action.AnchorPoint=Vector2.new(1,1)
        foodDiagnostic.Visible=RunService:IsStudio()
    end
    toastScale.Scale=math.min(1,(size.X-20)/440)
end
local function characterAdded(character: Model)
    local humanoid=character:WaitForChild("Humanoid",10) :: Humanoid?
    if not humanoid or player.Character~=character then return end
    local camera=workspace.CurrentCamera
    if camera then camera.CameraType,camera.CameraSubject=Enum.CameraType.Custom,humanoid end
    humanoid:SetStateEnabled(Enum.HumanoidStateType.Jumping,true)
    lastGrowth=0
    lastEggCount=0
end
player.CameraMaxZoomDistance=Config.CameraMaxZoom
player.CharacterAdded:Connect(characterAdded)
if player.Character then task.spawn(characterAdded,player.Character) end
if workspace.CurrentCamera then workspace.CurrentCamera:GetPropertyChangedSignal("ViewportSize"):Connect(scales) end
gui:GetPropertyChangedSignal("AbsoluteSize"):Connect(scales)
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
        notify(string.format("+%.1f Growth!",growth-lastGrowth),C.accent)
        if motion then
            hudScale.Scale*=1.06
            TweenService:Create(hudScale,TweenInfo.new(.2,Enum.EasingStyle.Back),{Scale=hud:GetAttribute("UIScaleBase") or 1}):Play()
        end
    end
    lastGrowth=growth
    local ok,tags=pcall(function() return Http:JSONDecode(if character then character:GetAttribute("RunEggEvents") or "[]" else "[]") end)
    if ok and typeof(tags)=="table" then
        if #tags>lastEggCount and state=="Active" then
            local newest=tags[#tags]
            local mutation=ProgressionRules.item(ProgressionConfig.EventMutations,newest.mutationId or "")
            notify(if mutation then mutation.name.." egg caught!" else "Reward egg caught!",if mutation then C.gold else C.blue)
        end
        lastEggCount=#tags
    end
    refreshProgressionHUD()
    if active=="eggs" and refreshEggs then refreshEggs() end
    if player:GetAttribute("ProfileState")=="Loaded" and state=="Sanctuary" and not seenTutorial then seenTutorial=true open("tutorial") end
end)
for _,attribute in {"EquippedSpeciesId","CollectionJson","ChestQueueJson","ProgressionJson"} do
    player:GetAttributeChangedSignal(attribute):Connect(function()
        if table.find({"collection","detail","fusion","eggs","auras","potions"},active) then body:ClearAllChildren() render(active) end
    end)
end
player:GetAttributeChangedSignal("LastClaimedChestId"):Connect(function() hatchPending=false task.defer(function() open("hatch") end) end)
player:GetAttributeChangedSignal("LastRunEndAt"):Connect(function() if not autoHatching then open("results") end end)
player:GetAttributeChangedSignal("LastSettledRunId"):Connect(function()
    local serial=hatchCancelSerial
    task.spawn(function()
        local deadline=os.clock()+15
        repeat task.wait(.1) until serial~=hatchCancelSerial or os.clock()>deadline
            or (player.Character and player.Character:GetAttribute("RunState")=="Sanctuary")
        if serial==hatchCancelSerial and str("NextChestId")~="" and player.Character and player.Character:GetAttribute("RunState")=="Sanctuary" then autoHatching=true hatchNext() end
    end)
end)
player:GetAttributeChangedSignal("LastRewardText"):Connect(function() if active=="results" then body:ClearAllChildren() render(active) end end)
for _,attribute in {"LastEquipStatus","LastMutationStatus","LastChestClaimStatus"} do
    player:GetAttributeChangedSignal(attribute):Connect(function()
        local status=str(attribute)
        if attribute=="LastChestClaimStatus" then hatchPending=false end
        if status=="claimed" then toast.Visible=false
        elseif status=="equipped" or status=="mutated" then notify("Success!",C.accent)
        elseif status~="" and status~="duplicate" then notify(status:gsub("_"," "),C.red) end
    end)
end
Input.InputBegan:Connect(function(input,processed)
    if processed then return end
    if (input.KeyCode==Enum.KeyCode.E or input.KeyCode==Enum.KeyCode.ButtonY) and not shade.Visible then leapRemote:FireServer()
    elseif input.KeyCode==Enum.KeyCode.Escape then close()
    elseif input.KeyCode==Enum.KeyCode.C then open("collection")
    elseif input.KeyCode==Enum.KeyCode.B then open("eggs") end
end)
