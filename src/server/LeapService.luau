--!strict
-- Leap, client-owned. The player's own client applies the launch impulse the instant LEAP is pressed and keeps simulating the
-- dino, so there is no network-ownership hand-over, no sink and no snap when the leap ends. The server only VALIDATES:
-- grounded start, cooldown, a wall check ahead, then every Heartbeat an envelope check (distance, height, speed) and a wall
-- check along the path. A violation rolls the dino back to its last valid position and adds a cooldown penalty.
local Players=game:GetService("Players")
local ReplicatedStorage=game:GetService("ReplicatedStorage")
local RunService=game:GetService("RunService")
local Config=require(ReplicatedStorage.Shared.ProgressionConfig)
local Leap={}
local active={}
local requests={}

-- PROVISIONAL tolerances: the client is trusted only inside this envelope.
Leap.LatencyGrace=.35    -- seconds added to the time-based distance limit
Leap.Slack=8             -- studs of position slack
Leap.SpeedTolerance=1.35 -- horizontal speed multiplier
Leap.HeightTolerance=1.3 -- apex multiplier
local leapReady: {[number]: number} = {} -- BD-363: UserId -> LeapReadyAt, survives leave/rejoin on this server
Leap.Penalty=30          -- extra cooldown seconds after a rejected leap

local function planar(a,b)
    local dx,dz=a.X-b.X,a.Z-b.Z
    return math.sqrt(dx*dx+dz*dz)
end

-- Pure envelope check: nil when the state is physically possible for this leap, else the reason.
-- start/position are positions, velocity the root's current velocity, elapsed seconds since takeoff.
function Leap.violation(config,gravity: number,start,position,velocity,elapsed: number): string?
    local reach=config.LeapHorizontalSpeed*(math.max(0,elapsed)+Leap.LatencyGrace)+Leap.Slack
    if planar(position,start)>reach then return "distance" end
    local apex=config.LeapVerticalSpeed*config.LeapVerticalSpeed/(2*math.max(1,gravity))
    if position.Y-start.Y>apex*Leap.HeightTolerance+Leap.Slack then return "height" end
    local speed=math.sqrt(velocity.X*velocity.X+velocity.Z*velocity.Z)
    if speed>config.LeapHorizontalSpeed*Leap.SpeedTolerance+2 then return "speed" end
    if velocity.Y>config.LeapVerticalSpeed*1.25+10 then return "lift" end
    return nil
end

-- Owner-only runtime tuning (AdminService "leapSpeed" multiplier, never persisted). Client and server read the same attribute.
function Leap.effective()
    local scale=workspace:GetAttribute("Admin_leapSpeed")
    if typeof(scale)~="number" or scale~=scale then scale=1 end
    return {LeapHorizontalSpeed=Config.LeapHorizontalSpeed*math.clamp(scale,.5,1.5),LeapVerticalSpeed=Config.LeapVerticalSpeed}
end

function Leap.start()
    local remote=Instance.new("RemoteEvent") remote.Name="RequestLeap" remote.Parent=ReplicatedStorage.BeDinoRemotes
    local params=RaycastParams.new()
    params.FilterType=Enum.RaycastFilterType.Include
    params.FilterDescendantsInstances={workspace.Terrain,workspace.BeDinoArena}

    local function finish(player,state)
        state.character:SetAttribute("LeapUntil",0)
        state.character:SetAttribute("MovementSpeedLimit",nil)
        state.trail:Destroy() state.a:Destroy() state.b:Destroy()
        active[player]=nil
    end

    local function reject(player,state,reason: string,now: number)
        local root=state.root
        if root.Parent then
            root.CFrame=state.lastCFrame
            root.AssemblyLinearVelocity=Vector3.zero
        end
        local readyAt=math.max(player:GetAttribute("LeapReadyAt") or 0,now)+Leap.Penalty
        player:SetAttribute("LeapReadyAt",readyAt)
        leapReady[player.UserId]=readyAt
        player:SetAttribute("LastLeapStatus","rejected")
        player:SetAttribute("LeapRejectCount",(player:GetAttribute("LeapRejectCount") or 0)+1)
        warn(string.format("[Be Dino leap] rejected for %s (%s)",tostring(player.Name),reason))
        finish(player,state)
    end

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
        if active[player] then return end
        if now<math.max(player:GetAttribute("LeapReadyAt") or 0,leapReady[player.UserId] or 0) then player:SetAttribute("LastLeapStatus","cooldown") return end
        local look=root.CFrame.LookVector
        local forward=Vector3.new(look.X,0,look.Z)
        if forward.Magnitude<.01 then return end forward=forward.Unit
        if workspace:Blockcast(root.CFrame,Vector3.new(root.Size.X,1.5,root.Size.Z),forward*3,params) then
            player:SetAttribute("LastLeapStatus","blocked") return
        end
        -- The client already launched itself; the server keeps ownership with the player and only records the leap.
        player:SetAttribute("LeapReadyAt",now+Config.LeapCooldown)
        leapReady[player.UserId]=now+Config.LeapCooldown -- BD-363: a rejoin cannot reset the cooldown (UserId keyed, pruned below)
        player:SetAttribute("LastLeapStatus","leaping")
        c:SetAttribute("LeapUntil",now+Config.LeapDuration)
        c:SetAttribute("MovementSpeedLimit",Leap.effective().LeapHorizontalSpeed)
        local a=Instance.new("Attachment") a.Position=Vector3.new(-.8,0,0) a.Parent=root
        local b=Instance.new("Attachment") b.Position=Vector3.new(.8,0,0) b.Parent=root
        local trail=Instance.new("Trail") trail.Attachment0,trail.Attachment1=a,b
        trail.Color=ColorSequence.new(Color3.fromRGB(80,214,255),Color3.new(1,1,1))
        trail.Lifetime,trail.FaceCamera,trail.Parent=.25,true,root
        active[player]={character=c,root=root,start=root.Position,position=root.Position,lastCFrame=root.CFrame,
            startedAt=now,endsAt=now+Config.LeapDuration,trail=trail,a=a,b=b}
    end)

    RunService.Heartbeat:Connect(function()
        local now=workspace:GetServerTimeNow()
        for player,state in active do
            local root=state.root
            if now>=state.endsAt or player.Character~=state.character or state.character:GetAttribute("RunState")~="Active" or not root.Parent then
                finish(player,state)
            else
                local delta=root.Position-state.position
                local blockedPath=false
                if delta.Magnitude>.001 then
                    blockedPath=workspace:Blockcast(CFrame.new(state.position),Vector3.new(root.Size.X,1.5,root.Size.Z),delta,params)~=nil
                end
                if blockedPath then
                    reject(player,state,"wall",now)
                else
                    local reason=Leap.violation(Leap.effective(),workspace.Gravity,state.start,root.Position,root.AssemblyLinearVelocity,now-state.startedAt)
                    if reason then
                        reject(player,state,reason,now)
                    else
                        state.position=root.Position
                        state.lastCFrame=root.CFrame
                    end
                end
            end
        end
    end)
    Players.PlayerRemoving:Connect(function(p)
        requests[p]=nil
        if active[p] then active[p].endsAt=0 end
        for id,at in leapReady do if workspace:GetServerTimeNow()>=at then leapReady[id]=nil end end -- only unexpired cooldowns are kept
    end)
end
return Leap
