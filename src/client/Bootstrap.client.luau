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
local NestQueue = require(Shared.NestQueue)
local EggsLogic = require(Shared.EggsLogic)
local EggsScreen = require(script.Parent.EggsScreen)
local Preview = require(Shared.DinosaurPreview)
local ModelPreview = require(Shared.ModelPreview)
local HatchPresentation = require(Shared.HatchPresentation)
local HatchTimeline = require(Shared.HatchTimeline)
local HatchSequence = require(script.Parent.HatchSequence)
local DinoIndexPanels = require(script.Parent.DinoIndexPanels)
local ProgressionConfig=require(Shared.ProgressionConfig)
local ProgressionRules=require(Shared.ProgressionRules)
local EggTraits=require(Shared.EggTraits)
local PreviewTraits=require(script.Parent.PreviewTraits)
local EggGenetics=require(Shared.EggGenetics)
local EggAppearance=require(Shared.EggAppearance)
local ShopOdds=require(Shared.ShopOdds)
local UIFormat=require(Shared.UIFormat)
local RevealSkip=require(Shared.RevealSkip)
local NotifyQueue=require(Shared.NotifyQueue)
local EggOutcomeView=require(Shared.EggOutcomeView)
local TouchLayout=require(Shared.TouchLayout)
local Sfx=require(Shared.Sfx)
local NextGoal=require(Shared.NextGoal)
local FusionSelection=require(Shared.FusionSelection)
local fusionMenuOk,FusionMenu=pcall(require,script.Parent.FusionMenu)
local Marketplace=game:GetService("MarketplaceService")
local C = Theme.Colors
local remotes = ReplicatedStorage:WaitForChild("BeDinoRemotes")
local startRun = remotes:WaitForChild("RequestStartRun") :: RemoteEvent
local endRun = remotes:WaitForChild("RequestEndRun") :: RemoteEvent
local equip = remotes:WaitForChild("EquipSpecies") :: RemoteEvent
local hatch = remotes:WaitForChild("ClaimChest") :: RemoteEvent
local setSkipRemote = remotes:WaitForChild("SetRevealSkip") :: RemoteEvent
local claimNestRemote = remotes:WaitForChild("ClaimNest") :: RemoteEvent -- BD-090 egg nests menu
local fuse = remotes:WaitForChild("MutateSpecies") :: RemoteEvent
local shopAction=remotes:WaitForChild("ProgressionAction") :: RemoteEvent
local shopResult=remotes:WaitForChild("ProgressionResult") :: RemoteEvent
local leapRemote=remotes:WaitForChild("RequestLeap") :: RemoteEvent
local gui = Instance.new("ScreenGui")
gui.Name,gui.ResetOnSpawn,gui.ZIndexBehavior = "BeDinoUI",false,Enum.ZIndexBehavior.Sibling
-- BD-054: lay out inside the device safe area and below/around Roblox core UI.
gui.ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets
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
local jsonCache = {}
local function decoded(attribute: string, fallback: string)
    local raw=str(attribute,fallback)
    local cached=jsonCache[attribute]
    if cached and cached.raw==raw then return cached.data end
    local ok,data=pcall(function() return Http:JSONDecode(raw) end)
    local result=if ok and typeof(data)=="table" then data else {}
    jsonCache[attribute]={raw=raw,data=result}
    return result
end
local function copies(id: string): (number,number,number)
    local entry = decoded("CollectionJson","{}")[id]
    return if entry then entry.base or 0 else 0, if entry then entry.gold or 0 else 0, if entry then entry.diamond or 0 else 0
end
local function bestMutation(id: string): string
    local _,gold,diamond = copies(id)
    return if diamond>0 then "diamond" elseif gold>0 then "gold" else "base"
end
local function eventMutation(id: string)
    return ProgressionRules.eventMutation(decoded("CollectionJson","{}")[id])
end
local fusionTarget = "gold"
local hatchPending = false
local autoHatching = false
-- BD-170: Open starts the hatch screen at once; the server answer is supplied to it later. pendingHatch = {version, supply, handle}.
local hatchState: {pending: {version: number, supply: () -> (), handle: any}?, fresh: boolean, next: (() -> boolean)?} = {pending=nil, fresh=false, next=nil}
local hatchCancelSerial = 0
local function ownedTraits(id: string)
    return EggTraits.selected(decoded("CollectionJson","{}")[id])
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
    b.Activated:Connect(function() Sfx.play("ui_click") callback() end)
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
local updateNavigation=function() end
local function close()
    autoHatching=false
    hatchCancelSerial+=1
    modalVersion+=1
    local version=modalVersion
    active=""
    updateNavigation()
    Theme.animate(scale,.12,{Scale=scale.Scale*.96})
    Theme.animate(shade,.12,{BackgroundTransparency=1})
    Theme.animate(panel,.12,{Position=UDim2.fromScale(.5,.52)})
    task.delay(if motion then .13 else 0,function() if modalVersion==version then shade.Visible=false end end)
    Theme.animate(blur,.12,{Size=0})
end
local closeButton=button(header,"X",770,1,80,76,C.red,close)
closeButton.AnchorPoint,closeButton.Position=Vector2.new(1,0),UDim2.new(1,-2,0,1)
shade.Activated:Connect(close)
-- BD-067 toasts: up to 3 pooled cards stacked from the old toast slot (y=80). NotifyQueue decides
-- what shows (priority, merge, throttle); this only draws. Tap a card to dismiss the newest one.
local drawToasts
local toastLayer=Instance.new("Frame")
toastLayer.Name,toastLayer.AnchorPoint,toastLayer.Position=  "Toasts",Vector2.new(.5,0),UDim2.new(.5,0,0,80)
toastLayer.Size,toastLayer.BackgroundTransparency,toastLayer.ZIndex,toastLayer.Parent=UDim2.fromOffset(440,186),1,50,gui
local toastScale=Instance.new("UIScale") toastScale.Parent=toastLayer
local notifyQueue=NotifyQueue.new()
local toastKindColor={info=C.blue,good=C.accent,warning=C.red,major=C.gold}
local toastCards={}
for i=1,NotifyQueue.MaxVisible do
    local card=box(toastLayer,0,(i-1)*62,440,56,C.card,50)
    card.Visible=false
    local bar=box(card,0,0,10,56,C.blue,51)
    local plate=box(card,16,6,44,44,C.panel,51)
    Theme.decorate(plate,22)
    local title=label(card,"",68,3,330,30,21)
    local detail=label(card,"",68,30,330,22,15,Color3.fromRGB(220,224,235))
    local count=label(card,"",392,6,44,44,20,C.gold)
    for _,t in {title,detail} do t.TextXAlignment=Enum.TextXAlignment.Left t.TextTruncate=Enum.TextTruncate.AtEnd end
    local tap=Instance.new("TextButton")
    tap.Text,tap.BackgroundTransparency,tap.Size,tap.ZIndex,tap.Parent="",1,UDim2.fromScale(1,1),55,card
    tap.Activated:Connect(function() if NotifyQueue.dismissTop(notifyQueue) then drawToasts() end end)
    toastCards[i]={frame=card,bar=bar,plate=plate,title=title,detail=detail,count=count,seq=0}
end
drawToasts=function()
    for i,slot in toastCards do
        local entry=notifyQueue.visible[i]
        slot.frame.Visible=entry~=nil
        if entry then
            local color=(entry.tint and Theme.RarityColors[entry.tint]) or toastKindColor[entry.kind] or C.blue
            slot.bar.BackgroundColor3,slot.plate.BackgroundColor3=color,C.panel:Lerp(color,.35)
            slot.title.Text,slot.detail.Text=entry.text,entry.body or ""
            slot.title.Size=UDim2.fromOffset(330,if entry.body then 30 else 50)
            slot.count.Text=if entry.count>1 and not entry.amount then "x"..entry.count else ""
            local target=UDim2.fromOffset(0,(i-1)*62)
            if slot.seq~=entry.seq then
                slot.seq=entry.seq
                for _,child in slot.plate:GetChildren() do if child:IsA("GuiObject") then child:Destroy() end end
                if entry.icon then art(slot.plate,entry.icon,2,2,40) end
                slot.frame.Position=if motion then target-UDim2.fromOffset(0,12) else target
                if motion and entry.kind=="major" then
                    local pop=slot.plate:FindFirstChildOfClass("UIScale") or Instance.new("UIScale")
                    pop.Scale,pop.Parent=1.15,slot.plate
                    Theme.animate(pop,.4,{Scale=1},Enum.EasingStyle.Back)
                end
            end
            Theme.animate(slot.frame,if motion then .14 else 0,{Position=target})
        else
            slot.seq=0
        end
    end
end
local function pumpToasts()
    if NotifyQueue.update(notifyQueue,os.clock(),shade.Visible) then drawToasts() end
end
-- Existing call sites keep notify(text,color); opts adds {kind,key,icon,body,tint,amount,format}.
local function notify(text: string,color: Color3?,opts: any?)
    local o=opts or {}
    local kind=o.kind or (if color==C.red then "warning" elseif color==C.gold or color==C.accent then "good" else "info")
    NotifyQueue.push(notifyQueue,os.clock(),{text=text,body=o.body,kind=kind,key=o.key,icon=o.icon,tint=o.tint,amount=o.amount,format=o.format})
    pumpToasts()
end
task.spawn(function()
    while gui.Parent do pumpToasts() task.wait(.1) end
end)
local function viewportScale(): number
    local camera=workspace.CurrentCamera
    local size=gui.AbsoluteSize
    return math.max(.05,math.min(1,(size.X-40)/860,(size.Y-40)/520))
end
-- BD-054: prefer the active input style; fall back to TouchEnabled on older clients.
local function touchMode(): boolean
    local ok,touch=pcall(function() return (Input :: any).PreferredInput==(Enum :: any).PreferredInput.Touch end)
    if ok and typeof(touch)=="boolean" then return touch end
    return Input.TouchEnabled
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
-- Polish: pooled reveal juice. At most one flash and one banner exist at a time; nothing runs per frame
-- except the capped <=0.22 s camera shake, and every effect is skipped when motion is off.
local flashFrame=Instance.new("Frame")
flashFrame.Name,flashFrame.BorderSizePixel,flashFrame.BackgroundTransparency,flashFrame.Visible="RevealFlash",0,1,false
flashFrame.Size,flashFrame.ZIndex,flashFrame.Active=UDim2.fromScale(1,1),44,false
flashFrame.Parent=gui
local function flash(color: Color3,strength: number)
    if not motion then return end
    flashFrame.BackgroundColor3,flashFrame.BackgroundTransparency,flashFrame.Visible=color,1-math.clamp(strength,0,.5),true
    Theme.animate(flashFrame,.35,{BackgroundTransparency=1})
    task.delay(.4,function() if flashFrame.BackgroundTransparency>=.99 then flashFrame.Visible=false end end)
end
local shaking=false
local function shake(amplitude: number)
    local camera=workspace.CurrentCamera
    if not motion or shaking or not camera then return end
    shaking=true
    local amp=math.min(amplitude,.15)
    local started=os.clock()
    RunService:BindToRenderStep("BeDinoRevealShake",Enum.RenderPriority.Camera.Value+1,function()
        local t=os.clock()-started
        if t>=.22 or not camera.Parent then RunService:UnbindFromRenderStep("BeDinoRevealShake") shaking=false return end
        local fade=1-t/.22
        camera.CFrame=camera.CFrame*CFrame.new(math.sin(t*90)*amp*fade,math.cos(t*70)*amp*fade,0)
    end)
