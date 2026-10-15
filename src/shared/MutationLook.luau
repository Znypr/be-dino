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

-- Pure maths: pull a base colour (0-255 triple) toward the mutation tint. amount defaults to the entry's own.
function Look.blend(base: {number}, id: string, amount: number?): {number}
    local entry = Look.get(id)
    if not entry then return {base[1], base[2], base[3]} end
    local a = math.clamp(amount or entry.amount, 0, Look.MaxAmount)
    return {base[1] + (entry.tint[1] - base[1]) * a, base[2] + (entry.tint[2] - base[2]) * a, base[3] + (entry.tint[3] - base[3]) * a}
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
