--!strict
-- BD-225 / BD-061: pure pattern masks for the low-poly dino bakes. No Roblox APIs (tools/verify_lowpoly_patterns.py).
-- The generated low-poly parts have one UV island PER FACET and no hand-authored pattern data, so a pattern computed in UV space
-- is chopped into a jigsaw at every facet edge. The mask is therefore PROCEDURAL IN 3D: the runtime rasterises each part's mesh
-- triangles into UV space once (EditableMesh, LowPolyTexture), giving every texel its model-space position (Pattern.rasterize,
-- a u8 position map), and the pattern is a 3D function of that position (spots are spheres, stripes are planes), so it flows
-- across facets and across parts. When the position map is unavailable the same ids fall back to the UV-space masks (Pattern.mask).
-- Same gene pattern ids as PatternGenes (EggGenetics.Patterns), two gene colours, deterministic from (species, part, pattern id).
-- The mask is only ever applied where LowPolyRecolor.bodyWeight > 0,
-- so eyes, claws and the cream belly are never painted; and the share of secondary colour follows genes.blend exactly like
-- PatternGenes (quantile threshold over the body pixels), so same-family genes still show lighter/darker regions.
-- Look (docs/87): calm, bubbly, readable at preview size: medium features (spots about 20 px of 256), soft 2 px edges,
-- no high-frequency noise, so flat low-poly facets still read as facets.
local Pattern = {}
Pattern.Size = 256
Pattern.Soft = 0.04 -- width (in mask units) of the soft edge between primary and secondary colour
Pattern.Ids = {"01_blank", "02_emerald_islands", "03_round_spots", "04_bold_patches", "05_horizontal_bands", "06_wavy_stripes",
    "07_diamond_scales", "08_freckles"}
-- deterministic 32-bit string hash (FNV-1a) so a species/part gets its own offsets; same inputs -> same mask forever.
function Pattern.seed(text: string): number
    local h = 2166136261
    for i = 1, #text do
        h = bit32.bxor(h, string.byte(text, i))
        h = bit32.band(h * 16777619, 0xFFFFFFFF)
    end
    return h
end
local function hash2(ix: number, iy: number, seed: number): number
    local h = bit32.band(ix * 374761393 + iy * 668265263 + seed * 1274126177, 0xFFFFFFFF)
    h = bit32.band(bit32.bxor(h, bit32.rshift(h, 13)) * 1274126177, 0xFFFFFFFF)
    h = bit32.bxor(h, bit32.rshift(h, 16))
    return (h % 65536) / 65535
end
local function smooth(t: number): number return t * t * (3 - 2 * t) end
-- value noise on a lattice of `cell` px, tiling at 256 so UV island edges wrap without a hard seam
local function noise(x: number, y: number, cell: number, seed: number): number
    local n = Pattern.Size / cell
    local fx, fy = x / cell, y / cell
    local ix, iy = math.floor(fx), math.floor(fy)
    local tx, ty = smooth(fx - ix), smooth(fy - iy)
    local function at(dx: number, dy: number) return hash2((ix + dx) % n, (iy + dy) % n, seed) end
    local a = at(0, 0) + (at(1, 0) - at(0, 0)) * tx
    local b = at(0, 1) + (at(1, 1) - at(0, 1)) * tx
    return a + (b - a) * ty
end
-- jittered dot grid: 1 at a dot centre, falling off continuously to the cell edge, so the blend quantile sets the dot SIZE
-- (a small share of secondary colour = small dots, a large share = big blobs) instead of hitting a hard 0 floor
local function dots(x: number, y: number, cell: number, reach: number, seed: number): number
    local best = 0
    local cx, cy = math.floor(x / cell), math.floor(y / cell)
    local n = Pattern.Size / cell
    for dy = -1, 1 do
        for dx = -1, 1 do
            local gx, gy = cx + dx, cy + dy
            local jx, jy = hash2(gx % n, gy % n, seed), hash2(gx % n, gy % n, seed + 77)
            local px, py = (gx + 0.3 + 0.4 * jx) * cell, (gy + 0.3 + 0.4 * jy) * cell
            local d = math.sqrt((x + 0.5 - px) ^ 2 + (y + 0.5 - py) ^ 2)
            local v = (1 - math.min(1, d / reach)) ^ 1.5
            if v > best then best = v end
        end
    end
    return best
