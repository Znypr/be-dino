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
        if root and root:IsA("BasePart") and camera and distance[player]<180 and count<8 then
            count+=1 keep[player]=true
            local auraId=character:GetAttribute("EquippedAuraId") or ""
            local trailId=character:GetAttribute("EquippedTrailId") or ""
            local mutationId=character:GetAttribute("EventMutationId") or ""
            local shiny=character:GetAttribute("ShinyDinosaur")==true
            local visual=character:FindFirstChild("LocalMeshVisual") or character:FindFirstChild("DinoVisual")
            local scale=character:GetAttribute("VisualScale") or 1
            local mode=require(Shared.SettingsModel).effects() -- BD-265: Settings Effects Full / Lite / Off
            local detail=if mode=="full" and (player==Players.LocalPlayer or (distance[player]<=25 and count<=fullDinos)) then "full" else "lite"
            local state=states[player]
            if not state or state.root~=root or state.auraId~=auraId or state.trailId~=trailId or state.mutationId~=mutationId or state.shiny~=shiny or state.visual~=visual or state.motion~=Theme.MotionEnabled or state.detail~=detail or state.mode~=mode then
                if state then destroy(state) end
                state={root=root,auraId=auraId,trailId=trailId,mutationId=mutationId,shiny=shiny,visual=visual,scale=scale,motion=Theme.MotionEnabled,detail=detail,mode=mode,rigs={}}
                local reduce=not Theme.MotionEnabled
                -- A second or third rig on the same dino always uses the lite layer count so the combined look stays inside one budget.
                local function add(kind: string,item: any)
                    if not item or (mode=="off" and kind~="mutation") then return end -- Off drops aura and trail, keeps the event mutation cue
                    local rigDetail=if #state.rigs>0 then "lite" else detail
                    table.insert(state.rigs,Rig.attach(root,kind,item,{reduce=reduce,detail=rigDetail,device=device}))
                end
                add("aura",Rules.item(Config.Auras,auraId))
                add("trail",Rules.item(Config.Trails,trailId))
                add("mutation",Look.get(mutationId))
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
