--!strict
-- BD-289 (docs/104 s7.6): pure rules for the "walk there" moss trail. With Settings "Teleport to shops" OFF a rail button
-- draws a soft dotted trail from the player to the station along the layout paths. route() follows CaveHubLayout.paths and
-- stations as waypoints (shortest flat path, never through the lava keep-out); dots() spaces at most MaxDots points along
-- it; update() is the 25 s life + fade + arrival timing. No Instances, no requires: pass the layout in. Coordinates in and
-- out are WORLD x, z (layout z + layout.CenterZ). HubGuideClient draws it; tools/verify_hub_walk_there.py runs this file.
local Rules = {}
Rules.MaxDots = 24 -- pooled parts cap
Rules.MinSpacing = 4 -- studs between dots on a short trail
Rules.LifeSeconds = 25
Rules.FadeInSeconds = 0.4
Rules.FadeOutSeconds = 1.5 -- end of life
Rules.ArriveFadeSeconds = 0.6 -- after the player reaches the pad
Rules.LavaMargin = 5 -- studs beyond the pool radius that a trail leg may never cross (the rim rocks sit at radius + 2)
Rules.NearPathLimit = 40 -- a start farther than this from every path is refused (the player is not in the cave)

local function finite(n: any): boolean return typeof(n) == "number" and n == n and n ~= math.huge and n ~= -math.huge end
local function dist(ax: number, az: number, bx: number, bz: number): number return math.sqrt((ax - bx) ^ 2 + (az - bz) ^ 2) end

-- Does the segment a->b pass within `r` of the circle centre c? (local coords)
local function hitsCircle(ax: number, az: number, bx: number, bz: number, cx: number, cz: number, r: number): boolean
    local dx, dz = bx - ax, bz - az
    local len2 = dx * dx + dz * dz
    local t = if len2 > 0 then math.clamp(((cx - ax) * dx + (cz - az) * dz) / len2, 0, 1) else 0
    return dist(ax + dx * t, az + dz * t, cx, cz) < r
end
Rules.hitsCircle = hitsCircle