end
local function banner(parent: GuiObject,text: string,color: Color3)
    local b=label(parent,text,80,2,660,52,40,color)
    b.TextXAlignment=Enum.TextXAlignment.Center
    if motion then
        local s=Instance.new("UIScale") s.Scale,s.Parent=.7,b
        Theme.animate(s,.25,{Scale=1},Enum.EasingStyle.Back)
    end
    task.delay(1.4,function() if b.Parent then b:Destroy() end end)
end
local popLabel=label(gui,"",0,0,160,40,28,C.accent)
popLabel.AnchorPoint,popLabel.Position,popLabel.Visible,popLabel.ZIndex=Vector2.new(.5,.5),UDim2.fromScale(.5,.4),false,43
local popSerial=0
local function pickupPop(text: string)
    popSerial+=1
    local serial=popSerial
    popLabel.Text=text
    popLabel.Visible=true
    popLabel.TextTransparency,popLabel.TextStrokeTransparency=0,0
    popLabel.Position=UDim2.fromScale(.5,.4)
    Theme.animate(popLabel,.5,{Position=UDim2.fromScale(.5,if motion then .33 else .4),TextTransparency=1,TextStrokeTransparency=1})
    task.delay(.55,function() if serial==popSerial then popLabel.Visible=false end end)
end
local render
local openFusion
local rail
local function open(name: string)
    local wasVisible=shade.Visible and active~=""
    modalVersion+=1
    active=name
    updateNavigation()
    body:ClearAllChildren()
    shade.Visible=true
    if not wasVisible then
        scale.Scale=viewportScale()*(if motion then .96 else 1)
        shade.BackgroundTransparency=1
        panel.Position=UDim2.fromScale(.5,.52)
    end
    Theme.animate(scale,.16,{Scale=viewportScale()})
    Theme.animate(panel,.16,{Position=UDim2.fromScale(.5,.5)})
    Theme.animate(shade,.14,{BackgroundTransparency=.42})
    Theme.animate(blur,.16,{Size=if motion then 8 else 0})
    render(name)
    -- Animate the content as one layer, keeping large collections inexpensive.
    body.Position=UDim2.fromOffset(18,if motion then 106 else 98)
    Theme.animate(body,.14,{Position=UDim2.fromOffset(18,98)})
end
local fusionProbe: string?=nil -- nil unknown, "ok", "disabled"
local function fusionRemote(): RemoteFunction?
    local folder=ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    local found=folder and folder:FindFirstChild("FusionAction")
    return if found and found:IsA("RemoteFunction") then found else nil
end
local function showFusionMenu()
    close()
    if rail then FusionMenu.setLeftInset(rail.AbsolutePosition.X+rail.AbsoluteSize.X+10-gui.AbsolutePosition.X) end
    FusionMenu.open()
end
-- Nav FUSION + Dino Index footer: the new Pattern Fusion Menu when FusionAction answers.
openFusion=function()
    local fn=fusionRemote()
    local function decide()
        local target=FusionSelection.navTarget({menuLoaded=fusionMenuOk,remote=fn~=nil,probe=fusionProbe,profile=Config.ReleaseProfile})
        if target=="menu" then showFusionMenu()
        elseif target=="legacy" then open("fusion")
        else notify("Fusion is not available on this server yet",C.gold) end
    end
    if fn and fusionMenuOk and fusionProbe==nil then
        task.spawn(function()
            local ok,response=pcall(function() return (fn :: RemoteFunction):InvokeServer({action="list",limit=1}) end)
            fusionProbe=if ok and typeof(response)=="table" and response.reason=="fusion_disabled" then "disabled" else "ok"
            decide()
        end)
    else decide() end
end
local function hero(parent: GuiObject,id: string,x: number,y: number,w: number,h: number,gold: (boolean | string)?,fusionPreview: boolean?)
    local traits=if fusionPreview then nil else ownedTraits(id)
    local view=Preview.add(parent,id,if traits and traits.genes then "base" else gold or "base")
    view.Position,view.Size = UDim2.fromOffset(x,y),UDim2.fromOffset(w,h)
    PreviewTraits.add(view,traits)
    return view
end
local rarityColors=Theme.RarityColors
local rarityNames=Config.SpeciesRarityNames
local function speciesIndex(id: string): number return Config.SpeciesRarities[id] or 1 end
local oddsWeight,oddsTotal={},0 -- base chance of one purchased egg, shown on Dino Index cards (docs/85)
for _,row in Config.ChestSpeciesWeights do oddsWeight[row.speciesId]=row.weight oddsTotal+=row.weight end
local function meter(parent: GuiObject,x: number,y: number,w: number,value: number,maxValue: number,color: Color3,text: string)
    local b=box(parent,x,y,w,34,C.outline,parent.ZIndex+1)
    local fill=Instance.new("Frame")
    local fraction=if maxValue>0 then math.clamp(value/maxValue,0,1) else 0
    fill.Size,fill.BorderSizePixel,fill.BackgroundColor3,fill.ZIndex,fill.Parent=UDim2.new(if motion then 0 else fraction,0,1,0),0,color,b.ZIndex+1,b
    Theme.animate(fill,.22,{Size=UDim2.new(fraction,0,1,0)})
    label(b,text,0,0,w,34,20)
end
local function ownsAutoOpen(): boolean return player:GetAttribute("OwnsAutoOpen")==true end
local function autoOpenSelection()
    return EggsLogic.effective(decoded("RevealSkipJson","[]"),Config.AutoOpenRequiresPass,ownsAutoOpen())
end
local function autoOpenText(): string
    if EggsLogic.locked(Config.AutoOpenRequiresPass,ownsAutoOpen()) then return "Auto-open is locked" end
    local names={}
    for _,rarity in autoOpenSelection() do table.insert(names,Config.SpeciesRarityNames[rarity]) end
    return if #names==0 then "Auto-open: off" else "Auto-open: "..table.concat(names,", ")
end
local function queue()
    return decoded("ChestQueueJson","[]")
end
local skipAllReveals=false -- "Skip all" during a hatch batch: every non-notable egg takes the quick path
local skippedEntries={} -- BD-044: eggs hatched and credited but not animated this batch
local batchEntries={} -- BD-069: every egg claimed this batch, for the one summary toast
local function emitHatchSummary()
    local summary=NotifyQueue.hatchSummary(batchEntries,rarityNames)
    batchEntries={}
    if summary then notify(summary.text,nil,summary) end
end
local function finishBatch()
    autoHatching=false
    skipAllReveals=false
    emitHatchSummary()
    if #skippedEntries>0 then open("batchSummary") else open("eggs") end
end
-- Sends the claim for the next egg. Returns true when a request went out (the batch goes on), false when the batch ended
-- or a request is already running.
hatchState.next = function(): boolean
    local id=str("NextChestId")
    if id=="" or workspace:GetServerTimeNow()<num("NextChestReadyAt") then
        finishBatch()
        return false
    end
    if hatchPending then return false end
    hatchPending=true
    hatch:FireServer(id,Http:GenerateGUID(false))
    task.delay(8,function()
        if hatchPending then
            hatchPending=false autoHatching=false skipAllReveals=false
            notify("Hatching stopped",C.red,{key="hatch_error",icon="egg",body="Tap an egg to try again"})
            local waiting=hatchState.pending
            if waiting and waiting.version==modalVersion and active=="hatch" and waiting.handle.pending() then open("eggs") end -- never leave an egg wobbling forever
        end
    end)
    return true
end
local function progression()
    local data=decoded("ProgressionJson","{}")
    if typeof(data.auras)~="table" or typeof(data.potions)~="table" or typeof(data.buffs)~="table" then return {crystals=0,auras={},equippedAura="",potions={},buffs={}} end
    return data
