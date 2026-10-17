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
local remotes = ReplicatedStorage:WaitForChild("BeDinoRemotes", 60) :: Folder -- BD-330: a timeout (no infinite-yield warning); the server makes this folder after the world
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
local ModalBlurGuard = require(Shared.ModalBlurGuard) -- BD-296: the blur only shows while a modal is really visible
local motion = true
require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("SettingsModel")).onChange(function(s) motion=not s.calm end) -- BD-266 Calm motion also quiets this file's shake and slides
local active = ""
local selected = "compy"
local seenTutorial = false
local lastGrowth = 0
local lastEggCount = 0
local PrivateState=require(script.Parent.PrivateState) -- BD-360: owner-only values arrive by remote, public ones stay attributes
local num,str=PrivateState.num,PrivateState.str -- same call shape as before; private names read the cache, public ones the attribute
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
local hatchState: {pending: {version: number, supply: () -> (), handle: any}?, fresh: boolean, next: (() -> boolean)?, serial: number} = {pending=nil, fresh=false, next=nil, serial=0}
local hatchCancelSerial = 0
local function ownedTraits(id: string)
    return EggTraits.selected(decoded("CollectionJson","{}")[id])
end
local function label(parent: Instance,text: string,x: number,y: number,w: number,h: number,size: number,color: Color3?): TextLabel
    local t = Instance.new("TextLabel")
    t.BackgroundTransparency,t.Position,t.Size = 1,UDim2.fromOffset(x,y),UDim2.fromOffset(w,h)
    t.Font,t.TextSize,t.Text,t.TextColor3 = Enum.Font.FredokaOne,size,text,color or C.text
    t.TextWrapped,t.ZIndex,t.Parent = true,if parent:IsA("GuiObject") then parent.ZIndex+1 else 1,parent
    Theme.TextStyle.apply(t) -- BD-390: one readable style (light fill + dark stroke 2..3)
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
    return icon
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
-- The modal blur belongs to a visible modal only (BD-296). Visible means: a menu is open, the scrim is shown, AND the BeDinoUI ScreenGui is
-- enabled and still in the PlayerGui. Disabling or destroying the ScreenGui while a menu was open used to leave the blur at 8 with nothing on screen.
local function modalState(): ModalBlurGuard.State
    return {active=active, shadeVisible=shade.Visible, guiEnabled=gui.Enabled, guiAttached=gui:IsDescendantOf(player) and shade:IsDescendantOf(gui)}
end
local function blurTarget(): number return ModalBlurGuard.target(modalState(),motion) end
local function clearStrayBlur()
    if ModalBlurGuard.mustClear(modalState(),blur.Size) then Theme.animate(blur,.08,{Size=0}) blur.Size=0 end -- cancels any running open tween, then snaps
end
for _,signal in {gui:GetPropertyChangedSignal("Enabled"),gui.AncestryChanged,shade:GetPropertyChangedSignal("Visible"),shade.AncestryChanged} do
    signal:Connect(clearStrayBlur)
end
gui.Destroying:Connect(function() blur.Size=0 end) -- a destroyed UI can never have a modal open
task.spawn(function() -- slow backstop for anything that slips past the change signals
    while true do
        task.wait(.5)
        clearStrayBlur()
    end
end)
local closeButton=button(header,"X",770,1,80,76,C.red,close)
closeButton.AnchorPoint,closeButton.Position=Vector2.new(1,0),UDim2.new(1,-2,0,1)
require(script.Parent.ModalCompact).attach({gui=gui,panel=panel,header=header,heading=heading,body=body,closeButton=closeButton,scale=scale}) -- BD-333: phone landscape layout, no-op on desktop
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
            slot.plate.Visible=entry.icon~=nil -- BD-304: no empty icon box
            local textX=if entry.icon then 68 else 22
            slot.title.Position,slot.detail.Position=UDim2.fromOffset(textX,if entry.body then 3 else 3),UDim2.fromOffset(textX,30)
            slot.title.Size=UDim2.fromOffset(398-textX,if entry.body then 30 else 50)
            slot.detail.Size=UDim2.fromOffset(398-textX,22)
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
    -- Slide the stack right, clear of the owner's admin panel (AdminPanel sets AdminPanelRight: px from the left edge, 0 = closed).
    local panelRight=player:GetAttribute("AdminPanelRight") or 0
    local half,halfCard=gui.AbsoluteSize.X/2,220*toastScale.Scale
    local shift=if panelRight>0 then math.clamp(panelRight+12+halfCard-half,0,math.max(0,half-halfCard)) else 0
    player:SetAttribute("MenuOpen",shade.Visible) -- BD-328: WeatherVisuals holds its big title card while a menu is open
    -- BD-304: with a menu open the toast rides the very top, clear of the menu title. BD-378: and clear of the Crystals / XP plates (WalletRect, set by scales()).
    local wallet=toastLayer:GetAttribute("WalletRect") :: Rect?
    local plates=if wallet then {x=wallet.Min.X,y=wallet.Min.Y,w=wallet.Width,h=wallet.Height} else nil
    local slide,topY=TouchLayout.toastPlacement(gui.AbsoluteSize.X,toastScale.Scale,plates,shade.Visible,shift)
    if toastLayer.Position.X.Offset~=slide or toastLayer.Position.Y.Offset~=topY then toastLayer.Position=UDim2.new(.5,slide,0,topY) end
    if NotifyQueue.update(notifyQueue,os.clock(),shade.Visible) then drawToasts() end
end
-- Existing call sites keep notify(text,color); opts adds {kind,key,icon,body,tint,amount,format}.
local function notify(text: string,color: Color3?,opts: any?)
    local o=opts or {}
    local kind=o.kind or (if color==C.red then "warning" elseif color==C.gold or color==C.accent then "good" else "info")
    NotifyQueue.push(notifyQueue,os.clock(),{text=text,body=o.body,kind=kind,key=o.key,icon=o.icon,tint=o.tint,amount=o.amount,format=o.format,live=o.live})
    pumpToasts()
end
task.spawn(function()
    while gui.Parent do pumpToasts() task.wait(.1) end
end)
local function viewportScale(): number
    local size=gui.AbsoluteSize
    return require(Shared.PhoneScale).modal(size.X,size.Y).scale -- BD-333: desktop = old (w-40)/860,(h-40)/520 rule; short canvases use the compact layout
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
    if not require(Shared.FtueP1).worldTextAllowed(shade.Visible) then return end -- BD-379: nothing floats over a menu
    popSerial+=1
    local serial=popSerial
    popLabel.Text=text
    popLabel.Visible=true
    popLabel.TextTransparency=0
    popLabel.Position=UDim2.fromScale(.5,.4)
    local popStroke=Theme.TextStyle.apply(popLabel,Color3.new(1,1,1)) -- BD-390: white fill + 3 px dark stroke; fades together
    Theme.animate(popLabel,.5,{Position=UDim2.fromScale(.5,if motion then .33 else .4),TextTransparency=1})
    Theme.animate(popStroke,.5,{Transparency=1})
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
    require(script.Parent.ModalCompact).layout()
    shade.Visible=true
    popSerial+=1 popLabel.Visible=false -- BD-379
    if not wasVisible then
        scale.Scale=viewportScale()*(if motion then .96 else 1)
        shade.BackgroundTransparency=1
        panel.Position=UDim2.fromScale(.5,.52)
    end
    Theme.animate(scale,.16,{Scale=viewportScale()})
    Theme.animate(panel,.16,{Position=UDim2.fromScale(.5,.5)})
    Theme.animate(shade,.14,{BackgroundTransparency=.42})
    Theme.animate(blur,.16,{Size=blurTarget()})
    if name=="hatch" then -- BD-519: a slide still running from the last modal must not move the hatch body; it starts from the settled home
        Theme.cancel(body)
        body.AnchorPoint,body.Position=Vector2.zero,require(script.Parent.ModalCompact).place(true,motion)
    end
    render(name)
    -- Animate the content as one layer, keeping large collections inexpensive.
    -- BD-519: not for the hatch. HatchSequence.play (inside render) already anchored the body at its centre (anchor .5, BODY_CENTER);
    -- a slide to the plain home position with that anchor drew the whole egg stage at the top-left corner for the first frames
    -- (long on the first OPEN of a session, when assets load). The hatch owns the body position itself.
    if name~="hatch" then
        body.Position=require(script.Parent.ModalCompact).place(false,motion)
        Theme.animate(body,.14,{Position=require(script.Parent.ModalCompact).place(true,motion)})
    end
    require(script.Parent.ModalCompact).reset()
