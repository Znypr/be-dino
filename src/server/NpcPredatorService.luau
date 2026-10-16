--!strict
-- BD-245 (docs/101 s8): thin glue for the calm NPC predators. ALL decisions live in Shared/NpcPredatorRules (pure, tested by
-- tools/verify_npc_predators.py); this file only builds models, feeds real positions in, drives Humanoids and writes attributes.
-- With Config.CombatEnabled (or Config.NpcPredatorsEnabled) false, start() returns before creating anything: no folder, no
-- models, no loop, no connection. NPC bites are CombatRules.attack calls in the SAME world as players, so HP, class, damage,
-- cooldown, spawn protection, Peaceful and the exactly-once defeat/settlement path are the ones CombatService already enforces.
-- This file never touches eggs, catches, growth or run settlement.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local PhysicsService = game:GetService("PhysicsService")
local Config = require(ReplicatedStorage.Shared.Config)
local Rules = require(ReplicatedStorage.Shared.NpcPredatorRules)
local CombatRules = require(ReplicatedStorage.Shared.CombatRules)
local Visual = require(ReplicatedStorage.Shared.DinosaurVisual)
local LowPoly = require(ReplicatedStorage.Shared.LowPolyDinos)
local NpcLowPoly = require(ReplicatedStorage.Shared.NpcLowPoly)

local NpcPredatorService = {}

local ROOT_SIZE = Vector3.new(2.4, 2, 3.2)
local HIP_HEIGHT = 2
local GROUND_HEIGHT = ROOT_SIZE.Y / 2 + HIP_HEIGHT -- what DinosaurVisual measures for an R15 Humanoid
local WILD_TINT = Color3.fromRGB(70, 40, 100) -- darker, a little purple: reads as "not a player" without new art
local TINT_AMOUNT = 0.45

