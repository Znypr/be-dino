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
local TouchLayout = require(Shared.TouchLayout)
local C = Theme.Colors

local Toasts: any = {}

-- Set by attach.
local gui: any, shade: any, box: any, label: any, art: any, motion: any
local toastLayer: any, toastScale: any, notifyQueue: any
local toastKindColor = {info=C.blue,good=C.accent,warning=C.red,major=C.gold}
local toastCards = {}
local drawToasts: any

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
local function pumpToasts()
    -- Slide the stack right, clear of the owner's admin panel (AdminPanel sets AdminPanelRight: px from the left edge, 0 = closed).
    local panelRight=player:GetAttribute("AdminPanelRight") or 0
    local half,halfCard=gui.AbsoluteSize.X/2,220*toastScale.Scale
    local shift=if panelRight>0 then math.clamp(panelRight+12+halfCard-half,0,math.max(0,half-halfCard)) else 0
    player:SetAttribute("MenuOpen",shade.Visible) -- BD-328: WeatherVisuals holds its big title card while a menu is open
    -- BD-304/378: with a menu open the toast rides the top, clear of the title and the wallet plates (WalletRect).
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
        local detail=label(card,"",68,30,330,22,15,Color3.fromRGB(220,224,235))
        local count=label(card,"",392,6,44,44,20,C.gold)
        for _,t in {title,detail} do t.TextXAlignment=Enum.TextXAlignment.Left t.TextTruncate=Enum.TextTruncate.AtEnd end
        local tap=Instance.new("TextButton")
        tap.Text,tap.BackgroundTransparency,tap.Size,tap.ZIndex,tap.Parent="",1,UDim2.fromScale(1,1),55,card
        tap.Activated:Connect(function() if NotifyQueue.dismissTop(notifyQueue) then drawToasts() end end)
        toastCards[i]={frame=card,bar=bar,plate=plate,title=title,detail=detail,count=count,seq=0}
    end
    Toasts.layer, Toasts.scale = toastLayer, toastScale
    task.spawn(function()
        while gui.Parent do pumpToasts() task.wait(.1) end
    end)
end

Toasts.notify = notify

return Toasts
