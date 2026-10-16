--!strict
-- Next-goal HUD line (top-right under the crystals) and its Goals panel wiring, moved out of Bootstrap.client.luau to free
-- top-level locals (Luau register limit; tools/verify_hatch_v2.py). Behaviour unchanged.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local ProgressionConfig = require(Shared.ProgressionConfig)
local NextGoal = require(Shared.NextGoal)
local FusionSelection = require(Shared.FusionSelection)
local GoalsRules = require(Shared.GoalsRules)
local PhoneScale = require(Shared.PhoneScale)
local EggGenetics = require(Shared.EggGenetics)
local PrivateState = require(script.Parent.PrivateState)
local GoalsPanel = require(script.Parent.GoalsPanel)
local FtueRules = require(Shared.FtueRules)

local GoalHud = {}
function GoalHud.build(ctx: any): (Frame, UIScale, TextLabel, UITextSizeConstraint)
    local box,label,C,num,gui=ctx.box,ctx.label,ctx.C,ctx.num,ctx.gui
    local goalHUD=box(gui,0,0,260,30,C.panel,2)
    local goalScale=Instance.new("UIScale") goalScale.Parent=goalHUD
    goalHUD.Name,goalHUD.BackgroundTransparency="NextGoal",.15
    local goalText=label(goalHUD,"",8,0,244,30,17,C.gold)
    goalText.TextScaled=true
    local goalLimit=Instance.new("UITextSizeConstraint") goalLimit.MaxTextSize=17 goalLimit.Parent=goalText
    local goalDinos=nil -- latest FusionAction list; nil = unavailable (falls back to level XP)
    local function refreshGoal()
        -- BD-440: hidden until the first egg (the Goals panel follows this frame's Visible)
        goalHUD.Visible=FtueRules.showGoals({activeEggs=PrivateState.get("ActiveChestCount"),waitingEggs=PrivateState.get("QueuedEggsWaiting"),
            lastRunEggs=PrivateState.get("LastRunEggCount"),copies=FtueRules.collectionCopies(ctx.decoded("CollectionJson","{}"))})
        local goal=NextGoal.pick({dinos=goalDinos,level=num("AccountLevel"),xp=num("AccountXP"),perLevel=ProgressionConfig.AccountXPPerLevel,
            maxLevel=ProgressionConfig.AccountMaxLevel,stages=FusionSelection.Stages,
            speciesName=function(id) return Config.SpeciesDisplayNames[id] or id end,patternName=FusionSelection.patternName})
        GoalsPanel.setDinos(goalDinos) -- BD-427: hub Goals panel reuses this list and the Index counts
        GoalsPanel.setSpecies(GoalsRules.indexCounts(ctx.decoded("CollectionJson","{}"),Config.SpeciesOrder,function(id) return ctx.eventMutation(id)~=nil or ctx.ownedTraits(id)~=nil end,goalDinos,{colours=#ProgressionConfig.EggColors,patterns=#EggGenetics.Patterns,mutations=#ProgressionConfig.EventMutations},ctx.decoded("DiscoveryJson","")))
        goalText.Text,goalText.TextColor3=(if ctx.touchMode() or PhoneScale.isCompact(gui.AbsoluteSize.Y) then "" else "Goal  ")..goal.text,if goal.ready then C.accent else C.gold
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
    for _,attribute in {"CollectionJson","AccountLevel","AccountXP","DiscoveryJson","ActiveChestCount","QueuedEggsWaiting","LastRunEggCount"} do
        PrivateState.onChanged(attribute, function() refreshGoal() if attribute=="CollectionJson" then loadGoalDinos() end end)
    end
    GoalsPanel.attach(gui,goalHUD,{stages=FusionSelection.Stages,speciesName=function(id) return Config.SpeciesDisplayNames[id] or id end,patternName=FusionSelection.patternName}) -- BD-427
    refreshGoal()
    loadGoalDinos()
    return goalHUD,goalScale,goalText,goalLimit
end
return GoalHud
