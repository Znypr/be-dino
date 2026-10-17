--!strict
-- BD-253 camera occlusion for decorative world props (docs/87 "readable at a glance"). PURE logic, numbers only (no Roblox
-- types) so tools/verify_camera_occlusion.py can run it offline. The client driver is src/client/CameraOcclusion.client.luau.
-- A prop qualifies when the camera->dino segment passes through its bounding ellipsoid, or the camera is inside/very near
-- it (leaves in the lens). Qualifying props fade to FadeTransparency and restore when clear. The caller only ever feeds it
-- WorldKit props, never the dino, food, eggs, colliders or UI.
local M = {}

M.FadeTransparency = 0.8 -- target LocalTransparencyModifier (owner brief: 0.7 to 0.85)
M.FadeRate = 9 -- 1/seconds; about 0.25 s to settle
M.MaxProps = 8 -- props faded at once
M.MaxParts = 40 -- parts touched at once (hard cap across the faded props)
M.CellSize = 32 -- spatial grid cell, studs
M.MaxRange = 100 -- ignore everything when the camera is farther than this from the dino (cinematics). BD-513: must stay above CameraFraming.MaxDistance (90) so the biggest dino's default camera still fades props
M.Shrink = 0.7 -- fraction of the bounding ellipsoid that counts (canopy corners are mostly empty air)
M.CameraPad = 3 -- studs: the camera counts as "inside" a prop this close to its ellipsoid
M.MinRadius = 1.2 -- horizontal half-extent below this is ground cover (grass, flowers, pebbles): never fades
M.MinHeight = 1.5 -- props flatter than this are ground cover
M.TargetEnd = 0.97 -- only the part of the segment before the dino counts (props behind the dino stay solid)
M.SnapEpsilon = 0.01

-- Closest approach of the segment a->b (clamped to t in [0, tEnd]) to the scaled centre, in ellipsoid-normalised space.
-- Returns the normalised distance (1 = on the ellipsoid surface) and t.
local function normalisedDistance(cx: number, cy: number, cz: number, rh: number, hv: number,
    ax: number, ay: number, az: number, bx: number, by: number, bz: number, tEnd: number): (number, number)
    local ky = rh / hv -- squash the vertical axis so the ellipsoid becomes a sphere of radius rh
    local dx, dy, dz = bx - ax, (by - ay) * ky, bz - az
    local px, py, pz = ax - cx, (ay - cy) * ky, az - cz
    local len2 = dx * dx + dy * dy + dz * dz
    local t = 0
    if len2 > 1e-9 then t = math.clamp(-(px * dx + py * dy + pz * dz) / len2, 0, tEnd) end
    local qx, qy, qz = px + dx * t, py + dy * t, pz + dz * t
    return math.sqrt(qx * qx + qy * qy + qz * qz) / rh, t
end
M.normalisedDistance = normalisedDistance

-- prop = {x,y,z (bounding-box centre), sx,sy,sz (full extents)}. Returns the camera distance (sort key) when the prop
-- should be faded, else nil.
function M.qualifies(prop: {x: number, y: number, z: number, sx: number, sy: number, sz: number},
    cam: {x: number, y: number, z: number}, target: {x: number, y: number, z: number}): number?
    local rh = math.max(prop.sx, prop.sz) / 2
    local hv = prop.sy / 2
    if rh < M.MinRadius or prop.sy < M.MinHeight or hv <= 0 then return nil end
    local camDist = math.sqrt((cam.x - target.x) ^ 2 + (cam.y - target.y) ^ 2 + (cam.z - target.z) ^ 2)
    if camDist ~= camDist or camDist > M.MaxRange then return nil end
    local n = normalisedDistance(prop.x, prop.y, prop.z, rh, hv, cam.x, cam.y, cam.z, target.x, target.y, target.z, M.TargetEnd)
    local toCam = normalisedDistance(prop.x, prop.y, prop.z, rh, hv, cam.x, cam.y, cam.z, cam.x, cam.y, cam.z, 0)
    if n < M.Shrink or toCam < 1 + M.CameraPad / rh then
        return math.sqrt((cam.x - prop.x) ^ 2 + (cam.y - prop.y) ^ 2 + (cam.z - prop.z) ^ 2)
    end
    return nil
end

-- Smooth fade step. Reduce Motion: no animation, the value jumps straight to the target. Returns the new value; a value
-- within SnapEpsilon of the target snaps to it exactly (so a restored prop is exactly 0 and can be dropped).
function M.step(current: number, target: number, dt: number, reduceMotion: boolean): number
    if reduceMotion or dt ~= dt or dt >= 1 then return target end
    if dt <= 0 then return current end
    local nextValue = current + (target - current) * (1 - math.exp(-M.FadeRate * dt))
    if math.abs(nextValue - target) < M.SnapEpsilon then return target end
    return nextValue
end

-- Spatial grid keyed by cell: props register in every cell their horizontal extent overlaps.
function M.newGrid(): {[string]: {number}}
    return {}
end
local function cell(v: number): number return math.floor(v / M.CellSize) end
function M.insert(grid: {[string]: {number}}, id: number, x: number, z: number, rh: number)
    for cx = cell(x - rh), cell(x + rh) do
        for cz = cell(z - rh), cell(z + rh) do
            local key = cx .. "," .. cz
            local list = grid[key]
            if not list then list = {} grid[key] = list end
            table.insert(list, id)
        end
    end
end
-- Ids registered in the cells covering the segment's horizontal bounding box (duplicates removed, deterministic order).
function M.query(grid: {[string]: {number}}, ax: number, az: number, bx: number, bz: number, out: {number}): {number}
    table.clear(out)
    local seen: {[number]: boolean} = {}
    for cx = cell(math.min(ax, bx)), cell(math.max(ax, bx)) do
        for cz = cell(math.min(az, bz)), cell(math.max(az, bz)) do
            local list = grid[cx .. "," .. cz]
            if list then
                for _, id in list do
                    if not seen[id] then seen[id] = true table.insert(out, id) end
                end
            end
        end
    end
    return out
end

-- Pick at most MaxProps / MaxParts of the qualifying candidates, nearest the camera first (those fill the lens).
-- candidates = {{id=, dist=, parts=}}; returns the chosen ids.
function M.select(candidates: {{id: number, dist: number, parts: number}}): {number}
    table.sort(candidates, function(a, b)
        if a.dist ~= b.dist then return a.dist < b.dist end
        return a.id < b.id
    end)
    local chosen, parts = {}, 0
    for _, c in candidates do
        if #chosen >= M.MaxProps then break end
        if parts + c.parts <= M.MaxParts then
            parts += c.parts
            table.insert(chosen, c.id)
        end
    end
    return chosen
end

return M
