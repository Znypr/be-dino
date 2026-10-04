--!strict
local Players=game:GetService("Players")
local ReplicatedStorage=game:GetService("ReplicatedStorage")
local RunService=game:GetService("RunService")
local Config=require(ReplicatedStorage.Shared.ProgressionConfig)
local Leap={}
local active={}
local requests={}
function Leap.start()
    local remote=Instance.new("RemoteEvent") remote.Name="RequestLeap" remote.Parent=ReplicatedStorage.BeDinoRemotes
    local params=RaycastParams.new()
    params.FilterType=Enum.RaycastFilterType.Include
    params.FilterDescendantsInstances={workspace.Terrain,workspace.BeDinoArena}
    remote.OnServerEvent:Connect(function(player,...)
        if select("#",...)~=0 then return end
        local now=workspace:GetServerTimeNow()
        if now-(requests[player] or -math.huge)<.3 then return end requests[player]=now
        local c=player.Character
        local h=if c then c:FindFirstChildOfClass("Humanoid") else nil
        local root=if c then c:FindFirstChild("HumanoidRootPart") else nil
        if not c or not root or not root:IsA("BasePart") or not h or h.Health<=0 or c:GetAttribute("RunState")~="Active"
            or player:GetAttribute("ProfileState")~="Loaded" or h.FloorMaterial==Enum.Material.Air
            or player:GetAttribute("MovementSecurityStatus")=="REJECTED" then return end
        if now<(player:GetAttribute("LeapReadyAt") or 0) then player:SetAttribute("LastLeapStatus","cooldown") return end
        local look=root.CFrame.LookVector
        local forward=Vector3.new(look.X,0,look.Z)
        if forward.Magnitude<.01 then return end forward=forward.Unit
        if workspace:Blockcast(root.CFrame,Vector3.new(root.Size.X,1.5,root.Size.Z),forward*3,params) then
            player:SetAttribute("LastLeapStatus","blocked") return
        end
        local ownerOk=pcall(function() root:SetNetworkOwner(nil) end)
        if not ownerOk then return end
        player:SetAttribute("LeapReadyAt",now+Config.LeapCooldown)
        player:SetAttribute("LastLeapStatus","leaping")
        c:SetAttribute("LeapUntil",now+Config.LeapDuration)
        c:SetAttribute("MovementSpeedLimit",Config.LeapHorizontalSpeed)
        h:ChangeState(Enum.HumanoidStateType.Jumping)
        root.AssemblyLinearVelocity=forward*Config.LeapHorizontalSpeed+Vector3.new(0,Config.LeapVerticalSpeed,0)
        local a=Instance.new("Attachment") a.Position=Vector3.new(-.8,0,0) a.Parent=root
        local b=Instance.new("Attachment") b.Position=Vector3.new(.8,0,0) b.Parent=root
        local trail=Instance.new("Trail") trail.Attachment0,trail.Attachment1=a,b
        trail.Color=ColorSequence.new(Color3.fromRGB(80,214,255),Color3.new(1,1,1))
        trail.Lifetime,trail.FaceCamera,trail.Parent=.25,true,root
        active[player]={character=c,root=root,position=root.Position,endsAt=now+Config.LeapDuration,trail=trail,a=a,b=b}
    end)
    RunService.Heartbeat:Connect(function()
        local now=workspace:GetServerTimeNow()
        for player,state in active do
            local root=state.root
            if now>=state.endsAt or player.Character~=state.character or state.character:GetAttribute("RunState")~="Active" then
                if root.Parent then
                    local velocity=root.AssemblyLinearVelocity
                    local h=state.character:FindFirstChildOfClass("Humanoid")
                    local speed=if h then h.WalkSpeed else 22
                    local horizontal=Vector3.new(velocity.X,0,velocity.Z)
                    if horizontal.Magnitude>speed then horizontal=horizontal.Unit*speed end
                    root.AssemblyLinearVelocity=horizontal+Vector3.new(0,velocity.Y,0)
                    pcall(function() root:SetNetworkOwnershipAuto() end)
                end
                state.character:SetAttribute("LeapUntil",0)
                state.character:SetAttribute("MovementSpeedLimit",nil)
                state.trail:Destroy() state.a:Destroy() state.b:Destroy()
                active[player]=nil
            else
                local delta=root.Position-state.position
                if delta.Magnitude>.001 then
                    local hit=workspace:Blockcast(CFrame.new(state.position),Vector3.new(root.Size.X,1.5,root.Size.Z),delta,params)
                    if hit then root.Position=state.position root.AssemblyLinearVelocity=Vector3.zero state.endsAt=now end
                end
                state.position=root.Position
            end
        end
    end)
    Players.PlayerRemoving:Connect(function(p) requests[p]=nil if active[p] then active[p].endsAt=0 end end)
end
return Leap
