--!strict
local Players=game:GetService("Players")
local RunService=game:GetService("RunService")
local Shared=game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Config=require(Shared.ProgressionConfig)
local Rules=require(Shared.ProgressionRules)
local Effects=require(Shared.CosmeticEffects)
local Style=require(Shared.AuraTrailStyle)
local Theme=require(Shared.UITheme)
local Mutations=require(Shared.MutationEffects)
local Shiny=require(Shared.ShinyEffects)
local Look=require(Shared.MutationLook)
local function destroy(state)
    state.effect:destroy()
    if state.mutation then state.mutation.Destroy() end
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
    -- Own equipment wins the distance budget; never create unbounded particle pools.
    -- v2 LOD (docs/81): own dino + 2 nearest within 25 studs full, others within 80 lite, else off.
    local players=Players:GetPlayers()
    local distance={}
    for _,player in players do
        local character=player.Character
        local root=if character then character:FindFirstChild("HumanoidRootPart") else nil
        distance[player]=if root and root:IsA("BasePart") and camera then (camera.CFrame.Position-root.Position).Magnitude else math.huge
    end
    table.sort(players,function(a,b)
        if (a==Players.LocalPlayer)~=(b==Players.LocalPlayer) then return a==Players.LocalPlayer end
        return distance[a]<distance[b]
    end)
    local nearRank=0
    for _,player in players do
        local character=player.Character
        local root=if character then character:FindFirstChild("HumanoidRootPart") else nil
        local isLocal=player==Players.LocalPlayer
        if not isLocal then nearRank+=1 end
        local quality=if Effects.v2Ready() then Style.quality(isLocal,distance[player],nearRank,Theme.MotionEnabled) else "full"
        if root and root:IsA("BasePart") and camera and distance[player]<180 and count<8 and quality~="off" then
            count+=1 keep[player]=true
            local auraId=character:GetAttribute("EquippedAuraId") or ""
            local trailId=character:GetAttribute("EquippedTrailId") or ""
            local mutationId=character:GetAttribute("EventMutationId") or ""
            local shiny=character:GetAttribute("ShinyDinosaur")==true
            local visual=character:FindFirstChild("LocalMeshVisual") or character:FindFirstChild("DinoVisual")
            local scale=character:GetAttribute("VisualScale") or 1
            local state=states[player]
            if not state or state.root~=root or state.auraId~=auraId or state.trailId~=trailId or state.mutationId~=mutationId or state.shiny~=shiny or state.visual~=visual or state.motion~=Theme.MotionEnabled or state.quality~=quality then
                if state then destroy(state) end
                state={root=root,auraId=auraId,trailId=trailId,mutationId=mutationId,shiny=shiny,visual=visual,scale=scale,motion=Theme.MotionEnabled,quality=quality,effect=Effects.create(root,Rules.item(Config.Auras,auraId),Rules.item(Config.Trails,trailId),nil,false,quality)}
                if visual and visual:IsA("Model") then
                    if (visual:GetAttribute("Mutation") or "base")=="base" then Look.apply(visual,mutationId) end -- BD-155: soft body tint, always (also with Reduce Motion); the mist below is the motion layer
                    state.mutation=Mutations.Create(visual,mutationId,"rbxassetid://105629313112163",not Theme.MotionEnabled)
                    if shiny then state.glints=Shiny.Create(visual,"rbxassetid://70885382548001",not Theme.MotionEnabled) end
                end
                states[player]=state
            end
            if state.scale~=scale then
                if state.glints then state.glints.Resize() end
                state.scale=scale
            end
            state.effect:update(character:GetAttribute("VisualScale") or 1,os.clock(),Theme.MotionEnabled)
        end
    end
    for player,state in states do if not keep[player] then destroy(state) states[player]=nil end end
end)
