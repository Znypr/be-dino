--!nonstrict
-- Texture keys for FX (docs/93). The recipes only name SEMANTIC keys; this table maps a key to a real texture.
-- Rule (AGENTS.md / docs/83): IDs come only from a real upload. `uploaded` stays "" until the lead renders and uploads the
-- Blender request (docs/93 section 8). While a key is empty we fall back to the engine's built-in white sprites, which are
-- tinted and layered at runtime. Never write an invented rbxassetid here.
local Assets = {}

-- Built-in engine sprites (no upload needed).
Assets.Builtin = {
    smoke = "rbxasset://textures/particles/smoke_main.dds",
    spark = "rbxasset://textures/particles/sparkles_main.dds",
    fire = "rbxasset://textures/particles/fire_main.dds",
}

-- Already-uploaded soft smoke used by the mutation mist since BD-155 (kept as-is, NOT new).
Assets.Uploaded = {
    softMist = "rbxassetid://105629313112163",
}

-- Blender requests (docs/93 section 8). key -> upload id (empty until rendered and uploaded) and the built-in used meanwhile.
Assets.Requested = {
    glowPlate = {id = "", fallback = "spark"},     -- neutral radial glow, 256 px
    ringSoft = {id = "", fallback = "spark"},      -- soft rim ring, 256 px
    ringShock = {id = "", fallback = "spark"},     -- thin shock ring, 256 px
    smokeSheet = {id = "", fallback = "smoke"},    -- layered smoke 4x4 flipbook, 512 px
    sparkSheet = {id = "", fallback = "spark"},    -- soft sparks, 4-point stars, bubbles 4x4, 512 px
    flameSheet = {id = "", fallback = "fire"},     -- soft flame wisps 4x4, 512 px
    ribbonSoft = {id = "", fallback = "spark"},    -- soft tapered ribbon strip for Trail/Beam, 512x64
    speedLine = {id = "", fallback = "spark"},     -- thin speed streak strip, 512x32
    starFour = {id = "", fallback = "spark"},      -- four-point twinkle, 128 px
    crystalSheet = {id = "", fallback = "spark"},  -- frost crystals, droplets, pebbles, embers 4x4
}

local function valid(id: any): boolean
    return type(id) == "string" and string.match(id, "^rbxassetid://%d+$") ~= nil
end
Assets.isValid = valid

-- Semantic key -> texture string. Unknown keys fall back to the built-in sparkle.
function Assets.resolve(key: string): string
    local up = Assets.Uploaded[key]
    if valid(up) then return up end
    local req = Assets.Requested[key]
    if req then
        if valid(req.id) then return req.id end
        return Assets.Builtin[req.fallback] or Assets.Builtin.spark
    end
    return Assets.Builtin[key] or Assets.Builtin.spark
end

-- True when the key currently shows the real Blender art (used by docs and the QA overlay).
function Assets.isReal(key: string): boolean
    local req = Assets.Requested[key]
    return (req ~= nil and valid(req.id)) or valid(Assets.Uploaded[key])
end

return Assets
