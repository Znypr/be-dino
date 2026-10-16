--!strict
-- BD-243 / BD-244 (docs/101 s4-s7): HP combat glue. Runs ONLY while Config.CombatEnabled is true; with the flag off
-- start() returns before creating anything (no remote, no attributes, no loops), so the shipped game is untouched.
-- All rules live in Shared/CombatRules (pure, tested by tools/verify_combat_service.py); this file only reads
-- characters, answers the Bite remote and hands a defeat to RunLifecycle.tryEnd, the single settlement path.
-- The client sends NOTHING but the request: the server auto-targets, measures range/cone, applies damage.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local HttpService = game:GetService("HttpService")
local Config = require(ReplicatedStorage.Shared.Config)
local Cfg = require(ReplicatedStorage.Shared.CombatConfig)
local Rules = require(ReplicatedStorage.Shared.CombatRules)
local SettingsModel = require(ReplicatedStorage.Shared.SettingsModel)
local TeamUp = require(ReplicatedStorage.Shared.CombatTeamUp)
local NpcRules = require(ReplicatedStorage.Shared.NpcPredatorRules)

local CombatService = {}
local PrivateState = require(script.Parent.PrivateState)
local CooldownMemory = require(script.Parent.CooldownMemory)
local biteMemory = CooldownMemory.new(120) -- BD-363: bite cooldown keyed by UserId, a rejoin does not reset it

local function numberAttribute(instance: Instance, name: string, fallback: number): number
    local value = instance:GetAttribute(name)
    return if typeof(value) == "number" then value else fallback
end

local function peacefulFor(player: Player): boolean
    local raw = PrivateState.get(player, "SettingsJson")
    if typeof(raw) ~= "string" or raw == "" then return false end
    local ok, decoded = pcall(function() return HttpService:JSONDecode(raw) end)
    return ok and SettingsModel.fromStore(decoded).peaceful
end

-- BD-311: planar half-size of a model's bounding box (the server measures it; the client never sends a size).
local function radiusOf(model: Model): number
    local ok, size = pcall(function() return model:GetExtentsSize() end)
    if not ok then return 0 end
    return math.max(size.X, size.Z) / 2
end

