--!strict
-- BD-1088 / docs/160 s10: the toast stack (BD-067), moved out of Bootstrap's main chunk, code unchanged. Up to NotifyQueue.MaxVisible pooled
-- cards stacked from the old toast slot (y=80). NotifyQueue decides what shows (priority, merge, throttle); this only draws. Tap a card to
-- dismiss the newest one. Bootstrap calls attach once, then uses Toasts.notify as its notify; Toasts.layer and Toasts.scale are the frame
-- and its UIScale (Bootstrap's layout code sizes them and publishes the wallet rect on the layer).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local player = Players.LocalPlayer
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared.UITheme)
local NotifyQueue = require(Shared.NotifyQueue)
local RarityWord = require(Shared.RarityWord) -- BD-1120: a toast that names a rarity shows the word in its colour
local ToastSlot = require(Shared.ToastSlot) -- BD-1102: where the stack goes (clear of the rail, the Crystals plate and, with a menu open, the top of the menu)
local C = Theme.Colors
-- BD-1237 (docs/240 step 4, style tile v2 board 7): with Config.MenusCohesionEnabled the cards are cream with an ink outline and ink words on the
-- 20 / 14 scale (R1, R2, R6); the kind (or rarity) colour stays only on the thin bar at the left edge. Flag off: nil, the navy cards as before.
local Cohesion = if (require(Shared.Config) :: any).MenusCohesionEnabled == true then require(Shared.MenusCohesionRules) else nil
local function rgb(t: {number}): Color3 return Color3.fromRGB(t[1], t[2], t[3]) end

local Toasts: any = {}

-- Set by attach.
local gui: any, shade: any, box: any, label: any, art: any, motion: any
local toastLayer: any, toastScale: any, notifyQueue: any
local toastKindColor = {info=C.blue,good=C.accent,warning=C.red,major=C.gold}
local toastCards = {}
local drawToasts: any
local baseScale, wroteScale = 1, 1 -- BD-1102: the layout's toast scale (Bootstrap writes it) and the last value this file wrote (a slim card along the bottom of a menu)
local oneCard = false -- BD-1102: with a menu open only the newest card shows
local passThrough = false -- BD-1102: along the bottom edge a tap goes to the menu under the card

