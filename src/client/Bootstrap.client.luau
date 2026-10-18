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
local HatchPresentation = require(Shared.HatchPresentation)
local HatchTimeline = require(Shared.HatchTimeline)
local HatchSequence = require(script.Parent.HatchSequence)
local ProgressionConfig=require(Shared.ProgressionConfig)
local ProgressionRules=require(Shared.ProgressionRules)
local EggTraits=require(Shared.EggTraits)
local PreviewTraits=require(script.Parent.PreviewTraits)
local EggGenetics=require(Shared.EggGenetics)
local UIFormat=require(Shared.UIFormat)
local RevealSkip=require(Shared.RevealSkip)
local NotifyQueue=require(Shared.NotifyQueue)
local TouchLayout=require(Shared.TouchLayout)
local Sfx=require(Shared.Sfx)
local NextGoal=require(Shared.NextGoal)
local FusionSelection=require(Shared.FusionSelection)
local fusionMenuOk,FusionMenu=pcall(require,script.Parent.FusionMenu)
local DinoIndexScreens=require(script.Parent.DinoIndexScreens) -- BD-1110: the Dino Index and dino details screens
local ShopScreens=require(script.Parent.ShopScreens) -- BD-1088: Crystal Shops, odds pages, purchase confirms, Potion Shop
local C = Theme.Colors
local remotes = ReplicatedStorage:WaitForChild("BeDinoRemotes", 60) :: Folder -- BD-330: a timeout (no infinite-yield warning); the server makes this folder
local startRun = remotes:WaitForChild("RequestStartRun") :: RemoteEvent
local endRun = remotes:WaitForChild("RequestEndRun") :: RemoteEvent
local equip = remotes:WaitForChild("EquipSpecies") :: RemoteEvent
local hatch = remotes:WaitForChild("ClaimChest") :: RemoteEvent
local setSkipRemote = remotes:WaitForChild("SetRevealSkip") :: RemoteEvent
local claimNestRemote = remotes:WaitForChild("ClaimNest") :: RemoteEvent -- BD-090 egg nests menu
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
local seenTutorial = false
local lastGrowth = 0
local lastEggCount = 0
local PrivateState=require(script.Parent.PrivateState) -- BD-360: owner-only values arrive by remote, public ones stay attributes
local num,str=PrivateState.num,PrivateState.str
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
    Theme.TextStyle.outlined(t,"card") -- BD-390 / BD-1119: one outlined style (light fill + dark stroke 2..3), card text is at least 16 px
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
Theme.TextStyle.outlined(heading,"title") -- BD-1119: the one outlined title style (22 px floor, outline 3); ModalCompact keeps it 22 px on screen
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
    Theme.animate(panel,.12,{Position=require(script.Parent.ModalCompact).home(.52)})
    task.delay(if motion then .13 else 0,function() if modalVersion==version then shade.Visible=false end end)
    Theme.animate(blur,.12,{Size=0})