end
local function tri(v: number): number local f = v - math.floor(v) return 1 - math.abs(f * 2 - 1) end
-- mask value 0..1 ("how much secondary colour") at texel (x, y) for a pattern id and seed. Unknown id / blank -> 0.
function Pattern.mask(id: string, x: number, y: number, seed: number): number
    if id == "02_emerald_islands" then
        return noise(x + seed % 64, y, 64, seed) * 0.7 + noise(x, y + seed % 32, 32, seed + 3) * 0.3
    elseif id == "03_round_spots" then
        return dots(x, y, 32, 26, seed)
    elseif id == "04_bold_patches" then
        return noise(x, y, 32, seed + 9) * 0.6 + noise(x, y, 16, seed + 11) * 0.4
    elseif id == "05_horizontal_bands" then
        local wobble = noise(x, y, 64, seed + 5) * 6
        return smooth(tri((y + wobble + seed % 36) / 36))
    elseif id == "06_wavy_stripes" then
        local wave = math.sin((y + seed % 256) / 256 * math.pi * 6) * 8
        return smooth(tri((x + wave + seed % 28) / 28))
    elseif id == "07_diamond_scales" then
        local p = 32
        local sx, sy = (x + seed % p) % p, (y + seed % p) % p
        local d = math.abs(sx - p / 2) + math.abs(sy - p / 2)
        return d / p -- diamond scales: centres primary, the outline toward the edges takes the secondary colour
    elseif id == "08_freckles" then
        return dots(x, y, 16, 12, seed + 21) * (0.55 + 0.45 * hash2(math.floor(x / 16), math.floor(y / 16), seed + 23))
    end
    return 0
