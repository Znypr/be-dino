--!strict
-- BD-254: the Sanctuary's decoration table (pure data, no Instances). Offsets are relative to the hub centre (x, dz) on the
-- floor (SpawnGeometry.HubFloorY). Arena.build turns each row into one anchored, non-colliding part: real generated meshes
-- only (statue / nest / egg keys of WorldGeneratedMeshes, so no invented ids), existing kit ids for bushes and flowers.
-- width = the longest horizontal side in studs the mesh is fitted to.
local Decor = {}
Decor.Keys = {statue = "landmark_dino_statue", nest = "nest", egg = "food_egg"}
Decor.KitBush, Decor.KitFlower = "world_bush_a", "world_flowers_a"
Decor.PartBudget = 150 -- BD-168: the whole Sanctuary (ground, fences, sign, decoration) stays under this
Decor.FixedParts = 12 -- ground, apron, 4 soft rim slabs, plaza, 4 hidden fences (the sign is counted in Decor.Extras)
Decor.Extras = 1 + 5 + 2 -- sign, five stepping stones, two trees
Decor.Plaza = {halfX = 17, halfZ = 15} -- NestPlaza footprint (spawn stands on it): kept clear
Decor.Inner = {halfX = 44, halfZ = 39} -- hedge ring sits at the fences; everything else stays inside this
Decor.NestXs = {-12, -6, 0, 6, 12}
Decor.NestDz = 20
Decor.EggNests = {1, 2, 3, 5} -- nest indices that hold an egg
Decor.Statue = {x = -30, dz = -4, width = 14, yaw = math.rad(40)}
function Decor.layout(): {{kind: string, x: number, dz: number, width: number, yaw: number, nest: number?}}
    local rows = {}
    local function add(kind: string, x: number, dz: number, width: number, yaw: number, nest: number?)
        table.insert(rows, {kind = kind, x = x, dz = dz, width = width, yaw = yaw, nest = nest})
    end
    add("statue", Decor.Statue.x, Decor.Statue.dz, Decor.Statue.width, Decor.Statue.yaw)
    for i, x in Decor.NestXs do add("nest", x, Decor.NestDz, 5.2, i * 1.3) end
    for _, i in Decor.EggNests do add("egg", Decor.NestXs[i], Decor.NestDz, 2.4, i * 2.1, i) end
    -- Soft hedge ring just inside the (now invisible) fences, a gap on the side of the sign so the sign stays readable.
    for i = 0, 7 do
        local x = -42 + i * 12
        add("bush", x, -37, 6 + (i % 3), i * 1.7)
        if math.abs(x) > 14 then add("bush", x, 37, 6 + ((i + 1) % 3), i * 2.3) end
    end
    for i = 0, 5 do
        local dz = -26 + i * 12
        add("bush", -43, dz, 6 + (i % 3), i * 0.9)
        add("bush", 43, dz, 6 + ((i + 2) % 3), i * 1.4)
    end
    -- Flower patches around the nests, the statue and the plaza edge.
    for _, f in {{-30, 6}, {-26, -12}, {-35, 4}, {-20, -2}, {20, -8}, {24, 6}, {30, -2}, {-22, 26}, {22, 26}, {-18, 31}, {18, 31}, {0, -24}, {-8, -26}, {8, -26}} do
        add("flower", f[1], f[2], 2.2, f[1] + f[2])
    end
    return rows
end
-- Stepping stones (primitive flat discs) from the plaza toward the nests; positions only.
function Decor.stones(): {{x: number, dz: number}}
    local out = {}
    for i = 1, 5 do table.insert(out, {x = (i - 3) * 2.2, dz = 16 + i * 0.1 - 0.5}) end
    return out
end
function Decor.partCount(): number
    return #Decor.layout() + Decor.FixedParts + Decor.Extras
end
function Decor.count(kind: string): number
    local n = 0
    for _, row in Decor.layout() do if row.kind == kind then n += 1 end end
    return n
end
return Decor