drawToasts=function()
    local shown=notifyQueue.visible
    if oneCard then shown={shown[#shown]} end -- the newest one, in the top slot of the stack
    for i,slot in toastCards do
        local entry=shown[i]
        slot.entry=entry -- BD-1168: the card this slot shows (its tap action, if it has one)
        slot.frame.Visible=entry~=nil
        if entry then
            local color=(entry.tint and Theme.RarityColors[entry.tint]) or toastKindColor[entry.kind] or C.blue
            slot.bar.BackgroundColor3,slot.plate.BackgroundColor3=color,if Cohesion then rgb(Cohesion.Card) else C.panel:Lerp(color,.35)
            RarityWord.set(slot.title,entry.text) RarityWord.set(slot.detail,entry.body or "")
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
                slot.frame.Position=if motion() then target-UDim2.fromOffset(0,12) else target
                if motion() and entry.kind=="major" then
                    local pop=slot.plate:FindFirstChildOfClass("UIScale") or Instance.new("UIScale")
                    pop.Scale,pop.Parent=1.15,slot.plate
                    Theme.animate(pop,.4,{Scale=1},Enum.EasingStyle.Back)
                end
            end
            Theme.animate(slot.frame,if motion() then .14 else 0,{Position=target})
        else
            slot.seq=0
        end
    end
end
-- The rect of a GuiObject in the canvas px of `gui` (nil when it is not there).
local function canvasRect(o: any): ToastSlot.Rect?
    if o == nil or not o.Visible then return nil end
    local origin=gui.AbsolutePosition
    return {x=o.AbsolutePosition.X-origin.X,y=o.AbsolutePosition.Y-origin.Y,w=o.AbsoluteSize.X,h=o.AbsoluteSize.Y}
end
-- The open menu: the biggest frame inside the scrim (Bootstrap's panel).
local function menuRect(): ToastSlot.Rect?
    local best: any,area=nil,0
    for _,child in shade:GetChildren() do
        if child:IsA("Frame") and child.Visible and child.AbsoluteSize.X*child.AbsoluteSize.Y>area then best,area=child,child.AbsoluteSize.X*child.AbsoluteSize.Y end
    end
    return canvasRect(best)
end
local function pumpToasts()
    -- Slide the stack right, clear of the owner's admin panel (AdminPanel sets AdminPanelRight: px from the left edge, 0 = closed).
    local panelRight=player:GetAttribute("AdminPanelRight") or 0
    if toastScale.Scale~=wroteScale then baseScale=toastScale.Scale wroteScale=baseScale end -- Bootstrap's layout pass wrote a new scale
    local half,halfCard=gui.AbsoluteSize.X/2,220*baseScale
    local shift=if panelRight>0 then math.clamp(panelRight+12+halfCard-half,0,math.max(0,half-halfCard)) else 0
    player:SetAttribute("MenuOpen",shade.Visible) -- BD-328: WeatherVisuals holds its big title card while a menu is open
    -- BD-304/378: the stack keeps clear of the Crystals plate and the goal line under it (WalletRect). BD-1102: also of the HUD rail (RailRect, set by
    -- HudV2.layout) and, with a menu open, it shows ONE card above, below or along the bottom of the menu panel, never over its top (ToastSlot).
    local keepClear: {ToastSlot.Rect}={}
    local wallet=toastLayer:GetAttribute("WalletRect") :: Rect?
    if wallet then table.insert(keepClear,{x=wallet.Min.X,y=wallet.Min.Y,w=wallet.Width,h=wallet.Height}) end
    local rail=gui:GetAttribute("RailRect") :: Rect?
    if rail then table.insert(keepClear,{x=rail.Min.X,y=rail.Min.Y,w=rail.Width,h=rail.Height}) end
    local place=ToastSlot.place({canvasW=gui.AbsoluteSize.X,canvasH=gui.AbsoluteSize.Y,scale=baseScale,keepClear=keepClear,menu=if shade.Visible then menuRect() else nil,shift=shift})
    Toasts.place=place
    if place.scale~=toastScale.Scale then toastScale.Scale=place.scale end
    wroteScale=place.scale
    if toastLayer.Position.X.Offset~=place.x or toastLayer.Position.Y.Offset~=place.y then toastLayer.Position=UDim2.new(.5,place.x,0,place.y) end
    local redraw=oneCard~=(place.cards==1)
    oneCard=place.cards==1
    if passThrough~=place.passThrough then
        passThrough=place.passThrough
        for _,slot in toastCards do slot.tap.Active=not passThrough end
    end
    if NotifyQueue.update(notifyQueue,os.clock(),shade.Visible) or redraw then drawToasts() end
end
-- Existing call sites keep notify(text,color); opts adds {kind,key,icon,body,tint,amount,format} and, BD-1168, {action,seconds}.
local function notify(text: string,color: Color3?,opts: any?)
    local o=opts or {}
    local kind=o.kind or (if color==C.red then "warning" elseif color==C.gold or color==C.accent then "good" else "info")
    NotifyQueue.push(notifyQueue,os.clock(),{text=text,body=o.body,kind=kind,key=o.key,icon=o.icon,tint=o.tint,amount=o.amount,format=o.format,live=o.live,action=o.action,seconds=o.seconds})
    pumpToasts()
end
-- d: {gui, shade, box, label, art, motion = function() return the Calm-motion flag end}
function Toasts.attach(d: any)
    gui, shade, box, label, art, motion = d.gui, d.shade, d.box, d.label, d.art, d.motion
    toastLayer=Instance.new("Frame")
    toastLayer.Name,toastLayer.AnchorPoint,toastLayer.Position=  "Toasts",Vector2.new(.5,0),UDim2.new(.5,0,0,80)
    toastLayer.Size,toastLayer.BackgroundTransparency,toastLayer.ZIndex,toastLayer.Parent=UDim2.fromOffset(440,186),1,50,gui
    toastScale=Instance.new("UIScale") toastScale.Parent=toastLayer
    notifyQueue=NotifyQueue.new()
    for i=1,NotifyQueue.MaxVisible do
        local card=box(toastLayer,0,(i-1)*62,440,56,C.card,50)
        card.Visible=false
        local bar=box(card,0,0,10,56,C.blue,51)
        local plate=box(card,16,6,44,44,C.panel,51)
        Theme.decorate(plate,22)
        local title=label(card,"",68,3,330,30,21)
        local detail=label(card,"",68,30,330,22,15,Color3.fromRGB(220,224,235)) detail:SetAttribute("TextKind","note") -- BD-1119: the second toast line is fine print (14 px note floor)
        local count=label(card,"",392,6,44,44,20,C.gold)
        for _,t in {title,detail} do t.TextXAlignment=Enum.TextXAlignment.Left t.TextTruncate=Enum.TextTruncate.AtEnd end
        local tap=Instance.new("TextButton")
        tap.Text,tap.BackgroundTransparency,tap.Size,tap.ZIndex,tap.Parent="",1,UDim2.fromScale(1,1),55,card
        tap.Activated:Connect(function()
            -- BD-1168: a card with a tap action (the welcome-back card opens the Nests screen) closes itself and runs it; every other card closes the newest one, as before
            local entry=toastCards[i].entry
            if entry and entry.action and NotifyQueue.dismiss(notifyQueue,entry) then drawToasts() task.spawn(entry.action) return end
            if NotifyQueue.dismissTop(notifyQueue) then drawToasts() end
        end)
        if Cohesion then -- BD-1237: cream card, ink words (a flat fill: the old gradient goes, the outline stays ink)
            for _,f in {card,plate} do
                local g=f:FindFirstChildOfClass("UIGradient") if g then g:Destroy() end
                local line=f:FindFirstChildOfClass("UIStroke") if line then line.Color,line.Thickness=rgb(Cohesion.Outline),Cohesion.Toast.stroke end
            end
            card.BackgroundColor3=rgb(Cohesion.Cream)
            local g=bar:FindFirstChildOfClass("UIGradient") if g then g:Destroy() end
            for _,t in {{title,Cohesion.Toast.title,Cohesion.Ink},{detail,Cohesion.Toast.detail,Cohesion.Muted},{count,Cohesion.Toast.count,Cohesion.Ink}} do
                local word,px,tone=t[1],t[2],t[3]
                word.TextSize,word.TextColor3,word.TextStrokeTransparency=px,rgb(tone),1
                for _,child in word:GetChildren() do if child:IsA("UIStroke") then child.Enabled=false end end
                word.ChildAdded:Connect(function(child) if child:IsA("UIStroke") then child.Enabled=false end end)
            end
        end
        toastCards[i]={frame=card,bar=bar,plate=plate,title=title,detail=detail,count=count,seq=0,tap=tap}
    end
    Toasts.layer, Toasts.scale = toastLayer, toastScale
    task.spawn(function()
        while gui.Parent do pumpToasts() task.wait(.1) end
    end)
end

Toasts.notify = notify

return Toasts
