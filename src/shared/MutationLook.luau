--!strict
-- BD-155: the ONE look table for event mutations. Pure data (RGB triples, no Roblox types) plus two small appliers.
-- Everything that shows a mutation reads this: the world dino (CosmeticVisuals), Dino Index / My dinos / detail
-- previews and the hatch dino (via PreviewTraits), egg cards (colour hint) and the mist (MutationEffects).
-- Calm and bubbly (docs/87): soft tint, soft glow, dinos stay matte (no Neon/Metal/Glass, no reflectance).
-- Conditions are egg-only and never appear here. Fusion tiers (Gold/Emerald/Diamond) never get a mutation tint.
local Look = {}

export type Entry = {
    id: string, name: string,
    tint: {number},       -- body colour the dino is gently pulled toward
    amount: number,       -- 0..1 pull toward tint (kept low: shell/gene colours must stay readable)
    rim: {number},        -- soft rim / glow colour (lights, badge outline)
    glow: number,         -- 0..1 glow strength (PointLight brightness / badge halo scale)
    material: string,     -- Enum.Material name; always matte (Plastic)
    mist: {number},       -- smoke colour (dark tone of the particle palette)
    spark: {number},      -- accent colour of beams / sparkles
    badge: {number},      -- badge / icon colour (same as ProgressionConfig.EventMutations colour)
    mood: string,
}

Look.Order = {"dewdrop", "charged", "frost", "seismic", "ember", "aurora", "bloodmoon"}
Look.MaxAmount = 0.35 -- hard ceiling for any tint pull (verified)
Look.Entries = {
    dewdrop = {id = "dewdrop", name = "Dewdrop", tint = {120, 226, 190}, amount = 0.22, rim = {112, 244, 191}, glow = 0.35, material = "Plastic",
        mist = {43, 154, 111}, spark = {112, 244, 191}, badge = {85, 216, 176}, mood = "fresh, dewy, playful"},
    charged = {id = "charged", name = "Charged", tint = {255, 226, 120}, amount = 0.22, rim = {255, 207, 72}, glow = 0.5, material = "Plastic",
        mist = {56, 66, 87}, spark = {255, 207, 72}, badge = {255, 218, 88}, mood = "zippy, bright, tingly"},
    frost = {id = "frost", name = "Frost", tint = {160, 232, 255}, amount = 0.26, rim = {175, 235, 255}, glow = 0.35, material = "Plastic",
        mist = {112, 184, 211}, spark = {175, 235, 255}, badge = {135, 233, 255}, mood = "crisp, sparkly, cool"},
    seismic = {id = "seismic", name = "Seismic", tint = {226, 190, 130}, amount = 0.22, rim = {210, 173, 113}, glow = 0.2, material = "Plastic",
        mist = {133, 97, 62}, spark = {210, 173, 113}, badge = {220, 180, 115}, mood = "warm, sturdy, rumbly"},
    ember = {id = "ember", name = "Ember", tint = {255, 140, 90}, amount = 0.24, rim = {255, 144, 51}, glow = 0.55, material = "Plastic",
        mist = {99, 54, 34}, spark = {255, 144, 51}, badge = {255, 116, 62}, mood = "cozy campfire glow"},
    aurora = {id = "aurora", name = "Aurora", tint = {140, 250, 220}, amount = 0.24, rim = {81, 233, 187}, glow = 0.6, material = "Plastic",
        mist = {109, 65, 150}, spark = {81, 233, 187}, badge = {112, 255, 205}, mood = "dreamy, shimmering, magical"},
    bloodmoon = {id = "bloodmoon", name = "Blood Moon", tint = {255, 120, 150}, amount = 0.24, rim = {250, 67, 102}, glow = 0.5, material = "Plastic",
        mist = {122, 26, 46}, spark = {250, 67, 102}, badge = {255, 85, 128}, mood = "moody but cozy"},
}

function Look.get(id: any): Entry?
    if type(id) ~= "string" or id == "" then return nil end
    return (Look.Entries :: any)[id]
end

function Look.color(rgb: {number}): Color3 return Color3.fromRGB(rgb[1], rgb[2], rgb[3]) end

-- BD-1066: a very dark body colour (Black gene, shaded facets) used to stay nearly black under the gentle pull, so a mutated dino read as
-- a black cut-out in the dim cave (Studio round 4, picture 227). A mutated body is therefore never darker than MinLuma (0..1, luma of the
-- result): below it the colour is lifted toward the mutation tint just far enough to reach it. Colours already above it are untouched.
Look.MinLuma = 0.3
local function luma(r: number, g: number, b: number): number return 0.299 * r + 0.587 * g + 0.114 * b end

-- Pure, per pixel (0..1 floats): pull a base colour gently toward the tint (amount), then lift it to MinLuma if it is still darker.
-- MeshPart.Color does NOT tint a part whose texture is a bake (TextureContent), so on low-poly dinos the tint has to live in the texture
-- itself (BD-518, LowPolyTexture.paint); Look.blend below is the same maths in 0-255 for Part.Color.
function Look.pull(r: number, g: number, b: number, id: any, amount: number?): (number, number, number)
    local entry = Look.get(id)
    if not entry then return r, g, b end
    local a = math.clamp(amount or entry.amount, 0, Look.MaxAmount)
    local t = entry.tint
    local tr, tg, tb = t[1] / 255, t[2] / 255, t[3] / 255
    local pr, pg, pb = r + (tr - r) * a, g + (tg - g) * a, b + (tb - b) * a
    local l, tl = luma(pr, pg, pb), luma(tr, tg, tb)
    if l < Look.MinLuma and tl > l then
        local k = math.clamp((Look.MinLuma - l) / (tl - l), 0, 1)
        pr, pg, pb = pr + (tr - pr) * k, pg + (tg - pg) * k, pb + (tb - pb) * k
    end
    return pr, pg, pb
end

-- Pure maths in 0-255: the same pull (and floor) for Part.Color. amount defaults to the entry's own.
function Look.blend(base: {number}, id: string, amount: number?): {number}
    if not Look.get(id) then return {base[1], base[2], base[3]} end
    local r, g, b = Look.pull(base[1] / 255, base[2] / 255, base[3] / 255, id, amount)
    return {r * 255, g * 255, b * 255}
end

-- Tints every BasePart under a model/viewport once and idempotently. The part remembers its own colour (MutBase)
-- and the colour it painted (MutOut): if something else recolours it meanwhile (genes), the new colour becomes the
-- base. Materials are never changed (dinos stay matte). id nil/"" restores the original colour.
function Look.apply(container: Instance, id: any, amount: number?)
    local entry = Look.get(id)
    for _, part in container:GetDescendants() do
        if part:IsA("BasePart") then
            local out = part:GetAttribute("MutOut")
            local base = part:GetAttribute("MutBase")
            if typeof(out) ~= "Color3" or typeof(base) ~= "Color3" or part.Color ~= out then base = part.Color end
            if entry then
                local b = base :: Color3
                local pulled = Look.blend({b.R * 255, b.G * 255, b.B * 255}, entry.id, amount)
                local colour = Color3.fromRGB(math.floor(pulled[1] + .5), math.floor(pulled[2] + .5), math.floor(pulled[3] + .5))
                part:SetAttribute("MutBase", b)
                part:SetAttribute("MutOut", colour)
                part.Color = colour
            elseif typeof(out) == "Color3" and typeof(base) == "Color3" then
                if part.Color == out then part.Color = base end
                part:SetAttribute("MutBase", nil)
                part:SetAttribute("MutOut", nil)
            end
        end
    end
end

return Look
