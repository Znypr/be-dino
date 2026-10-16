--!strict
-- BD-360: client cache of the owner-only values (docs/112). Same shape the UI already used with Player attributes:
-- get/num/str read a value, onChanged(name, fn) replaces GetAttributeChangedSignal. PUBLIC names still come from the
-- Player attributes, so UI code can call one getter for both. Before the first snapshot every read gives nil/0/"" and
-- isReady() is false, which is what the screens already treat as "not loaded yet".
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Core = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("PrivateStateCore"))

local PrivateState = {}
local player = Players.LocalPlayer
local cache = Core.newCache()
local listeners: {[string]: {[number]: (any) -> ()}} = {}
local anyListeners: {[number]: (string) -> ()} = {}
local nextId = 0
local remote: RemoteEvent? = nil

local function connection(bucket: {[number]: any}, fn: any)
    nextId += 1
    local id = nextId
    bucket[id] = fn
    return {Disconnect = function() bucket[id] = nil end}
end

function PrivateState.isReady(): boolean return cache.received end

function PrivateState.get(name: string): any
    if Core.isPrivate(name) then return cache.values[name] end
    return player:GetAttribute(name)
end

function PrivateState.num(name: string): number
    local value = PrivateState.get(name)
    return if typeof(value) == "number" then value else 0
end

function PrivateState.str(name: string, fallback: string?): string
    local value = PrivateState.get(name)
    return if typeof(value) == "string" then value else (fallback or "")
end

-- fn(value) runs after every change of name, for private and public names alike.
function PrivateState.onChanged(name: string, fn: (any) -> ())
    if not Core.isPrivate(name) then
        return player:GetAttributeChangedSignal(name):Connect(function() fn(player:GetAttribute(name)) end)
    end
    local bucket = listeners[name]
    if not bucket then bucket = {}; listeners[name] = bucket end
    return connection(bucket, fn)
end

-- fn(name) runs for every private change (used by the diagnostics line and the tests).
function PrivateState.onAnyChanged(fn: (string) -> ())
    return connection(anyListeners, fn)
end

local function fire(names: {string})
    for _, name in names do
        local value = cache.values[name]
        local bucket = listeners[name]
        if bucket then
            for _, fn in table.clone(bucket) do
                local ok, err = pcall(fn, value)
                if not ok then warn("[Be Dino] PrivateState listener failed for " .. name .. ": " .. tostring(err)) end
            end
        end
        for _, fn in table.clone(anyListeners) do pcall(fn, name) end
    end
end

-- Used by the receiver and by tests: apply one server message.
function PrivateState.receive(message: any)
    local changed, problem = Core.apply(cache, message)
    if problem == "gap" then
        local target = remote
        if target then target:FireServer("resync") end
        return
    end
    fire(changed)
end

task.spawn(function()
    local folder = ReplicatedStorage:WaitForChild("BeDinoRemotes", 30)
    local event = if folder then folder:WaitForChild("PrivateState", 30) else nil
    if not event or not event:IsA("RemoteEvent") then
        warn("[Be Dino] PrivateState remote not found: owner-only data will not load")
        return
    end
    remote = event
    event.OnClientEvent:Connect(PrivateState.receive)
    for _ = 1, 15 do -- hello until the first snapshot arrived (the server answers at once)
        if cache.received then return end
        event:FireServer("hello")
        task.wait(2)
    end
end)

return PrivateState
