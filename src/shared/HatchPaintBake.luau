--!strict
-- BD-397 (docs/114): PURE pixel maths of the two-coat paint reveal on the hatch egg. No Roblox APIs (tools/verify_hatch_v2.py).
-- The egg texture is ONE EditableImage (size x size, under the docs/105 byte budget) that client/HatchEggV2 rewrites a few times
-- per second while a coat runs: every texel knows (from the egg's position map, LowPolyPattern.rasterize, or its UV as a
-- fallback) the second at which the base coat and the accent coat reach it (Bake.revealMap, from HatchV2Plan splats and
-- drips), so compositing at a coat time t is a per-texel lerp: cream shell -> base colour (coat 1) -> accent colour where the
-- gene pattern mask says so (coat 2). Facet shading of the source texture is kept (Bake.shade), the fresh paint front gets a
-- thin bright wet edge. Deterministic: same inputs -> same bytes.
local Plan = require(script.Parent.HatchV2Plan)
local Bake = {}

-- Per-texel shading factor from the egg's own texture (luminance over the mean body luminance, clamped so paint stays readable).
-- src = RGBA buffer (size x size). nil src -> flat shading (every factor 1).
function Bake.shade(src: buffer?, size: number): {number}
    local n = size * size
    local out = table.create(n, 1)
    if not src then return out end
    local sum, count = 0, 0
    local lum = table.create(n, 1)
    for i = 0, n - 1 do
        local o = i * 4
        local l = (.299 * buffer.readu8(src, o) + .587 * buffer.readu8(src, o + 1) + .114 * buffer.readu8(src, o + 2)) / 255
        lum[i + 1] = l
        if buffer.readu8(src, o + 3) > 0 then sum += l count += 1 end
    end
    local mean = if count > 0 then math.max(.05, sum / count) else 1
    for i = 1, n do out[i] = math.clamp(lum[i] / mean, .55, 1.25) end
    return out
end

-- Model-space position of texel i (1-based) from the position map (alpha 255 = covered) or, without a map, from its UV: u -> x,
-- v -> y (top row = top of the egg), z = 0. Returns x, y, z.
local function position(posmap: buffer?, i: number, size: number): (number, number, number)
    if posmap then
        local o = (i - 1) * 4
        if buffer.readu8(posmap, o + 3) == 255 then
            return buffer.readu8(posmap, o) / 127.5 - 1, buffer.readu8(posmap, o + 1) / 127.5 - 1, buffer.readu8(posmap, o + 2) / 127.5 - 1
        end
    end
    local x, y = (i - 1) % size, (i - 1) // size
    return (x + .5) / size * 2 - 1, 1 - (y + .5) / size * 2, 0
end
Bake.position = position

-- Reveal time (seconds after the coat's impact) per texel for one coat. side -1 left / +1 right, coat 1 / 2.
function Bake.revealMap(size: number, posmap: buffer?, seed: number, side: number, coat: number, onRow: ((number) -> ())?): {number}
    local splats = Plan.splats(seed, side, coat)
    local drips = Plan.drips3(seed, splats, coat)
    local span = Plan.Coat.span
    local n = size * size
    local out = table.create(n, span)
    for i = 1, n do
        if onRow and (i - 1) % size == 0 then onRow((i - 1) // size) end
        local x, y, z = position(posmap, i, size)
        out[i] = Plan.revealTime(x, y, z, splats, drips, span)
    end
    return out
end

-- Composite at coat times t1 (base) and t2 (accent), seconds after each impact (negative = not started, large = finished).
-- shade: Bake.shade; mask: pattern weights 0..1 (LowPolyPattern.compute) or nil (plain egg: the accent paints nothing);
-- cream / base / accent are {r, g, b} 0..1. Writes RGBA into `out` (alpha 255). onRow lets the runtime yield.
function Bake.composite(size: number, shade: {number}, mask: {number}?, map1: {number}, map2: {number}, t1: number, t2: number,
    cream: {number}, base: {number}, accent: {number}, out: buffer, onRow: ((number) -> ())?)
    local cr, cg, cb = cream[1], cream[2], cream[3]
    local br, bg, bb = base[1], base[2], base[3]
    local ar, ag, ab = accent[1], accent[2], accent[3]
    for y = 0, size - 1 do
        if onRow then onRow(y) end
        for x = 0, size - 1 do
            local i = y * size + x + 1
            local k = shade[i]
            local a1 = Plan.coatAlpha(map1[i], t1)
            local a2 = if mask then Plan.coatAlpha(map2[i], t2) * mask[i] else 0
            local r, g, b = cr, cg, cb
            r, g, b = r + (br - r) * a1, g + (bg - g) * a1, b + (bb - b) * a1
            r, g, b = r + (ar - r) * a2, g + (ag - g) * a2, b + (ab - b) * a2
            local edge = .2 * Plan.wetEdge(a1) + .2 * Plan.wetEdge(if mask and mask[i] > .5 then Plan.coatAlpha(map2[i], t2) else 0)
            r, g, b = r * k + edge, g * k + edge, b * k + edge
            local o = (i - 1) * 4
            buffer.writeu8(out, o, math.clamp(math.floor(r * 255 + .5), 0, 255))
            buffer.writeu8(out, o + 1, math.clamp(math.floor(g * 255 + .5), 0, 255))
            buffer.writeu8(out, o + 2, math.clamp(math.floor(b * 255 + .5), 0, 255))
            buffer.writeu8(out, o + 3, 255)
        end
    end
end

-- Share of texels fully painted (alpha >= .999) at coat time t: the verifier's coverage curve.
function Bake.coverage(map: {number}, t: number): number
    local n, hit = #map, 0
    for i = 1, n do if Plan.coatAlpha(map[i], t) >= .999 then hit += 1 end end
    return if n > 0 then hit / n else 0
end

-- Accent paint share at a texel: what the accent coat may ever reach (the pattern mask), used by tests and the pattern chip.
function Bake.accentShare(mask: {number}?): number
    if not mask then return 0 end
    local s = 0
    for _, m in mask do s += m end
    return s / math.max(1, #mask)
end

-- Cache key of a bake: everything that changes the bytes.
function Bake.key(seed: number, size: number, patternId: string?, blend: number, primary: string, secondary: string, hasPos: boolean): string
    return string.format("%d|%d|%s|%d|%s|%s|%s", seed, size, patternId or "01_blank", math.floor(blend + .5), primary, secondary, if hasPos then "3d" else "uv")
end

return Bake
