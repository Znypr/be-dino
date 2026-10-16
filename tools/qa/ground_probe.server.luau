--!nocheck
-- BD-409 GROUNDING probe (docs/114 s8.1 item 4). Run with execute_luau (Server, Play mode) in YOUR OWN temp Studio copy.
-- Cave: set Config.CaveHub = true in the copy first (the folder is found automatically). Output is parsed by
-- tools/qa/ground_report.py (save the returned text to a file). Terrain raycast from above at the centre and four points
-- around the footprint; SUNK = highest terrain under the footprint minus the prop's lowest corner; FLOAT = lowest corner minus
-- the highest terrain hit. FLOAT 0.3 (BD-417, was 0.5). Plants use the same footprint as the placement (PropGround.footprintRadius).
local SUNK, FLOAT = 0.3, 0.3
-- Props that are placed off the floor on purpose (ceiling / wall / basin pieces): not a floor-grounding question.
local SKIP = {cave_stalactite = true, cave_moss_hang = true, cave_stepping_stone = true}
local rp = RaycastParams.new()
rp.FilterType, rp.FilterDescendantsInstances = Enum.RaycastFilterType.Include, {workspace.Terrain}
local function lowest(mesh)
    local cf, s, lo = mesh.CFrame, mesh.Size / 2, math.huge
    for _, sx in {-1, 1} do for _, sy in {-1, 1} do for _, sz in {-1, 1} do
        lo = math.min(lo, (cf * Vector3.new(sx * s.X, sy * s.Y, sz * s.Z)).Y)
    end end end
    return lo
end
local function probe(container, label, up, len)
    local stat, worst, n, lying = {}, {}, 0, 0
    for _, m in container:GetDescendants() do
        local mesh = if m:IsA("Model") then m:FindFirstChildWhichIsA("MeshPart") elseif m:IsA("MeshPart") and not (m.Parent and m.Parent:IsA("Model")) then m else nil
        if mesh and not m.Name:find("Collider") and not SKIP[m.Name] then
            do
                n += 1
                local p = if m:IsA("Model") then m:GetPivot().Position else m.Position
                -- trunk-sized footprint for plants (like the placement rule); rocks and landmarks: centre only, and they are meant to
                -- sit RockSink (12% of the height) in the ground, so their sunk tolerance is larger. Lying logs are skipped (reported LYING).
                local solid = m.Name:find("boulder") or m.Name:find("rocks_") or m.Name:find("landmark") or m.Name:find("rock_") or m.Name:find("cave_") or m.Name:find("hub_")
                local rocky = solid and not label:find("cave") -- island rocks: footprint sampled, compared to the LOWEST ground under them (they sit on the low side by design)
                local r = if rocky then math.min(6, 0.3 * math.max(mesh.Size.X, mesh.Size.Z)) elseif solid then 0 else math.min(1.0, 0.04 * math.max(mesh.Size.X, mesh.Size.Z))
                local tolSunk = SUNK + (if solid and not label:find("cave") then 0.12 * mesh.Size.Y else 0)
                if math.abs(mesh.CFrame.UpVector.Y) < 0.7 then lying += 1 continue end
                local hi, lo, found = -math.huge, math.huge, 0
                local bottom = lowest(mesh)
                -- island: from 80 studs above the pivot; cave: from just above the prop's bottom (the roof is above, never hit)
                local y0 = if up then bottom + up else p.Y + 80
                for _, o in {{0, 0}, {r, 0}, {-r, 0}, {0, r}, {0, -r}} do
                    local hit = workspace:Raycast(Vector3.new(p.X + o[1], y0, p.Z + o[2]), Vector3.new(0, -(len or 200), 0), rp)
                    if hit then hi = math.max(hi, hit.Position.Y) lo = math.min(lo, hit.Position.Y) found += 1 end
                end
                if found > 0 then
                    local ref = if rocky then lo else hi
                    local sunk, float = ref - bottom, bottom - ref
                    local s = stat[m.Name] or {n = 0, sunk = 0, float = 0, worstSunk = 0, worstFloat = 0}
                    stat[m.Name] = s
                    s.n += 1
                    if sunk > tolSunk then s.sunk += 1 s.worstSunk = math.max(s.worstSunk, sunk) end
                    if float > FLOAT then s.float += 1 s.worstFloat = math.max(s.worstFloat, float) end
                    if sunk > tolSunk or float > FLOAT then
                        table.insert(worst, {sunk > tolSunk and sunk or -float, m.Name, p.X, p.Z})
                    end
                end
            end
        end
    end
    table.sort(worst, function(a, b) return math.abs(a[1]) > math.abs(b[1]) end)
    local out = {string.format("PLACE\t%s\t%d\t%d", label, n, lying)}
    for k, s in stat do
        table.insert(out, string.format("KIND\t%s\t%s\t%d\t%d\t%d\t%.2f\t%.2f", label, k, s.n, s.sunk, s.float, s.worstSunk, s.worstFloat))
    end
    for i = 1, math.min(15, #worst) do
        local w = worst[i]
        table.insert(out, string.format("WORST\t%s\t%s\t%.2f\t%.1f\t%.1f", label, w[2], w[1], w[3], w[4]))
    end
    return out
end
local lines = {}
local arena = workspace:FindFirstChild("BeDinoArena")
local kit = arena and arena:FindFirstChild("WorldKit")
if kit then for _, l in probe(kit, "island") do table.insert(lines, l) end end
local sanct = arena and arena:FindFirstChild("Sanctuary")
local caveProps = sanct and sanct:FindFirstChild("CaveProps")
if caveProps then for _, l in probe(caveProps, "cave", 6, 40) do table.insert(lines, l) end end
return table.concat(lines, "\n")
