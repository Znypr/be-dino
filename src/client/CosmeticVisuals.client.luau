--!strict
local Players=game:GetService("Players")
local RunService=game:GetService("RunService")
local Shared=game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Config=require(Shared.ProgressionConfig)
local Rules=require(Shared.ProgressionRules)
local Effects=require(Shared.CosmeticEffects)
local Theme=require(Shared.UITheme)
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
    local players=Players:GetPlayers()
    table.sort(players,function(a,b) return a==Players.LocalPlayer and b~=Players.LocalPlayer end)
    for _,player in players do
        local character=player.Character
        local root=if character then character:FindFirstChild("HumanoidRootPart") else nil
        if root and root:IsA("BasePart") and camera and (camera.CFrame.Position-root.Position).Magnitude<180 and count<8 then
            count+=1 keep[player]=true
            local auraId=character:GetAttribute("EquippedAuraId") or ""
            local trailId=character:GetAttribute("EquippedTrailId") or ""
            local mutationId=character:GetAttribute("EventMutationId") or ""
            local state=states[player]
            if not state or state.root~=root or state.auraId~=auraId or state.trailId~=trailId or state.mutationId~=mutationId then
                if state then state.effect:destroy() end
                state={root=root,auraId=auraId,trailId=trailId,mutationId=mutationId,effect=Effects.create(root,Rules.item(Config.Auras,auraId),Rules.item(Config.Trails,trailId),Rules.item(Config.EventMutations,mutationId))}
                states[player]=state
            end
            state.effect:update(character:GetAttribute("VisualScale") or 1,os.clock(),Theme.MotionEnabled)
        end
    end
    for player,state in states do if not keep[player] then state.effect:destroy() states[player]=nil end end
end)
