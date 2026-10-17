--!strict
-- BD-246 (docs/101 s2, s11-12): applies the class movement rules to the player's Humanoid. Runs ONLY while Config.ClassMovementEnabled
-- is true; with the flag off start() returns before touching anything (no remote, no loop), so default behaviour is unchanged.
--  * JumpPower = Config.JumpPower x class powerX (Water 0 = cannot jump). The WalkSpeed class multiplier lives in ProgressionService.
--  * FLY hover cap and glide: NOT here. The character is owned by its client, so a server velocity write never reached it (BD-593,
--    measured 0.00 studs). Both run in src/client/ClassGlide.client.luau (ClassMovement.glideStep / hoverStep); BD-595 deleted the dead loop.
--  * WATER dash: remote "ClassDash" (no arguments). The server validates and answers the SAME player with the velocity; the client
--    applies it (it owns its physics, like the leap). Rate limited, cooldown from ClassMovement, grounded, Water only, never upward.
--  * FLY glide (BD-246 remainder): remote "ClassGlide" (one boolean: jump held). The server only records the flag; the client applies it.
-- Every number is PROVISIONAL (docs/101); they all come from Shared/ClassMovement and CombatConfig.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local CM = require(ReplicatedStorage.Shared.ClassMovement)

local Service = {}
Service.MinRequestGap = 0.3 -- seconds: requests closer than this are dropped without any work

local function classOf(player: Player): string
    return CM.classForSpecies(player:GetAttribute("EquippedSpeciesId"))
end

-- Pure decision for the glide (offline tested): may a Fly dino glide now? glidedFor = glide seconds spent this airtime.
function Service.glideDecision(class: string, held: boolean, grounded: boolean, glidedFor: number): boolean
    if class ~= "Fly" or held ~= true or grounded then return false end
    return glidedFor < CM.rules(class).jump.glideSeconds
end

-- Pure decision for the dash remote (offline tested): returns ok, reason.
function Service.dashDecision(class: string, state: any): (boolean, string)
    if class ~= "Water" then return false, "class" end
    local ok = CM.canStart(class, "jump", state)
    if not ok then return false, if typeof(state) == "table" and state.grounded ~= true then "air" else "cooldown" end
    return true, "dash"
end

function Service.start()
    if not Config.ClassMovementEnabled then return end
    local remote = Instance.new("RemoteEvent")
    remote.Name = "ClassDash"
    remote.Parent = ReplicatedStorage:WaitForChild("BeDinoRemotes")
    local lastRequest: {[Player]: number} = {}
    local lastDash: {[Player]: number} = {}
    local glideRemote = Instance.new("RemoteEvent")
    glideRemote.Name = "ClassGlide"
    glideRemote.Parent = remote.Parent
    local glideHeld: {[Player]: boolean} = {}
    local lastGlideRequest: {[Player]: number} = {}
    local params = RaycastParams.new()
    params.FilterType = Enum.RaycastFilterType.Include
    params.FilterDescendantsInstances = {workspace.Terrain, workspace:FindFirstChild("BeDinoArena") or workspace.Terrain}

    local function applyJump(player: Player)
        local c = player.Character
        local h = if c then c:FindFirstChildOfClass("Humanoid") else nil
        if not c or not h or c:GetAttribute("DinoAttached") ~= true then return end
        local base = (workspace:GetAttribute("Admin_jumpPower") :: number?) or Config.JumpPower
        h.UseJumpPower = true
        h.JumpPower = CM.jumpPower(classOf(player), base)
    end

    local function hookPlayer(player: Player)
        player:GetAttributeChangedSignal("EquippedSpeciesId"):Connect(function() applyJump(player) end)
        local function hookCharacter(c: Model)
            c:GetAttributeChangedSignal("DinoAttached"):Connect(function() applyJump(player) end)
        end
        player.CharacterAdded:Connect(hookCharacter)
        if player.Character then hookCharacter(player.Character) end
        applyJump(player)
    end
    Players.PlayerAdded:Connect(hookPlayer)
    for _, p in Players:GetPlayers() do hookPlayer(p) end
    Players.PlayerRemoving:Connect(function(p) lastRequest[p] = nil lastDash[p] = nil
        glideHeld[p] = nil lastGlideRequest[p] = nil end)
    glideRemote.OnServerEvent:Connect(function(player: Player, ...)
        if select("#", ...) ~= 1 or typeof((...)) ~= "boolean" then return end
        local now = workspace:GetServerTimeNow()
        if now - (lastGlideRequest[player] or -math.huge) < 0.1 then return end
        lastGlideRequest[player] = now
        glideHeld[player] = (...) :: boolean
    end)

    remote.OnServerEvent:Connect(function(player: Player, ...)
        if select("#", ...) ~= 0 then return end
        local now = workspace:GetServerTimeNow()
        if now - (lastRequest[player] or -math.huge) < Service.MinRequestGap then return end
        lastRequest[player] = now
        local c = player.Character
        local h = if c then c:FindFirstChildOfClass("Humanoid") else nil
        local root = if c then c:FindFirstChild("HumanoidRootPart") else nil
        if not c or not h or not root or not root:IsA("BasePart") or h.Health <= 0 or c:GetAttribute("RunState") ~= "Active"
            or player:GetAttribute("ProfileState") ~= "Loaded" or player:GetAttribute("MovementSecurityStatus") == "REJECTED" then return end
        local class = classOf(player)
        local ok = Service.dashDecision(class, {grounded = h.FloorMaterial ~= Enum.Material.Air, now = now, lastJumpAt = lastDash[player]})
        if not ok then return end
        local look = root.CFrame.LookVector
        if Vector3.new(look.X, 0, look.Z).Magnitude < 0.01 then return end
        local vx, vy, vz = CM.launchVelocity(class, "jump", look.X, look.Z)
        local dist = math.sqrt(vx * vx + vz * vz) * CM.duration(class, "jump")
        if workspace:Blockcast(root.CFrame, Vector3.new(root.Size.X, 1.5, root.Size.Z), Vector3.new(vx, 0, vz).Unit * math.min(3, dist), params) then return end
        lastDash[player] = now
        c:SetAttribute("MovementSpeedLimit", CM.speedLimit(class, "jump")) -- MovementGuard accepts the dash speed meanwhile
        task.delay(CM.duration(class, "jump") + 0.25, function()
            if c.Parent and lastDash[player] == now then c:SetAttribute("MovementSpeedLimit", nil) end
        end)
        remote:FireClient(player, vx, vy, vz)
    end)
end

return Service
