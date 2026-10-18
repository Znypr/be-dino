--!strict
-- BD-1110 / docs/160 s10: the small screens (Go home?, Run Crystal Box, Auto-opened eggs, Settings with its Help page, Food & Growth and the
-- tutorial) were inline in Bootstrap's render function. They live here now, code unchanged except where Bootstrap's own variables are read
-- through the helpers given to attach (modalVersion, the list of auto-opened eggs, "tutorial seen"). Bootstrap calls attach once, then
-- render(name) for every name in SmallScreens.names.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local player = Players.LocalPlayer
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Theme = require(Shared.UITheme)
local EggsLogic = require(Shared.EggsLogic)
local RevealSkip = require(Shared.RevealSkip)
local C = Theme.Colors
local rarityColors = Theme.RarityColors

local Screens = {}
Screens.names = {exit = true, crystalReveal = true, batchSummary = true, settings = true, food = true, tutorial = true}

-- Bootstrap's screen helpers, set by attach.
local body: any, heading: any, header: any, label: any, box: any, button: any, art: any
local open: any, close: any, notify: any, viewportScale: any, touchMode: any, num: any, str: any, decoded: any
local modalVersion: any, motionNow: any, celebrate: any, skipped: any, clearSkipped: any, markTutorialSeen: any, ownsAutoOpen: any, autoOpenSelection: any
local endRun: any, setSkipRemote: any

-- d: {body, heading, header, label, box, button, art, open, close, notify, viewportScale, touchMode, num, str, decoded, modalVersion, motion,
--     celebrate, skipped, clearSkipped, markTutorialSeen, ownsAutoOpen, autoOpenSelection}
function Screens.attach(d: any)
    body, heading, header, label, box, button, art = d.body, d.heading, d.header, d.label, d.box, d.button, d.art
    open, close, notify, viewportScale, touchMode, num, str, decoded = d.open, d.close, d.notify, d.viewportScale, d.touchMode, d.num, d.str, d.decoded
    modalVersion, motionNow, celebrate = d.modalVersion, d.motion, d.celebrate
    skipped, clearSkipped, markTutorialSeen, ownsAutoOpen, autoOpenSelection = d.skipped, d.clearSkipped, d.markTutorialSeen, d.ownsAutoOpen, d.autoOpenSelection
    local remotes = ReplicatedStorage:WaitForChild("BeDinoRemotes", 60) :: Folder
    endRun = remotes:WaitForChild("RequestEndRun")
    setSkipRemote = remotes:WaitForChild("SetRevealSkip")
end

function Screens.render(name: string)
    if name=="exit" then
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
        local version=modalVersion()
        art(body,"amber",262,8,300)
        local amount=label(body,"Opening...",70,282,684,65,38,C.gold)
        task.delay(1.2,function()
            if modalVersion()~=version or not amount.Parent then return end
            amount.Text="+"..num("LastRunCrystalBox").." Crystals"
            local rewardScale=Instance.new("UIScale")
            rewardScale.Scale,rewardScale.Parent=if motionNow() then .92 else 1,amount
            Theme.animate(rewardScale,.22,{Scale=1},Enum.EasingStyle.Back)
            celebrate()
        end)
        label(body,"Run total: +"..num("LastRunCrystals").." Crystals, already saved",70,353,684,40,22)
    elseif name=="batchSummary" then
        heading.Text,header.BackgroundColor3="Auto-opened eggs",C.gold
        local summary=RevealSkip.summarize(skipped())
        local lines=EggsLogic.summaryLines(summary)
        label(body,table.concat(lines,"\n"),24,16,760,90,24)
        local notes={}
        for _,entry in summary.notable do table.insert(notes,Config.SpeciesDisplayNames[entry.speciesId] or require(Shared.SecretSpeciesConfig).name(entry.speciesId)) end
        label(body,if #notes>0 then "Notable finds: "..table.concat(notes,", ") else "All saved in your collection!",24,120,760,120,22,C.gold)
        button(body,"COLLECTION",24,300,370,64,C.blue,function() clearSkipped() open("collection") end)
        button(body,"DONE",424,300,370,64,C.accent,function() clearSkipped() open("eggs") end)
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
        button(body,"Let's play",212,324,400,62,C.accent,function() markTutorialSeen() open("home") end)
    end
end

return Screens