-- The walkable graph from the layout: nodes = station centres (flat pads), edges = star and ring paths between them.
local function graph(layout: any): ({[string]: any}, {any})
    local nodes: {[string]: any} = {}
    for _, s in layout.get().stations do nodes[s.id] = {x = s.x, z = s.z, r = s.r} end
    local edges = {}
    for _, p in layout.get().paths do
        local a: string?, b: string? = nil, nil
        local starId = string.match(p.id, "^star_(.+)$") -- star_<id> joins the heart to <id>
        if starId then
            a, b = "heart", starId
        else
            a, b = string.match(p.id, "^ring_([^_]+)_(.+)$")
        end
        if a and b and nodes[a] and nodes[b] then edges[#edges + 1] = {a = a, b = b, width = p.width} end
    end
    return nodes, edges
end
Rules.graph = graph

-- route(layout, worldX, worldZ, stationId) -> {points = {{x, z}...}, length} | nil, reason
-- reasons: "bad_input", "no_station", "here" (already on that pad: just open it), "outside" (not near any path).
function Rules.route(layout: any, wx: any, wz: any, stationId: any): (any?, string?)
    if not finite(wx) or not finite(wz) or typeof(stationId) ~= "string" then return nil, "bad_input" end
    local nodes, edges = graph(layout)
    local target = nodes[stationId]
    if target == nil then return nil, "no_station" end
    local px, pz = wx :: number, (wz :: number) - layout.CenterZ
    if dist(px, pz, target.x, target.z) <= target.r then return nil, "here" end
    local pool = layout.Pool
    local keep = pool.r + Rules.LavaMargin

    -- nearest flat attachment: the player's projection onto an edge, whose straight leg avoids the lava keep-out
    local best: any = nil
    for _, e in edges do
        local A, B = nodes[e.a], nodes[e.b]
        local dx, dz = B.x - A.x, B.z - A.z
        local len2 = dx * dx + dz * dz
        local t = math.clamp(((px - A.x) * dx + (pz - A.z) * dz) / len2, 0, 1)
        local qx, qz = A.x + dx * t, A.z + dz * t
        local d = dist(px, pz, qx, qz)
        if d <= Rules.NearPathLimit and (best == nil or d < best.d) and not hitsCircle(px, pz, qx, qz, pool.x, pool.z, keep) then
            best = {d = d, e = e, qx = qx, qz = qz}
        end
    end
    if best == nil then return nil, "outside" end

    -- Dijkstra over station nodes plus Q (the attachment point, splitting its edge into two)
    local adj: {[string]: {{to: string, w: number}}} = {}
    local function link(u: string, v: string, w: number)
        adj[u] = adj[u] or {}
        adj[v] = adj[v] or {}
        table.insert(adj[u], {to = v, w = w})
        table.insert(adj[v], {to = u, w = w})
    end
    for _, e in edges do
        if e ~= best.e then link(e.a, e.b, dist(nodes[e.a].x, nodes[e.a].z, nodes[e.b].x, nodes[e.b].z)) end
    end
    local A, B = nodes[best.e.a], nodes[best.e.b]
    link("Q", best.e.a, dist(best.qx, best.qz, A.x, A.z))
    link("Q", best.e.b, dist(best.qx, best.qz, B.x, B.z))
    local cost: {[string]: number} = {Q = 0}
    local prev: {[string]: string} = {}
    local done: {[string]: boolean} = {}
    while true do
        local u: string? = nil
        for id, c in cost do
            if not done[id] and (u == nil or c < cost[u]) then u = id end
        end
        if u == nil or u == stationId then break end
        done[u] = true
        for _, edge in adj[u] or {} do
            local c = cost[u] + edge.w
            if cost[edge.to] == nil or c < cost[edge.to] then cost[edge.to], prev[edge.to] = c, u end
        end
    end
    if cost[stationId] == nil then return nil, "outside" end

    local chain = {stationId}
    while chain[1] ~= "Q" do table.insert(chain, 1, prev[chain[1]]) end
    local pts = {{x = px, z = pz}}
    for _, id in chain do
        local node = if id == "Q" then {x = best.qx, z = best.qz} else nodes[id]
        local x, z = node.x, node.z
        local last = pts[#pts]
        if dist(last.x, last.z, x, z) > 0.01 then pts[#pts + 1] = {x = x, z = z} end
    end
    local length = 0
    for i = 1, #pts do
        if i > 1 then length += dist(pts[i - 1].x, pts[i - 1].z, pts[i].x, pts[i].z) end
    end
    local world = {}
    for i, p in pts do world[i] = {x = p.x, z = p.z + layout.CenterZ} end
    return {points = world, length = length}, nil
end

-- dots(points, cap) -> {{x, z}...} evenly spaced along the polyline, first at the start, last at the end; at most
-- min(cap, MaxDots) points, never closer together than MinSpacing unless the cap forces it.
function Rules.dots(points: any, cap: any): {any}
    local out = {}
    if typeof(points) ~= "table" or #points == 0 then return out end
    local limit = math.clamp(if finite(cap) then math.floor(cap :: number) else Rules.MaxDots, 1, Rules.MaxDots)
    local length = 0
    for i = 2, #points do length += dist(points[i - 1].x, points[i - 1].z, points[i].x, points[i].z) end
    if length < 0.01 or limit == 1 then return {{x = points[#points].x, z = points[#points].z}} end
    local count = math.min(limit, math.max(2, math.floor(length / Rules.MinSpacing) + 1))
    local step = length / (count - 1)
    local seg, walked = 1, 0
    for k = 0, count - 1 do
        local want = if k == count - 1 then length else k * step
        while seg < #points - 1 do
            local segLen = dist(points[seg].x, points[seg].z, points[seg + 1].x, points[seg + 1].z)
            if walked + segLen >= want then break end
            walked += segLen
            seg += 1
        end
        local a, b = points[seg], points[seg + 1]
        local segLen = dist(a.x, a.z, b.x, b.z)
        local t = if segLen > 0 then math.clamp((want - walked) / segLen, 0, 1) else 0
        out[#out + 1] = {x = a.x + (b.x - a.x) * t, z = a.z + (b.z - a.z) * t}
    end
    return out
end

-- ---- timing. state = {station, born, ended}; calm = Reduce Motion (static dots: no fade in or out, no pulse; they just go).
function Rules.begin(station: string, now: number): any return {station = station, born = now, ended = nil} end

-- One tick. `pad` = the menu station whose pad the player stands on (or nil). Returns alpha 0..1 and finished.
function Rules.update(state: any, now: number, pad: string?, calm: boolean): (number, boolean)
    if state.ended == nil and pad == state.station then state.ended = now end
    local age = now - state.born
    local gone = age >= Rules.LifeSeconds
    local fadeOut = if calm then 0 else Rules.ArriveFadeSeconds
    if state.ended ~= nil and now - state.ended >= fadeOut then gone = true end
    if gone then return 0, true end
    if calm then return 1, false end
    local alpha = math.clamp(age / Rules.FadeInSeconds, 0, 1)
    alpha = math.min(alpha, math.clamp((Rules.LifeSeconds - age) / Rules.FadeOutSeconds, 0, 1))
    if state.ended ~= nil then alpha = math.min(alpha, 1 - (now - state.ended) / Rules.ArriveFadeSeconds) end
    return math.clamp(alpha, 0, 1), false
end

-- BD-396: one pulse loops every PulseSeconds (1.2 s) and travels along the trail toward the station (dot 1 = nearest the player),
-- twice per trail so a long path shows more than one. Exactly 1 (static) when calm (Reduce Motion).
Rules.PulseSeconds = 1.2
local function wave(index: number, count: number, now: number): number
    return 0.5 + 0.5 * math.sin(2 * math.pi * (now / Rules.PulseSeconds - 2 * index / math.max(count, 1)))
end
-- Gentle size ripple that travels along the trail; exactly 1 (static) when calm.
function Rules.pulse(index: number, count: number, now: number, calm: boolean): number
    if calm or count <= 0 then return 1 end
    return 1 + 0.2 * (2 * wave(index, count, now) - 1)
end
-- Glow strength 0..1 for the soft halo behind a dot: always visible (0.55 floor, daylight), brightest on the pulse crest.
-- Calm: a steady 0.8.
function Rules.glow(index: number, count: number, now: number, calm: boolean): number
    if calm or count <= 0 then return 0.8 end
    return 0.55 + 0.45 * wave(index, count, now)
end

-- BD-396: look of one dot, in studs and 0..1 factors (the client draws it; tests pin it). Moss-green ring with a white core
-- and a soft halo; bigger than BD-289 so it reads in daylight.
Rules.Look = {dotSize = 1.8, haloScale = 2.6, coreScale = 0.42, brightness = 1.6, haloTransparency = 0.72, lightEmission = 0.6}

-- Edge-of-screen arrow for an off-screen station. sx, sy = WorldToViewportPoint result (pixels), depth = its z (negative
-- means behind the camera), vw, vh = viewport size, margin = distance kept from the edge. Returns
-- {visible, x, y, angle} (x, y = arrow centre in pixels, angle = degrees clockwise from "up"). Visible only when the station
-- is NOT on screen.
function Rules.edgeArrow(sx: any, sy: any, depth: any, vw: any, vh: any, margin: any): any
    if not (finite(sx) and finite(sy) and finite(depth) and finite(vw) and finite(vh)) or (vw :: number) <= 0 or (vh :: number) <= 0 then
        return {visible = false, x = 0, y = 0, angle = 0}
    end
    local m = if finite(margin) then margin :: number else 40
    local w, h = vw :: number, vh :: number
    local x, y = sx :: number, sy :: number
    if (depth :: number) < 0 then x, y = w - x, h - y end -- behind the camera: the projection is mirrored
    if (depth :: number) >= 0 and x >= 0 and x <= w and y >= 0 and y <= h then return {visible = false, x = x, y = y, angle = 0} end
    local cx, cy = w / 2, h / 2
    local dx, dy = x - cx, y - cy
    if math.abs(dx) < 1e-6 and math.abs(dy) < 1e-6 then dy = 1 end
    local tx = if dx ~= 0 then ((w / 2 - m) / math.abs(dx)) else math.huge
    local ty = if dy ~= 0 then ((h / 2 - m) / math.abs(dy)) else math.huge
    local t = math.min(tx, ty)
    return {visible = true, x = cx + dx * t, y = cy + dy * t, angle = math.deg(math.atan2(dx, -dy))}
end

return Rules
