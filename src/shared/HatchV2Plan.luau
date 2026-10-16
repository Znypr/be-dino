--!strict
-- BD-397 hatch redesign (docs/114): the PURE beat sheet, bucket / paint / drip physics and the paint-reveal maths of the v2
-- hatch. No Roblox APIs, no time source (tools/verify_hatch_v2.py). Behind Config.HatchV2 (false): nothing here runs for the
-- shipped sequence. HatchTimeline reads Plan.Build / Plan.paintPlan() for the v2 state machine; client/HatchEggV2 draws it.
-- Units: seconds; "studs" are the viewport scene (egg height = Plan.EggHeight); "px" are hatch-panel pixels (824 x 402);
-- model space is the egg normalised to its longest side = 1 (y up), the same space LowPolyPattern.mask3 uses.
local Plan = {}

-- ---------------------------------------------------------------- beat sheet (full motion). Calm (docs/87): nothing snaps.
Plan.Build = 6.7 -- seconds from Open to the burst (v1: 3.6). Tap once after the first 0.5 s fast-forwards to the burst.
-- One bucket window (seconds since the bucket's start): arrives from its side, hovers, tips, pours, tips back, leaves.
Plan.Bucket = {arrive = 0, hover = .45, tip = .5, pour = .65, impact = .8, pourEnd = 1.15, untilt = 1.35, leave = 1.7}
Plan.Left, Plan.Right = .4, 2.5       -- bucket window starts (left = base colour, right = accent colour on the pattern)
Plan.Coat = {span = 1.0, soft = .14}  -- one coat floods the whole egg in `span` s after its impact; `soft` s fade per texel
Plan.Drips = {delay = .3, span = 1.1} -- 2D drip streaks after an impact
Plan.PatternWash = .4                 -- the pattern chip pops while the accent coat dries
Plan.Condition = {delay = .4, span = .4} -- condition overlay (cracks, dirt, stars) fades in after the pattern chip
Plan.CracksMin = 1.2                  -- rattle + cracks get at least this long before the burst
Plan.Gloss = {peak = .28, rise = .15, dry = 1.6} -- wet paint shines, then dries matte (docs/87: matte final look)

function Plan.paintPlan()
    local b = Plan.Bucket
    local leftImpact, rightImpact = Plan.Left + b.impact, Plan.Right + b.impact
    local patternAt = Plan.Right + b.leave + .1
    local patternEnd = patternAt + Plan.PatternWash
    local endsAt = patternEnd + Plan.Condition.delay + Plan.Condition.span
    return {leftStart = Plan.Left, leftImpact = leftImpact, leftEnd = Plan.Left + b.leave,
        rightStart = Plan.Right, rightImpact = rightImpact, rightEnd = Plan.Right + b.leave,
        patternAt = patternAt, patternEnd = patternEnd, endsAt = endsAt,
        window = b.leave, wash = Plan.Coat.span, patternWash = Plan.PatternWash, v2 = true}
end
-- Reduce Motion: no buckets, no drips, no squash; the finished egg is shown at once (same as v1 Reduced), chips in order.
Plan.Reduced = {build = 0, chipGap = .3}

-- ---------------------------------------------------------------- scene (viewport)
Plan.EggHeight = 2.4      -- studs
Plan.BucketHeight = 1.35  -- studs (PLACEHOLDER barrel until the bucket mesh exists)
Plan.BucketX = 2.75       -- studs from the egg centre (= HatchTimeline.BucketX 265 px at the camera below)
Plan.BucketY = .45        -- hover height above the egg centre (Studio pass 1: .8 swung the tipping bucket above the panel edge)
Plan.Camera = {fov = 30, distance = 7.8, dir = {.32, .22, 1}, eggPx = {412, 130}} -- egg centre lands on HatchFxPlan.Center.egg
Plan.ScreenHeightPx = 402
Plan.ScreenWidthPx = 824

local function clamp01(x: number): number return math.clamp(x, 0, 1) end
local function easeOut(x: number): number local u = 1 - clamp01(x) return 1 - u * u * u end
local function easeInOut(x: number): number x = clamp01(x) return x * x * (3 - 2 * x) end
local function backOut(x: number): number
    x = clamp01(x)
    local c1, c3 = 1.2, 2.2
    return 1 + c3 * (x - 1) ^ 3 + c1 * (x - 1) ^ 2
end
Plan.easeOut, Plan.easeInOut, Plan.backOut = easeOut, easeInOut, backOut

-- Deterministic hashing (same egg id -> same splats forever).
function Plan.seed(text: string): number
    local h = 2166136261
    for i = 1, #text do
        h = bit32.bxor(h, string.byte(text, i))
        h = bit32.band(h * 16777619, 0xFFFFFFFF)
    end
    return h
end
function Plan.hash(i: number, seed: number): number
    local h = bit32.band(i * 374761393 + seed * 668265263, 0xFFFFFFFF)
    h = bit32.band(bit32.bxor(h, bit32.rshift(h, 13)) * 1274126177, 0xFFFFFFFF)
    h = bit32.bxor(h, bit32.rshift(h, 16))
    return (h % 65536) / 65535
end

-- ---------------------------------------------------------------- bucket pose. s = seconds since the bucket window start,
-- side -1 left / +1 right. Returns x (studs, signed), y (studs above the egg centre), tilt (deg toward the egg, signed),
-- alpha 0..1, squash (bucket y scale: a little bounce as it arrives and as it tips back).
function Plan.bucketPose(s: number, side: number): (number, number, number, number, number)
    local b = Plan.Bucket
    if s < 0 then return side * (Plan.BucketX + 1.6), Plan.BucketY, 0, 0, 1 end
    local arrive = backOut(s / b.hover)
    local x = Plan.BucketX + 1.6 * (1 - arrive)
    local tilt = 0
    if s >= b.tip and s < b.pourEnd then tilt = easeInOut((s - b.tip) / (b.impact - b.tip))
    elseif s >= b.pourEnd then tilt = 1 - easeInOut((s - b.pourEnd) / (b.untilt - b.pourEnd)) end
    tilt = clamp01(tilt)
    local leave = clamp01((s - b.untilt) / (b.leave - b.untilt))
    x += 1.8 * leave * leave
    local y = Plan.BucketY + .06 * math.sin(s * 2.4) - .12 * tilt
    local alpha = if s <= 0 then 0 else 1 - clamp01((leave - .6) / .4)
    local squash = 1 + .06 * math.sin(math.pi * clamp01(s / b.hover)) * (1 - clamp01(s / b.hover)) - .05 * tilt
    return side * x, y, -side * 72 * tilt, alpha, squash
end
-- Pour stream strength 0..1 (thick liquid leaving the lip) over the window.
function Plan.stream(s: number): number
    local b = Plan.Bucket
    if s < b.pour then return 0 end
    local grow = easeOut((s - b.pour) / (b.impact - b.pour))
    local thin = 1 - clamp01((s - b.pourEnd) / .2)
    return grow * thin
end
-- Thick liquid arc from the lip (lx, ly px) to the impact point (ix, iy px): `n` blob centres along a quadratic curve whose
-- control point sags with gravity; `grow` 0..1 is how far the stream has reached. Returns {x, y, r} per blob (r = radius px).
function Plan.streamBlobs(lx: number, ly: number, ix: number, iy: number, grow: number, n: number): {{number}}
    local out = {}
    local cx, cy = (lx + ix) / 2, math.min(ly, iy) - 18 + (iy - ly) * .15
    local reach = clamp01(grow)
    for i = 1, n do
        local u = (i - 1) / math.max(1, n - 1)
        local x = (1 - u) ^ 2 * lx + 2 * (1 - u) * u * cx + u * u * ix
        local y = (1 - u) ^ 2 * ly + 2 * (1 - u) * u * cy + u * u * iy
        local r = 15 - 4 * u + 3 * math.sin(i * 1.7) * u -- wobbly, a little thinner toward the egg
        if u <= reach then table.insert(out, {x, y, math.max(8, r)}) end
    end
    return out
end
-- Splash crown: droplet j of n, `since` seconds after the impact, thrown up and out (leaning away from the bucket side).
-- Returns dx, dy (px from the impact), size px, opacity 0..1. Bounded; nothing falls below the chips (HatchFxPlan.Limits.maxFall).
Plan.CrownLife = .6
function Plan.crown(j: number, n: number, since: number, side: number, seed: number): (number, number, number, number)
    if since < 0 or since >= Plan.CrownLife then return 0, 0, 0, 0 end
    local k = since / Plan.CrownLife
    local h1, h2 = Plan.hash(j * 3, seed), Plan.hash(j * 3 + 1, seed)
    local a = (-.08 - .84 * ((j - .5) / math.max(n, 1))) * math.pi
    local speed = 120 + 110 * h1
    local dx = math.cos(a) * speed * since - side * 36 * since
    local dy = math.sin(a) * speed * since + 420 * since * since
    dy = math.min(dy, 140)
    local size = (12 + 8 * h2) * (1 - .5 * k)
    return dx, dy, math.max(3, size), clamp01(1 - k ^ 1.6)
end
-- 2D drip streak i, `since` seconds after the impact, hanging under the splash. Returns x offset (px), top y offset (px),
-- length px, width px, opacity. nil before it starts / after it dried.
function Plan.dripStreak(i: number, since: number, seed: number): (number?, number?, number?, number?, number?)
    local d = Plan.Drips
    local start = d.delay + .12 * Plan.hash(i * 5, seed)
    local k = (since - start) / d.span
    if k < 0 or k >= 1 then return nil, nil, nil, nil, nil end
    local x = (Plan.hash(i * 5 + 1, seed) - .5) * 120
    local length = (34 + 40 * Plan.hash(i * 5 + 2, seed)) * easeOut(k / .75)
    local width = 7 - 3 * k
    return x, 10 + 6 * Plan.hash(i * 5 + 3, seed), length, width, clamp01(1 - (k - .55) / .45)
end
-- Egg squash and stretch at an impact: x scale, y scale (decaying wobble, 1 at rest). A soft bubble, never a snap.
function Plan.squash(sinceImpact: number): (number, number)
    if sinceImpact < 0 then return 1, 1 end
    local w = .11 * math.exp(-6 * sinceImpact) * math.cos(14 * sinceImpact)
    return 1 + w, 1 - w
end
-- Wet gloss (MeshPart reflectance) after an impact: rises to `peak`, then dries to 0 (matte).
function Plan.gloss(sinceImpact: number): number
    if sinceImpact < 0 then return 0 end
    local g = Plan.Gloss
    if sinceImpact < g.rise then return g.peak * easeOut(sinceImpact / g.rise) end
    return g.peak * (1 - easeInOut((sinceImpact - g.rise) / g.dry))
end
-- Idle sway (degrees, px) while the server answer is on its way or between beats: gentle, slow.
function Plan.sway(vt: number): (number, number)
    return math.sin(vt * 2.1) * 2.2, math.sin(vt * 1.6) * 2.5
end

-- ---------------------------------------------------------------- splats and the paint-reveal time field (model space)
-- Impact points of one coat on the egg (model space, egg longest side = 1, y up, camera roughly along +z): a main splat on the
-- camera-facing upper flank of the bucket's side plus two smaller ones, jittered by the egg's seed. t0 = seconds after impact.
Plan.SplatsPerCoat = 3
function Plan.splats(seed: number, side: number, coat: number): {{x: number, y: number, z: number, t0: number, r: number}}
    local out = {}
    local base = {{.28, .2, .22, 0, 1}, {.14, .36, .3, .08, .7}, {.33, -.02, .24, .16, .75}}
    for i, b in base do
        local j = (coat - 1) * 10 + i
        local jx, jy, jz = (Plan.hash(j, seed) - .5) * .08, (Plan.hash(j + 100, seed) - .5) * .08, (Plan.hash(j + 200, seed) - .5) * .06
        table.insert(out, {x = side * b[1] + jx, y = b[2] + jy, z = b[3] + jz, t0 = b[4], r = b[5]})
    end
    return out
end
-- Drip streaks of a coat in model space: two per splat, hanging down (-y) from near the splat centre.
Plan.DripWidth, Plan.DripLength = .055, .5
function Plan.drips3(seed: number, splats: {any}, coat: number): {{x: number, y: number, z: number, t0: number, w: number, len: number}}
    local out = {}
    for i, s in splats do
        for d = 1, 2 do
            local j = (coat - 1) * 50 + i * 4 + d
            local off = (if d == 1 then -.07 else .06) * (.7 + .6 * Plan.hash(j, seed))
            table.insert(out, {x = s.x + off, y = s.y + .02, z = s.z, t0 = s.t0 + .05,
                w = Plan.DripWidth * (.8 + .5 * Plan.hash(j + 7, seed)), len = Plan.DripLength * (.7 + .6 * Plan.hash(j + 9, seed))})
        end
    end
    return out
end
-- Flood speed (model units / s): the farthest texel of a unit-height egg is < 1.3 model units from any splat, so every texel
-- is wet before `span` ends (verified: coverage reaches 100%).
function Plan.floodSpeed(span: number): number return 1.3 / (.8 * span) end
-- Seconds after the impact at which the texel at model position (x, y, z) gets its paint: the first splat whose growing circle
-- reaches it, or a drip streak running down from a splat (drips run faster than the flood, so they read as streaks ahead of it).
function Plan.revealTime(x: number, y: number, z: number, splats: {any}, drips: {any}, span: number): number
    local speed = Plan.floodSpeed(span)
    local best = span
    for _, s in splats do
        local d = math.sqrt((x - s.x) ^ 2 + (y - s.y) ^ 2 + (z - s.z) ^ 2)
        local t = s.t0 + math.max(0, d - .04 * s.r) / (speed * s.r)
        if t < best then best = t end
    end
    for _, d in drips do
        local dy = y - d.y
        if dy < 0 and -dy <= d.len then
            local lateral = math.sqrt((x - d.x) ^ 2 + (z - d.z) ^ 2)
            local w = d.w * (1 - .35 * (-dy / d.len)) -- streaks taper
            if lateral <= w then
                local t = d.t0 + (-dy) / (speed * 2.6) + lateral / (speed * 2)
                if t < best then best = t end
            end
        end
    end
    return math.clamp(best, 0, span - Plan.Coat.soft) -- every texel is fully wet by the end of the span
end
-- Texel alpha 0..1 at coat time t (seconds after the impact) for a texel with reveal time `at`.
function Plan.coatAlpha(at: number, t: number): number
    return clamp01((t - at) / Plan.Coat.soft)
end
-- Wet-edge brightness 0..1: the advancing front shines (a thin bright rim on the fresh edge).
function Plan.wetEdge(alpha: number): number
    if alpha <= 0 or alpha >= 1 then return 0 end
    return 1 - math.abs(alpha * 2 - 1)
end

-- ---------------------------------------------------------------- projection (pure): camera-space point (z negative = in front)
-- to panel px; nil when behind the camera.
function Plan.project(x: number, y: number, z: number, fovDeg: number, w: number, h: number): (number?, number?)
    if z >= -1e-4 then return nil, nil end
    local tanHalf = math.tan(math.rad(fovDeg / 2))
    local aspect = w / h
    local nx, ny = (x / -z) / (tanHalf * aspect), (y / -z) / tanHalf
    return w / 2 + nx * w / 2, h / 2 - ny * h / 2
end
-- Camera-space position of the egg centre so that it projects to Plan.Camera.eggPx (used by the client to place the camera).
function Plan.eggCameraSpace(): (number, number, number)
    local c = Plan.Camera
    local tanHalf = math.tan(math.rad(c.fov / 2))
    local nx = (c.eggPx[1] / Plan.ScreenWidthPx) * 2 - 1
    local ny = 1 - (c.eggPx[2] / Plan.ScreenHeightPx) * 2
    return nx * tanHalf * (Plan.ScreenWidthPx / Plan.ScreenHeightPx) * c.distance, ny * tanHalf * c.distance, -c.distance
end
function Plan.pxPerStud(): number
    local c = Plan.Camera
    return Plan.ScreenHeightPx / (2 * c.distance * math.tan(math.rad(c.fov / 2)))
end

-- ---------------------------------------------------------------- budget per device (docs/105: EditableImage bytes; docs/87: phone rate)
-- bake = texture side (px): one EditableImage of bake^2 x 4 bytes per hatch panel (256 px = 256 KiB) plus transient source reads.
-- writes = max composite writes per second during a coat; sprite counts are pooled 2D ImageLabels / Frames over the viewport.
Plan.Budget = {
    desktop = {bake = 256, writes = 15, streamBlobs = 12, crown = 14, drips = 6},
    tablet = {bake = 256, writes = 12, streamBlobs = 10, crown = 10, drips = 5},
    phone = {bake = 128, writes = 8, streamBlobs = 8, crown = 8, drips = 4},
}
Plan.MaxImageKiB = 256
function Plan.budget(device: string)
    return Plan.Budget[device] or Plan.Budget.desktop
end
function Plan.imageKiB(bake: number): number return bake * bake * 4 / 1024 end
function Plan.sprites(b): number return b.streamBlobs + 2 * b.crown + 2 * b.drips end

-- ---------------------------------------------------------------- chips and cue names (reused from v1: no new copy, no new sounds)
Plan.Cues = {swoosh = "pickup_lo", splashLeft = "pickup", splashRight = "pickup_hi"}

return Plan
