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
local LowPoly=require(Shared.LowPolyDinos) -- BD-518: a low-poly body is a baked texture, the event mutation tint is baked in (Part.Color does nothing there)
local Recipes=require(Shared.FxRecipes)
local Rig=require(script.Parent.FxRig)
local Lod=require(Shared.EffectsLod) -- BD-095 distance LOD
local Guards=require(Shared.PhoneGuards) -- BD-507: cosmetic beam ceiling inside the hub on a phone
local Settings=require(Shared.SettingsModel)
local Cave=require(script.Parent.CaveAtmosphere) -- BD-495: is this player inside the cave hub (phones draw no cosmetic glow light there)
local MomentRim=require(script.Parent.MomentRim) -- BD-433: 1.5 s rim on the own dino when a mutation is revealed
local function destroy(state)
    for _,rig in state.rigs do rig:destroy() end
    if state.glints then state.glints.Destroy() end
    if state.visual and state.visual.Parent and state.mutationId~="" then -- restore the body colour
        Look.apply(state.visual,nil)
        if state.visual:GetAttribute("LowPoly")==true then LowPoly.setMutation(state.visual,nil) end
    end
end
local states={}
local lastOwnMutation=nil -- BD-433: the own dino's mutation as last seen (nil = not seen yet, so joining with one worn gives no rim)
-- BD-432 global live-FX budget: what every OTHER dino's rigs already use (beams, trails, lights, shells).
local function liveUsed(except)
    local used={}
    for player,st in states do
        if player~=except then
            for _,rig in st.rigs do for _,k in Lod.CostKeys do used[k]=(used[k] or 0)+(rig.budgetCost[k] or 0) end end
        end
    end
    return used
end
local elapsed=0
RunService.Heartbeat:Connect(function(dt)
    elapsed+=dt
    if elapsed<1/30 then return end
    elapsed=0
    local camera=workspace.CurrentCamera
    local keep={}
    local count=0
    local device=Rig.device()
    local inHub=Cave.inside()
    Rig.setInHub(inHub)
    -- BD-507: inside the hub on a phone the 4 shaft beams share the 24-beam phone budget, so cosmetic beams stop at 24-4=20 (hub total <= 24).
    -- Desktop and tablet: hubPhone is always false, beamCap is the unchanged live cap. Entering or leaving the hub rebuilds the phone's rigs once.
    local hubPhone=inHub and Guards.isPhone(device)
    local beamCap=Guards.cosmeticBeamCap(device,hubPhone,(Lod.Live[device] or Lod.Live.desktop).beams)
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
            if not state or state.root~=root or state.auraId~=auraId or state.trailId~=trailId or state.mutationId~=mutationId or state.shiny~=shiny or state.visual~=visual or state.motion~=Theme.MotionEnabled or state.detail~=detail or state.mode~=mode or state.hubPhone~=hubPhone then
                if state then destroy(state) end
                if own then
                    -- BD-433: a NEW event mutation on the own dino is "revealed": one 1.5 s rim (MomentRim owns Full / Lite / Off, Reduce Motion, the budget).
                    if lastOwnMutation~=nil and mutationId~="" and mutationId~=lastOwnMutation then pcall(MomentRim.play,character,{mutationId=mutationId}) end
                    lastOwnMutation=mutationId
                end
                state={root=root,auraId=auraId,trailId=trailId,mutationId=mutationId,shiny=shiny,visual=visual,scale=scale,motion=Theme.MotionEnabled,detail=detail,mode=mode,hubPhone=hubPhone,rigs={}}
                local reduce=not Theme.MotionEnabled
                -- A second or third rig on the same dino always uses the lite layer count so the combined look stays inside one budget.
                local function add(kind: string,item: any)
                    if not item or (mode=="off" and kind~="mutation") then return end -- Off drops aura and trail, keeps the event mutation cue
                    -- BD-353 stacked budget: the mutation cue always keeps its own detail (glow + ground ring + motes even when lite);
                    -- an aura and a trail on the same dino drop to the lite layer count instead, so the combined look stays in budget.
                    local rigDetail=if kind~="mutation" and (#state.rigs>0 or mutationId~="") then "lite" else detail
                    -- BD-432: the scene-wide ceiling steps this look down to lite, or drops it. The local dino and the mutation cue
                    -- never vanish (lite floor); the local dino is not counted against others' use.
                    local used=if own then {} else liveUsed(player)
                    for _,r in state.rigs do for _,k in Lod.CostKeys do used[k]=(used[k] or 0)+(r.budgetCost[k] or 0) end end
                    rigDetail=Lod.fit(device,rigDetail,used,function(d) return Rig.cost(kind,item,{reduce=reduce,detail=d,device=device}) end,own or kind=="mutation",beamCap)
                    if rigDetail=="none" then return end
                    local rig=Rig.attach(root,kind,item,{reduce=reduce,detail=rigDetail,device=device})
                    rig.budgetCost=Rig.cost(kind,item,{reduce=reduce,detail=rigDetail,device=device})
                    table.insert(state.rigs,rig)
                end
                add("aura",Rules.item(Config.Auras,auraId))
                add("mutation",Look.get(mutationId))
                add("trail",Rules.item(Config.Trails,trailId))
                if visual and visual:IsA("Model") then
                    if (visual:GetAttribute("Mutation") or "base")=="base" then -- BD-155: soft body tint, always (also with Reduce Motion)
                        if visual:GetAttribute("LowPoly")==true then LowPoly.setMutation(visual,mutationId) else Look.apply(visual,mutationId) end
                    end
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
