--!strict
-- Weather title card (BD-627, docs/153): the big event name and the soft cave toast, moved unchanged out of WeatherVisuals.client.luau.
local TweenService=game:GetService("TweenService")
local Shared=game:GetService("ReplicatedStorage").Shared
local Theme=require(Shared.UITheme)
local WL=require(Shared.WeatherLooks)
local Slot=require(Shared.WeatherTitleSlot)
local HudRects=require(Shared.HubPromptBubbleRules) -- the names of the HUD rectangles (attributes of BeDinoUI) and the reader for them
return function(ctx:any)
local player:Player=ctx.player
local Cave=ctx.Cave
local TITLE_COLOR:{[string]:Color3}={
    rain=Color3.fromRGB(110,200,255),thunder=Color3.fromRGB(190,170,255),blizzard=Color3.fromRGB(190,235,255),
    volcano=Color3.fromRGB(255,150,60),aurora=Color3.fromRGB(110,255,200),quake=Color3.fromRGB(235,190,120),bloodmoon=Color3.fromRGB(255,70,100),
}

-- ---------------------------------------------------------------- title card
local gui=Instance.new("ScreenGui") gui.Name="WeatherTitle" gui.ResetOnSpawn=false gui.IgnoreGuiInset=true gui.DisplayOrder=40
gui.Parent=player:WaitForChild("PlayerGui")
local title=Instance.new("TextLabel") title.Name="Title" title.AnchorPoint=Vector2.new(.5,.5) title.Position=UDim2.fromScale(.5,WL.Title.y) title.Size=UDim2.fromScale(WL.Title.width,WL.Title.height)
title.BackgroundTransparency=1 title.Font=Enum.Font.FredokaOne title.TextScaled=true title.TextTransparency=1 title.Text="" title.ZIndex=5 title.Parent=gui
local stroke=Instance.new("UIStroke") stroke.Thickness=5 stroke.Color=Color3.fromRGB(14,20,34) stroke.Transparency=1 stroke.Parent=title
local titleScale=Instance.new("UIScale") titleScale.Parent=title
local sub=Instance.new("TextLabel") sub.Name="Sub" sub.AnchorPoint=Vector2.new(.5,0) sub.Position=UDim2.fromScale(.5,1) sub.Size=UDim2.fromScale(.7,.42)
sub.BackgroundTransparency=1 sub.Font=Enum.Font.FredokaOne sub.TextScaled=true sub.TextTransparency=1 sub.TextColor3=Color3.new(1,1,1) sub.Text="Special eggs can drop!" sub.ZIndex=5 sub.Parent=title
local subStroke=Instance.new("UIStroke") subStroke.Thickness=3 subStroke.Color=Color3.fromRGB(14,20,34) subStroke.Transparency=1 subStroke.Parent=sub
local titleToken=0
-- BD-1132 (docs/205 picture 447): the SOFT line (at home in the cave) slides clear of the HUD rail and plates instead of lying over the Potions button. Any
-- failure falls back to the old spot. The big card (in a run) keeps WL.Title.y.
local SOFT_SCALE=.4
local function softY():number
    local ok,y=pcall(function():number
        local size=gui.AbsoluteSize
        if size.X<=0 or size.Y<=0 then return WL.Title.y end
        local ui:any=player:WaitForChild("PlayerGui"):FindFirstChild("BeDinoUI")
        local blockers={}
        if ui then
            local origin=ui.AbsolutePosition -- the HUD canvas starts below the Roblox top bar; this layer ignores the inset
            for _,name in HudRects.HardRects do
                local r=HudRects.rectOf(ui:GetAttribute(name))
                if r then table.insert(blockers,{x=r.x+origin.X,y=r.y+origin.Y,w=r.w,h=r.h}) end
            end
        end
        local cy=Slot.centreY({w=size.X,h=size.Y,boxW=size.X*WL.Title.width*SOFT_SCALE,boxH=size.Y*WL.Title.height*SOFT_SCALE,wantY=size.Y*WL.Title.y,blockers=blockers})
        return cy/size.Y
    end)
    return if ok and typeof(y)=="number" then y else WL.Title.y
end
-- BD-328: the big title card never draws over an open menu: it waits (up to 20 s) for the menu to close, then plays.
local function menuOpen():boolean return player:GetAttribute("MenuOpen")==true end
player:GetAttributeChangedSignal("MenuOpen"):Connect(function() gui.Enabled=not menuOpen() end) -- a menu opened mid-card hides it
local titleBig=false -- true while the big card (with the bonus line) is showing
local function inHall():boolean return Cave.inside() or Cave.amount()>.01 end
-- BD-403: walking into the cave while the big card is up turns it into the small soft toast at once (no bonus line).
local function softenTitle()
    if not titleBig then return end
    titleBig=false
    titleScale.Scale=SOFT_SCALE
    title.Position=UDim2.fromScale(.5,softY())
    title.TextTransparency,stroke.Transparency,sub.TextTransparency,subStroke.Transparency=.35,.5,1,1
end
local function showTitle(id:string,name:string,soft:boolean?)
    titleToken+=1 local mine=titleToken
    soft=soft or inHall() -- re-checked here: the cave may have been entered since the weather changed
    titleBig=not soft
    if menuOpen() then
        task.spawn(function()
            local waited=0
            while menuOpen() and waited<20 do task.wait(.25) waited+=.25 end
            if mine==titleToken and not menuOpen() then showTitle(id,name,soft or inHall()) end
        end)
        return
    end
    title.Text=if soft then name else string.upper(name).."!" title.TextColor3=TITLE_COLOR[id] or Color3.new(1,1,1)
    titleScale.Scale=if soft then SOFT_SCALE elseif Theme.MotionEnabled then 2.2 else 1
    title.Position=UDim2.fromScale(.5,if soft then softY() else WL.Title.y)
    title.TextTransparency,stroke.Transparency,sub.TextTransparency,subStroke.Transparency=if soft then .35 else 0,if soft then .5 else 0,1,1
    if not soft then sub.TextTransparency,subStroke.Transparency=0,0 end
    if Theme.MotionEnabled and not soft then TweenService:Create(titleScale,TweenInfo.new(.45,Enum.EasingStyle.Back,Enum.EasingDirection.Out),{Scale=1}):Play() end
    task.delay(if soft then 1.8 else 3.2,function()
        if mine~=titleToken then return end
        titleBig=false -- the card is fading out: a later softenTitle() (walking into the cave) must not bring the faded RAIN! back (BD-541 walk, step 8 capture)
        local info=TweenInfo.new(.8)
        TweenService:Create(title,info,{TextTransparency=1}):Play() TweenService:Create(stroke,info,{Transparency=1}):Play()
        TweenService:Create(sub,info,{TextTransparency=1}):Play() TweenService:Create(subStroke,info,{Transparency=1}):Play()
    end)
end
return {show=showTitle,soften=softenTitle}
end