function NpcPredatorService.start(combat: any?)
    if not Config.CombatEnabled or not Config.NpcPredatorsEnabled or not combat then return end
    local world = Rules.newWorld(true, Config.WorldArtSeed + os.time(), Rules.newTerrain({half = Config.ArenaHalfWidth, seed = Config.WorldArtSeed}))
    local folder = Instance.new("Folder")
    folder.Name = "BeDinoNpcs"
    folder.Parent = workspace
    local entries: {[number]: {model: Model, humanoid: Humanoid, root: BasePart, lastState: string}} = {}
    local groundParams = RaycastParams.new()
    groundParams.FilterType = Enum.RaycastFilterType.Include
    groundParams.FilterDescendantsInstances = {workspace.Terrain, workspace:FindFirstChild("BeDinoArena") or workspace.Terrain}
    local collisionGroupReady = PhysicsService:IsCollisionGroupRegistered("DinoControllers")

    -- fade = true (BD-312, a defeat): the model stays a moment, frozen and marked NpcFading; every client fades it out softly
    -- (0.6 s, or 0.15 s under Reduce Motion), then the server removes it. Anything else is removed at once.
    local function destroy(slot: number, key: string?, fade: boolean?)
        local entry = entries[slot]
        entries[slot] = nil
        if key then combat.removeNpc(key) end
        if not entry then return end
        if fade then
            entry.model:SetAttribute("NpcCue", "")
            entry.model:SetAttribute("NpcFading", true)
            entry.root.Anchored = true
            task.delay(Rules.Config.FadeSeconds + Rules.Config.FadeCleanupExtra, function() entry.model:Destroy() end)
        else
            entry.model:Destroy()
        end
    end

    local function build(npc: any, now: number): boolean
        local hit = workspace:Raycast(Vector3.new(npc.x, Config.TerrainTop + 200, npc.z), Vector3.new(0, -(Config.TerrainTop + 400), 0), groundParams)
        if not hit then return false end -- terrain not there (yet): the slot retries after the respawn delay
        local model = Instance.new("Model")
        model.Name = "WildPredator" .. npc.slot
        local root = Instance.new("Part")
        root.Name = "HumanoidRootPart"
        root.Size = ROOT_SIZE
        root.Transparency = 1
        root.CanTouch = false
        root.CanQuery = false
        root.CFrame = CFrame.new(npc.x, hit.Position.Y + GROUND_HEIGHT + 1, npc.z)
        if collisionGroupReady then root.CollisionGroup = "DinoControllers" end -- passes through players, like players pass each other
        root.Parent = model
        local humanoid = Instance.new("Humanoid")
        humanoid.HipHeight = HIP_HEIGHT
        humanoid.RequiresNeck = false
        humanoid.BreakJointsOnDeath = false
        humanoid.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
        humanoid.HealthDisplayType = Enum.HumanoidHealthDisplayType.AlwaysOff
        humanoid.UseJumpPower = true
        humanoid.JumpPower = 0
        humanoid.AutoJumpEnabled = false
        humanoid.MaxSlopeAngle = Config.MaxSlopeAngle
        humanoid.WalkSpeed = Rules.Config.PatrolSpeed
        humanoid.Parent = model
        model.PrimaryPart = root
        model:SetAttribute("NpcPredator", true)
        model:SetAttribute("CombatClass", npc.class)
        model:SetAttribute("HpByte", 255)
        model:SetAttribute("NpcCue", "")
        model.Parent = folder
        pcall(function() root:SetNetworkOwner(nil) end) -- the server owns the physics: no client can steer or exploit it
        -- BD-324: with Config.LowPolyDinos on, the species' low-poly model (the same clone players use), flat dark tint, no bake; any
        -- failure (flag off, unmapped species, model not loaded, build error) keeps the legacy visual below.
        local lowPoly: Model? = nil
        local models = ReplicatedStorage:FindFirstChild(LowPoly.FolderName)
        local mode = NpcLowPoly.pick(LowPoly.enabled(), LowPoly.has(npc.species), models ~= nil and models:FindFirstChild(npc.species) ~= nil)
        if mode == "lowpoly" then
            local ok, result = pcall(function(): Model?
                local clone = LowPoly.clone(npc.species, nil)
                if not clone then return nil end
                clone.Name = "NpcVisual"
                clone:ScaleTo(npc.visualScale)
                clone:PivotTo(root.CFrame * CFrame.new(0, -GROUND_HEIGHT, 0))
                local r, g, b = NpcLowPoly.shellColor(npc.species)
                for _, part in clone:GetDescendants() do
                    if part:IsA("MeshPart") then
                        part.Anchored = false
                        local textured = part:GetAttribute("LPTexture")
                        local pieces = {part}
                        if type(textured) == "string" and textured ~= "" then
                            -- MeshPart.Color is ignored on a textured mesh and a material colour map is not writable from a game script,
                            -- so the wild look is a thin dark translucent shell over the same part (texture shows through; no bake).
                            local shell = part:Clone()
                            shell.Name = part.Name .. "_wild"
                            shell.TextureID = ""
                            shell.Color = Color3.new(r, g, b)
                            shell.Material = Enum.Material.Plastic
                            shell.Transparency = NpcLowPoly.ShellTransparency
                            shell.CastShadow = false
                            shell.Size = part.Size * NpcLowPoly.ShellGrow
                            shell.Parent = clone
                            table.insert(pieces, shell)
                        end
                        for _, piece in pieces do
                            local weld = Instance.new("Weld") -- a Weld (not a WeldConstraint): the client animator writes C1, like the players' rigs
                            weld.Name = "ResourceWeld"
                            weld.C0 = root.CFrame:ToObjectSpace(piece.CFrame)
                            weld.Part0, weld.Part1, weld.Parent = root, piece, piece
                        end
                    end
                end
                clone.Parent = model
                return clone
            end)
            if ok and result then lowPoly = result else warn("[Be Dino] NPC low-poly visual failed for " .. npc.species .. " (" .. tostring(result) .. "); legacy visual") end
        end
        if lowPoly then
            model:SetAttribute("NpcLowPoly", true)
        else
            Visual.render(model, npc.visualScale, npc.species, "base") -- the same visual path as player dinos
            for _, item in model:GetDescendants() do
                if item:IsA("BasePart") and item ~= root then
                    item.CanCollide, item.CanTouch, item.CanQuery, item.Massless = false, false, false, true
                    item.Color = item.Color:Lerp(WILD_TINT, TINT_AMOUNT)
                end
            end
        end
        local size = model:GetExtentsSize()
        npc.radius = math.clamp(math.max(size.X, size.Z) / 2, 1, 14) -- BD-311: the measured body size, used for chase and bite reach
        local joined = Rules.joinCombat(world, combat.world, npc, now)
        if not joined then model:Destroy() return false end
        combat.addNpc(npc.key, model)
        entries[npc.slot] = {model = model, humanoid = humanoid, root = root, lastState = "patrol"}
        return true
    end

    local function lose(slot: number, now: number, fade: boolean?)
        local npc = Rules.defeated(world, slot, now)
        if npc then destroy(slot, npc.key, fade) end
    end

    -- A player defeated this NPC (CombatService already ran the exactly-once settle and the capped assist growth).
    combat.onNpcDefeated = function(key: string)
        local now = workspace:GetServerTimeNow()
        for slot, npc in world.slots do
            if npc.key == key then lose(slot, now, true) return end
        end
    end

    local function playerSnapshot(now: number): any
        local list = {}
        for _, player in Players:GetPlayers() do
            local character = player.Character
            local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
            local humanoid = if character then character:FindFirstChildOfClass("Humanoid") else nil
            local runId = if character then character:GetAttribute("RunId") else nil
            if character and root and root:IsA("BasePart") and humanoid and typeof(runId) == "string" then
                local key = CombatRules.key(player.UserId, runId)
                local size = character:GetExtentsSize()
                local dino = combat.world.dinos[key] -- only players CombatService tracks can be targeted at all
                if dino then
                    table.insert(list, {
                        key = key, character = character, x = root.Position.X, y = root.Position.Y, z = root.Position.Z, radius = math.clamp(math.max(size.X, size.Z) / 2, 0, 14),
                        alive = dino.state.phase == "Alive" and humanoid.Health > 0,
                        active = character:GetAttribute("RunState") == "Active",
                        peaceful = dino.peaceful, protectedUntil = dino.protectedUntil,
                    })
                end
            end
        end
        return list
    end

    local accumulator = 0
    RunService.Heartbeat:Connect(function(dt)
        accumulator += dt
        if accumulator < 1 / Rules.Config.TickHz then return end
        local step = accumulator
        accumulator = 0
        local now = workspace:GetServerTimeNow()
        local players = playerSnapshot(now)

        local changes = Rules.populate(world, now, players)
        for _, npc in changes.removed do destroy(npc.slot, npc.key) end
        for _, npc in changes.spawned do
            if not build(npc, now) then
                world.slots[npc.slot] = nil
                world.respawnAt[npc.slot] = now + Rules.Config.RetrySeconds
            end
        end

        -- Feed the real physics positions in (a fallen or vanished NPC is simply replaced after the respawn delay).
        for slot, npc in world.slots do
            local entry = entries[slot]
            if not entry or not entry.model.Parent or not entry.root.Parent or entry.root.Position.Y < -50 then
                lose(slot, now)
            else
                local p = entry.root.Position
                npc.x, npc.y, npc.z = p.X, p.Y, p.Z
            end
        end

        for _, event in Rules.step(world, now, step, players) do
            local result = Rules.performBite(world, combat.world, event, now, players)
            local entry = entries[event.slot]
            if entry then entry.model:SetAttribute("BiteSeq", ((entry.model:GetAttribute("BiteSeq") :: number?) or 0) + 1) end
            if result.ok then
                for _, p in players do
                    if p.key == result.targetKey then
                        local target = p.character :: Model
                        target:SetAttribute("HitSeq", ((target:GetAttribute("HitSeq") :: number?) or 0) + 1)
                        target:SetAttribute("HitByUserId", 0)
                        local byte = CombatRules.pendingHpByte(combat.world, result.targetKey, now)
                        if byte then target:SetAttribute("HpByte", byte) end
                    end
                end
            end
        end

        for slot, npc in world.slots do
            local entry = entries[slot]
            if entry then
                local cue = if npc.state == "windup" then "windup" elseif npc.state == "alert" then "alert" else ""
                if entry.model:GetAttribute("NpcCue") ~= cue then entry.model:SetAttribute("NpcCue", cue) end
                if npc.state ~= entry.lastState then
                    if npc.state == "alert" or npc.state == "windup" then -- turn to face (only on entry; the humanoid turns itself while walking)
                        local position = entry.root.Position
                        entry.root.CFrame = CFrame.lookAt(position, position + Vector3.new(npc.faceX, 0, npc.faceZ))
                    end
                    entry.lastState = npc.state
                end
                if npc.moving then
                    entry.humanoid.WalkSpeed = npc.speed
                    entry.humanoid:MoveTo(Vector3.new(npc.goalX, npc.y, npc.goalZ))
                else
                    entry.humanoid:Move(Vector3.zero)
                end
                local byte = CombatRules.pendingHpByte(combat.world, npc.key, now)
                if byte then entry.model:SetAttribute("HpByte", byte) end
            end
        end
    end)
end

return NpcPredatorService
