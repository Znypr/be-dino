--!strict
-- BD-360: server side of the owner-only state channel (docs/112). set/get replace Player:SetAttribute/GetAttribute for the
-- PRIVATE names in Shared/PrivateStateCore. Values live only in server memory; the owner gets one snapshot when its client
-- says hello and then deltas, coalesced for Core.CoalesceSeconds. Nobody else ever receives them.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Core = require(ReplicatedStorage.Shared.PrivateStateCore)

local PrivateState = {}
local buffers: {[Player]: Core.Buffer} = setmetatable({}, {__mode = "k"}) :: any
local remote: RemoteEvent? = nil
local stats = {snapshots = 0, deltas = 0, bytes = 0}
PrivateState.stats = stats

local function bufferOf(player: Player): Core.Buffer
    local buffer = buffers[player]
    if not buffer then
        buffer = Core.newBuffer()
        buffers[player] = buffer
    end
    return buffer
end

local function send(player: Player, message: any)
    local target = remote
    if not target then return end
    stats.bytes += Core.bytes(message)
    target:FireClient(player, message)
end

function PrivateState.flush(player: Player)
    local buffer = buffers[player]
    if not buffer then return end
    buffer.scheduled = false
    if not buffer.ready then return end -- the client has not said hello yet: the snapshot will carry everything
    local message = Core.deltaMessage(buffer)
    if message then
        stats.deltas += 1
        send(player, message)
    end
end

function PrivateState.sendSnapshot(player: Player)
    local buffer = bufferOf(player)
    buffer.ready = true
    stats.snapshots += 1
    send(player, Core.snapshotMessage(buffer))
end

function PrivateState.set(player: Player, name: string, value: any)
    assert(Core.isPrivate(name), "PrivateState.set: not a private name: " .. tostring(name))
    local buffer = bufferOf(player)
    if not Core.set(buffer, name, value) then return end
    if buffer.ready and not buffer.scheduled then
        buffer.scheduled = true
        task.delay(Core.CoalesceSeconds, PrivateState.flush, player)
    end
end

function PrivateState.get(player: Player, name: string): any
    local buffer = buffers[player]
    return if buffer then buffer.values[name] else nil
end

-- A copy of everything held for the player (tests and the admin size probe).
function PrivateState.snapshot(player: Player): {[string]: any}
    local buffer = buffers[player]
    return if buffer then table.clone(buffer.values) else {}
end

function PrivateState.forget(player: Player)
    buffers[player] = nil
end

function PrivateState.start()
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes") :: Folder?
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end
    local event = Instance.new("RemoteEvent")
    event.Name = "PrivateState"
    event.Parent = folder
    remote = event
    -- hello = "I am listening": sent once per client start and again whenever a delta was missed. A rejoin is a new
    -- client, so it says hello again and receives the full snapshot.
    local lastHello: {[Player]: number} = setmetatable({}, {__mode = "k"}) :: any
    event.OnServerEvent:Connect(function(player: Player)
        local now = os.clock()
        if now - (lastHello[player] or -math.huge) < 0.5 then return end
        lastHello[player] = now
        PrivateState.sendSnapshot(player)
    end)
    Players.PlayerRemoving:Connect(function(player: Player)
        local buffer = buffers[player]
        if buffer then buffer.ready = false end -- stop sending; the values stay readable until release
    end)
end

return PrivateState