end
-- BD-296: the modal blur belongs to a visible modal only (menu open, scrim shown, ScreenGui enabled and in the PlayerGui).
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
shade.Activated:Connect(function() if require(script.Parent.ModalClose).outsideTap() then close() end end) -- BD-1019: a tap on the dark backdrop = X, except while a hatch is cracking
local Toasts=require(script.Parent.Toasts) -- BD-1088: the toast stack (BD-067) lives in Toasts.luau
Toasts.attach({gui=gui,shade=shade,box=box,label=label,art=art,motion=function() return motion end})
local notify=Toasts.notify
local function viewportScale(): number
    local size=gui.AbsoluteSize
    return require(script.Parent.ModalCompact).model().scale -- BD-546/BD-333: PhoneScale.modal plus the rail clearance; short canvases use the compact layout
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
        panel.Position=require(script.Parent.ModalCompact).home(.52)
    end
    Theme.animate(scale,.16,{Scale=viewportScale()})
    Theme.animate(panel,.16,{Position=require(script.Parent.ModalCompact).home(.5)})
    Theme.animate(shade,.14,{BackgroundTransparency=.42})
    Theme.animate(blur,.16,{Size=blurTarget()})
    if name=="hatch" then -- BD-519: the hatch body starts from the settled home, not a slide still running
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
local function speciesIndex(id: string): number return Config.SpeciesRarities[id] or require(Shared.SecretSpeciesConfig).displayTier(id) or 1 end -- BD-604: a secret species wears the calm Legendary look, it is not a tier
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
    local serial=hatchState.serial -- BD-525: this claim's own 8 s watchdog
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
local refreshEggs
render=function(name: string)
    if name=="home" then
        heading.Text,header.BackgroundColor3="Sanctuary",C.accent
        local heroCard=box(body,0,0,290,330,C.card,24)
        local id=str("EquippedSpeciesId","compy")
        hero(heroCard,id,8,8,274,230,bestMutation(id))
        label(heroCard,Config.SpeciesDisplayNames[id] or require(Shared.SecretSpeciesConfig).name(id),0,244,290,42,30)
        label(heroCard,"Equipped dinosaur",0,296,290,26,18,C.accent)
        label(body,"Ready for an adventure?",320,0,495,58,32)
        label(body,require(Shared.FtueCopy).sanctuaryTip1,330,74,474,85,22)
        label(body,require(Shared.FtueCopy).sanctuaryTip2,330,170,474,75,22,C.gold)
        button(body,"Explore",340,280,460,68,C.accent,function()
            local character=player.Character
            if character and character:GetAttribute("RunState")=="Sanctuary" then startRun:FireServer() close()
            else close() notify("You are already exploring",C.blue) end
        end)

    elseif ShopScreens.names[name] then ShopScreens.render(name)
    elseif DinoIndexScreens.names[name] then DinoIndexScreens.render(name)
    elseif name=="eggs" then
        -- Owner 2026-10-15: ONE Eggs screen = five nest slots + a single Next egg card (src/client/EggsScreen.luau).
        heading.Text,header.BackgroundColor3="Eggs",C.gold
        local nestOk,nestList=pcall(function() return Http:JSONDecode(str("NestsJson","[]")) end)
        if not nestOk or typeof(nestList)~="table" then nestList={} end
        local version=modalVersion
        refreshEggs=EggsScreen.render({
            body=body,C=C,label=label,box=box,button=button,art=art,queue=queue,str=str,num=num,nestList=nestList,
            rarityNames=rarityNames,rarityColors=rarityColors,scale=viewportScale,notify=notify,bodyH=require(script.Parent.ModalCompact).bodyHeight(),bodyScale=require(script.Parent.ModalCompact).bodyScale(), -- BD-531: phone canvas = fit the visible body, no scroll
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
            if not Config.SpeciesDisplayNames[id] and not require(Shared.SecretSpeciesConfig).isSecret(id) then id="compy" end -- BD-604: a hatched secret keeps its own name
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
            local displayName=Config.SpeciesDisplayNames[id] or require(Shared.SecretSpeciesConfig).name(id)
            rewardLabel.Text=if failed then HatchTimeline.FailTitle elseif count>1 then count.."x "..displayName else displayName
            rewardLabel.TextColor3=if failed then C.gold else rarityColors[rarity]
            oddsLabel.Text=if failed then HatchTimeline.FailSub else HatchTimeline.oddsLine(if require(Shared.SecretSpeciesConfig).isSecret(id) then require(Shared.SecretSpeciesConfig).RarityLabel else rarityNames[rarity],HatchTimeline.speciesPct(Config.ChestSpeciesWeights,id),(FusionSelection :: any).pct or HatchTimeline.pct)
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
                local tint=mutationColor :: Color3 -- BD-155: PreviewTraits tints the dinosaur itself
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
            gui=gui,panel=panel,header=header,body=body,eggView=eggView,animateEgg=animateEgg,splitEgg=splitEgg,paint=paint,
            nameLabel=rewardLabel,oddsLabel=oddsLabel,detailLabel=detailLabel,motion=motion,
            eggCondition=HatchTimeline.queueCondition(queue(),str("NextChestId")), -- BD-223: the egg's condition look from the first frame
            eggId=str("NextChestId"), -- BD-397: seeds the v2 paint splats (no-op while Config.HatchV2 is false)
            alive=function() return modalVersion==version and active=="hatch" end,
            flash=flash,
            onSkipAll=function() autoHatching=true skipAllReveals=true end,
            onAbort=function() skipAllReveals=false HatchTimeline.batchReset(HatchTimeline.session) emitHatchSummary() skippedEntries={} end, -- BD-1019: X / tap outside / Escape mid-party: the rest stays in the queue
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
        -- BD-531: on a phone-landscape canvas the body is only ~270-330 px tall: a smaller picture, tighter lines and buttons at the bottom of the
        -- VISIBLE body (ModalCompact.bodyHeight), so GO HOME and CANCEL need no scroll. Desktop (402) keeps today's numbers.
        local visibleH=require(script.Parent.ModalCompact).bodyHeight()
        local X=require(Shared.PhoneScale).exitLayout(visibleH,require(script.Parent.ModalCompact).bodyScale()) -- only read when visibleH<402 (numbers asserted in tools/verify_phone_scale.py)
        art(body,"home",36,if visibleH<402 then X.artY else 28,if visibleH<402 then X.artSize else 214)
        label(body,require(Shared.FtueCopy).homeConfirmLine,300,if visibleH<402 then X.lineY else 8,500,if visibleH<402 then X.lineH else 100,if visibleH<402 then 26 else 28,C.gold)
        local character=player.Character
        local catches=if character then character:GetAttribute("CatchScore") or 0 else 0
        local growth=if character then character:GetAttribute("GrowthScore") or 0 else 0
        label(body,require(Shared.FtueCopy).homeConfirmTotals(catches,growth),300,if visibleH<402 then X.totalsY else 116,500,if visibleH<402 then X.totalsH else 60,22)
        local buttonHeight=if visibleH<402 then X.buttonH elseif touchMode() then math.max(68,46/viewportScale()) else 68
        local buttonsY=if visibleH<402 then X.buttonsY else 396-buttonHeight
        button(body,"GO HOME",300,buttonsY,244,buttonHeight,C.accent,function()
            local current=player.Character
            close()
            if current and current:GetAttribute("RunState")=="Active" then endRun:FireServer() notify("Going home...",C.gold) end
        end)
        button(body,"CANCEL",556,buttonsY,244,buttonHeight,C.blue,close)
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
        label(body,"Run total: +"..num("LastRunCrystals").." Crystals, already saved",70,353,684,40,22)
    elseif name=="results" then
        -- BD-315: a defeat is a gentle first section of THIS modal (a toast was covered by it); eggs, crystals and nests stay banked.
        local oops=if str("LastRunEndReason")=="Defeated" then 26 else 0
        heading.Text,header.BackgroundColor3=if oops>0 then "Oops! Good try!" else "Run Complete!",if oops>0 then C.blue else C.gold
        if oops>0 then label(body,"Your eggs are safe!",30,0,760,30,24,C.blue) end
        local hasEggs=str("NextChestId")~="" or num("QueuedEggsWaiting")>0 or #decoded("NestsJson","[]")>0
        require(script.Parent.RunComplete).build({body=body,C=C,label=label,box=box,art=art,button=button,num=num,oops=oops,hasEggs=hasEggs,
            back=function() open("home") end,
            openEggs=function() if not require(script.Parent.HubTravelClient).press("eggs",true) then open("eggs") end end})
    elseif name=="batchSummary" then
        heading.Text,header.BackgroundColor3="Auto-opened eggs",C.gold
        local summary=RevealSkip.summarize(skippedEntries)
        local lines=EggsLogic.summaryLines(summary)
        label(body,table.concat(lines,"\n"),24,16,760,90,24)
        local notes={}
        for _,entry in summary.notable do table.insert(notes,Config.SpeciesDisplayNames[entry.speciesId] or require(Shared.SecretSpeciesConfig).name(entry.speciesId)) end
        label(body,if #notes>0 then "Notable finds: "..table.concat(notes,", ") else "All saved in your collection!",24,120,760,120,22,C.gold)
        button(body,"COLLECTION",24,300,370,64,C.blue,function() skippedEntries={} open("collection") end)
        button(body,"DONE",424,300,370,64,C.accent,function() skippedEntries={} open("eggs") end)
    elseif name=="settings" then
        heading.Text,header.BackgroundColor3="Settings",C.purple
        -- BD-263 Settings v2: tabs Sound / Look / Controls / Help are drawn by SettingsMenu; Help (guides, auto-open) stays here. Body is 824 x 402.
        local tab=require(script.Parent.SettingsMenu).build(body,{label=label,button=button,open=open,notify=notify,cameraReset=function() player.CameraMaxZoomDistance=Config.CameraMaxZoom end})
        if tab=="help" then
        button(body,"How to play",0,70,400,76,C.gold,function() open("tutorial") end).TextSize=26
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
        label(body,"Shiny, BIG and special eggs always show.",0,324,824,60,20)
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
        label(body,string.format("Eat 500 food for %d eggs. Weather can add more!",math.floor(500*Config.FoodCatchRate+.5)),18,316,788,72,23)
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
        button(body,"Let's play",212,324,400,62,C.accent,function() seenTutorial=true open("home") end)
    end
end
ShopScreens.attach({body=body,heading=heading,header=header,label=label,box=box,button=button,art=art,open=open,notify=notify,viewportScale=viewportScale,num=num,str=str,decoded=decoded,progression=progression,render=render,active=function() return active end})
DinoIndexScreens.attach({body=body,heading=heading,header=header,label=label,box=box,button=button,open=open,notify=notify,viewportScale=viewportScale,num=num,str=str,decoded=decoded,openFusion=function() openFusion() end,equip=equip,copies=copies,bestMutation=bestMutation,eventMutation=eventMutation,ownedTraits=ownedTraits,hero=hero,speciesIndex=speciesIndex,motion=function() return motion end})
-- BD-539: Luau allows 200 locals per function and this main chunk was at 198. Everything from here to the end of the script runs inside
-- one function so its locals (about 56) count against that function instead. Same order, same code, nothing is reindented.
do local function mountHud()
local buildBadge=label(gui,"BUILD "..Config.Build,0,0,250,24,16,C.blue)
buildBadge.Name,buildBadge.AnchorPoint,buildBadge.Position="BuildBadge",Vector2.new(.5,0),UDim2.new(.5,0,0,36)
local foodDiagnostic=label(gui,"",0,0,450,22,16,C.accent)
foodDiagnostic.TextXAlignment,foodDiagnostic.Visible=Enum.TextXAlignment.Left,false
local function refreshFoodDiagnostic()
    local status=workspace:GetAttribute("FoodSpawnStatus") or "Starting"
    foodDiagnostic.Text="FOOD: "..tostring(workspace:GetAttribute("FoodCount") or 0).."  •  "..tostring(status)
    foodDiagnostic.TextColor3=if status=="Failed" or status=="No valid ground" then C.red else C.accent
end
workspace:GetAttributeChangedSignal("FoodSpawnStatus"):Connect(refreshFoodDiagnostic)
workspace:GetAttributeChangedSignal("FoodCount"):Connect(refreshFoodDiagnostic)
refreshFoodDiagnostic()
local previewNotice=label(gui,"STUDIO PREVIEW • progress not saved • test currency",0,0,500,25,16,C.gold)
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
require(script.Parent.HubTravelClient).attach({gui=gui,buttons=navigationButtons,open=function(name) if name=="auras" then require(script.Parent.ShopTiles).enter(require(Shared.FtueP1).shopTabs(num("AccountLevel"))) end open(name) end,openFusion=openFusion,notify=notify,close=close,current=function() return if shade.Visible then active else "" end}) -- BD-288: no-op while Config.CaveHub is false
require(script.Parent.FtueRail).attach(rail,navigationButtons) -- BD-368: first run: only POTIONS, SETTINGS and a MENU chip until the first egg
local hud=box(gui,0,0,390,94,C.panel,2)
hud.AnchorPoint,hud.Position=Vector2.new(0,1),UDim2.new(0,18,1,-18)
local hudScale=Instance.new("UIScale") hudScale.Parent=hud
require(script.Parent.HudV2).attach(hud,gui,{notify=notify}) -- BD-080: egg plate (bottom-left) + SIZE bar (top-centre)
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
    leapText.Text=if left>0 then "LEAP "..timerText(left) else "LEAP [E] ready"
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
    ShopScreens.retryPending() -- same token again after 8 s, so a delayed result cannot charge twice
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
    local railRun=require(script.Parent.RailRun)
    local layout=TouchLayout.compute({width=size.X,height=size.Y,touch=touch,navCount=railRun.count(navigationButtons),
        thumb=if touch then coreTouchRect("DynamicThumbstickFrame") or coreTouchRect("ThumbstickFrame") else nil,
        jump=if touch then coreTouchRect("JumpButton") else nil,
        goals=goalHUD.Visible and (player.Character==nil or player.Character:GetAttribute("RunState")~="Active"), -- BD-531: the hub Goals header takes space under the goal line
        objectives=Config.ObjectivesEnabled==true and goalHUD.Visible and (player.Character==nil or player.Character:GetAttribute("RunState")~="Active")}) -- BD-075: the objectives pill sits next to it (flag off = false, layout identical)
    require(script.Parent.ModalCompact).setClearLeft(TouchLayout.modalClearLeft(layout)) -- BD-546: menu cards stay right of the desktop rail (phones unchanged)
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
        local cellPosition=railRun.position(navigationButtons,i,layout.rail.positions)
        b.Position,b.Size=UDim2.fromOffset(cellPosition.x,cellPosition.y),UDim2.fromOffset(cell.w,cell.h)
        for _,child in b:GetChildren() do
            if child:IsA("TextLabel") then
                child.Position,child.Size,child.TextSize=UDim2.fromOffset(cell.labelX,cell.labelY),UDim2.fromOffset(cell.labelW,cell.labelH),cell.textSize
                child.Visible=not cell.iconOnly -- BD-333: narrow phones show the icon only
                child.TextScaled=not layout.touch -- BD-333: phones: real >= 14 px, no shrink
                local limit=child:FindFirstChildOfClass("UITextSizeConstraint") or Instance.new("UITextSizeConstraint")
                limit.MaxTextSize,limit.Parent=cell.textSize,child
            elseif child:IsA("GuiObject") and child.Name~="ActiveTab" and child.Name~="IndexDot" then
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
    foodDiagnostic.Visible,foodDiagnostic.AnchorPoint,foodDiagnostic.Position=require(Shared.HudRules).showFoodDebug(RunService:IsStudio(),player:GetAttribute("IsAdmin")==true,touch),Vector2.new(0,1),UDim2.fromOffset(layout.hud.x,(if touch then layout.hud.y else math.min(layout.hud.y,layout.feedback.y))-6) -- BD-080/BD-507: debug line for Studio/admin only, above the egg plate and the Tell us! button
    require(script.Parent.HudV2).layout(layout)
    gui:SetAttribute("FeedbackRect",Rect.new(layout.feedback.x,layout.feedback.y,layout.feedback.x+layout.feedback.w,layout.feedback.y+layout.feedback.h)) -- BD-507: FeedbackClient puts its Tell us! button here, clear of the egg plate
    gui:SetAttribute("GoalsRect",if layout.goals then Rect.new(layout.goals.x,layout.goals.y,layout.goals.x+layout.goals.w,layout.goals.y+layout.goals.h) else nil) -- BD-531: GoalsPanel sits on the reserved spot (nil = its own desktop formula)
    if Config.ObjectivesEnabled==true then -- BD-075: ObjectivesPanel sits on these (nil while hidden); never touched with the flag off
        gui:SetAttribute("ObjectivesRect",if layout.objectives then Rect.new(layout.objectives.x,layout.objectives.y,layout.objectives.x+layout.objectives.w,layout.objectives.y+layout.objectives.h) else nil)
        gui:SetAttribute("ObjectivesOpenRect",if layout.objectivesOpen then Rect.new(layout.objectivesOpen.x,layout.objectivesOpen.y,layout.objectivesOpen.x+layout.objectivesOpen.w,layout.objectivesOpen.y+layout.objectivesOpen.h) else nil)
    end
    gui:SetAttribute("AdminRect",Rect.new(layout.admin.x,layout.admin.y,layout.admin.x+layout.admin.w,layout.admin.y+layout.admin.h)) -- BD-531: AdminPanel puts its Admin button here (phone: not on the egg plate)
    gui:SetAttribute("ChipRect",Rect.new(layout.chip.x,layout.chip.y,layout.chip.x+layout.chip.w,layout.chip.y+layout.chip.h)) -- BD-538: HubTravelClient puts the Back to the middle chip here
    if Config.GiftClaimEnabled==true then -- BD-570: GiftPopup sits on this rect; flag off = no attribute
        local gift=TouchLayout.giftRect(layout,size.X,size.Y)
        gui:SetAttribute("GiftRect",Rect.new(gift.x,gift.y,gift.x+gift.w,gift.y+gift.h))
        gui:SetAttribute("GiftVariant",gift.variant)
    end
    Toasts.scale.Scale=layout.toastScale
    local wallet=TouchLayout.walletPlates(layout) -- BD-378: the toast stack keeps clear of the Crystals plate and the goal line under it
    Toasts.layer:SetAttribute("WalletRect",Rect.new(wallet.x,wallet.y,wallet.x+wallet.w,wallet.y+wallet.h))
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
gui:GetAttributeChangedSignal("RailRun"):Connect(scales)
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
goalHUD:GetPropertyChangedSignal("Visible"):Connect(queueLayout) -- BD-531: the Goals header appears after the first egg
do -- BD-531: hidden during a run, so the right column re-lays out when a run starts or ends
    local function watch(character: Model) character:GetAttributeChangedSignal("RunState"):Connect(queueLayout) end
    player.CharacterAdded:Connect(watch)
    if player.Character then watch(player.Character) end
end
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
    action.Text=if state=="Sanctuary" then (if action:GetAttribute("GoCue")==true then require(Shared.FtueRules).GoCueText else "Explore") elseif state=="Active" then "HOME" else "SAVING..."
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
        if table.find({"collection","detail","eggs","auras","potions","settings"},active) then
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
    table.insert(batchEntries,{rarity=rarity,name=Config.SpeciesDisplayNames[species] or require(Shared.SecretSpeciesConfig).name(species),failed=outcome.failed,shiny=outcome.shiny==true,big=outcome.big==true})
    if autoHatching and skip then
        table.insert(skippedEntries,{rarity=rarity,speciesId=species,outcome=outcome})
        HatchTimeline.batchStep(HatchTimeline.session,HatchTimeline.remaining(str("NextChestId")~="",num("ActiveChestCount"),num("QueuedEggsWaiting"),num("BufferedRevealCount")),os.clock()) -- BD-444: a quickly opened egg still counts
        task.delay(Config.ChestClaimRequestCooldownSeconds+.15,function() if autoHatching then (hatchState.next :: any)() end end) -- stay under the server claim cooldown; BD-1019: X / Escape stops the loop
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
-- docs/133 demo hook: DemoStartHatch opens the first waiting egg like OPEN.
do -- same effect as pressing OPEN: nothing is granted here, so no flag is needed
    player:GetAttributeChangedSignal("DemoStartHatch"):Connect(function()
        if player:GetAttribute("DemoStartHatch")~=true or hatchPending then return end
        player:SetAttribute("DemoStartHatch",nil)
        autoHatching=true
        if (hatchState.next :: any)() then open("hatch") end
    end)
end
do -- docs/133 demo hooks (dev-only): skip the welcome modal, close the open modal
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
for _,attribute in {"LastEquipStatus","LastChestClaimStatus","LastNestClaimStatus","LastRunStartStatus"} do
    PrivateState.onChanged(attribute, function()
        local status=str(attribute)
        if attribute=="LastChestClaimStatus" then hatchPending=false end
        if status=="claimed" then return
        elseif attribute=="LastNestClaimStatus" then
            if status=="not_ready" or status=="nest_pending" or status=="bank_full" then notify(NotifyQueue.statusText(status),C.gold,{icon="egg_nest",key="nest_status"})
            elseif status~="opened" and status~="duplicate" and status~="" then notify(NotifyQueue.statusText(status),C.red,{key="error"}) end
        elseif status=="next_run" then notify(NotifyQueue.statusText(status),C.gold,{key="ok"}) -- BD-613: picked during a run, applied at the next spawn
        elseif status=="equipped" or status=="mutated" or status=="opened" then notify("Done!",C.accent,{key="ok"})
        elseif status=="already_equipped" then notify(NotifyQueue.statusText(status),C.gold,{key="ok"}) -- BD-1000: a calm note, not a red error
        elseif status~="" and status~="duplicate" then notify(NotifyQueue.statusText(status),C.red,{key="error"}) end
    end)
end
Input.InputBegan:Connect(function(input,processed)
    if processed then return end
    if (input.KeyCode==Enum.KeyCode.E or input.KeyCode==Enum.KeyCode.ButtonY) and not shade.Visible then requestLeap()
    elseif (input.KeyCode==Enum.KeyCode.Escape or input.KeyCode==Enum.KeyCode.ButtonB) and shade.Visible then close()
    elseif input.KeyCode==Enum.KeyCode.C or input.KeyCode==Enum.KeyCode.B then
        local want=if input.KeyCode==Enum.KeyCode.C then "collection" else "eggs"
        if require(Shared.ModalCloseRules).keyAction(if shade.Visible then active else "",want)=="close" then close() else open(want) end -- BD-1074: key twice = closed
    end
end)
end mountHud() end
