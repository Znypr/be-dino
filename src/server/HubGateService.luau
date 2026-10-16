--!strict
-- BD-290 / BD-291 (docs/104 s2.3, s9): the thin server side of the Cave hub Island Gate and the hub-only HubDinos collision
-- group. start() does NOTHING unless Config.CaveHub is true (it ships false: no connection, no collision group, no change).
-- All decisions live in the pure CaveGateRules; this file only reads the character, ticks, and applies the answers:
--   * gate: a Sanctuary player who stands in the arch zone for 1.5 s starts the run through RunLifecycle.requestStart, the
--     very function the RequestStartRun remote calls (so there is no second start path, and begin() stays exactly-once);
--   * collisions: characters at home inside the cave join HubDinos (does not collide with itself); they get their own group
--     back as soon as a run starts or they leave the hub.
local Players = game:GetService("Players")
local PhysicsService = game:GetService("PhysicsService")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local Rules = require(ReplicatedStorage.Shared.CaveGateRules)
local SpawnGeometry = require(ReplicatedStorage.Shared.SpawnGeometry)
local RunLifecycle = require(script.Parent.RunLifecycle)
local HubGateService = {}
HubGateService.TickSeconds = 0.1
local sessions: {[Player]: any} = {}
local originals: {[BasePart]: string} = {} -- part -> the group it had before HubDinos (weak keys: parts die with the character)
setmetatable(originals :: any, {__mode = "k"})

local function gather(player: Player): any
    local character = player.Character
    local humanoid = if character then character:FindFirstChildOfClass("Humanoid") else nil
    local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
    local x, y, z = nil, nil, nil
    local inHub = false
    if root and root:IsA("BasePart") then
        local p = root.Position
        x, y, z = p.X, p.Y, p.Z
        inHub = p.X == p.X and p.Z == p.Z and SpawnGeometry.inHub(Config, p.X, p.Z)
    end
    return {
        caveHub = Config.CaveHub == true, profileState = player:GetAttribute("ProfileState"),
        runState = if character then character:GetAttribute("RunState") else nil,
        dinoAttached = character ~= nil and character:GetAttribute("DinoAttached") == true,
        alive = humanoid ~= nil and humanoid.Health > 0, inHub = inHub, x = x, y = y, z = z,
    }, character
end

local function applyGroup(character: Model, group: string?)
    for _, item in character:GetDescendants() do
        if item:IsA("BasePart") then
            if group ~= nil then
                if item.CollisionGroup ~= group then
                    if originals[item] == nil then originals[item] = item.CollisionGroup end
                    item.CollisionGroup = group
                end
            else
                local was = originals[item]
                if was ~= nil then
                    originals[item] = nil
                    item.CollisionGroup = was
                end
            end
        end
    end
end

-- One player, one tick. `now` is os.clock(). Exposed for the Studio check.
function HubGateService.tick(player: Player, now: number)
    local state, character = gather(player)
    if character == nil then return end
    local session = sessions[player]
    if not session then
        session = Rules.newSession()
        session.scanAt, session.group = -math.huge, nil
        sessions[player] = session
    end
    local group = Rules.groupFor(state)
    -- Re-scan when the wanted group changes, and once a second so parts added later (a new dino model) follow too.
    if group ~= session.group or now - session.scanAt >= 1 then
        session.group, session.scanAt = group, now
        applyGroup(character, group)
    end
    local inside = Rules.inZone(state.x, state.z, state.y)
    local _, fire = Rules.step(session, inside, Rules.eligible(state), now)
    if fire then
        local started = RunLifecycle.requestStart(player)
        if not started then Rules.retry(session, now) end
    end
end

function HubGateService.start()
    if Config.CaveHub ~= true then return end -- flag off: no group, no connection, nothing observable changes
    if not PhysicsService:IsCollisionGroupRegistered(Rules.GroupName) then PhysicsService:RegisterCollisionGroup(Rules.GroupName) end
    PhysicsService:CollisionGroupSetCollidable(Rules.GroupName, Rules.GroupName, false)
    Players.PlayerRemoving:Connect(function(player) sessions[player] = nil end)
    local sinceTick = 0
    RunService.Heartbeat:Connect(function(dt)
        sinceTick += dt
        if sinceTick < HubGateService.TickSeconds then return end
        sinceTick = 0
        local now = os.clock()
        for _, player in Players:GetPlayers() do
            local ran = pcall(HubGateService.tick, player, now)
            if not ran then sessions[player] = nil end
        end
    end)
end

return HubGateService
