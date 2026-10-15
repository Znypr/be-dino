--!strict
-- BD-210: tell the server when this client's own copy of the island terrain around the run spawn is loaded. The
-- character's physics runs on this client, so a run that starts before the local terrain arrives drops the dinosaur
-- straight through the world. The server waits for this (RunLifecycle.worldReady, with a timeout fallback).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Layout = require(Shared:WaitForChild("IslandLayout"))
local remotes = ReplicatedStorage:WaitForChild("BeDinoRemotes")
local remote = remotes:WaitForChild("ClientWorldReady") :: RemoteEvent

local params = RaycastParams.new()
params.FilterType = Enum.RaycastFilterType.Include
params.FilterDescendantsInstances = {workspace.Terrain}
local function terrainLoaded(): boolean
    -- 5x5 grid, 48 studs wide, around the run spawn: every ray must land on terrain near the authored height.
    for dx = -24, 24, 12 do
        for dz = -24, 24, 12 do
            local x, z = dx, Layout.SpawnZ + dz
            local expected = Layout.height(x, z)
            local hit = workspace:Raycast(Vector3.new(x, expected + 40, z), Vector3.new(0, -80, 0), params)
            if not hit or math.abs(hit.Position.Y - expected) > 4 then return false end
        end
    end
    return true
end

while workspace:GetAttribute("IslandTerrainReady") ~= true or not terrainLoaded() do task.wait(.25) end
task.wait(.5) -- one more beat for collision of the neighbouring voxel chunks
remote:FireServer()