-- Returns nil while the flag is off. With it on, the returned api lets NpcPredatorService (BD-245) put wild predators into the SAME
-- rules world: api.world is the CombatRules world, api.npcs = {[combat key] = Model} are bite targets like player dinos.
function CombatService.start(runLifecycle, dinosaur): any?
    if not Config.CombatEnabled then return end
    local world = Rules.new(true)
    local api: any = {world = world, npcs = {}, onNpcDefeated = nil, npcRewards = NpcRules.newRewardLimiter()}
    local tracked: {[Model]: string} = {}
    local connections: {[Model]: {RBXScriptConnection}} = {}
    local characterOf: {[string]: Model} = {}

    local folder = ReplicatedStorage:WaitForChild("BeDinoRemotes")
    local remote = Instance.new("RemoteEvent")
    remote.Name = "CombatBite"
    remote.Parent = folder

    local params = RaycastParams.new()
    params.FilterType = Enum.RaycastFilterType.Include
    params.FilterDescendantsInstances = {workspace.Terrain, workspace:FindFirstChild("BeDinoArena") or workspace.Terrain}

    local function leave(character: Model)
        local key = tracked[character]
        if not key then return end
        tracked[character] = nil
        characterOf[key] = nil
        Rules.leave(world, key)
        for _, c in connections[character] or {} do c:Disconnect() end
        connections[character] = nil
    end

    local function join(player: Player, character: Model)
        if tracked[character] then return end
        local runId = character:GetAttribute("RunId")
        if typeof(runId) ~= "string" or character:GetAttribute("RunState") ~= "Active" then return end
        local now = workspace:GetServerTimeNow()
        local d = Rules.join(world, {
            userId = player.UserId, runId = runId,
            class = Rules.classForSpecies(player:GetAttribute("EquippedSpeciesId")),
            score = numberAttribute(character, "GrowthScore", 0), now = now,
            peaceful = peacefulFor(player),
            protectedUntil = numberAttribute(character, "SpawnProtectionEndsAt", 0),
        })
        if not d then return end
        local lastBite = biteMemory.last(player.UserId, "bite")
        if lastBite > d.lastBiteAt then d.lastBiteAt = lastBite end
        tracked[character] = d.key
        characterOf[d.key] = character
        -- A friend shield extends the spawn protection; write it back so RunLifecycle and Home agree.
        if d.protectedUntil > numberAttribute(character, "SpawnProtectionEndsAt", 0) then
            character:SetAttribute("SpawnProtectionEndsAt", d.protectedUntil)
        end
        character:SetAttribute("CombatClass", d.class)
        character:SetAttribute("CombatPeaceful", d.peaceful)
        character:SetAttribute("HpByte", Cfg.HpByteMax)
        d.hpSentByte, d.hpSentAt = Cfg.HpByteMax, now
        local list = {}
        connections[character] = list
        local lastScore = d.score
        table.insert(list, character:GetAttributeChangedSignal("GrowthScore"):Connect(function()
            local score = numberAttribute(character, "GrowthScore", 0)
            Rules.setScore(world, d.key, score)
            if score > lastScore then Rules.foodHeal(world, d.key) end -- eating heals 5% (docs/101 s4)
            lastScore = score
        end))
        table.insert(list, character:GetAttributeChangedSignal("RunState"):Connect(function()
            if character:GetAttribute("RunState") ~= "Active" then leave(character) end
        end))
    end

    function api.addNpc(key: string, model: Model)
        api.npcs[key] = model
        characterOf[key] = model
    end
    function api.removeNpc(key: string)
        api.npcs[key] = nil
        characterOf[key] = nil
        Rules.leave(world, key)
    end

    world.onDefeat = function(victim, attacker, bonuses)
        -- Exactly once per (userId, runId): CombatState fires the defeat once and settle() flips Defeated -> Settled once.
        if not Rules.settle(world, victim.key) then return end
        if api.npcs[victim.key] then
            -- A wild predator was defeated (BD-245/BD-313): no run, no eggs, no catches, no crystals. Only a SMALL growth bonus
            -- (5% of each killer's own growth, split by damage share, once per NPC slot per 120 s, a few per 5 minutes).
            local now = workspace:GetServerTimeNow()
            local growthOf, userOf, assisters = {}, {}, {}
            for _, assister in TeamUp.assisters(victim.ledger, victim.state.maxHp, now) do
                local d = world.dinos[assister.id]
                local c = characterOf[assister.id]
                if d and c and not api.npcs[assister.id] and c:GetAttribute("RunState") == "Active" and not d.peaceful then
                    growthOf[assister.id], userOf[assister.id] = numberAttribute(c, "GrowthScore", 0), d.userId
                    table.insert(assisters, assister)
                end
            end
            for key, amount in NpcRules.growthRewards(api.npcRewards, victim.userId, assisters, growthOf, userOf, now) do
                local c = characterOf[key]
                if c and amount > 0 then dinosaur.addGrowth(c, amount) end
            end
            if api.onNpcDefeated then api.onNpcDefeated(victim.key) end
            return
        end
        local character = characterOf[victim.key]
        local player = Players:GetPlayerByUserId(victim.userId)
        if character and player and player.Character == character and character:GetAttribute("RunId") == victim.runId then
            character:SetAttribute("HpByte", 0)
            -- Same idempotent path as "Eaten"/"ManualExit"/"Death": Active -> Ending once, settlement keyed by runId.
            -- The victim keeps every run egg, crystal and nest earned so far; nothing moves to the attackers.
            runLifecycle.tryEnd(player, character, "Defeated", if typeof(attacker.userId) == "number" then attacker.userId else nil) -- a wild predator has no user id
        end
        for key, amount in bonuses do
            local c = characterOf[key]
            if c and not api.npcs[key] and c:GetAttribute("RunState") == "Active" and amount > 0 then
                dinosaur.addGrowth(c, amount) -- server-minted assist growth, capped by CombatTeamUp (no eggs, no catches)
            end
        end
    end

    remote.OnServerEvent:Connect(function(player: Player, ...)
        if select("#", ...) ~= 0 then return end -- the client never sends a target or damage
        if player:GetAttribute("ProfileState") ~= "Loaded" or player:GetAttribute("MovementSecurityStatus") == "REJECTED" then return end
        local character = player.Character
        local key = if character then tracked[character] else nil
        local humanoid = if character then character:FindFirstChildOfClass("Humanoid") else nil
        local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
        if not character or not key or not humanoid or humanoid.Health <= 0 or not root or not root:IsA("BasePart")
            or not runLifecycle.isActive(character) then return end
        local now = workspace:GetServerTimeNow()
        -- BD-354: refuse a bite that is still on cooldown BEFORE the O(players) candidate scan (GetExtentsSize per model);
        -- otherwise one client spamming the remote makes the server do that scan on every request.
        local biter = Rules.get(world, key)
        if biter and now - biter.lastBiteAt < Cfg.BiteCooldownSeconds then player:SetAttribute("LastBiteStatus", "cooldown") return end
        local candidates = {}
        for other, otherKey in tracked do
            local otherRoot = if other ~= character and other.Parent then other:FindFirstChild("HumanoidRootPart") else nil
            if otherRoot and otherRoot:IsA("BasePart") then
                table.insert(candidates, {key = otherKey, pos = otherRoot.Position, radius = radiusOf(other)})
            end
        end
        for npcKey, npcModel in api.npcs do -- wild predators are bite targets too (BD-245)
            local npcRoot = if npcModel.Parent then npcModel:FindFirstChild("HumanoidRootPart") else nil
            if npcRoot and npcRoot:IsA("BasePart") then table.insert(candidates, {key = npcKey, pos = npcRoot.Position, radius = radiusOf(npcModel)}) end
        end
        local leaping = now < numberAttribute(character, "LeapUntil", 0)
        local result = Rules.attack(world, key, now, root.Position, root.CFrame.LookVector, candidates, leaping, radiusOf(character))
        player:SetAttribute("LastBiteStatus", result.reason)
        if not result.ok then return end
        biteMemory.mark(player.UserId, "bite", now)
        character:SetAttribute("BiteSeq", numberAttribute(character, "BiteSeq", 0) + 1) -- BD-079 lunge cue (same as predation)
        local target = characterOf[result.targetKey]
        if not target then return end
        target:SetAttribute("HitSeq", numberAttribute(target, "HitSeq", 0) + 1)
        target:SetAttribute("HitByUserId", player.UserId)
        local byte = Rules.pendingHpByte(world, result.targetKey, now)
        if byte then target:SetAttribute("HpByte", byte) end
        -- Soft knockback: a short planar nudge (<= KnockbackStuds, inside MovementGuardBurstStuds), only onto clear
        -- ground inside the arena; a server CFrame write, never a physics impulse (docs/101 s4, s13).
        local targetRoot = if not result.defeated and not api.npcs[result.targetKey] then target:FindFirstChild("HumanoidRootPart") else nil
        if targetRoot and targetRoot:IsA("BasePart") then
            local push = Vector3.new(result.knockX, 0, result.knockZ)
            local half = Config.ArenaHalfWidth
            local destination = targetRoot.Position + push
            if math.abs(destination.X) <= half and math.abs(destination.Z) <= half
                and workspace:Raycast(targetRoot.Position, push, params) == nil then
                targetRoot.CFrame = targetRoot.CFrame + push
            end
        end
    end)

    local accumulator = 0
    RunService.Heartbeat:Connect(function(dt)
        accumulator += dt
        if accumulator < 1 / Cfg.TickHz then return end
        local step = accumulator
        accumulator = 0
        local now = workspace:GetServerTimeNow()
        Rules.tick(world, now, step)
        for character, key in tracked do
            if not character.Parent then
                leave(character)
            else
                local byte = Rules.pendingHpByte(world, key, now)
                if byte then character:SetAttribute("HpByte", byte) end
            end
        end
    end)

    local function watch(player: Player)
        local function onCharacter(character: Model)
            character:GetAttributeChangedSignal("RunState"):Connect(function()
                if character:GetAttribute("RunState") == "Active" then join(player, character) end
            end)
            if character:GetAttribute("RunState") == "Active" then join(player, character) end
        end
        player.CharacterAdded:Connect(onCharacter)
        if player.Character then onCharacter(player.Character) end
    end
    Players.PlayerAdded:Connect(watch)
    for _, player in Players:GetPlayers() do watch(player) end
    Players.PlayerRemoving:Connect(function(player)
        if player.Character then leave(player.Character) end
    end)
    return api
end

return CombatService