end
-- 3D value noise on a lattice of `cell` model units (positions are normalised: the model's longest side is 1.0)
local function noise3(x: number, y: number, z: number, cell: number, seed: number): number
    local fx, fy, fz = x / cell + 64, y / cell + 64, z / cell + 64
    local ix, iy, iz = math.floor(fx), math.floor(fy), math.floor(fz)
    local tx, ty, tz = smooth(fx - ix), smooth(fy - iy), smooth(fz - iz)
    local function at(dx: number, dy: number, dz: number) return hash2(ix + dx + (iz + dz) * 131, iy + dy, seed) end
    local function lerp(a: number, b: number, t: number) return a + (b - a) * t end
    local c00 = lerp(at(0, 0, 0), at(1, 0, 0), tx)
    local c10 = lerp(at(0, 1, 0), at(1, 1, 0), tx)
    local c01 = lerp(at(0, 0, 1), at(1, 0, 1), tx)
    local c11 = lerp(at(0, 1, 1), at(1, 1, 1), tx)
    return lerp(lerp(c00, c10, ty), lerp(c01, c11, ty), tz)
end
-- 3D jittered sphere grid: 1 at a centre, falling off to the cell edge (so the blend quantile sets the spot size)
local function dots3(x: number, y: number, z: number, cell: number, seed: number): number
    local best = 0
    local cx, cy, cz = math.floor(x / cell + 64), math.floor(y / cell + 64), math.floor(z / cell + 64)
    for dz = -1, 1 do for dy = -1, 1 do for dx = -1, 1 do
        local gx, gy, gz = cx + dx, cy + dy, cz + dz
        local jx, jy, jz = hash2(gx + gz * 131, gy, seed), hash2(gx + gz * 131, gy, seed + 77), hash2(gx + gz * 131, gy, seed + 151)
        local px, py, pz = (gx - 64 + 0.25 + 0.5 * jx) * cell, (gy - 64 + 0.25 + 0.5 * jy) * cell, (gz - 64 + 0.25 + 0.5 * jz) * cell
        local d = math.sqrt((x - px) ^ 2 + (y - py) ^ 2 + (z - pz) ^ 2)
        local v = (1 - math.min(1, d / (cell * 0.8))) ^ 1.5
        if v > best then best = v end
    end end end
    return best
end
-- mask value 0..1 at a model-space position (normalised, longest side = 1, y up, -z forward). Feature sizes are fractions of
-- the dino's length so a Compy and a T-Rex carry the same number of spots.
function Pattern.mask3(id: string, x: number, y: number, z: number, seed: number): number
    if id == "02_emerald_islands" then
        return noise3(x, y, z, 0.26, seed) * 0.7 + noise3(x, y, z, 0.13, seed + 3) * 0.3
    elseif id == "03_round_spots" then
        return dots3(x, y, z, 0.17, seed)
    elseif id == "04_bold_patches" then
        return noise3(x, y, z, 0.16, seed + 9) * 0.6 + noise3(x, y, z, 0.08, seed + 11) * 0.4
    elseif id == "05_horizontal_bands" then
        local wobble = (noise3(x, y, z, 0.3, seed + 5) - 0.5) * 0.04
        return smooth(tri((y + wobble) / 0.14))
    elseif id == "06_wavy_stripes" then
        local wave = math.sin(y * math.pi * 7) * 0.03
        return smooth(tri((z + wave + x * 0.15) / 0.12))
    elseif id == "07_diamond_scales" then
        -- BD-307: STAGGERED plump scales in the side view (y, z), like fish/reptile scales: every other row is shifted by half a
        -- scale and each scale is a rounded diamond (exponent 1.6), so the flanks read as overlapping scales with the secondary
        -- colour as the rim between them (the blend sets the rim thickness). The old version was a square lattice (zigzag look).
        -- Each texel belongs to the NEAREST scale centre among its own row and the two staggered neighbour rows (a scale lattice
        -- with no gaps), so the mask rises evenly toward every scale boundary: the quantile then paints a continuous outline of
        -- the chosen thickness instead of corner blobs.
        local p = 0.11               -- scale length along the body
        local h = p * 0.72           -- row height (rows overlap like scales)
        local yy, zz = y + 64 * p, z + 64 * p
        local row = math.floor(yy / h)
        local best = 2
        for dr = -1, 1 do
            local r = row + dr
            local off = if r % 2 == 1 then p / 2 else 0
            local cy = yy - (r + 0.5) * h
            local cz = (zz + off) % p - p / 2
            local d = (math.abs(cz) / (p / 2)) ^ 1.6 + (math.abs(cy) / (h * 0.62)) ^ 1.6
            if d < best then best = d end
        end
        return math.clamp(best, 0, 1)
    elseif id == "08_freckles" then
        return dots3(x, y, z, 0.07, seed + 21) * (0.55 + 0.45 * noise3(x, y, z, 0.2, seed + 23))
    end
    return 0
end
-- Position map: 4 bytes per texel (x, y, z quantised 0..255 over -1..1, covered 0/255) at Pattern.Size. tris = flat array of
-- {u1,v1,x1,y1,z1, u2,v2,x2,y2,z2, u3,v3,x3,y3,z3} with u,v in 0..1 (v = 0 at the TOP row) and positions normalised.
-- Pure rasteriser (barycentric), then one dilation pass so facet edges have no uncovered seam texels.
function Pattern.rasterize(tris: {{number}}, size: number?): buffer
    local size = size or Pattern.Size
    local map = buffer.create(size * size * 4)
    local function put(x: number, y: number, px: number, py: number, pz: number)
        local o = (y * size + x) * 4
        buffer.writeu8(map, o, math.clamp(math.floor((px + 1) * 127.5 + 0.5), 0, 255))
        buffer.writeu8(map, o + 1, math.clamp(math.floor((py + 1) * 127.5 + 0.5), 0, 255))
        buffer.writeu8(map, o + 2, math.clamp(math.floor((pz + 1) * 127.5 + 0.5), 0, 255))
        buffer.writeu8(map, o + 3, 255)
    end
    for _, t in tris do
        local x1, y1, x2, y2, x3, y3 = t[1] * size, t[2] * size, t[6] * size, t[7] * size, t[11] * size, t[12] * size
        local det = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        if math.abs(det) < 1e-9 then continue end
        local minX, maxX = math.max(0, math.floor(math.min(x1, x2, x3))), math.min(size - 1, math.ceil(math.max(x1, x2, x3)))
        local minY, maxY = math.max(0, math.floor(math.min(y1, y2, y3))), math.min(size - 1, math.ceil(math.max(y1, y2, y3)))
        for y = minY, maxY do
            local cy = y + 0.5
            for x = minX, maxX do
                local cx = x + 0.5
                local l2 = ((cx - x1) * (y3 - y1) - (x3 - x1) * (cy - y1)) / det
                local l3 = ((x2 - x1) * (cy - y1) - (cx - x1) * (y2 - y1)) / det
                local l1 = 1 - l2 - l3
                if l1 >= -0.002 and l2 >= -0.002 and l3 >= -0.002 then
                    put(x, y, l1 * t[3] + l2 * t[8] + l3 * t[13], l1 * t[4] + l2 * t[9] + l3 * t[14], l1 * t[5] + l2 * t[10] + l3 * t[15])
                end
            end
        end
    end
    local copy = buffer.create(size * size * 4)
    buffer.copy(copy, 0, map)
    local around = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}}
    for y = 0, size - 1 do
        for x = 0, size - 1 do
            local o = (y * size + x) * 4
            if buffer.readu8(copy, o + 3) == 0 then
                for _, d in around do
                    local nx, ny = x + d[1], y + d[2]
                    if nx >= 0 and nx < size and ny >= 0 and ny < size then
                        local no = (ny * size + nx) * 4
                        if buffer.readu8(copy, no + 3) == 255 then buffer.copy(map, o, copy, no, 4) break end
                    end
                end
            end
        end
    end
    return map
