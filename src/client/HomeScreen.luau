--!strict
-- BD-1214 / docs/160 s10: the Home (Sanctuary) screen, moved out of Bootstrap's render function (Bootstrap is at its size ceiling). The old
-- card is the old code unchanged; with Config.ScreensCohesionEnabled it is drawn on the style rules by ScreensCohesion.home (docs/240 step 3).
local Players = game:GetService("Players")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Config = require(Shared.Config) :: any
local player = Players.LocalPlayer

local Home = {}

-- d: {body, heading, header, C, label, box, button, hero, bestMutation, str, num, decoded, close, notify, open, startRun}
function Home.render(d: any)
    local body, C, label, str = d.body, d.C, d.label, d.str
    d.heading.Text,d.header.BackgroundColor3="Sanctuary",C.accent
    local id=str("EquippedSpeciesId","compy")
    local name=Config.SpeciesDisplayNames[id] or require(Shared.SecretSpeciesConfig).name(id)
    local function explore()
        local character=player.Character
        if character and character:GetAttribute("RunState")=="Sanctuary" then d.startRun:FireServer() d.close()
        else d.close() d.notify("You are already exploring",C.blue) end
    end
    if Config.ScreensCohesionEnabled==true then
        return require(script.Parent.ScreensCohesion).home({body=body,hero=d.hero,bestMutation=d.bestMutation,id=id,name=name,
            eggsWaiting=d.num("ActiveChestCount")+d.num("QueuedEggsWaiting"),nests=#d.decoded("NestsJson","[]"),level=d.num("AccountLevel"),explore=explore,
            openEggs=function() if not require(script.Parent.HubTravelClient).press("eggs",true) then d.open("eggs") end end})
    end
    local heroCard=d.box(body,0,0,290,330,C.card,24)
    d.hero(heroCard,id,8,8,274,230,d.bestMutation(id))
    label(heroCard,name,0,244,290,42,30)
    label(heroCard,"Equipped dinosaur",0,296,290,26,18,C.accent)
    label(body,"Ready for an adventure?",320,0,495,58,32)
    label(body,require(Shared.FtueCopy).sanctuaryTip1,330,74,474,85,22)
    label(body,require(Shared.FtueCopy).sanctuaryTip2,330,170,474,75,22,C.gold)
    d.button(body,"Explore",340,280,460,68,C.accent,explore)
end

return Home
