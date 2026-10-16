--!nonstrict
-- World cosmetics. docs/93: auras, trails and event mutations are all built by client/FxRig from Shared/FxRecipes
-- (layered anime-style looks that grow with rarity, budgeted per device, Reduce Motion = one soft light / one short ribbon).
-- Replaces the old CosmeticEffects strips and the MutationEffects mist (those modules stay for history and tests).
local Players=game:GetService("Players")
local RunService=game:GetService("RunService")
local Shared=game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Config=require(Shared.ProgressionConfig)
local Rules=require(Shared.ProgressionRules)
local Theme=require(Shared.UITheme)
local Shiny=require(Shared.ShinyEffects)
local Look=require(Shared.MutationLook)
local Recipes=require(Shared.FxRecipes)
local Rig=require(script.Parent.FxRig)
local Lod=require(Shared.EffectsLod) -- BD-095 distance LOD
local Settings=require(Shared.SettingsModel)
local function destroy(state)
    for _,rig in state.rigs do rig:destroy() end
    if state.glints then state.glints.Destroy() end
    if state.visual and state.visual.Parent and state.mutationId~="" then Look.apply(state.visual,nil) end -- restore the body colour
end
local states={}
local elapsed=0
RunService.Heartbeat:Connect(function(dt)
    elapsed+=dt
    if elapsed<1/30 then return end
    elapsed=0
    local camera=workspace.CurrentCamera
    local keep={}
    local count=0
    local device=Rig.device()
    local fullDinos=Recipes.Devices[device].fullDinos
    -- Own equipment wins the distance budget; nearest dinos get full detail, the rest a lite look. Never unbounded pools.
    local distance={}
    local players=Players:GetPlayers()
    for _,player in players do
        local root=if player.Character then player.Character:FindFirstChild("HumanoidRootPart") else nil
        distance[player]=if root and root:IsA("BasePart") and camera then (camera.CFrame.Position-root.Position).Magnitude else math.huge
    end
    table.sort(players,function(a,b)
        if a==Players.LocalPlayer then return b~=Players.LocalPlayer end
        if b==Players.LocalPlayer then return false end
        return distance[a]<distance[b]
    end)
    for _,player in players do
        local character=player.Character
        local root=if character then character:FindFirstChild("HumanoidRootPart") else nil
        local own=player==Players.LocalPlayer
        if root and root:IsA("BasePart") and camera and Lod.visible(Settings.effects(),distance[player],own,count+1) then
            count+=1 keep[player]=true
            local auraId=character:GetAttribute("EquippedAuraId") or ""
            local trailId=character:GetAttribute("EquippedTrailId") or ""
            local mutationId=character:GetAttribute("EventMutationId") or ""
            local shiny=character:GetAttribute("ShinyDinosaur")==true
            local visual=character:FindFirstChild("LocalMeshVisual") or character:FindFirstChild("DinoVisual")
            local scale=character:GetAttribute("VisualScale") or 1
            local mode=Settings.effects() -- BD-265: Settings Effects Full / Lite / Off
            local detail=Lod.detail(mode,"mutation",distance[player],own,count,fullDinos) -- never "none" here: visible() passed; Off drops aura/trail in add()
            local state=states[player]
            if not state or state.root~=root or state.auraId~=auraId or state.trailId~=trailId or state.mutationId~=mutationId or state.shiny~=shiny or state.visual~=visual or state.motion~=Theme.MotionEnabled or state.detail~=detail or state.mode~=mode then
                if state then destroy(state) end
                state={root=root,auraId=auraId,trailId=trailId,mutationId=mutationId,shiny=shiny,visual=visual,scale=scale,motion=Theme.MotionEnabled,detail=detail,mode=mode,rigs={}}
                local reduce=not Theme.MotionEnabled
                -- A second or third rig on the same dino always uses the lite layer count so the combined look stays inside one budget.
                local function add(kind: string,item: any)
                    if not item or (mode=="off" and kind~="mutation") then return end -- Off drops aura and trail, keeps the event mutation cue
                    -- BD-353 stacked budget: the mutation cue always keeps its own detail (glow + ground ring + motes even when lite);
                    -- an aura and a trail on the same dino drop to the lite layer count instead, so the combined look stays in budget.
                    local rigDetail=if kind~="mutation" and (#state.rigs>0 or mutationId~="") then "lite" else detail
                    table.insert(state.rigs,Rig.attach(root,kind,item,{reduce=reduce,detail=rigDetail,device=device}))
                end
                add("aura",Rules.item(Config.Auras,auraId))
                add("mutation",Look.get(mutationId))
                add("trail",Rules.item(Config.Trails,trailId))
                if visual and visual:IsA("Model") then
                    if (visual:GetAttribute("Mutation") or "base")=="base" then Look.apply(visual,mutationId) end -- BD-155: soft body tint, always (also with Reduce Motion)
                    if shiny then state.glints=Shiny.Create(visual,"rbxassetid://70885382548001",reduce) end
                end
                states[player]=state
            end
            if state.scale~=scale then
                if state.glints then state.glints.Resize() end
                state.scale=scale
            end
            local velocity=root.AssemblyLinearVelocity
            local moving=Vector3.new(velocity.X,0,velocity.Z).Magnitude>1
            for _,rig in state.rigs do rig:update(scale,os.clock(),moving) end
        end
    end
    for player,state in states do if not keep[player] then destroy(state) states[player]=nil end end
end)
