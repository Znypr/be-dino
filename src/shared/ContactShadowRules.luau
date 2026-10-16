--!strict
-- BD-460 (docs/138): soft contact shadow under every dino so it sits ON the grass instead of floating flat against it.
-- Pure rules, no Roblox services (tools/verify_contact_shadow.py runs this offline). ContactShadow.client.luau owns the Instances.
-- Look: three stacked flat discs (big and faint, medium, small and a little darker) give a soft falloff without any texture or art
-- asset. Cost: three anchored, non-colliding, non-shadow-casting parts per shown dino, one raycast each; the local dino is
-- always shown, the others are capped per device class and by the Effects setting.
local Rules = {}

-- Disc layers, outer to inner: size = share of the full footprint, alpha = how dark that disc is on its own (1 - Transparency).
-- Stacked at the centre they add up to about 0.57 darkness; the rim fades out over three steps. (BD-460 round 2: the first version, .33 and a
-- footprint narrower than the body, was invisible at 25 studs in Studio.)
Rules.Layers = table.freeze({
    table.freeze({size = 1.00, alpha = .20}),
    table.freeze({size = .72, alpha = .24}),
    table.freeze({size = .46, alpha = .30}),
})
Rules.Thickness = .05 -- studs; a flat cylinder
Rules.LayerStep = .015 -- studs between stacked discs (no z-fighting)
Rules.Lift = .07 -- studs above the ground surface
Rules.Color = {12, 20, 16} -- cool dark green-navy, never pure black (docs/114 s4.3)

-- Footprint in studs for a dino of this VisualScale (1 = start size, grows to about 4): width across, length along.
function Rules.footprint(visualScale: number): (number, number)
    local s = if visualScale ~= visualScale then 1 else math.clamp(visualScale, .5, 5)
    local width = math.clamp(5.4 * s, 4, 18) -- the starting dino is about 3.5 studs wide: the outer disc must stick out past the body
    return width, width * 1.4
end

-- Others' shadows: nearest first, within range, capped per device class. The local dino is never limited (it is not in this list).
Rules.MaxOthers = table.freeze({Phone = 2, Tablet = 4, Desktop = 6})
Rules.Range = table.freeze({Phone = 40, Tablet = 60, Desktop = 80})
Rules.OthersHz = 10 -- others update ten times a second; the local dino every frame

-- Effects setting (Full / Lite / Off): Lite halves the count, Off keeps only the local dino.
function Rules.maxOthers(device: string, effects: string): number
    local base = Rules.MaxOthers[device] or Rules.MaxOthers.Desktop
    if effects == "off" then return 0 end
    if effects == "lite" then return math.floor(base / 2) end
    return base
end

-- Pure: which of these candidates ({id, distance}) get a shadow? Returns ids, nearest first.
function Rules.pick(candidates: {{id: any, distance: number}}, device: string, effects: string): {any}
    local range = Rules.Range[device] or Rules.Range.Desktop
    local cap = Rules.maxOthers(device, effects)
    local near = {}
    for _, c in candidates do
        if c.distance == c.distance and c.distance <= range then table.insert(near, c) end
    end
    table.sort(near, function(a, b) return a.distance < b.distance end)
    local out = {}
    for i = 1, math.min(cap, #near) do out[i] = near[i].id end
    return out
end

-- Jumping or falling lifts the dino off the ground: the shadow gets smaller and fainter, and is gone about 9 studs up.
-- Returns (opacityFactor, sizeFactor), both in [0, 1].
function Rules.airborne(heightAboveStand: number): (number, number)
    local h = if heightAboveStand ~= heightAboveStand then 0 else math.max(0, heightAboveStand)
    local t = math.clamp(h / 9, 0, 1)
    return 1 - t, 1 - .35 * t
end

-- Transparency of disc i (1-based) for an opacity factor in [0, 1].
function Rules.transparency(layer: number, opacity: number): number
    local l = Rules.Layers[layer]
    return 1 - l.alpha * math.clamp(opacity, 0, 1)
end

-- Total darkness at the centre for full opacity (used by the verify script to keep the look soft).
function Rules.centreDarkness(): number
    local through = 1
    for _, l in Rules.Layers do through *= 1 - l.alpha end
    return 1 - through
end

-- Ground normals flatter than this (nearly a wall) fall back to straight up.
Rules.MinNormalY = .35

return Rules