end
local fusionProbe: string?=nil -- nil unknown, "ok", "disabled"
local function fusionRemote(): RemoteFunction?
    local folder=ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    local found=folder and folder:FindFirstChild("FusionAction")
    return if found and found:IsA("RemoteFunction") then found else nil
end
local function showFusionMenu()
    close()
    if rail then FusionMenu.setLeftInset(if require(Shared.PhoneScale).isCompact(gui.AbsoluteSize.Y) then 0 else rail.AbsolutePosition.X+rail.AbsoluteSize.X+10-gui.AbsolutePosition.X) end -- BD-334: the phone rail is a top bar, not a left column
    FusionMenu.open()
end
-- Nav FUSION + Dino Index footer: the new Pattern Fusion Menu when FusionAction answers.
openFusion=function()
    local fn=fusionRemote()
    local function decide()
        local target=FusionSelection.navTarget({menuLoaded=fusionMenuOk,remote=fn~=nil,probe=fusionProbe,profile=Config.ReleaseProfile})
        if target=="menu" then showFusionMenu()
        elseif target=="legacy" then open("fusion")
        else notify("Fusion is coming soon",C.gold) end
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
    HatchTimeline.batchReset(HatchTimeline.session) -- BD-444: the party is over; the next one counts from Egg 1
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
    hatchState.serial+=1
    local serial=hatchState.serial -- BD-525: this claim's own 8 s watchdog; an older one must not cancel a LATER claim still in flight
    hatch:FireServer(id,Http:GenerateGUID(false))
    task.delay(8,function()
        if hatchPending and hatchState.serial==serial then
            hatchPending=false autoHatching=false skipAllReveals=false HatchTimeline.batchReset(HatchTimeline.session)
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
        label(body,require(Shared.FtueCopy).sanctuaryTip1,330,74,474,85,22)
        label(body,require(Shared.FtueCopy).sanctuaryTip2,330,170,474,75,22,C.gold)
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
        if cosmeticTab=="conditions" and num("AccountLevel")<require(Shared.FtueP1).ConditionsTabLevel then cosmeticTab="auras" isTrail=false end -- BD-445: tab hidden until level 3
        local noCrystalsHint=require(Shared.FtueP1).noCrystalsHintShown(num("Crystals"),cosmeticTab)
        local hintInFooter=noCrystalsHint and (cosmeticTab=="auras" or cosmeticTab=="trails") -- BD-445 / BD-530: the aura and trail pages own the bottom line, so the hint takes its place instead of drawing over it
        if noCrystalsHint and not hintInFooter then label(body,require(Shared.FtueP1).NoCrystalsHint,0,362,824,34,22,C.gold) end -- BD-445
        local ShopTiles=require(script.Parent.ShopTiles) -- BD-047: tab icons, green-spotted egg, landing tiles; each shows only when its image id exists
        local shopTabs=require(Shared.FtueP1).shopTabs(num("AccountLevel"))
        if ShopTiles.landing then
            ShopTiles.build({label=label,box=box},body,{tabs=shopTabs,info=ShopTiles.info(p,ProgressionConfig.RandomEggPrice,num("Crystals")),
                onPick=function(tab) Sfx.play("ui_click") ShopTiles.landing=false cosmeticTab=tab open("auras") end})
            return
        end
        for i,tab in shopTabs do
            local tabButton=button(body,string.upper(tab),(i-1)*165,0,155,tabsHeight,if cosmeticTab==tab then C.blue else C.card,function() cosmeticTab=tab open("auras") end)
            tabButton.TextSize=20
            ShopTiles.decorateTab(tabButton,tab,tabsHeight)
        end
        if cosmeticTab=="eggs" then
            if not ShopTiles.eggProduct(body,20,cardsY+12,220) then art(body,"egg",20,cardsY+12,220) end
            label(body,"Random Egg",270,cardsY,535,40,30,C.gold)
            label(body,ProgressionConfig.RandomEggPrice.." Crystals\nBalance: "..num("Crystals").."  •  Level "..num("AccountLevel"),270,cardsY+45,535,60,22)
            button(body,"ODDS / DETAILS",270,cardsY+119,535,targetHeight,C.blue,function() oddsLevelOverride=nil outcomeState={page=1,filters={}} open("oddsSimple") end)
            local eggShort=num("Crystals")<ProgressionConfig.RandomEggPrice -- BD-531: no confirm screen with a negative balance
            button(body,if eggShort then "NEED "..ProgressionConfig.RandomEggPrice.." CRYSTALS" else "BUY EGG",270,cardsY+targetHeight+130,535,targetHeight,if eggShort then C.card else C.accent,function()
                if eggShort then notify("Need "..ProgressionConfig.RandomEggPrice.." Crystals",C.gold) return end
                open("eggPurchase")
            end)
            -- BD-391/405 (docs/115 D22): Fast travel perk, bought with crystals. PROVISIONAL price. Walking stays the default.
            if Config.FastTravelPerk and Config.CaveHub and require(Shared.FtueP1).fastTravelEntryShown(num("AccountLevel"),type(p.perks)=="table" and p.perks.fastTravel==true) then -- BD-447
                local owned=type(p.perks)=="table" and p.perks.fastTravel==true
                local perkPrice=ProgressionConfig.FastTravelPrice
                label(body,"Fast travel: zip to the shops",0,math.max(cardsY+targetHeight*2+150,336),520,34,22,C.gold)
                button(body,if owned then "YOURS" else perkPrice.." Crystals",540,math.max(cardsY+targetHeight*2+146,332),284,targetHeight,if owned then C.card else C.accent,function()
                    if not owned then transact("buyPerk","fastTravel") open("auras") end
                end).Active=not owned
            end
            return
        elseif cosmeticTab=="conditions" then
            local weights=ShopOdds.conditionPercents(p.conditionLevel or 0) -- BD-045: normalized percents
            local upgrade=ProgressionConfig.ConditionUpgrades[(p.conditionLevel or 0)+1]
            -- docs/73: plain egg per condition on a floor swatch; chance only (no stats text, no odds screen).
            label(body,require(Shared.FtueP1).ConditionsHeader,0,cardsY,824,30,20,C.gold) -- BD-372: the safe-first-eggs note, no level number
            -- BD-394: the owner's Blender stage (jungle backdrop + condition eggs) when uploaded (ConditionStageAssetIds); else the live egg tiles, bigger.
            local staged=require(script.Parent.ConditionStage).background(body,0,cardsY+62,824,144)
            for i,row in ProgressionConfig.Conditions do
                local x=(i-1)*165
                label(body,row.name,x,cardsY+32,155,28,22)
                local tile=box(body,x,cardsY+62,155,144,Color3.fromRGB(122,148,112):Lerp(C.panel,.25),24)
                if staged then tile.BackgroundTransparency=1 end
                if not (staged and require(script.Parent.ConditionStage).egg(tile,row.id)) then
                    -- BD-141: the flat official egg render + this condition's registered overlay (docs/77) fills the tile. The 3D viewport egg
                    -- could fall back to a plain cream shape, so the tile uses the deterministic image path (never a bare box).
                    local pic=require(script.Parent.EggPicture).add(tile,EggGenetics.neutral(row.id),150)
                    pic.Name,pic.AnchorPoint,pic.Position="ConditionEggPicture",Vector2.new(.5,.5),UDim2.fromScale(.5,.5)
                end
                label(body,string.format("%g%%",weights[i]),x,cardsY+210,155,34,24,C.blue)
            end
            local upgradeText,upgradeOk=require(Shared.FtueP1).upgradeButton(upgrade,num("AccountLevel"),num("Crystals")) -- BD-372: grey with the reason, never green over a lock
            local upgradeButton=button(body,upgradeText,142,cardsY+254,540,targetHeight,if upgradeOk then C.accent else C.card,function() if upgradeOk and upgrade then open("conditionConfirm") end end)
            upgradeButton.TextSize=20
            upgradeButton.Name=if upgradeOk then "UpgradeButton" else "UpgradeLocked"
            if not upgradeOk then upgradeButton.AutoButtonColor=false upgradeButton.TextTransparency=.15 end
            label(body,require(Shared.FtueP1).upgradeHint(upgrade,num("AccountLevel")),0,cardsY+254+targetHeight+4,824,30,19,C.gold)
            return
        elseif cosmeticTab=="crystals" then
            -- BD-179: one card per pack in a 3-wide grid (same card look as the potion shop). Prices load from the marketplace.
            label(body,"You have "..num("Crystals").." Crystals",0,cardsY-4,824,34,26,C.gold)
            if not Config.CrystalPacksEnabled then label(body,"Coming soon!",0,cardsY+28,824,26,19,C.accent) end
            local products={} for id,amount in Config.DeveloperProducts do table.insert(products,{id=id,amount=amount}) end
            table.sort(products,function(a,b) return a.amount<b.amount end)
            if #products==0 then label(body,"Crystal packs are not ready yet",0,cardsY+80,824,60,27)
            else
                local gridTop=cardsY+58
                local grid=Instance.new("ScrollingFrame") grid.Name="CrystalGrid"
                grid.BackgroundTransparency,grid.BorderSizePixel,grid.ScrollBarThickness,grid.ZIndex=1,0,8,body.ZIndex+1
                grid.Position,grid.Size=UDim2.fromOffset(0,gridTop),UDim2.fromOffset(824,402-gridTop)
                grid.CanvasSize=UDim2.fromOffset(0,math.ceil(#products/3)*152) grid.Parent=body
                local cards={}
                for i,product in products do
                    local x=((i-1)%3)*276 local y=math.floor((i-1)/3)*152
                    local card=box(grid,x,y,264,144,C.card:Lerp(C.purple,.25),24)
                    local iconSize=52+math.min(i,6)*4 -- art grows with pack size
                    art(card,"amber",10+(76-iconSize)/2,8+(76-iconSize)/2,iconSize)
                    label(card,tostring(product.amount),92,6,166,44,32,C.gold)
                    label(card,"Crystals",92,48,166,26,19)
                    local tag=label(card,"",92,74,166,20,15,C.accent) tag.Visible=false
                    local b=button(card,require(Shared.ShopCardState).packButton(nil),8,96,248,44,C.gold:Lerp(C.panel,.35),function() end)
                    b.TextScaled=true b.TextWrapped=false b.Active=false -- BD-430: the price always fits the button, never "..."
                    local fit=Instance.new("UITextSizeConstraint") fit.MaxTextSize,fit.MinTextSize,fit.Parent=22,14,b -- docs/114 s4.4: never under 14 px
                    cards[i]={button=b,tag=tag}
                end
                -- Each card shows its price as soon as it is known; a price that never arrives stays "Price soon".
                local ShopCardState=require(Shared.ShopCardState)
                local prices={}
                local function paint(i,product)
                    local c=cards[i]
                    if not c or not c.button.Parent then return end
                    local price=prices[i]
                    c.button.Text=ShopCardState.packButton(price)
                    if price and Config.CrystalPacksEnabled==true then
                        c.button.Active=true c.button.BackgroundColor3=C.gold:Lerp(C.panel,.1)
                        if not c.wired then c.wired=true c.button.Activated:Connect(function() Marketplace:PromptProductPurchase(player,product.id) end) end
                    end
                end
                local function tags()
                    local baseRate=if prices[1] then products[1].amount/prices[1] else nil
                    for i,product in products do
                        local price=prices[i]
                        if price and baseRate and i>1 and cards[i] then
                            local bonus=math.floor((product.amount/price/baseRate-1)*100+.5)
                            if bonus>=1 then cards[i].tag.Text="+"..bonus.."% extra" cards[i].tag.Visible=true end
                        end
                    end
                end
                for i,product in products do
                    task.spawn(function()
                        local ok,info=pcall(function() return Marketplace:GetProductInfo(product.id,Enum.InfoType.Product) end)
                        if ok and info.IsForSale~=false and typeof(info.PriceInRobux)=="number" then prices[i]=info.PriceInRobux end
                        if grid.Parent then paint(i,product) tags() end
                    end)
                end
            end
            return
        end
        -- BD-393: say whose style this is (the one equipped dino) and where to change it; the cards move down a little.
        require(script.Parent.ShopCards).forHeader({label=label,box=box},body,cardsY-2,str("EquippedSpeciesId","compy"))
        cardsY+=require(Shared.ShopForDino).HeaderHeight
        cardsHeight=if touch then 402-cardsY-targetHeight-12 else require(Shared.ShopForDino).CardsHeightDesktop
        buyY=cardsHeight-targetHeight-10
        local owned=if isTrail then p.trails else p.auras
        local equippedId=if isTrail then p.equippedTrail or "" else p.equippedAura
        for i,item in (if isTrail then ProgressionConfig.Trails else ProgressionConfig.Auras) do
            if isTrail and (i<(trailPage-1)*3+1 or i>trailPage*3) then continue end
            local slot=if isTrail then (i-1)%3 else i-1
            -- BD-142/BD-143: big live previews, rarity chip, words for speed, shared card states (src/client/ShopCards).
            local equipped,locked=equippedId==item.id,isTrail and num("AccountLevel")<item.level and not owned[item.id]
            require(script.Parent.ShopCards).build({label=label,box=box,button=button,art=art},body,{
                kind=if isTrail then "trail" else "aura",item=item,speciesId=str("EquippedSpeciesId","compy"),owned=owned[item.id]==true,equipped=equipped,level=num("AccountLevel"),
                x=slot*276,y=cardsY,height=cardsHeight,buyY=buyY,targetHeight=targetHeight,
                onPress=function()
                    if locked then notify("Requires account level "..item.level,C.gold) return end
                    if owned[item.id] then transact(if isTrail then "equipTrail" else "equipAura",if equipped then "" else item.id)
                    else chosenAura=item.id open("auraConfirm") end
                end})
        end
        local footerY=402-targetHeight
        if isTrail then
            -- BD-334: the arrow that cannot go further is dimmed and inert (page 1 "<", page 4 ">").
            button(body,"<",0,footerY,110,targetHeight,if trailPage<=1 then C.card else C.blue,function() if trailPage<=1 then return end trailPage=math.max(1,trailPage-1) open("auras") end).TextTransparency=if trailPage<=1 then .6 else 0
            button(body,">",714,footerY,110,targetHeight,if trailPage>=4 then C.card else C.blue,function() if trailPage>=4 then return end trailPage=math.min(4,trailPage+1) open("auras") end).TextTransparency=if trailPage>=4 then .6 else 0
        end
        label(body,(if hintInFooter then require(Shared.FtueP1).NoCrystalsHint else "Level "..num("AccountLevel").." • "..num("Crystals").." Crystals")..(if isTrail then " • "..trailPage.." / 4" else ""),115,footerY,590,targetHeight,21,C.gold)
    elseif name=="oddsSimple" then
        -- BD-270: short, kid-readable odds (src/shared/OddsCopy). Every group adds up to 100%.
        local OddsCopy=require(Shared.OddsCopy)
        local upgradeOdds=oddsLevelOverride~=nil
        heading.Text,header.BackgroundColor3=if upgradeOdds then "Upgrade Odds" else "Egg Odds",C.blue
        local groups=if upgradeOdds then OddsCopy.upgradeGroups(oddsLevelOverride :: number) else OddsCopy.eggGroups(progression().conditionLevel or 0)
        local list=Instance.new("ScrollingFrame") list.Name,list.BackgroundTransparency,list.BorderSizePixel,list.Size,list.ScrollBarThickness,list.ZIndex,list.Parent="OddsSimple",1,0,UDim2.fromOffset(824,308),8,24,body
        local lineY=0
        for _,group in groups do
            label(list,group.title,10,lineY,790,34,26,C.gold) lineY+=36
            for _,row in group.rows do
                label(list,row.name,30,lineY,520,30,22).TextXAlignment=Enum.TextXAlignment.Left
                label(list,row.text,560,lineY,220,30,22,C.blue).TextXAlignment=Enum.TextXAlignment.Right
                lineY+=32
            end
            if group.note then label(list,group.note,10,lineY,790,28,18) lineY+=30 end
            label(list,"Total: 100%",10,lineY,790,26,17,C.gold) lineY+=36
        end
        for _,note in OddsCopy.notes(not upgradeOdds) do label(list,note,10,lineY,790,28,19) lineY+=32 end
        list.CanvasSize=UDim2.fromOffset(0,lineY)
        button(body,"MORE DETAILS",0,322,402,math.max(64,45/viewportScale()),C.blue,function() open("eggOdds") end).TextSize=20
        button(body,"BACK",422,322,402,math.max(64,45/viewportScale()),C.blue,function() open(if upgradeOdds then "conditionConfirm" else "eggPurchase") end)
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
        local OddsCopy=require(Shared.OddsCopy)
        if isEgg or not upgrade then art(body,"egg",20,15,200)
        else -- BD-303: show the egg whose chance grows most, not a plain egg
            local tile=box(body,20,15,200,175,Color3.fromRGB(122,148,112):Lerp(C.panel,.25),24)
            local view=ModelPreview.add(tile,"egg")
            view:SetAttribute("InspectZoom",1.6)
            EggAppearance.apply(view,EggGenetics.neutral(OddsCopy.biggestGain(upgrade.level-1,upgrade.level)),true)
        end
        label(body,price.." Crystals\nBalance after: "..(num("Crystals")-price),260,10,550,80,27,C.gold)
        label(body,if isEgg then OddsCopy.hatchSentence(p.conditionLevel or 0) else OddsCopy.upgradeUnlock(if upgrade then upgrade.requiredLevel else nil,num("AccountLevel"))..(if upgrade then " Only new eggs get better chances." else ""),260,105,550,95,23)
        if not isEgg and upgrade then
            local parts={} local newOdds=ShopOdds.conditionPercents(upgrade.level) for i,row in ProgressionConfig.Conditions do table.insert(parts,row.name.." "..string.format("%g",newOdds[i]).."%") end
            label(body,table.concat(parts," • "),0,213,824,60,21,C.blue)
        end
        -- BD-270: the odds button sits before every random, crystal-costing action (egg purchase and condition upgrade).
        button(body,"ODDS / DETAILS",0,300,250,math.max(64,45/viewportScale()),C.blue,function()
            oddsLevelOverride=if isEgg then nil else (if upgrade then upgrade.level else nil)
            outcomeState={page=1,filters={}} open("oddsSimple")
        end).TextSize=20
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
            -- BD-267: shared card states (Normal / Sold out): src/shared/ShopCardState + src/client/ShopCard.
            local ShopCardState,ShopCard=require(Shared.ShopCardState),require(script.Parent.ShopCard)
            local look=ShopCardState.look({left=left,buyButton=item.price.." Crystals"},item.price.." Crystals")
            local card=box(scroller,x,y,264,132,ShopCard.cardColor(C.card:Lerp(color,.28),look),24)
            art(card,bottle(item),6,8,64)
            label(card,item.name,74,2,186,24,19,color)
            label(card,UIFormat.potion(item.kind,item.multiplier,item.duration),74,26,186,36,15)
            label(card,if left>0 then left.." left" else look.caption,74,62,186,20,15,ShopCard.captionColor(look))
            local buy=button(card,look.buttonText,8,84,248,44,color:Lerp(C.panel,.45),function() -- docs/114 s4.4: 44 px target
                if left>0 then chosenPotion=item.id open("potionConfirm") end
            end)
            ShopCard.styleButton(buy,look,color:Lerp(C.panel,.45))
            buy.TextSize=16
        end
        label(scroller,"Rarer potions appear less often. Six of twelve are offered each restock.",0,284,824,22,15,C.gold)
        label(scroller,"Your potions (tap to use)",0,310,824,24,18,C.gold)
        local slot=0
        for _,item in ProgressionConfig.Potions do
            local owned=p.potions[item.id] or 0
            if owned>0 then
                local x=(slot%3)*276 local y=338+math.floor(slot/3)*50
                slot+=1
                local useButton=button(scroller,item.name.." x"..owned.."  USE",x,y,264,44,C.purple,function()
                    chosenPotion=item.id
                    local buff=p.buffs[item.kind]
                    if buff and buff.expiresAt>workspace:GetServerTimeNow() then open("potionReplace") else transact("usePotion",item.id,false) end
                end)
                useButton.TextSize=16
                -- BD-101: the owner's potion icon beside the name (a sibling above the button, so the text keeps its own padding);
                -- no valid image id -> no icon and the button looks exactly as before.
                if require(Shared.PotionArt).icon(scroller,item.id,UDim2.fromOffset(34,34),UDim2.fromOffset(x+5,y+22),useButton.ZIndex+1) then
                    local pad=Instance.new("UIPadding") pad.PaddingLeft=UDim.new(0,40) pad.Parent=useButton
                end
            end
        end
        if slot==0 then label(scroller,"No potions yet. Buy from this restock's offers above.",0,338,824,32,18) end
        scroller.CanvasSize=UDim2.fromOffset(0,338+math.max(1,math.ceil(slot/3))*50+8)
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
        -- BD-269: at most 24 cards are built per page, so a long Index stays light on phones (pager shows only if >1 page).
        local IndexProgress=require(Shared.IndexProgress)
        local pg=IndexProgress.page(#Config.SpeciesOrder,24,IndexProgress.state.page)
        IndexProgress.state.page=pg.page
        local list=Instance.new("ScrollingFrame")
        list.Name,list.Size,list.Position="DinoCards",UDim2.fromOffset(824,326),UDim2.fromOffset(0,0)
        list.BackgroundTransparency,list.BorderSizePixel,list.ScrollBarThickness=1,0,6
        local lay=IndexProgress.cardLayout(viewportScale(),326) -- BD-332: two rows always visible (compact cards when short)
        local cardButtonHeight,cardHeight,rowHeight=lay.buttonHeight,lay.cardHeight,lay.rowHeight
        list.CanvasSize=UDim2.fromOffset(0,math.ceil((pg.last-pg.first+1)/3)*rowHeight)
        list.ZIndex,list.Parent=24,body
        for i,id in Config.SpeciesOrder do
            local base,gold,diamond=copies(id)
            local event=eventMutation(id)
            local rarity=speciesIndex(id)
            local found=base+gold+diamond>0 or event~=nil or ownedTraits(id)~=nil
            if found then unlocked+=1 end
            if i<pg.first or i>pg.last then continue end
            local look=FusionSelection.indexCard(found)
            local card=box(list,((i-pg.first)%3)*276,math.floor((i-pg.first)/3)*rowHeight,264,cardHeight,if found then rarityColors[rarity] else Color3.fromRGB(62,64,74),24)
            Theme.texture(card,264,cardHeight)
            label(card,look.nameText or Config.SpeciesDisplayNames[id],4,if lay.compact then 3 else 8,256,if lay.compact then 26 else 35,if lay.compact then 21 else 25)
            label(card,look.rarityText or (rarityNames[rarity].." • "..FusionSelection.pct(100*(oddsWeight[id] or 0)/oddsTotal).." of eggs"),4,if lay.compact then 28 else 44,256,if lay.compact then 20 else 25,if lay.compact then 15 else 18)
            if found then
                hero(card,id,7,lay.heroY,250,lay.heroHeight,bestMutation(id))
                label(card,if event then "" elseif ownedTraits(id) then (require(Shared.ColourBonus).text(ProgressionConfig.EggColors,(ownedTraits(id) :: any).genes) or "Special variant") else require(Shared.ClassInfo).Labels[require(Shared.ClassInfo).forSpecies(id).class].." • "..require(Shared.FtueP1).indexCount(base,gold,diamond),5,lay.detailY,254,if lay.compact then 22 else 25,if lay.compact then 14 else 16)
                if event then require(script.Parent.MutationBadge).chip(card,event.id,UDim2.new(0.5,0,0,lay.detailY),Vector2.new(0.5,0)) end -- BD-352: real badge, not 9 px text
                if lay.compact then
                    local tap=Instance.new("TextButton") -- the whole card opens the dino (no VIEW DINO bar when short)
                    tap.Name,tap.Text,tap.BackgroundTransparency,tap.Size,tap.ZIndex,tap.Parent="ViewDino","",1,UDim2.fromScale(1,1),card.ZIndex+8,card
                    tap.Activated:Connect(function() selected=id open("detail") end)
                else
                    button(card,"VIEW DINO",12,233,240,cardButtonHeight,C.card,function() selected=id open("detail") end)
                end
            else
                -- No button: silhouette block re-centered in the freed space. Soft edge = a faint, slightly larger
                -- copy underneath (2 viewports max, no per-frame work); skipped when motion/effects are reduced.
                local blockY=if lay.compact then lay.heroY else 70+math.floor((cardButtonHeight+12)/2)
                if motion then
                    local halo=Preview.add(card,id,"silhouette")
                    halo.Name,halo.ImageTransparency=("SilhouetteSoftEdge"),.82
                    halo.Position,halo.Size=UDim2.fromOffset(-2,blockY-9),UDim2.fromOffset(268,if lay.compact then lay.heroHeight+18 else 146)
                end
                local view=Preview.add(card,id,"silhouette")
                view.Position,view.Size=UDim2.fromOffset(7,blockY),UDim2.fromOffset(250,if lay.compact then lay.heroHeight else 128)
                label(card,look.status,5,if lay.compact then lay.detailY else blockY+134,254,if lay.compact then 22 else 25,if lay.compact then 14 else 15)
            end
        end
        -- BD-269: "Collected X of Y (P%)" bar with milestone ticks (src/shared/IndexProgress).
        local progress=IndexProgress.summary(unlocked,#Config.SpeciesOrder)
        local meterWidth=if pg.pages>1 then 420 else 600
        meter(body,0,356,meterWidth,unlocked,#Config.SpeciesOrder,C.accent,progress.text)
        if pg.pages>1 then
            button(body,"<",430,350,50,44,C.blue,function() IndexProgress.state.page=pg.page-1 open("collection") end)
            label(body,pg.page.." / "..pg.pages,482,350,60,44,20)
            button(body,">",546,350,50,44,C.blue,function() IndexProgress.state.page=pg.page+1 open("collection") end)
        end
        for _,tick in progress.ticks do
            if tick.fraction<1 then
                local mark=Instance.new("Frame") mark.Name,mark.BorderSizePixel,mark.ZIndex,mark.Parent="IndexMilestone",0,body.ZIndex+8,body
                mark.Size,mark.Position=UDim2.fromOffset(4,8),UDim2.fromOffset(math.floor(meterWidth*tick.fraction)-2,388) -- BD-300: below the bar, never over its text
                mark.BackgroundColor3=if tick.reached then C.gold else C.text
                mark.BackgroundTransparency=if tick.reached then 0 else .35
            end
        end
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
        label(body,if event then event.name.." • "..table.concat(UIFormat.boostLines(event.growth,event.speed,1)," • ") else "Cosmetic fusion: 6 Base → Gold; 3 Gold → Emerald; 2 Emerald → Diamond. Highest owned variant equips.",414,173,400,66,22,C.gold)
        do local line=label(body,require(Shared.ClassInfo).line(selected),414,241,400,28,22,require(Shared.ClassInfo).Colors[require(Shared.ClassInfo).forSpecies(selected).class]) -- BD-423: class + one-line feel hint
            line.TextScaled,line.TextWrapped=true,false -- BD-443: shrink to fit one line on a phone, never clip
            local fit=Instance.new("UITextSizeConstraint") fit.MinTextSize,fit.MaxTextSize,fit.Parent=14,22,line end
        local equipped=str("EquippedSpeciesId","compy")==selected
        button(body,if equipped then "EQUIPPED" elseif not owned then "LOCKED" else "EQUIP",426,273,372,52,if owned then C.accent else C.card,function()
            if not owned then notify("Hatch eggs to find this dino") return end
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
        button(body,"GOLD",388,0,200,44,C.gold,function() fusionTarget="gold" open("fusion") end)
        button(body,"DIAMOND",600,0,200,44,C.blue,function() fusionTarget="diamond" open("fusion") end)
        label(body,"MAKE IT "..string.upper(target),388,56,420,54,30,if diamond then C.blue else C.gold)
        label(body,"Consume "..cost.." "..source.." copies for 1 "..target.." "..Config.SpeciesDisplayNames[selected]..". Cosmetic only.",392,118,420,76,22)
        meter(body,400,214,400,owned,cost,C.gold,string.format("%d / %d %s copies",owned,cost,source))
        button(body,"FUSE SELECTED DINO",400,277,400,56,if owned>=cost then C.accent else C.card,function()
            if owned<cost then notify("You need "..cost.." "..source.." copies",C.red) return end
            open("fusionConfirm")
        end)
        button(body,"CHOOSE DINO",70,342,264,47,C.blue,function() open("collection") end)
        local patternHeight=math.min(60,math.max(47,45/viewportScale()))
        if fusionMenuOk then button(body,"PATTERN FUSION: 6 -> NEW GOLD",400,402-patternHeight,400,patternHeight,C.purple,function() close() FusionMenu.open() end).TextSize=20 end
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
            -- BD-369: the empty card is a way out, not a dead end; the cracked hint needs the dino count.
            explore=function()
                local character=player.Character
                if character and character:GetAttribute("RunState")=="Sanctuary" then startRun:FireServer() close() else close() end
            end,
            collectionCopies=function() return require(Shared.FtueRules).collectionCopies(decoded("CollectionJson","{}")) end,
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
        local remainingAfter,failedEgg,shownReason=0,false,nil
        local handle: any=nil
        local function supply()
            if modalVersion~=version or active~="hatch" or not handle or not handle.pending() then return end
            local reward=str("LastChestRewardText","New dinosaur")
            local failed=PrivateState.get("LastChestFailed")==true
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
            PreviewTraits.add(view,{big=PrivateState.get("LastChestBig"),shiny=PrivateState.get("LastChestShiny"),genes=genes,mutationId=str("LastChestEventMutation")})
            view.Visible=false
            task.spawn(function() pcall(function() game:GetService("ContentProvider"):PreloadAsync(view:GetDescendants()) end) end)
            local rarity=speciesIndex(id)
            shownReason=if failed then nil else EggsLogic.shownReason(decoded("RevealSkipJson","[]"),Config.AutoOpenRequiresPass,ownsAutoOpen(),rarity,genes)
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
            if colorReveal then colorReveal.bonusText=require(Shared.ColourBonus).text(ProgressionConfig.EggColors,genes) end -- BD-172
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
                local tint=mutationColor :: Color3 -- BD-155: the dinosaur itself is tinted by PreviewTraits (MutationLook) when the view is created
                detailText=mutation.name.." • "..table.concat(UIFormat.boostLines(mutation.growth,mutation.speed,1)," • ")
                if not genes then detailColor=tint end
            elseif colorReveal and patternReveal then
                detailText=HatchTimeline.detailLine(colorReveal,patternReveal,colorReveal.bonusText) -- BD-220: colour bonus shown once, here
            end
            detailLabel.Text,detailLabel.TextColor3=detailText,detailColor
            remainingAfter=HatchTimeline.remaining(str("NextChestId")~="" and workspace:GetServerTimeNow()>=num("NextChestReadyAt"),num("ActiveChestCount"),num("QueuedEggsWaiting"),num("BufferedRevealCount"))
            paint.setRarityColor(rarityColors[rarity])
            handle.supply({
                dino=view,speciesId=id,rarity=rarity,color=rarityColors[rarity],failed=failed,
                shiny=not failed and PrivateState.get("LastChestShiny")==true,big=not failed and PrivateState.get("LastChestBig")==true,
                mutationName=if mutation and not failed then mutation.name else nil,mutationColor=mutationColor,mutationId=if mutation and not failed then mutation.id else nil,
                newFind=not failed and next(decoded("LastChestNewJson","{}"))~=nil, -- BD-436: first colour/pattern/mutation
                remaining=remainingAfter,genes=if geneticsOk then genes else nil,colorReveal=colorReveal,patternReveal=patternReveal,paintColors=paintColors,
                secondReveal=if geneticsOk then HatchTimeline.colorReveal(ProgressionConfig.EggColors,genes,"secondary") else nil, -- BD-220: right bucket
            })
            -- BD-380: the egg counts are published a moment after the result; re-count so the hint equals the eggs really left.
            task.delay(.6,function() if modalVersion==version and active=="hatch" and handle then (handle :: any).setRemaining(HatchTimeline.remaining(str("NextChestId")~="",num("ActiveChestCount"),num("QueuedEggsWaiting"),num("BufferedRevealCount"))) end end)
        end
        Sfx.play("hatch_crack")
        handle=HatchSequence.play({
            gui=gui,panel=panel,body=body,eggView=eggView,animateEgg=animateEgg,splitEgg=splitEgg,paint=paint,
            nameLabel=rewardLabel,oddsLabel=oddsLabel,detailLabel=detailLabel,motion=motion,
            eggCondition=HatchTimeline.queueCondition(queue(),str("NextChestId")), -- BD-223: the egg's condition look from the first frame
            eggId=str("NextChestId"), -- BD-397: seeds the v2 paint splats (no-op while Config.HatchV2 is false)
            alive=function() return modalVersion==version and active=="hatch" end,
            flash=flash,
            onSkipAll=function() autoHatching=true skipAllReveals=true end,
            onReveal=function() if modalVersion==version then heading.Text=if failedEgg then "Oops! Splat!" else shownReason or "You hatched a dinosaur!" end end,
            onAgain=function() -- BD-371: after a splat with no eggs left, TRY AGAIN goes straight back to the island
                autoHatching=false skipAllReveals=false HatchTimeline.batchReset(HatchTimeline.session) emitHatchSummary() close()
                local character=player.Character
                if character and character:GetAttribute("RunState")=="Sanctuary" then startRun:FireServer() end
            end,
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
        heading.Text,header.BackgroundColor3="Go home?",C.red
        art(body,"home",36,28,214)
        label(body,require(Shared.FtueCopy).homeConfirmLine,300,8,500,100,28,C.gold)
        local character=player.Character
        local catches=if character then character:GetAttribute("CatchScore") or 0 else 0
        local growth=if character then character:GetAttribute("GrowthScore") or 0 else 0
        label(body,require(Shared.FtueCopy).homeConfirmTotals(catches,growth),300,116,500,60,22)
        local buttonHeight=if touchMode() then math.max(68,46/viewportScale()) else 68
        button(body,"GO HOME",300,396-buttonHeight,244,buttonHeight,C.accent,function()
            local current=player.Character
            close()
            if current and current:GetAttribute("RunState")=="Active" then endRun:FireServer() notify("Going home...",C.gold) end
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
        -- BD-315: a defeat is a gentle first section of THIS modal (a toast was covered by it); eggs, crystals and nests stay banked.
        local oops=if str("LastRunEndReason")=="Defeated" then 26 else 0
        heading.Text,header.BackgroundColor3=if oops>0 then "Oops! Good try!" else "Run Complete!",if oops>0 then C.blue else C.gold
        if oops>0 then label(body,"Your eggs are safe!",30,0,760,30,24,C.blue) end
        local hasEggs=str("NextChestId")~="" or num("QueuedEggsWaiting")>0 or #decoded("NestsJson","[]")>0
        require(script.Parent.RunComplete).build({body=body,C=C,label=label,box=box,art=art,button=button,num=num,oops=oops,hasEggs=hasEggs,
            back=function() open("home") end,
            openEggs=function() if not require(script.Parent.HubTravelClient).press("eggs") then open("eggs") end end})
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
        -- BD-263 Settings v2: tabs Sound / Look / Controls / Help are drawn by SettingsMenu; Help (guides, auto-open) stays here. Body is 824 x 402.
        local tab=require(script.Parent.SettingsMenu).build(body,{label=label,button=button,open=open,notify=notify,cameraReset=function() player.CameraMaxZoomDistance=Config.CameraMaxZoom end})
        if tab=="help" then
        button(body,"HOW TO PLAY",0,70,400,76,C.gold,function() open("tutorial") end).TextSize=26
        button(body,"FOOD GUIDE",424,70,400,76,C.accent,function() open("food") end).TextSize=26
        label(body,"Auto-open eggs",0,172,824,40,28).TextXAlignment=Enum.TextXAlignment.Left
        local locked=EggsLogic.locked(Config.AutoOpenRequiresPass,ownsAutoOpen())
        local chosen=RevealSkip.set(autoOpenSelection())
        for i,rarityName in RevealSkip.Names do
            -- BD-304: five big buttons, 22 px text (about 16 px on a small screen): name on top, state below.
            button(body,rarityName.."\n"..(if locked then "LOCKED" elseif chosen[i] then "AUTO" else "SHOW"),(i-1)*168,222,158,math.max(76,45/viewportScale()),if chosen[i] then C.card else rarityColors[i],function()
                if locked then notify("Auto-open needs a pass",C.gold) return end
                setSkipRemote:FireServer(RevealSkip.toggle(decoded("RevealSkipJson","[]"),i))
            end).TextSize=22
        end
        label(body,"Shiny, BIG and special eggs always show. Auto-opened eggs are still saved!",0,324,824,60,20)
        end
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
        local steps=require(Shared.FtueCopy).tutorialSteps
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
foodDiagnostic.TextXAlignment,foodDiagnostic.Visible=Enum.TextXAlignment.Left,false
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
for i,entry in {{"DINOS","dinos","collection",C.blue},{"EGGS","egg","eggs",C.gold},{"FUSION","fusion","fusion",C.purple},{"SHOP","aura","auras",C.purple},{"POTIONS","potion","potions",C.accent},{"SETTINGS","shield","settings",C.card}} do
    local b=button(rail,entry[1],7,7+(i-1)*62,172,54,entry[4],function() if require(script.Parent.HubTravelClient).press(entry[3]) then return end if entry[3]=="fusion" then openFusion() else if entry[3]=="auras" then require(script.Parent.ShopTiles).enter(require(Shared.FtueP1).shopTabs(num("AccountLevel"))) end open(entry[3]) end end)
    b.TextSize=20
    art(b,if entry[3]=="auras" then "amber" else (NavigationArtwork[entry[3]] or entry[2]),5,6,40) -- BD-046: SHOP wears the crystal icon
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
require(script.Parent.HubTravelClient).attach({gui=gui,buttons=navigationButtons,open=function(name) if name=="auras" then require(script.Parent.ShopTiles).enter(require(Shared.FtueP1).shopTabs(num("AccountLevel"))) end open(name) end,openFusion=openFusion,notify=notify,close=close}) -- BD-288: no-op while Config.CaveHub is false
require(script.Parent.FtueRail).attach(rail,navigationButtons) -- BD-368: first run: only POTIONS, SETTINGS and a MENU chip until the first egg
local hud=box(gui,0,0,390,94,C.panel,2)
hud.AnchorPoint,hud.Position=Vector2.new(0,1),UDim2.new(0,18,1,-18)
local hudScale=Instance.new("UIScale") hudScale.Parent=hud
require(script.Parent.HudV2).attach(hud,gui,{notify=notify}) -- BD-080: egg plate (bottom-left) + SIZE bar (top-centre); growth tile and catches text removed
local crystalHUD=box(gui,0,0,260,48,C.panel,2)
local crystalScale=Instance.new("UIScale") crystalScale.Parent=crystalHUD
crystalHUD.AnchorPoint,crystalHUD.Position=Vector2.new(1,0),UDim2.new(1,-20,0,8)
art(crystalHUD,"amber",6,4,40)
local crystalText=label(crystalHUD,"0 Crystals",50,0,203,48,24,C.gold)
do local crystalOpen=Instance.new("TextButton") -- BD-046: tapping the crystal count opens the same Shop as the SHOP button
    crystalOpen.Name,crystalOpen.Text,crystalOpen.BackgroundTransparency,crystalOpen.Size,crystalOpen.ZIndex,crystalOpen.Parent="OpenShop","",1,UDim2.fromScale(1,1),crystalHUD.ZIndex+5,crystalHUD
    crystalOpen.Activated:Connect(function() Sfx.play("ui_click") if require(script.Parent.HubTravelClient).press("auras") then return end require(script.Parent.ShopTiles).enter(require(Shared.FtueP1).shopTabs(num("AccountLevel"))) open("auras") end) end
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
        Sfx.playAlias("crystal_reward")
        notify("+"..math.round(delta).." Crystals",C.gold,{key="crystals",icon="amber",amount=math.round(delta),format="+%d Crystals"})
    end
    crystalInitialized=true
end
PrivateState.onChanged("Crystals", refreshCrystals)
refreshCrystals()
local goalHUD,goalScale,goalText,goalLimit=require(script.Parent.GoalHud).build({gui=gui,box=box,label=label,C=C,num=num,touchMode=touchMode,decoded=decoded,eventMutation=eventMutation,ownedTraits=ownedTraits}) -- next-goal HUD line + Goals panel
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
-- BD-247 HP combat HUD (health bars, Bite button in this row): no-op while Config.CombatEnabled is false. No new locals here (200-local limit).
require(script.Parent.CombatHud).attach({timers=timers,leapButton=leapButton,leapText=leapText,button=button,label=label,notify=notify,shade=shade})
local weatherTile=box(timers,0,72,286,62,C.panel,2)
local weatherArt=Theme.icon(weatherTile,"weather")
if weatherArt then weatherArt.Position,weatherArt.Size=UDim2.fromOffset(4,7),UDim2.fromOffset(48,48) end
local weatherText=label(weatherTile,"Weather in 10:00",56,0,226,62,20)
local buffsText=label(timers,"",0,145,286,68,16,C.gold)
require(script.Parent.PotionChips).attach(buffsText) -- BD-101: potion icons beside the active-potion timer lines
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
    require(script.Parent.PotionChips).update(p.buffs,now)
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
require(script.Parent.GoCue).attach(action,require(script.Parent.FtueRail).hasFoundEgg,function() return shade.Visible end) -- BD-442: one gentle go cue until the first run
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
    require(script.Parent.ModalCompact).layout()
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
    local goalFloor=if layout.touch then require(Shared.PhoneScale).floorText(17,layout.crystal.scale) else 17 -- BD-333: goal text renders >= 14 px, truncated instead of shrunk
    goalLimit.MaxTextSize,goalLimit.MinTextSize=goalFloor,if layout.touch then goalFloor else require(Shared.PhoneScale).MinText -- docs/114 s4.4: the desktop line wraps to two lines before it ever shrinks under 14 px
    goalText.TextScaled,goalText.TextSize=not layout.touch,goalFloor
    goalText.TextWrapped,goalText.TextTruncate=not layout.touch,if layout.touch then Enum.TextTruncate.AtEnd else Enum.TextTruncate.None
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
                child.Visible=not cell.iconOnly -- BD-333: narrow phones show the icon only
                child.TextScaled=not layout.touch -- BD-333: phones draw the label at its real >= 14 px size instead of shrinking it to fit
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
    leapText.TextSize,weatherText.TextSize,buffsText.TextSize=t.leapText,t.weatherText,t.buffsText -- BD-333: design sizes that render >= 14 px
    for _,item in {{buildBadge,layout.badge},{previewNotice,layout.notice}} do
        local labelObject,entry=item[1],item[2]
        labelObject.AnchorPoint,labelObject.Position,labelObject.Size=Vector2.zero,UDim2.fromOffset(entry.x,entry.y),UDim2.fromOffset(entry.w,entry.h)
        labelObject.TextScaled,labelObject.TextSize,labelObject.TextXAlignment=touch,entry.textSize,if touch then Enum.TextXAlignment.Left else Enum.TextXAlignment.Center
    end
    previewNotice.Text=if touch then "STUDIO PREVIEW: UNSAVED" else "STUDIO PREVIEW • progress not saved • test currency"
    foodDiagnostic.Visible,foodDiagnostic.AnchorPoint,foodDiagnostic.Position=require(Shared.HudRules).showFoodDebug(RunService:IsStudio(),player:GetAttribute("IsAdmin")==true,touch),Vector2.new(0,1),UDim2.fromOffset(layout.hud.x,(if touch then layout.hud.y else math.min(layout.hud.y,layout.feedback.y))-6) -- BD-080: debug line only for Studio/admin, parked above the egg plate (never under the toasts); BD-507: and above the Tell us! button
    require(script.Parent.HudV2).layout(layout)
    gui:SetAttribute("FeedbackRect",Rect.new(layout.feedback.x,layout.feedback.y,layout.feedback.x+layout.feedback.w,layout.feedback.y+layout.feedback.h)) -- BD-507: FeedbackClient puts its Tell us! button here, clear of the egg plate
    toastScale.Scale=layout.toastScale
    local wallet=TouchLayout.walletPlates(layout) -- BD-378: the toast stack keeps clear of the Crystals plate and the goal line under it
    toastLayer:SetAttribute("WalletRect",Rect.new(wallet.x,wallet.y,wallet.x+wallet.w,wallet.y+wallet.h))
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
    if lastLevel>0 and level>lastLevel then Sfx.playCue("level_up") notify("Level "..level.."!",C.gold,{kind="major",icon="trophy",key="level"}) end
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
    -- BD-500: the aim lift follows the dinosaur's REAL height (the measured model box, Shared/CameraFraming), not only its growth step;
    -- a Compy gets exactly the old 2 x (scale - 1). cameraLift is in studs now.
    local target=require(script.Parent.CameraFit).lift(character :: Model)
    cameraLift+=(target-cameraLift)*(1-math.exp(-dt*Config.CameraLiftSharpness))
    cameraLiftY=cameraLift
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
    action.Text=if state=="Sanctuary" then (if action:GetAttribute("GoCue")==true then require(Shared.FtueRules).GoCueText else "EXPLORE ISLAND") elseif state=="Active" then "HOME" else "SAVING..."
    action.BackgroundColor3=if state=="Active" then C.red else C.accent
    if actionIcon then actionIcon.Visible=state=="Active" end
    actionPadding.PaddingLeft=UDim.new(0,if actionIcon and state=="Active" then 52 else 6)
    actionPadding.PaddingRight=UDim.new(0,6)
    if active=="exit" and state~="Active" then close() end
    if character then
        -- BD-500: the minimum zoom frames the real model size (height and length), never closer than the old 12 x growth scale.
        player.CameraMinZoomDistance=require(script.Parent.CameraFit).minZoom(Config.CameraMinZoom,character)
    end
    if state~=lastRunState then
        if lastRunState=="Sanctuary" and state=="Active" then Sfx.play("run_start") elseif lastRunState=="Active" and state=="Sanctuary" then Sfx.playCue("run_end") end
        lastRunState=state
    end
    local ok,tags=pcall(function() return Http:JSONDecode(if character then character:GetAttribute("RunEggEvents") or "[]" else "[]") end)
    if ok and typeof(tags)=="table" then
        -- BD-154/BD-378: the found-egg toast (HudV2) names weather eggs; no second card from here.
        lastEggCount=#tags
    end
    refreshProgressionHUD()
    if active=="eggs" and refreshEggs then refreshEggs() end
    if player:GetAttribute("ProfileState")=="Loaded" and state=="Sanctuary" and not seenTutorial and player:GetAttribute("DemoSkipTutorial")~=true then seenTutorial=true open("tutorial") end
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
    PrivateState.onChanged(attribute, function()
        scheduleModalRefresh()
    end)
end
PrivateState.onChanged("LastClaimedChestId", function()
    hatchPending=false
    -- Skippable eggs (selected rarities, nothing notable) are already credited: no animation.
    local okGenes,genes=pcall(function() return Http:JSONDecode(str("LastChestGenesJson","null")) end)
    local outcome={big=PrivateState.get("LastChestBig"),shiny=PrivateState.get("LastChestShiny"),eventMutationId=str("LastChestEventMutation"),
        genes=if okGenes and typeof(genes)=="table" then genes else nil,failed=PrivateState.get("LastChestFailed")==true}
    -- BD-525: the decision (species read, rarity, notable rules) is EggsLogic's; an unreadable or unknown species is never skipped.
    local skip,parsed=EggsLogic.autoOpenDecision(decoded("RevealSkipJson","[]"),Config.AutoOpenRequiresPass,ownsAutoOpen(),str("LastChestRewardText"),Config.SpeciesRarities,outcome,skipAllReveals)
    local species=parsed or "compy"
    local rarity=speciesIndex(species)
    table.insert(batchEntries,{rarity=rarity,name=Config.SpeciesDisplayNames[species] or species,failed=outcome.failed,shiny=outcome.shiny==true,big=outcome.big==true})
    if autoHatching and skip then
        table.insert(skippedEntries,{rarity=rarity,speciesId=species,outcome=outcome})
        HatchTimeline.batchStep(HatchTimeline.session,HatchTimeline.remaining(str("NextChestId")~="",num("ActiveChestCount"),num("QueuedEggsWaiting"),num("BufferedRevealCount")),os.clock()) -- BD-444: a quickly opened egg still counts
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
-- docs/133 demo hook (client attribute, set only by the dev-only trailer director sets DemoStartHatch to open the first waiting egg exactly like OPEN on the Eggs screen.
do -- same effect as pressing OPEN: nothing is granted here, so no flag is needed
    player:GetAttributeChangedSignal("DemoStartHatch"):Connect(function()
        if player:GetAttribute("DemoStartHatch")~=true or hatchPending then return end
        player:SetAttribute("DemoStartHatch",nil)
        autoHatching=true
        if (hatchState.next :: any)() then open("hatch") end
    end)
end
do -- docs/133 demo hooks (dev-only trailer director): skip the welcome (How to play) modal, and close whatever modal is open
    player:GetAttributeChangedSignal("DemoSkipTutorial"):Connect(function()
        if player:GetAttribute("DemoSkipTutorial")~=true then return end
        seenTutorial=true
        if active=="tutorial" then close() end
    end)
    player:GetAttributeChangedSignal("DemoCloseModal"):Connect(function()
        if player:GetAttribute("DemoCloseModal")~=true then return end
        player:SetAttribute("DemoCloseModal",nil)
        close()
    end)
end
player:GetAttributeChangedSignal("LastRunEndAt"):Connect(function() if not autoHatching then open("results") end end)
PrivateState.onChanged("LastSettledRunId", function()
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
                    waitSeconds=NestQueue.secondsUntilNextReady(nestList,math.floor(workspace:GetServerTimeNow()),Config.NestIncubationSeconds)
                end
                notify("New Egg Nest!",C.gold,{icon="egg_nest",key="nest",body="Ready in "..UIFormat.duration(math.max(3600,waitSeconds))}) -- no extra sound: it stacked with run_end (BD-166)
            end
            if num("LastRunNestCrystals")>0 then
                notify("Nests full!",C.gold,{icon="egg_nest",key="nestcrystals",body="Extra nests became "..num("LastRunNestCrystals").." crystals"}) -- docs/72: short, kid-friendly
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
    Sfx.playCue("level_up")
    notify("Nest opened!",C.accent,{icon="egg_nest",body="Open your eggs when ready"})
end)
PrivateState.onChanged("LastRewardText", function() if active=="results" then body:ClearAllChildren() render(active) end end)
PrivateState.onChanged("LastRunNestCrystals", function() if active=="results" then body:ClearAllChildren() render(active) end end) -- BD-448: last private value set at settlement, so the rows show final numbers
for _,attribute in {"LastEquipStatus","LastMutationStatus","LastChestClaimStatus","LastNestClaimStatus","LastRunStartStatus"} do
    PrivateState.onChanged(attribute, function()
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
