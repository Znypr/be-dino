--!strict
-- BD-498 (docs/150): the world as StreamingEnabled wants it. INERT while workspace.StreamingEnabled is false (today's shipped profiles), so nothing changes.
-- With streaming on, every Model of the arena (island props, the cave hub, its lights and stations) is Persistent: it is sent at join and never streamed out.
-- What streams by distance is then only what is not in a Model: the 3,573 food pickups, the loose prop colliders, the crystal pickups and the Terrain voxels.
-- (Default models would arrive as EMPTY shells whose parts stream in later, which breaks every script that reads a prop's parts once: docs/150 s4.)
local StreamingSetup = {}

function StreamingSetup.start()
    if not workspace.StreamingEnabled then return end
    local arena = workspace:FindFirstChild("BeDinoArena")
    if not arena then return end
    local function persist(item: Instance)
        if item:IsA("Model") then item.ModelStreamingMode = Enum.ModelStreamingMode.Persistent end
    end
    for _, item in arena:GetDescendants() do persist(item) end
    arena.DescendantAdded:Connect(persist) -- the cave props and lights are built after Arena.build()
end

return StreamingSetup