end
local chosenAura="meadow"
local cosmeticTab="auras"
local trailPage=1
local oddsLevelOverride=nil
local outcomeState={page=1,filters={}}
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
    if ok then Sfx.play("shop_buy") end
    notify(if ok then "Done!" else NotifyQueue.statusText(status),if ok then C.accent else C.red,{key=if ok then "ok" else "error"})
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
        heading.Text,header.BackgroundColor3="Crystal Shops",C.purple
        local p=progression()
        p.trails=p.trails or {}
        local isTrail=cosmeticTab=="trails"
        local touch=Input.TouchEnabled
        local targetHeight=if touch then math.max(45,45/viewportScale()) else 44
        local tabsHeight=if touch then targetHeight else 40
        local cardsY=tabsHeight+12
        local cardsHeight=if touch then 402-cardsY-targetHeight-12 else 270
        local buyY=cardsHeight-targetHeight-10
        for i,tab in {"auras","trails","eggs","conditions","crystals"} do
            button(body,string.upper(tab),(i-1)*165,0,155,tabsHeight,if cosmeticTab==tab then C.blue else C.card,function() cosmeticTab=tab open("auras") end).TextSize=20
        end
        if cosmeticTab=="eggs" then
            art(body,"egg",20,cardsY+12,220)
            label(body,"Random Egg",270,cardsY,535,40,30,C.gold)
            label(body,ProgressionConfig.RandomEggPrice.." Crystals\nBalance: "..num("Crystals").."  •  Level "..num("AccountLevel"),270,cardsY+45,535,60,22)
            button(body,"VIEW ODDS",270,cardsY+119,535,targetHeight,C.blue,function() oddsLevelOverride=nil outcomeState={page=1,filters={}} open("eggOdds") end)
            button(body,"BUY EGG",270,cardsY+targetHeight+130,535,targetHeight,C.accent,function() open("eggPurchase") end)
            return
        elseif cosmeticTab=="conditions" then
            local weights=ShopOdds.conditionPercents(p.conditionLevel or 0) -- BD-045: normalized percents
            local upgrade=ProgressionConfig.ConditionUpgrades[(p.conditionLevel or 0)+1]
            -- docs/73: plain egg per condition on a floor swatch; chance only (no stats text, no odds screen).
            label(body,"Condition level "..(p.conditionLevel or 0),0,cardsY,824,30,24,C.gold)
            for i,row in ProgressionConfig.Conditions do
                local x=(i-1)*165
                label(body,row.name,x,cardsY+32,155,28,22)
                local tile=box(body,x,cardsY+62,155,110,Color3.fromRGB(122,148,112):Lerp(C.panel,.25),24)
                local view=ModelPreview.add(tile,"egg")
                EggAppearance.apply(view,EggGenetics.neutral(row.id),true)
                label(body,string.format("%g%%",weights[i]),x,cardsY+176,155,34,24,C.blue)
            end
            button(body,if upgrade then "UPGRADE: "..upgrade.price.." CRYSTALS" else "MAX LEVEL",142,cardsY+220,540,targetHeight,C.accent,function() if upgrade then open("conditionConfirm") end end).TextSize=20
            label(body,if upgrade then "Unlocks at level "..upgrade.requiredLevel else "Top level reached",0,cardsY+220+targetHeight+6,824,30,19,C.gold)
            return
        elseif cosmeticTab=="crystals" then
            art(body,"amber",20,cardsY+12,220)
            label(body,num("Crystals").." Crystals",270,cardsY,535,50,30,C.gold)
            if not Config.CrystalPacksEnabled then label(body,"COMING SOON",270,cardsY+38,535,20,16,C.gold) end
            local products={} for id,amount in Config.DeveloperProducts do table.insert(products,{id=id,amount=amount}) end
            table.sort(products,function(a,b) return a.amount<b.amount end)
            if #products==0 then label(body,"Robux packs unavailable",270,cardsY+70,535,80,27)
            else
                local list=Instance.new("ScrollingFrame") list.BackgroundTransparency,list.BorderSizePixel,list.Size,list.Position,list.CanvasSize,list.ZIndex,list.Parent=1,0,UDim2.fromOffset(535,250),UDim2.fromOffset(270,cardsY+60),UDim2.fromOffset(0,#products*(targetHeight+12)),24,body
                for i,product in products do
                    local saleReady=false
                    local rowY=(i-1)*(targetHeight+12)
                    art(list,"amber",4,rowY+6,targetHeight-12)
                    local b=button(list,product.amount.." CRYSTALS",targetHeight+4,rowY,516-targetHeight,targetHeight,C.gold,function() if saleReady then Marketplace:PromptProductPurchase(player,product.id) end end)
                    task.spawn(function()
                        local ok,info=pcall(function() return Marketplace:GetProductInfo(product.id,Enum.InfoType.Product) end)
                        if b.Parent then
                            if ok and info.IsForSale~=false and typeof(info.PriceInRobux)=="number" then
                                saleReady=Config.CrystalPacksEnabled==true
                                b.Text=product.amount.." CRYSTALS • R$ "..info.PriceInRobux
                                b.Active=saleReady
                                if not saleReady then b.BackgroundColor3=C.card end
                            else b.Text=product.amount.." CRYSTALS • UNAVAILABLE" b.Active=false end
                        end
                    end)
                end
            end
            return
        end
        local owned=if isTrail then p.trails else p.auras
        local equippedId=if isTrail then p.equippedTrail or "" else p.equippedAura
        for i,item in (if isTrail then ProgressionConfig.Trails else ProgressionConfig.Auras) do
            if isTrail and (i<(trailPage-1)*3+1 or i>trailPage*3) then continue end
            local slot=if isTrail then (i-1)%3 else i-1
            local color=Color3.fromRGB(item.color[1],item.color[2],item.color[3])
            local card=box(body,slot*276,cardsY,264,cardsHeight,color,24)
            label(card,item.name,6,5,252,34,25)
            label(card,if isTrail then "Level "..item.level.." • "..(UIFormat.boost("Speed",item.speed) or "Speed") else (UIFormat.boost("Growth",item.growth) or "Growth"),4,42,256,30,19)
            art(card,(if isTrail then "trail_" else "aura_")..item.id,102,76,60)
            label(card,if owned[item.id] then "Owned" else item.price.." Crystals",4,buyY-30,256,27,21,C.gold)
            local equipped=equippedId==item.id
            local locked=isTrail and num("AccountLevel")<item.level and not owned[item.id]
            button(card,if equipped then "UNEQUIP" elseif owned[item.id] then "EQUIP" elseif locked then "LEVEL "..item.level else "BUY",12,buyY,240,targetHeight,C.card,function()
                if locked then notify("Requires account level "..item.level,C.gold) return end
                if owned[item.id] then transact(if isTrail then "equipTrail" else "equipAura",if equipped then "" else item.id)
                else chosenAura=item.id open("auraConfirm") end
            end)
        end
        local footerY=402-targetHeight
        if isTrail then
            button(body,"<",0,footerY,110,targetHeight,C.blue,function() trailPage=math.max(1,trailPage-1) open("auras") end)
            button(body,">",714,footerY,110,targetHeight,C.blue,function() trailPage=math.min(4,trailPage+1) open("auras") end)
        end
        label(body,"Level "..num("AccountLevel").." • "..num("Crystals").." Crystals"..(if isTrail then " • "..trailPage.." / 4" else ""),115,footerY,590,targetHeight,21,C.gold)
    elseif name=="eggOdds" then
        heading.Text,header.BackgroundColor3="Egg Odds",C.blue
        local level=oddsLevelOverride or progression().conditionLevel or 0
        local lines=ShopOdds.lines(level)
        local list=Instance.new("ScrollingFrame") list.Name,list.BackgroundTransparency,list.BorderSizePixel,list.Size,list.CanvasSize,list.ScrollBarThickness,list.ZIndex,list.Parent="EggOdds",1,0,UDim2.fromOffset(824,308),UDim2.fromOffset(0,#lines*46),8,24,body
        local lineY=0
        for _,line in lines do
            local lineHeight=if #line>95 then 88 elseif #line>60 then 66 else 44
            label(list,line,10,lineY,790,lineHeight,21)
            lineY+=lineHeight+2
        end
        list.CanvasSize=UDim2.fromOffset(0,lineY)
        button(body,"FINAL OUTCOME DETAILS",0,322,402,math.max(64,45/viewportScale()),C.blue,function() open("eggOutcomes") end).TextSize=20
        button(body,"BACK TO SHOP",422,322,402,math.max(64,45/viewportScale()),C.blue,function() open("auras") end)
    elseif name=="eggOutcomes" then
        heading.Text,header.BackgroundColor3="Final Egg Outcomes",C.blue
        EggOutcomeView.add(body,outcomeState,oddsLevelOverride or progression().conditionLevel or 0,
            math.max(64,45/viewportScale()),function() open("eggOutcomes") end,function() open("eggOdds") end)
    elseif name=="eggPurchase" or name=="conditionConfirm" then
        local p=progression()
        local upgrade=ProgressionConfig.ConditionUpgrades[(p.conditionLevel or 0)+1]
        local isEgg=name=="eggPurchase"
        heading.Text,header.BackgroundColor3=if isEgg then "Buy Random Egg?" else "Upgrade Conditions?",C.gold
        local price=if isEgg then ProgressionConfig.RandomEggPrice elseif upgrade then upgrade.price else 0
        art(body,"egg",20,15,200)
        label(body,price.." Crystals\nBalance after: "..(num("Crystals")-price),260,10,550,80,27,C.gold)
        label(body,if isEgg then "Cracked: 20% hatch success. A failed hatch gives no dinosaur or refund. Queue-full purchases are not charged." else "Unlocks at level "..(if upgrade then upgrade.requiredLevel else 60)..". New eggs only.",260,105,550,95,23)
        if not isEgg and upgrade then
            local parts={} for i,row in ProgressionConfig.Conditions do table.insert(parts,row.name.." "..ShopOdds.conditionPercents(upgrade.level)[i].."%") end
            label(body,table.concat(parts," • "),0,213,824,60,21,C.blue)
        end
        if isEgg then -- docs/73: condition odds screen stays out of the UI (egg odds remain)
            button(body,"VIEW ODDS",0,300,250,math.max(64,45/viewportScale()),C.blue,function()
                oddsLevelOverride=nil
                outcomeState={page=1,filters={}} open("eggOdds")
            end)
        end
        button(body,"CONFIRM",270,300,270,math.max(64,45/viewportScale()),C.accent,function()
            transact(if isEgg then "buyEgg" else "upgradeCondition",if isEgg then "random" elseif upgrade then tostring(upgrade.level) else "") open("auras")
        end)
        button(body,"CANCEL",560,300,264,math.max(64,45/viewportScale()),C.red,function() open("auras") end)
    elseif name=="auraConfirm" then
        local isTrail=cosmeticTab=="trails"
        local item=ProgressionRules.item(if isTrail then ProgressionConfig.Trails else ProgressionConfig.Auras,chosenAura)
        heading.Text,header.BackgroundColor3=if isTrail then "Buy Trail?" else "Buy Aura?",C.purple
        art(body,(if isTrail then "trail_" else "aura_")..item.id,30,25,220)
        label(body,item.name.." • "..(if isTrail then "Cosmetic trail" else (UIFormat.boost("Growth",item.growth) or "Growth")),290,24,510,70,29)
        label(body,item.price.." Crystals\nBalance after purchase: "..(num("Crystals")-item.price),290,125,510,90,25,C.gold)
        button(body,if isTrail then "BUY TRAIL" else "BUY AURA",290,261,510,57,C.accent,function() transact(if isTrail then "buyTrail" else "buyAura",item.id) open("auras") end)
        button(body,"CANCEL",290,337,510,45,C.red,function() open("auras") end)
    elseif name=="potions" then
        heading.Text,header.BackgroundColor3="Potion Shop",C.accent
        local p=progression()
        -- BD-051: server-clock rotation. Offers/stock come from the shared deterministic rules; the server re-checks every purchase.
        local window=ProgressionRules.shopWindow(workspace:GetServerTimeNow())
        chosenPotionWindow=window
        local restock=label(body,"",0,0,824,32,21,C.gold)
        local function header_text()
            local left=math.max(0,math.ceil(ProgressionRules.shopEndsAt(window)-workspace:GetServerTimeNow()))
            restock.Text=string.format("Crystals: %s  •  New offers in %s",num("Crystals"),UIFormat.duration(left))
        end
        header_text()
        task.spawn(function()
            while restock.Parent and active=="potions" do
                task.wait(1)
                if not restock.Parent or active~="potions" then return end
                if ProgressionRules.shopWindow(workspace:GetServerTimeNow())~=window then
                    notify("Potion shop restocked",C.blue,{key="potion_restock",icon="potion_speed_Common"}) Sfx.play("shop_refresh")
                    body:ClearAllChildren() render("potions") return
                end
                header_text()
            end
        end)
        -- docs/68: 6 offers in a 3x2 grid plus the owned list scroll together, so the panel fits a phone landscape (UIScale) and desktop.
        local scroller=Instance.new("ScrollingFrame")
        scroller.Name="PotionScroll"
        scroller.Position,scroller.Size,scroller.BackgroundTransparency=UDim2.fromOffset(0,34),UDim2.fromOffset(824,368),1
        scroller.BorderSizePixel,scroller.ScrollBarThickness,scroller.ZIndex,scroller.Parent=0,8,body.ZIndex+1,body
        scroller.ScrollingDirection=Enum.ScrollingDirection.Y
        local rarityColor=Theme.RarityColors
        local function bottle(item) return "potion_"..item.kind.."_"..item.rarity end -- native vector bottle (PotionArt): shape = effect, trim/glow/pips = rarity
        for i,offer in ProgressionRules.shopOffers(window) do
            local item=ProgressionRules.item(ProgressionConfig.Potions,offer.id)
            local left=ProgressionRules.shopRemaining(p,window,offer.id)
            local x=((i-1)%3)*276 local y=math.floor((i-1)/3)*140
            local color=rarityColor[item.rarity] or C.accent
            local card=box(scroller,x,y,264,132,C.card:Lerp(color,if left>0 then .28 else .08),24)
            art(card,bottle(item),6,8,64)
            label(card,item.name,74,3,186,26,19,color)
            label(card,UIFormat.potion(item.kind,item.multiplier,item.duration),74,28,186,44,15)
            label(card,if left>0 then left.." left" else "Sold Out - back later",74,74,186,20,15,if left>0 then C.gold else C.red)
            local buy=button(card,if left>0 then item.price.." Crystals" else "SOLD OUT",8,96,248,30,if left>0 then color:Lerp(C.panel,.45) else C.card,function()
                if left>0 then chosenPotion=item.id open("potionConfirm") end
            end)
            buy.TextSize=16
        end
        label(scroller,"Rarer potions appear less often. Six of twelve are offered each restock.",0,284,824,22,15,C.gold)
        label(scroller,"Your potions (tap to use)",0,310,824,24,18,C.gold)
        local slot=0
        for _,item in ProgressionConfig.Potions do
            local owned=p.potions[item.id] or 0
            if owned>0 then
                local x=(slot%3)*276 local y=338+math.floor(slot/3)*46
                slot+=1
                button(scroller,item.name.." x"..owned.."  USE",x,y,264,40,C.purple,function()
                    chosenPotion=item.id
                    local buff=p.buffs[item.kind]
                    if buff and buff.expiresAt>workspace:GetServerTimeNow() then open("potionReplace") else transact("usePotion",item.id,false) end
                end).TextSize=16
            end
        end
        if slot==0 then label(scroller,"No potions yet. Buy from this restock's offers above.",0,338,824,32,18) end
        scroller.CanvasSize=UDim2.fromOffset(0,338+math.max(1,math.ceil(slot/3))*46+8)
    elseif name=="potionConfirm" or name=="potionReplace" then
        local item=ProgressionRules.item(ProgressionConfig.Potions,chosenPotion)
        local replacing=name=="potionReplace"
        heading.Text,header.BackgroundColor3=if replacing then "Replace Active Potion?" else "Buy Potion?",C.accent
        art(body,"potion_"..item.kind.."_"..item.rarity,30,22,220)
        label(body,item.name.." • "..UIFormat.potion(item.kind,item.multiplier,item.duration),290,15,510,62,28)
        label(body,if replacing then "Your current "..item.kind.." potion ends immediately. Its remaining time is lost. Consume 1 potion for a fresh "..UIFormat.duration(item.duration).."?" else UIFormat.duration(item.duration).." • "..item.price.." Crystals\nBalance after purchase: "..(num("Crystals")-item.price),290,101,510,135,24,C.gold)
        button(body,if replacing then "REPLACE & USE" else "BUY POTION",290,263,510,58,C.accent,function()
            if replacing then transact("usePotion",item.id,true) else transact("buyPotion",item.id.."@"..chosenPotionWindow,false) end
            open("potions")
        end)
        button(body,"CANCEL",290,339,510,44,C.red,function() open("potions") end)
    elseif name=="collection" then
        heading.Text,header.BackgroundColor3="Dino Index",C.blue
        local unlocked=0
        local list=Instance.new("ScrollingFrame")
        list.Name,list.Size,list.Position="DinoCards",UDim2.fromOffset(824,326),UDim2.fromOffset(0,0)
        list.BackgroundTransparency,list.BorderSizePixel,list.ScrollBarThickness=1,0,6
        local cardButtonHeight=math.max(45,45/viewportScale())
        local cardHeight=242+cardButtonHeight
        local rowHeight=cardHeight+12
        list.CanvasSize=UDim2.fromOffset(0,math.ceil(#Config.SpeciesOrder/3)*rowHeight)
        list.ZIndex,list.Parent=24,body
        for i,id in Config.SpeciesOrder do
            local base,gold,diamond=copies(id)
            local event=eventMutation(id)
            local rarity=speciesIndex(id)
            local found=base+gold+diamond>0 or event~=nil or ownedTraits(id)~=nil
            if found then unlocked+=1 end
            local look=FusionSelection.indexCard(found)
            local card=box(list,((i-1)%3)*276,math.floor((i-1)/3)*rowHeight,264,cardHeight,if found then rarityColors[rarity] else Color3.fromRGB(62,64,74),24)
            Theme.texture(card,264,cardHeight)
            label(card,look.nameText or Config.SpeciesDisplayNames[id],4,8,256,35,25)
            label(card,look.rarityText or (rarityNames[rarity].." • "..FusionSelection.pct(100*(oddsWeight[id] or 0)/oddsTotal).." of eggs"),4,44,256,25,18)
            if found then
                hero(card,id,7,70,250,128,bestMutation(id))
                label(card,if event then event.name.." mutation" elseif ownedTraits(id) then "Special variant" else string.format("%d Base • %d Gold • %d Diamond",base,gold,diamond),5,201,254,25,15)
                button(card,"VIEW DINO",12,233,240,cardButtonHeight,C.card,function() selected=id open("detail") end)
            else
                -- No button: silhouette block re-centered in the freed space. Soft edge = a faint, slightly larger
                -- copy underneath (2 viewports max, no per-frame work); skipped when motion/effects are reduced.
                local blockY=70+math.floor((cardButtonHeight+12)/2)
                if motion then
                    local halo=Preview.add(card,id,"silhouette")
                    halo.Name,halo.ImageTransparency=("SilhouetteSoftEdge"),.82
                    halo.Position,halo.Size=UDim2.fromOffset(-2,blockY-9),UDim2.fromOffset(268,146)
                end
                local view=Preview.add(card,id,"silhouette")
                view.Position,view.Size=UDim2.fromOffset(7,blockY),UDim2.fromOffset(250,128)
                label(card,look.status,5,blockY+134,254,25,15)
            end
        end
        meter(body,0,356,600,unlocked,#Config.SpeciesOrder,C.accent,string.format("Discovered: %d / %d",unlocked,#Config.SpeciesOrder))
        button(body,"FUSION",624,350,200,44,C.gold,function() openFusion() end)
    elseif name=="detail" and DinoIndexPanels.supported() then
        -- BD-149/150/151: drag-to-turn hero, My dinos grid, per-copy EQUIP, Sort and filter (src/client/DinoIndexPanels).
        local index=speciesIndex(selected)
        local base,gold,diamond=copies(selected)
        local event=eventMutation(selected)
        heading.Text,header.BackgroundColor3=Config.SpeciesDisplayNames[selected],rarityColors[index]
        DinoIndexPanels.species({
            body=body,speciesId=selected,color=rarityColors[index],
            owned=base+gold+diamond>0 or event~=nil or ownedTraits(selected)~=nil,
            fallbackStage=bestMutation(selected),
            fallbackLine=string.format("Base: %d • Gold: %d • Diamond: %d",base,gold,diamond),
            scale=viewportScale,
            revision=function() return num("ProfileRevision") end,
            equipped=function()
                local ok,genes=pcall(function() return Http:JSONDecode(str("EquippedGenesJson","null")) end)
                return {speciesId=str("EquippedSpeciesId","compy"),genes=if ok and typeof(genes)=="table" then genes else nil,
                    shiny=player:GetAttribute("EquippedShiny")==true,big=player:GetAttribute("EquippedBig")==true,mutationId=str("EquippedEventMutation")}
            end,
            equip=function(speciesId,variantKey) notify("Equipping...",C.blue) equip:FireServer(speciesId,Http:GenerateGUID(false),variantKey) end,
            notify=notify,
            onBack=function() open("collection") end,
        })
    elseif name=="detail" then
        local index=speciesIndex(selected)
        local base,gold,diamond=copies(selected)
        local event=eventMutation(selected)
        local owned=base+gold+diamond>0 or event~=nil or ownedTraits(selected)~=nil
        heading.Text,header.BackgroundColor3=Config.SpeciesDisplayNames[selected],rarityColors[index]
        local stage=box(body,0,0,380,360,rarityColors[index],24)
        hero(stage,selected,0,20,380,280,bestMutation(selected))
        label(stage,rarityNames[index].." • "..FusionSelection.pct(100*(oddsWeight[selected] or 0)/oddsTotal).." of eggs",0,302,380,42,28)
        label(body,"YOUR COLLECTION",414,0,400,42,28)
        label(body,string.format("Base: %d • Gold: %d\nDiamond: %d",base,gold,diamond),414,62,400,92,25)
        label(body,if event then event.name.." • "..table.concat(UIFormat.boostLines(event.growth,event.speed,1)," • ") else "Cosmetic fusion: 6 Base → Gold; 3 Gold → Emerald; 2 Emerald → Diamond. Highest owned variant equips.",414,173,400,76,22,C.gold)
        local equipped=str("EquippedSpeciesId","compy")==selected
        button(body,if equipped then "EQUIPPED" elseif not owned then "LOCKED" else "EQUIP",426,273,372,52,if owned then C.accent else C.card,function()
            if not owned then notify("Hatch reward eggs to discover this dino") return end
            if not equipped then notify("Equipping...",C.blue) equip:FireServer(selected,Http:GenerateGUID(false)) end
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
        hero(body,selected,14,0,360,260,fusionTarget,true)
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
        local patternHeight=math.min(60,math.max(47,45/viewportScale()))
        if fusionMenuOk then button(body,"PATTERN FUSION: 15 -> NEW GOLD",400,402-patternHeight,400,patternHeight,C.purple,function() close() FusionMenu.open() end).TextSize=20 end
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
        -- Owner 2026-10-15: ONE Eggs screen = five nest slots + a single Next egg card (src/client/EggsScreen.luau).
        heading.Text,header.BackgroundColor3="Eggs",C.gold
        local nestOk,nestList=pcall(function() return Http:JSONDecode(str("NestsJson","[]")) end)
        if not nestOk or typeof(nestList)~="table" then nestList={} end
        local version=modalVersion
        refreshEggs=EggsScreen.render({
            body=body,C=C,label=label,box=box,button=button,art=art,queue=queue,str=str,num=num,nestList=nestList,
            rarityNames=rarityNames,rarityColors=rarityColors,scale=viewportScale,notify=notify,
            openNest=function(id) Sfx.play("shop_buy") claimNestRemote:FireServer(id) end,
            openEgg=function()
                if hatchPending then return end
                autoHatching=true
                -- BD-170: the egg starts opening this very frame; the server answer is handed to the screen when it arrives.
                if (hatchState.next :: any)() then open("hatch") end
            end,
            openSettings=function() open("settings") end,
            autoOpenText=autoOpenText,
        })
        task.spawn(function() -- live countdowns; stops when the screen is left
            while modalVersion==version and active=="eggs" do
                task.wait(1)
                if modalVersion==version and active=="eggs" and refreshEggs then refreshEggs() end
            end
        end)
    elseif name=="hatch" then
        -- BD-170/171: the plain, colourless egg is on screen and wobbling the moment this opens (no dino, no cube, no pattern).
        -- The server answer is handed to the running sequence through pendingHatch.supply() when it arrives.
        heading.Text,header.BackgroundColor3="An egg is hatching...",C.gold
        local version=modalVersion
        local eggView,animateEgg,splitEgg,paint=HatchPresentation.add(body,nil,rarityColors[1])
        eggView.Size=UDim2.fromOffset(304,260) -- HatchSequence centres and animates it
        local rewardLabel=label(body,"",80,236,660,54,38,C.gold)
        local oddsLabel=label(body,"",80,288,660,28,22,C.text)
        local detailLabel=label(body,"",80,316,660,28,20,C.gold)
        local remainingAfter,failedEgg=0,false
        local handle: any=nil
        local function supply()
            if modalVersion~=version or active~="hatch" or not handle or not handle.pending() then return end
            local reward=str("LastChestRewardText","New dinosaur")
            local failed=player:GetAttribute("LastChestFailed")==true
            failedEgg=failed
            local genesOk,genes=pcall(function() return Http:JSONDecode(str("LastChestGenesJson","null")) end)
            if not genesOk or typeof(genes)~="table" then genes=nil end
            local geneticsOk=genes~=nil and EggGenetics.valid(genes)
            local id=string.match(reward,"x (%w+)") or "compy"
            if not Config.SpeciesDisplayNames[id] then id="compy" end
            -- The dinosaur view only exists from here on and stays transparent until the burst. BD-174: PreviewTraits draws
            -- colours and pattern only, never the egg condition.
            local view=Preview.add(body,id,"base")
            view.Position,view.Size=UDim2.fromOffset(160,-12),UDim2.fromOffset(504,260)
            PreviewTraits.add(view,{big=player:GetAttribute("LastChestBig"),shiny=player:GetAttribute("LastChestShiny"),genes=genes})
            view.Visible=false
            task.spawn(function() pcall(function() game:GetService("ContentProvider"):PreloadAsync(view:GetDescendants()) end) end)
            local rarity=speciesIndex(id)
            local count=tonumber(string.match(reward,"^(%d+)x")) or 1
            local displayName=Config.SpeciesDisplayNames[id] or id
            rewardLabel.Text=if failed then HatchTimeline.FailTitle elseif count>1 then count.."x "..displayName else displayName
            rewardLabel.TextColor3=if failed then C.gold else rarityColors[rarity]
            oddsLabel.Text=if failed then HatchTimeline.FailSub else HatchTimeline.oddsLine(rarityNames[rarity],HatchTimeline.speciesPct(Config.ChestSpeciesWeights,id),(FusionSelection :: any).pct or HatchTimeline.pct)
            local mutation=ProgressionRules.item(ProgressionConfig.EventMutations,str("LastChestEventMutation"))
            local detailText,detailColor="",C.gold
            local mutationColor=if mutation then Color3.fromRGB(mutation.color[1],mutation.color[2],mutation.color[3]) else nil
            -- BD-171: the paint buckets name the colour and the pattern with their rarity tiers.
            local colorReveal=if geneticsOk then HatchTimeline.colorReveal(ProgressionConfig.EggColors,genes) else nil
            local patternReveal=if geneticsOk then HatchTimeline.patternReveal(EggGenetics.Patterns,genes.patternId,FusionSelection.patternName) else nil
            local paintColors={rarityColors[rarity],rarityColors[rarity]}
            if geneticsOk then
                local tint=EggGenetics.tint(genes)
                local second=EggGenetics.color(genes.secondaryColorId)
                paintColors={tint,if genes.secondaryColorId~=genes.primaryColorId and second then Color3.fromRGB(second.rgb[1],second.rgb[2],second.rgb[3]) else tint:Lerp(Color3.new(0,0,0),.35)}
            end
            if failed then
                -- A cracked egg that does not hatch: the egg's own condition is the story (this is the EGG, not a dinosaur).
                detailText=HatchTimeline.failChance((EggGenetics.condition("cracked") :: any).hatchChance)
            elseif mutation then
                -- Event mutation: name and perk, tint the dinosaur. BD-174: the egg condition is never shown on the dinosaur.
                local tint=mutationColor :: Color3
                for _,part in view:GetDescendants() do if part:IsA("BasePart") then part.Color=part.Color:Lerp(tint,if genes then .35 else .55) end end
                detailText=mutation.name.." • "..table.concat(UIFormat.boostLines(mutation.growth,mutation.speed,1)," • ")
                if not genes then detailColor=tint end
            elseif colorReveal and patternReveal then
                detailText=colorReveal.name.." • "..patternReveal.name
            end
            detailLabel.Text,detailLabel.TextColor3=detailText,detailColor
            remainingAfter=HatchTimeline.remaining(str("NextChestId")~="" and workspace:GetServerTimeNow()>=num("NextChestReadyAt"),num("ActiveChestCount"),num("QueuedEggsWaiting"))
            paint.setRarityColor(rarityColors[rarity])
            handle.supply({
                dino=view,rarity=rarity,color=rarityColors[rarity],failed=failed,
                shiny=not failed and player:GetAttribute("LastChestShiny")==true,big=not failed and player:GetAttribute("LastChestBig")==true,
                mutationName=if mutation and not failed then mutation.name else nil,mutationColor=mutationColor,
                remaining=remainingAfter,genes=if geneticsOk then genes else nil,colorReveal=colorReveal,patternReveal=patternReveal,paintColors=paintColors,
            })
        end
        Sfx.play("hatch_crack")
        handle=HatchSequence.play({
            gui=gui,panel=panel,body=body,eggView=eggView,animateEgg=animateEgg,splitEgg=splitEgg,paint=paint,
            nameLabel=rewardLabel,oddsLabel=oddsLabel,detailLabel=detailLabel,motion=motion,
            alive=function() return modalVersion==version and active=="hatch" end,
            flash=flash,
            onSkipAll=function() autoHatching=true skipAllReveals=true end,
            onReveal=function() if modalVersion==version then heading.Text=if failedEgg then "Oops! Splat!" else "You hatched a dinosaur!" end end,
            onNext=function()
                -- BD-170: Next egg stays inside the opening sequence; only the end of the batch returns to the Eggs screen.
                heading.Text="An egg is hatching..."
                if EggsLogic.afterReveal(skipAllReveals,remainingAfter)=="continue" then
                    autoHatching=true
                    if (hatchState.next :: any)() then open("hatch") end
                else
                    finishBatch()
                end
            end,
        })
        hatchState.pending={version=version,supply=supply,handle=handle}
        if hatchState.fresh then hatchState.fresh=false supply() end
    elseif name=="exit" then
        -- BD-052: one confirmation, no stay-still channel; the server settles through tryEnd.
        heading.Text,header.BackgroundColor3="Return to Sanctuary?",C.red
        art(body,"home",36,28,214)
        label(body,"Your current run will end and rewards will be banked.",300,8,500,100,28,C.gold)
        local character=player.Character
        local catches=if character then character:GetAttribute("CatchScore") or 0 else 0
        local growth=if character then character:GetAttribute("GrowthScore") or 0 else 0
        label(body,string.format("Banking %d catches  •  %d growth",catches,math.floor(growth)),300,116,500,60,22)
        local buttonHeight=if touchMode() then math.max(68,46/viewportScale()) else 68
        button(body,"RETURN",300,396-buttonHeight,244,buttonHeight,C.accent,function()
            local current=player.Character
            close()
            if current and current:GetAttribute("RunState")=="Active" then endRun:FireServer() notify("Returning to Sanctuary...",C.gold) end
        end)
        button(body,"CANCEL",556,396-buttonHeight,244,buttonHeight,C.blue,close)
    elseif name=="crystalReveal" then
        heading.Text,header.BackgroundColor3="Run Crystal Box",C.gold
        local version=modalVersion
        art(body,"amber",262,8,300)
        local amount=label(body,"Opening...",70,282,684,65,38,C.gold)
        task.delay(1.2,function()
            if modalVersion~=version or not amount.Parent then return end
            amount.Text="+"..num("LastRunCrystalBox").." Crystals"
            local rewardScale=Instance.new("UIScale")
            rewardScale.Scale,rewardScale.Parent=if motion then .92 else 1,amount
            Theme.animate(rewardScale,.22,{Scale=1},Enum.EasingStyle.Back)
            celebrate()
        end)
        label(body,"Run total: +"..num("LastRunCrystals").." Crystals • already banked",70,353,684,40,22)
    elseif name=="results" then
        heading.Text,header.BackgroundColor3="Run Complete!",C.gold
        art(body,"trophy",24,42,240)
        label(body,"Growth  "..math.floor(num("LastRunGrowthScore")),300,18,500,60,34,C.accent)
        label(body,"Catches  "..num("LastRunCatchScore"),300,93,500,60,34,C.blue)
        label(body,str("LastRewardText","Saving rewards..."),290,168,510,100,24,C.gold)
        label(body,"+"..num("LastRunCrystals").." Crystals • Level "..num("AccountLevel"),30,302,760,40,21)
        local hasEggs=str("NextChestId")~="" or num("QueuedEggsWaiting")>0 or #decoded("NestsJson","[]")>0
        button(body,"BACK TO SANCTUARY",if hasEggs then 30 else 212,348,if hasEggs then 370 else 400,48,C.accent,function() open("home") end)
        if hasEggs then button(body,"OPEN EGGS",424,348,370,48,C.gold,function() open("eggs") end) end
    elseif name=="batchSummary" then
        heading.Text,header.BackgroundColor3="Auto-opened eggs",C.gold
        local summary=RevealSkip.summarize(skippedEntries)
        local lines=EggsLogic.summaryLines(summary)
        label(body,table.concat(lines,"\n"),24,16,760,90,24)
        local notes={}
        for _,entry in summary.notable do table.insert(notes,Config.SpeciesDisplayNames[entry.speciesId] or entry.speciesId) end
        label(body,if #notes>0 then "Notable finds: "..table.concat(notes,", ") else "All saved in your collection!",24,120,760,120,22,C.gold)
        button(body,"COLLECTION",24,300,370,64,C.blue,function() skippedEntries={} open("collection") end)
        button(body,"DONE",424,300,370,64,C.accent,function() skippedEntries={} open("eggs") end)
    elseif name=="settings" then
        heading.Text,header.BackgroundColor3="Settings",C.purple
        label(body,"Visual effects",24,24,410,56,30)
        button(body,if motion then "ON" else "OFF",560,24,230,56,if motion then C.accent else C.card,function() motion=not motion Theme.MotionEnabled=motion open("settings") end)
        label(body,"Camera distance",24,114,410,56,30)
        button(body,"RESET CAMERA",470,114,320,56,C.blue,function() player.CameraMaxZoomDistance=Config.CameraMaxZoom notify("Camera reset",C.blue) end)
        label(body,"Hatch sounds",24,182,410,44,26)
        button(body,if Theme.HatchSoundEnabled~=false then "SOUND ON" else "SOUND OFF",560,182,230,44,C.blue,function() Theme.HatchSoundEnabled=Theme.HatchSoundEnabled==false open("settings") end).TextSize=20
        button(body,"HOW TO PLAY",24,238,370,64,C.gold,function() open("tutorial") end)
        label(body,"Auto-open:",24,312,160,52,24)
        local locked=EggsLogic.locked(Config.AutoOpenRequiresPass,ownsAutoOpen())
        local chosen=RevealSkip.set(autoOpenSelection())
        for i,rarityName in RevealSkip.Names do
            -- Five rarities: name on top, state below; rarity colour while shown, dark while skipped.
            button(body,rarityName.."\n"..(if locked then "LOCKED" elseif chosen[i] then "AUTO" else "SHOW"),190+(i-1)*126,312,120,52,if chosen[i] then C.card else rarityColors[i],function()
                if locked then notify("Auto-open needs a pass",C.gold) return end
                setSkipRemote:FireServer(RevealSkip.toggle(decoded("RevealSkipJson","[]"),i))
            end).TextSize=16
        end
        button(body,"FOOD GUIDE",424,238,366,64,C.accent,function() open("food") end)
        label(body,"Shiny, BIG and special eggs always show. Auto-opened eggs are still saved!",24,370,766,30,18)
    elseif name=="food" then
        heading.Text,header.BackgroundColor3="Food & Growth",C.accent
        local types={{"Berries","leaf",1,C.accent},{"Fruit","leaf",4,C.gold},{"Eggs","egg",15,C.blue},{"Crystals","amber",50,C.purple}}
        for i,food in types do
            local card=box(body,(i-1)*208,0,196,286,food[4],24)
            art(card,food[2],28,30,140)
            label(card,food[1],0,180,196,42,26)
            label(card,"+"..food[3].." Growth",0,226,196,42,26)
        end
        label(body,string.format("Eat 500 food to earn %d eggs. Some weather gives more!",math.floor(500*Config.FoodCatchRate+.5)),18,316,788,72,23)
    elseif name=="tutorial" then
        heading.Text,header.BackgroundColor3="Welcome to Be Dino!",C.blue
        local steps={{"1","EAT & GROW","Find small food clusters across the island."},{"2","JUMP & EXPLORE","Space to jump, E to leap. Buttons on mobile."},{"3","BANK & HATCH","Return to sanctuary to bank catches and eggs."}}
        for i,step in steps do
            local card=box(body,(i-1)*276,0,264,278,C.card,24)
            local stepColor=({C.accent,C.blue,C.gold})[i]
            label(card,step[1],12,12,240,80,64,stepColor)
            label(card,step[2],10,110,244,46,25,stepColor)
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
rail=box(gui,14,0,186,382,C.panel,2)
rail.AnchorPoint,rail.Position=Vector2.new(0,.5),UDim2.new(0,14,.5,0)
local railScale=Instance.new("UIScale") railScale.Parent=rail
local navigationButtons = {}
for i,entry in {{"DINOS","dinos","collection",C.blue},{"EGGS","egg","eggs",C.gold},{"FUSION","fusion","fusion",C.purple},{"AURAS","aura","auras",C.purple},{"POTIONS","potion","potions",C.accent},{"SETTINGS","shield","settings",C.card}} do
    local b=button(rail,entry[1],7,7+(i-1)*62,172,54,entry[4],function() if entry[3]=="fusion" then openFusion() else open(entry[3]) end end)
    b.TextSize=20
    art(b,NavigationArtwork[entry[3]] or entry[2],5,6,40)
    b.Text=""
    label(b,entry[1],52,0,114,54,19)
    table.insert(navigationButtons,b)
    b:SetAttribute("Destination",entry[3])
    local marker=Instance.new("Frame")
    marker.Name,marker.Size,marker.Position="ActiveTab",UDim2.new(0,4,1,-12),UDim2.fromOffset(2,6)
    marker.BackgroundColor3,marker.BorderSizePixel,marker.Visible,marker.ZIndex,marker.Parent=C.gold,0,false,b.ZIndex+3,b
end
updateNavigation=function()
    local destination=if active=="detail" then "collection" elseif active=="hatch" then "eggs" else active
    for _,b in navigationButtons do
        local marker=b:FindFirstChild("ActiveTab") :: Frame
        marker.Visible=b:GetAttribute("Destination")==destination
    end
end
updateNavigation()
local hud=box(gui,0,0,390,94,C.panel,2)
hud.AnchorPoint,hud.Position=Vector2.new(0,1),UDim2.new(0,18,1,-18)
local hudScale=Instance.new("UIScale") hudScale.Parent=hud
do -- clean "growth" icon: three rising bars on a green tile (native vector, no asset ids)
    local tile=box(hud,8,12,64,64,C.accent,hud.ZIndex+1)
    tile.Name="GrowthIcon"
    for i=1,3 do
        local bar=Instance.new("Frame")
        bar.Name,bar.BorderSizePixel,bar.BackgroundColor3,bar.ZIndex="GrowthBar"..i,0,Color3.fromRGB(255,255,255),tile.ZIndex+1
        bar.AnchorPoint,bar.Position,bar.Size=Vector2.new(0,1),UDim2.fromOffset(10+(i-1)*17,54),UDim2.fromOffset(12,10+i*11)
        local corner=Instance.new("UICorner") corner.CornerRadius=UDim.new(0,3) corner.Parent=bar
        bar.Parent=tile
    end
end
local growthLabel=label(hud,"0 GROWTH",82,3,290,42,30,C.accent)
art(hud,"catches",40,48,32)
local catchLabel=label(hud,"0 catches  •  Sanctuary",82,47,290,34,20)
local crystalHUD=box(gui,0,0,260,48,C.panel,2)
local crystalScale=Instance.new("UIScale") crystalScale.Parent=crystalHUD
crystalHUD.AnchorPoint,crystalHUD.Position=Vector2.new(1,0),UDim2.new(1,-20,0,8)
art(crystalHUD,"amber",6,4,40)
local crystalText=label(crystalHUD,"0 Crystals",50,0,203,48,24,C.gold)
local crystalValue=Instance.new("NumberValue")
crystalValue.Value=num("Crystals")
crystalText.Text=math.round(crystalValue.Value).." Crystals"
crystalValue.Parent=crystalHUD
local crystalInitialized=false
local lastCrystalAmount=num("Crystals")
crystalValue.Changed:Connect(function(value) crystalText.Text=math.round(value).." Crystals" end)
local function refreshCrystals()
    local amount=num("Crystals")
    local delta=amount-lastCrystalAmount
    lastCrystalAmount=amount
    Theme.animate(crystalValue,.28,{Value=amount})
    if crystalInitialized and delta>0 then
        notify("+"..math.round(delta).." Crystals",C.gold,{key="crystals",icon="amber",amount=math.round(delta),format="+%d Crystals"})
    end
    crystalInitialized=true
end
player:GetAttributeChangedSignal("Crystals"):Connect(refreshCrystals)
refreshCrystals()
-- Polish: persistent "next goal" line under the crystal HUD (top-right, clear of the thumbstick/jump area).
local goalHUD=box(gui,0,0,260,30,C.panel,2)
local goalScale=Instance.new("UIScale") goalScale.Parent=goalHUD
goalHUD.Name,goalHUD.BackgroundTransparency="NextGoal",.15
local goalText=label(goalHUD,"",8,0,244,30,17,C.gold)
goalText.TextScaled=true
local goalLimit=Instance.new("UITextSizeConstraint") goalLimit.MaxTextSize=17 goalLimit.Parent=goalText
local goalDinos=nil -- latest FusionAction list; nil = unavailable (falls back to level XP)
local function refreshGoal()
    local goal=NextGoal.pick({dinos=goalDinos,level=num("AccountLevel"),xp=num("AccountXP"),perLevel=ProgressionConfig.AccountXPPerLevel,
        maxLevel=ProgressionConfig.AccountMaxLevel,stages=FusionSelection.Stages,
        speciesName=function(id) return Config.SpeciesDisplayNames[id] or id end,patternName=FusionSelection.patternName})
    goalText.Text,goalText.TextColor3="Goal  "..goal.text,if goal.ready then C.accent else C.gold
end
local goalQueued=false
local function loadGoalDinos()
    if goalQueued then return end
    goalQueued=true
    task.delay(2,function() -- debounce bursts of hatches; one request, up to 5 pages, never blocks the UI
        goalQueued=false
        local folder=ReplicatedStorage:FindFirstChild("BeDinoRemotes")
        local fn=folder and folder:FindFirstChild("FusionAction")
        if not fn or not fn:IsA("RemoteFunction") then goalDinos=nil refreshGoal() return end
        local all,cursor,pages={},nil,0
        repeat
            local ok,response=pcall(function() return (fn :: RemoteFunction):InvokeServer({action="list",cursor=cursor,limit=200}) end)
            if not ok or typeof(response)~="table" or response.ok~=true or typeof(response.dinosaurs)~="table" then goalDinos=nil refreshGoal() return end
            for _,d in response.dinosaurs do table.insert(all,d) end
            cursor=response.nextCursor
            pages+=1
        until cursor==nil or pages>=5
        goalDinos=all
        refreshGoal()
    end)
end
for _,attribute in {"CollectionJson","AccountLevel","AccountXP"} do
    player:GetAttributeChangedSignal(attribute):Connect(function() refreshGoal() if attribute=="CollectionJson" then loadGoalDinos() end end)
end
refreshGoal()
loadGoalDinos()
local timers=Instance.new("Frame")
timers.BackgroundTransparency,timers.Size,timers.AnchorPoint,timers.Position,timers.Parent=1,UDim2.fromOffset(286,220),Vector2.new(1,1),UDim2.new(1,-20,1,-100),gui
local timerScale=Instance.new("UIScale") timerScale.Parent=timers
-- Movement feel: the leap impulse is applied locally the instant the key/button is pressed
-- (same numbers as LeapService) so there is no round-trip wait; the server still validates,
-- owns the cooldown and re-applies the impulse. PROVISIONAL.
local predictedLeap:{ready:number,at:number,character:Model}?=nil
-- Humanoid air control would damp the launch speed within ~0.4 s (measured 18 of ~50 intended studs), so the client holds the
-- launch heading until the leap ends. Dropped if the server does not confirm the leap ("leaping") within half a second.
local function leapSpeed():number -- owner "Feel" tuning multiplier (runtime only), mirrored from the server
    local scale=workspace:GetAttribute("Admin_leapSpeed")
    return ProgressionConfig.LeapHorizontalSpeed*(if typeof(scale)=="number" then math.clamp(scale,.5,1.5) else 1)
end
local leapHold:{forward:Vector3,at:number,untilAt:number,character:Model,root:BasePart}?=nil
game:GetService("RunService").Heartbeat:Connect(function()
    local hold=leapHold
    if not hold then return end
    local now=os.clock()
    if now>=hold.untilAt or player.Character~=hold.character or not hold.root.Parent
        or (now-hold.at>.5 and player:GetAttribute("LastLeapStatus")~="leaping") then
        leapHold=nil return
    end
    local velocity=hold.root.AssemblyLinearVelocity
    hold.root.AssemblyLinearVelocity=Vector3.new(hold.forward.X*leapSpeed(),velocity.Y,hold.forward.Z*leapSpeed())
end)
local function requestLeap()
    leapRemote:FireServer()
    local c=player.Character
    local h=if c then c:FindFirstChildOfClass("Humanoid") else nil
    local root=if c then c:FindFirstChild("HumanoidRootPart") else nil
    if not (c and h and root and root:IsA("BasePart")) or h.Health<=0 or h.FloorMaterial==Enum.Material.Air
        or c:GetAttribute("RunState")~="Active" or workspace:GetServerTimeNow()<num("LeapReadyAt") then return end
    local look=root.CFrame.LookVector
    local forward=Vector3.new(look.X,0,look.Z)
    if forward.Magnitude<.01 then return end
    -- The leap is client-owned: this client launches and simulates the dino itself; the server only validates (LeapService).
    h:ChangeState(Enum.HumanoidStateType.Jumping)
    root.AssemblyLinearVelocity=forward.Unit*leapSpeed()+Vector3.new(0,ProgressionConfig.LeapVerticalSpeed,0)
    leapHold={forward=forward.Unit,at=os.clock(),untilAt=os.clock()+ProgressionConfig.LeapDuration,character=c,root=root}
    -- Client-local attribute: DinoMotion starts wind-up + leap pose now instead of on the replicated cooldown.
    c:SetAttribute("LeapPredictAt",os.clock())
    predictedLeap={ready=num("LeapReadyAt"),at=os.clock(),character=c}
end
local leapButton=button(timers,"LEAP [E]",0,0,286,60,C.blue,function()
    if shade.Visible then return end
    requestLeap()
end)
leapButton.Text=""
art(leapButton,"leap",4,5,48)
local leapText=label(leapButton,"LEAP [E]",56,0,225,60,22)
local weatherTile=box(timers,0,72,286,62,C.panel,2)
local weatherArt=Theme.icon(weatherTile,"weather")
if weatherArt then weatherArt.Position,weatherArt.Size=UDim2.fromOffset(4,7),UDim2.fromOffset(48,48) end
local weatherText=label(weatherTile,"Weather in 10:00",56,0,226,62,20)
local buffsText=label(timers,"",0,145,286,68,16,C.gold)
local function timerText(seconds) return UIFormat.duration(seconds) end
local lastWeather=""
local function refreshProgressionHUD()
    local now=workspace:GetServerTimeNow()
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
        if id~="clear" then
            notify((workspace:GetAttribute("WeatherName") or id).." started!",C.blue,{key="weather",icon=if event then event.icon or id else "weather",body="Special eggs can drop!"})
            Sfx.play("weather_start")
        end
    end
    weatherText.Text=if id=="clear" then "Weather in "..timerText((workspace:GetAttribute("NextWeatherAt") or now)-now) else (workspace:GetAttribute("WeatherName") or id).." "..timerText((workspace:GetAttribute("WeatherEndsAt") or now)-now)
    local p=progression() local lines={}
    for kind,buff in p.buffs do
        if buff.expiresAt>now then table.insert(lines,string.upper(string.sub(kind,1,1))..string.sub(kind,2).." potion "..timerText(buff.expiresAt-now)) end
    end
    table.sort(lines)
    local boosts=UIFormat.boostLines(num("GrowthMultiplier"),num("SpeedMultiplier"),num("LootMultiplier"))
    if #boosts>0 then table.insert(lines,table.concat(boosts," • ")) end
    buffsText.Text=table.concat(lines,"\n")
    if pendingShop and os.clock()-pendingShop.started>8 then
        -- Retry the same operation token so a delayed result cannot charge twice.
        pendingShop.started=os.clock()
        shopAction:FireServer(pendingShop.action,pendingShop.id,pendingShop.token,pendingShop.replace)
    end
end
-- BD-052: the single Home control (bottom-centre). In Sanctuary it starts a run instead.
local action=button(gui,"EXPLORE",0,0,244,60,C.accent,function()
    local character=player.Character
    if character and character:GetAttribute("RunState")=="Active" then open("exit")
    elseif character and character:GetAttribute("RunState")=="Sanctuary" then startRun:FireServer() close() end
end)
action.Name="HomeButton"
action.TextScaled=true
local actionTextLimit=Instance.new("UITextSizeConstraint") actionTextLimit.MaxTextSize=23 actionTextLimit.Parent=action
local actionPadding=Instance.new("UIPadding") actionPadding.Parent=action
local actionIcon=Theme.icon(action,"home")
-- UIPadding (52 px while the icon shows) also shifts children, so -44 lands the icon at x=8.
if actionIcon then actionIcon.Position,actionIcon.Size,actionIcon.Visible=UDim2.fromOffset(-44,8),UDim2.fromOffset(44,44),false end
local actionScale=action:FindFirstChildOfClass("UIScale") :: UIScale
-- BD-054: measured Roblox touch controls, in this ScreenGui's pixel space.
local function coreTouchRect(name: string)
    local playerGui=player:FindFirstChildOfClass("PlayerGui")
    local touchGui=if playerGui then playerGui:FindFirstChild("TouchGui") else nil
    local object=if touchGui then touchGui:FindFirstChild(name,true) else nil
    if not object or not object:IsA("GuiObject") or object.AbsoluteSize.X<=0 or object.AbsoluteSize.Y<=0 then return nil end
    local origin=gui.AbsolutePosition
    return {x=object.AbsolutePosition.X-origin.X,y=object.AbsolutePosition.Y-origin.Y,w=object.AbsoluteSize.X,h=object.AbsoluteSize.Y}
end
local function scales()
    scale.Scale=viewportScale()
    closeButton.Size=UDim2.fromOffset(math.max(80,46/viewportScale()),math.max(62,46/viewportScale()))
    local size=gui.AbsoluteSize
    if size.X<=0 or size.Y<=0 then return end
    local touch=touchMode()
    local layout=TouchLayout.compute({width=size.X,height=size.Y,touch=touch,navCount=#navigationButtons,
        thumb=if touch then coreTouchRect("DynamicThumbstickFrame") or coreTouchRect("ThumbstickFrame") else nil,
        jump=if touch then coreTouchRect("JumpButton") else nil})
    local function place(object: GuiObject,uiScale: UIScale,entry)
        object.AnchorPoint,object.Position,object.Size=Vector2.zero,UDim2.fromOffset(entry.x,entry.y),UDim2.fromOffset(entry.w,entry.h)
        uiScale.Scale=entry.scale
        object:SetAttribute("UIScaleBase",entry.scale)
    end
    place(crystalHUD,crystalScale,layout.crystal)
    goalHUD.AnchorPoint,goalHUD.Size=Vector2.zero,UDim2.fromOffset(layout.crystal.w,30)
    goalHUD.Position=UDim2.fromOffset(layout.crystal.x,layout.crystal.y+layout.crystal.h*layout.crystal.scale+4)
    goalScale.Scale=layout.crystal.scale
    place(hud,hudScale,layout.hud)
    place(rail,railScale,layout.rail)
    place(timers,timerScale,layout.timers)
    place(action,actionScale,layout.action)
    local cell=layout.rail.button
    for i,b in navigationButtons do
        local cellPosition=layout.rail.positions[i]
        b.Position,b.Size=UDim2.fromOffset(cellPosition.x,cellPosition.y),UDim2.fromOffset(cell.w,cell.h)
        for _,child in b:GetChildren() do
            if child:IsA("TextLabel") then
                child.Position,child.Size,child.TextSize=UDim2.fromOffset(cell.labelX,cell.labelY),UDim2.fromOffset(cell.labelW,cell.labelH),cell.textSize
                child.TextScaled=true
                local limit=child:FindFirstChildOfClass("UITextSizeConstraint") or Instance.new("UITextSizeConstraint")
                limit.MaxTextSize,limit.Parent=cell.textSize,child
            elseif child:IsA("GuiObject") and child.Name~="ActiveTab" then
                child.Position,child.Size=UDim2.fromOffset(cell.iconX,cell.iconY),UDim2.fromOffset(cell.icon,cell.icon)
            end
        end
    end
    local t=layout.timers
    leapButton.Position=UDim2.fromOffset(0,t.leapY)
    weatherTile.Position,weatherTile.Visible=UDim2.fromOffset(0,t.weatherY),t.weatherVisible
    buffsText.Position,buffsText.Size,buffsText.Visible=UDim2.fromOffset(0,t.buffsY),UDim2.fromOffset(286,t.buffsH),t.buffsVisible
    for _,item in {{buildBadge,layout.badge},{previewNotice,layout.notice}} do
        local labelObject,entry=item[1],item[2]
        labelObject.AnchorPoint,labelObject.Position,labelObject.Size=Vector2.zero,UDim2.fromOffset(entry.x,entry.y),UDim2.fromOffset(entry.w,entry.h)
        labelObject.TextSize,labelObject.TextXAlignment=entry.textSize,if touch then Enum.TextXAlignment.Left else Enum.TextXAlignment.Center
    end
    previewNotice.Text=if touch then "STUDIO PREVIEW: UNSAVED" else "STUDIO PREVIEW • progress not saved • test currency"
    foodDiagnostic.Visible=not touch and RunService:IsStudio()
    toastScale.Scale=layout.toastScale
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
-- Re-layout when Roblox creates/moves its touch controls or the preferred input changes.
local layoutQueued=false
local function queueLayout()
    if layoutQueued then return end
    layoutQueued=true
    task.defer(function() layoutQueued=false scales() end)
end
local touchControlNames={JumpButton=true,DynamicThumbstickFrame=true,ThumbstickFrame=true}
player:WaitForChild("PlayerGui").DescendantAdded:Connect(function(descendant)
    if touchControlNames[descendant.Name] and descendant:IsA("GuiObject") and descendant:FindFirstAncestor("TouchGui") then
        descendant:GetPropertyChangedSignal("AbsolutePosition"):Connect(queueLayout)
        descendant:GetPropertyChangedSignal("AbsoluteSize"):Connect(queueLayout)
        queueLayout()
    end
end)
pcall(function() Input:GetPropertyChangedSignal("PreferredInput"):Connect(queueLayout) end)
scales()
gui:SetAttribute("Ready",true)
local elapsed=0
local lastRunState=""
local lastLevel=num("AccountLevel")
player:GetAttributeChangedSignal("AccountLevel"):Connect(function()
    local level=num("AccountLevel")
    if lastLevel>0 and level>lastLevel then Sfx.play("level_up") notify("Level "..level.."!",C.gold,{kind="major",icon="trophy",key="level"}) end
    lastLevel=level
end)
-- Movement feel: camera height follows growth every frame (not the 0.15 s HUD tick), and the
-- pickup pop/sfx fire the frame GrowthScore replicates instead of waiting for the next tick.
local cameraLift=0
local smoothRootY: number?=nil
local cameraLiftY=0
RunService.RenderStepped:Connect(function(dt)
    local character=player.Character
    local humanoid=if character then character:FindFirstChildOfClass("Humanoid") else nil
    local growth=if character then character:GetAttribute("GrowthScore") or 0 else 0
    if character and growth>lastGrowth and character:GetAttribute("RunState")=="Active" then
        Sfx.play("pickup")
        pickupPop(string.format("+%.1f",growth-lastGrowth))
        if motion then
            hudScale.Scale=(hud:GetAttribute("UIScaleBase") or 1)*1.06
            Theme.animate(hudScale,.2,{Scale=hud:GetAttribute("UIScaleBase") or 1},Enum.EasingStyle.Back)
        end
    end
    lastGrowth=growth
    if not humanoid then return end
    -- Movement feel: the Humanoid turns at ~8 rad/s (180 degrees in ~0.38 s measured), which reads as heavy.
    -- Steer the facing toward the move direction at Config.TurnRate (x owner "Feel" responsiveness) instead.
    local rootPart=(character :: Model):FindFirstChild("HumanoidRootPart")
    local moveDirection=humanoid.MoveDirection
    if rootPart and rootPart:IsA("BasePart") and humanoid.Health>0 and moveDirection.Magnitude>.1 and not leapHold then
        local scale=workspace:GetAttribute("Admin_moveResponsiveness")
        local rate=Config.TurnRate*(if typeof(scale)=="number" then math.clamp(scale,.5,2) else 1)
        local look=rootPart.CFrame.LookVector
        local current=math.atan2(-look.X,-look.Z)
        local diff=(math.atan2(-moveDirection.X,-moveDirection.Z)-current+math.pi)%(2*math.pi)-math.pi
        humanoid.AutoRotate=false
        rootPart.CFrame=CFrame.new(rootPart.Position)*CFrame.Angles(0,current+math.clamp(diff,-rate*dt,rate*dt),0)
    else
        humanoid.AutoRotate=true
    end
    local target=((character :: Model):GetAttribute("VisualScale") or 1)-1
    cameraLift+=(target-cameraLift)*(1-math.exp(-dt*Config.CameraLiftSharpness))
    cameraLiftY=cameraLift*2
end)
-- BD-164: terrain bumps move the root ~1 stud per step and the camera followed it 1:1 (rattle). Low-pass only the vertical
-- follow (Config.CameraVerticalSmoothing); horizontal follow is untouched (no steering lag). Runs just before the
-- camera each frame so it uses the same root height the camera is about to read. Snaps on teleports/falls.
RunService:BindToRenderStep("BeDinoCameraSmooth",Enum.RenderPriority.Camera.Value-1,function(dt)
    local character=player.Character
    local humanoid=character and character:FindFirstChildOfClass("Humanoid")
    local rootPart=character and character:FindFirstChild("HumanoidRootPart")
    if not humanoid or not rootPart or not rootPart:IsA("BasePart") then smoothRootY=nil return end
    local y=rootPart.Position.Y
    if not smoothRootY or math.abs(y-smoothRootY)>5 then smoothRootY=y end
    smoothRootY+=(y-smoothRootY)*(1-math.exp(-dt/Config.CameraVerticalSmoothing))
    humanoid.CameraOffset=Vector3.new(0,cameraLiftY+math.clamp(smoothRootY-y,-2.5,2.5),0)
end)
-- Reconcile a predicted leap: the server raising LeapReadyAt confirms it; if it has not within 0.6 s
-- (cooldown/blocked/guard) cancel the pose and drop the extra horizontal speed.
RunService.Heartbeat:Connect(function()
    local p=predictedLeap
    if not p then return end
    if num("LeapReadyAt")>p.ready then predictedLeap=nil return end
    if os.clock()-p.at>.6 then
        predictedLeap=nil
        if p.character.Parent then
            p.character:SetAttribute("LeapRejectAt",os.clock())
            local root=p.character:FindFirstChild("HumanoidRootPart")
            if root and root:IsA("BasePart") then
                local v=root.AssemblyLinearVelocity
                root.AssemblyLinearVelocity=Vector3.new(v.X*.3,v.Y,v.Z*.3)
            end
        end
    end
end)
RunService.Heartbeat:Connect(function(dt)
    elapsed+=dt
    if elapsed<.15 then return end elapsed=0
    local character=player.Character
    local state=if character then character:GetAttribute("RunState") else "Loading"
    local growth=if character then character:GetAttribute("GrowthScore") or 0 else 0
    local catches=if character then character:GetAttribute("CatchScore") or 0 else 0
    growthLabel.Text=string.format("%d GROWTH",growth)
    catchLabel.Text=string.format("%d catches  •  %s",catches,if state=="Sanctuary" then "Safe sanctuary" else "Island")
    action.Text=if state=="Sanctuary" then "EXPLORE ISLAND" elseif state=="Active" then "HOME" else "SAVING..."
    action.BackgroundColor3=if state=="Active" then C.red else C.accent
    if actionIcon then actionIcon.Visible=state=="Active" end
    actionPadding.PaddingLeft=UDim.new(0,if actionIcon and state=="Active" then 52 else 6)
    actionPadding.PaddingRight=UDim.new(0,6)
    if active=="exit" and state~="Active" then close() end
    if character then
        player.CameraMinZoomDistance=Config.CameraMinZoom*(character:GetAttribute("VisualScale") or 1)
    end
    if state~=lastRunState then
        if lastRunState=="Sanctuary" and state=="Active" then Sfx.play("run_start") elseif lastRunState=="Active" and state=="Sanctuary" then Sfx.play("run_end") end
        lastRunState=state
    end
    local ok,tags=pcall(function() return Http:JSONDecode(if character then character:GetAttribute("RunEggEvents") or "[]" else "[]") end)
    if ok and typeof(tags)=="table" then
        if #tags>lastEggCount and state=="Active" then
            local newest=tags[#tags]
            local mutation=ProgressionRules.item(ProgressionConfig.EventMutations,newest.mutationId or "")
            -- Plain eggs show on the HUD counter; only special eggs get a card (docs/65).
            if mutation then notify(mutation.name.." egg caught!",C.gold,{kind="major",icon="egg",body="Hatch it at Home"}) end
        end
        lastEggCount=#tags
    end
    refreshProgressionHUD()
    if active=="eggs" and refreshEggs then refreshEggs() end
    if player:GetAttribute("ProfileState")=="Loaded" and state=="Sanctuary" and not seenTutorial then seenTutorial=true open("tutorial") end
end)
local refreshQueued=false
local function scheduleModalRefresh()
    if refreshQueued then return end
    refreshQueued=true
    task.defer(function()
        refreshQueued=false
        if table.find({"collection","detail","fusion","eggs","auras","potions","settings"},active) then
            body:ClearAllChildren()
            render(active)
        end
    end)
end
for _,attribute in {"EquippedSpeciesId","CollectionJson","ChestQueueJson","ProgressionJson","NestsJson","QueuedEggsWaiting","RevealSkipJson"} do
    player:GetAttributeChangedSignal(attribute):Connect(function()
        scheduleModalRefresh()
    end)
end
player:GetAttributeChangedSignal("LastClaimedChestId"):Connect(function()
    hatchPending=false
    -- Skippable eggs (selected rarities, nothing notable) are already credited: no animation.
    local species=string.match(str("LastChestRewardText"),"x (%w+)") or "compy"
    local okGenes,genes=pcall(function() return Http:JSONDecode(str("LastChestGenesJson","null")) end)
    local outcome={big=player:GetAttribute("LastChestBig"),shiny=player:GetAttribute("LastChestShiny"),eventMutationId=str("LastChestEventMutation"),
        genes=if okGenes and typeof(genes)=="table" then genes else nil,failed=player:GetAttribute("LastChestFailed")==true}
    local rarity=speciesIndex(species)
    table.insert(batchEntries,{rarity=rarity,name=Config.SpeciesDisplayNames[species] or species,failed=outcome.failed,shiny=outcome.shiny==true,big=outcome.big==true})
    if autoHatching and EggsLogic.shouldAutoOpen(decoded("RevealSkipJson","[]"),Config.AutoOpenRequiresPass,ownsAutoOpen(),rarity,outcome,skipAllReveals) then
        table.insert(skippedEntries,{rarity=rarity,speciesId=species,outcome=outcome})
        task.delay(Config.ChestClaimRequestCooldownSeconds+.15,function() (hatchState.next :: any)() end) -- stay under the server claim cooldown
        return
    end
    -- BD-170: when Open (or Next egg) already put a waiting egg on screen, hand the answer to it; otherwise open the screen with the result.
    local waiting=hatchState.pending
    if waiting and waiting.version==modalVersion and active=="hatch" and waiting.handle.pending() then
        task.defer(waiting.supply)
    else
        hatchState.fresh=true
        task.defer(function() open("hatch") end)
    end
end)
player:GetAttributeChangedSignal("LastRunEndAt"):Connect(function() if not autoHatching then open("results") end end)
player:GetAttributeChangedSignal("LastSettledRunId"):Connect(function()
    local serial=hatchCancelSerial
    task.spawn(function()
        local deadline=os.clock()+15
        repeat task.wait(.1) until serial~=hatchCancelSerial or os.clock()>deadline
            or (player.Character and player.Character:GetAttribute("RunState")=="Sanctuary")
        if serial==hatchCancelSerial and player.Character and player.Character:GetAttribute("RunState")=="Sanctuary" then
            if num("LastRunNestCount")>0 then
                local nestOk,nestList=pcall(function() return Http:JSONDecode(str("NestsJson","[]")) end)
                local waitSeconds=Config.NestIncubationSeconds
                if nestOk and typeof(nestList)=="table" then
                    waitSeconds=NestQueue.secondsUntilAllReady(nestList,math.floor(workspace:GetServerTimeNow()),Config.NestIncubationSeconds)
                end
                notify("New Egg Nest!",C.gold,{icon="egg_nest",key="nest",body="Ready in "..UIFormat.duration(math.max(3600,waitSeconds))}) -- no extra sound: it stacked with run_end (BD-166)
            end
            if num("LastRunCrystalBox")>0 then
                open("crystalReveal")
                local version=modalVersion
                task.wait(3)
                if modalVersion~=version or serial~=hatchCancelSerial then return end
            end
            open("results") -- never forced into hatching: the summary offers "Open eggs"
        end
    end)
end)
player:GetAttributeChangedSignal("LastExitStatusAt"):Connect(function()
    if str("LastExitStatus")=="predator_nearby" then notify("Too dangerous to go home!",C.red,{icon="shield",key="predator",body="A bigger dino is close"}) end
end)
player:GetAttributeChangedSignal("LastNestClaimAt"):Connect(function()
    if str("LastNestClaimStatus")~="opened" then return end
    Sfx.play("level_up")
    notify("Nest opened!",C.accent,{icon="egg_nest",body="Open your eggs when ready"})
end)
player:GetAttributeChangedSignal("LastRewardText"):Connect(function() if active=="results" then body:ClearAllChildren() render(active) end end)
for _,attribute in {"LastEquipStatus","LastMutationStatus","LastChestClaimStatus","LastNestClaimStatus","LastRunStartStatus"} do
    player:GetAttributeChangedSignal(attribute):Connect(function()
        local status=str(attribute)
        if attribute=="LastChestClaimStatus" then hatchPending=false end
        if status=="claimed" then return
        elseif attribute=="LastNestClaimStatus" then
            if status=="not_ready" or status=="nest_pending" or status=="bank_full" then notify(NotifyQueue.statusText(status),C.gold,{icon="egg_nest",key="nest_status"})
            elseif status~="opened" and status~="duplicate" and status~="" then notify(NotifyQueue.statusText(status),C.red,{key="error"}) end
        elseif status=="equipped" or status=="mutated" or status=="opened" then notify("Done!",C.accent,{key="ok"})
        elseif status~="" and status~="duplicate" then notify(NotifyQueue.statusText(status),C.red,{key="error"}) end
    end)
end
Input.InputBegan:Connect(function(input,processed)
    if processed then return end
    if (input.KeyCode==Enum.KeyCode.E or input.KeyCode==Enum.KeyCode.ButtonY) and not shade.Visible then requestLeap()
    elseif input.KeyCode==Enum.KeyCode.Escape then close()
    elseif input.KeyCode==Enum.KeyCode.C then open("collection")
    elseif input.KeyCode==Enum.KeyCode.B then open("eggs") end
end)
