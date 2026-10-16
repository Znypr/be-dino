--!nocheck
-- BD-413 BUDGET probe (docs/107, handbook 8.1 item 8). Run with execute_luau (Server, Play mode) in YOUR OWN temp Studio copy (CaveHub = true).
-- Counts BaseParts, MeshParts, lights and particle emitters per place. Triangles are not readable in Studio from a script: the offline
-- tools/verify_world_budget.py estimates them; this probe measures the REAL part / light / emitter numbers.
-- Row: BUD <place> <baseParts> <meshParts> <lights> <emitters> <enabledEmitters>
local function count(root)
    local parts, meshes, lights, em, emOn = 0, 0, 0, 0, 0
    for _, d in root:GetDescendants() do
        if d:IsA("BasePart") then
            parts += 1
            if d:IsA("MeshPart") then meshes += 1 end
        elseif d:IsA("PointLight") or d:IsA("SpotLight") or d:IsA("SurfaceLight") then
            if d.Enabled then lights += 1 end
        elseif d:IsA("ParticleEmitter") then
            em += 1
            if d.Enabled then emOn += 1 end
        end
    end
    return parts, meshes, lights, em, emOn
end
local lines = {}
local arena = workspace:FindFirstChild("BeDinoArena")
local function row(name, root)
    if root then
        local p, m, l, e, eo = count(root)
        table.insert(lines, string.format("BUD\t%s\t%d\t%d\t%d\t%d\t%d", name, p, m, l, e, eo))
    end
end
row("island_world_kit", arena and arena:FindFirstChild("WorldKit"))
row("cave_hub", arena and arena:FindFirstChild("Sanctuary"))
row("workspace_total", workspace)
return table.concat(lines, "\n")