end
-- Quantile threshold (PatternGenes' rule): primaryShare (0..1, genes.blend/100) of the body pixels stay primary. hist[i+1] counts
-- body pixels with mask quantised to i (0..254). Returns the mask level (0..1) above which a pixel takes the secondary colour.
function Pattern.threshold(hist: {number}, count: number, primaryShare: number): number
    local target = math.floor(count * math.clamp(primaryShare, 0, 1))
    local cumulative = 0
    for rank = 0, 254 do
        cumulative += hist[rank + 1]
        if cumulative >= target then return (rank + 0.5) / 255 end
    end
    return 1
end
-- BD-307 coverage curve: the share of the body the SECONDARY colour may cover, per pattern, from genes.blend (primaryShare =
-- blend / 100). Spot-like patterns are capped so a low blend never turns spots into big blobs (the dot masks are continuous,
-- so the quantile would otherwise just grow every spot); area patterns (islands, patches, bands, stripes) follow the blend
-- directly, as PatternGenes does. Returns the effective PRIMARY share handed to the quantile. Pure, monotonic in primaryShare.
Pattern.Coverage = {
    ["03_round_spots"] = {scale = 0.55, min = 0.05, max = 0.28},
    ["08_freckles"] = {scale = 0.40, min = 0.04, max = 0.20},
    ["07_diamond_scales"] = {scale = 0.50, min = 0.10, max = 0.30},
}
function Pattern.coverage(id: string, primaryShare: number): number
    local s = math.clamp(primaryShare, 0, 1)
    local rule = (Pattern.Coverage :: any)[id]
    if not rule then return s end
    return 1 - math.clamp((1 - s) * rule.scale, rule.min, rule.max)
end
-- Full mask for one part: array of secondary-colour weights (0 primary .. 1 secondary, fractional only in a soft edge
-- Pattern.Soft wide around the cut so facets do not show pixel stairs), computed only for pixels whose bodyWeight > 0.
-- weights: array (1-based, size*size) of body weights 0..1. Pure so the verifier can run it on a synthetic texture.
-- onRow (optional) is called after every row so the runtime bake can yield (task.wait) and never stall a frame; pure tests pass nil.
-- posmap (optional, from Pattern.rasterize at the same size): texels it covers use the 3D mask; others (and no map) use the UV mask.
-- size (optional, default Pattern.Size): the texture side; the UV-space masks are scaled so a 128 px limb bake shows the same
-- features as a 256 px body bake (BD-306).
function Pattern.compute(id: string, seed: number, weights: {number}, primaryShare: number, same: boolean, onRow: ((number) -> ())?, posmap: buffer?, size: number?): {number}
    local size = size or Pattern.Size
    local n = size * size
    local out = table.create(n, 0)
    if id == "01_blank" or table.find(Pattern.Ids, id) == nil then return out end
    local raw = table.create(n, 0)
    local hist = table.create(255, 0)
    local count = 0
    local uvScale = Pattern.Size / size
    for y = 0, size - 1 do
        if onRow then onRow(y) end
        for x = 0, size - 1 do
            local i = y * size + x + 1
            if weights[i] > 0 then
                local m
                local o = (i - 1) * 4
                if posmap and buffer.readu8(posmap, o + 3) == 255 then
                    m = Pattern.mask3(id, buffer.readu8(posmap, o) / 127.5 - 1, buffer.readu8(posmap, o + 1) / 127.5 - 1, buffer.readu8(posmap, o + 2) / 127.5 - 1, seed)
                else m = Pattern.mask(id, x * uvScale, y * uvScale, seed) end
                m = math.clamp(m, 0, 1)
                raw[i] = m
                hist[math.floor(m * 254 + 0.5) + 1] += 1
                count += 1
            end
        end
    end
    if count == 0 then return out end
    local share = Pattern.coverage(id, if same then 0.5 else primaryShare)
    local cut = Pattern.threshold(hist, count, share)
    local soft = Pattern.Soft
    for i = 1, n do
        if weights[i] > 0 then out[i] = math.clamp((raw[i] - cut) / soft + 0.5, 0, 1) end
    end
    return out
end
return Pattern
