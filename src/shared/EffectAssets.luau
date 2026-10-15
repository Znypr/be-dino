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

-- Flipbook sheets (docs/93 section 8): 512 px square, 4 x 4 cells. A sprite showing a sheet MUST select one cell, otherwise the
-- whole sheet is drawn. cellRect is pure: it returns nil while the key still uses a built-in sprite (single image, no cell).
Assets.Sheets = {smokeSheet = {size = 512, grid = 4}, sparkSheet = {size = 512, grid = 4}, flameSheet = {size = 512, grid = 4}, crystalSheet = {size = 512, grid = 4}}
function Assets.cellRect(key: string, cell: number): (number?, number?, number?)
    local sheet = Assets.Sheets[key]
    if not sheet or not Assets.isReal(key) then return nil, nil, nil end
    local n = sheet.grid * sheet.grid
    local c = (math.floor(cell) - 1) % n
    local px = sheet.size / sheet.grid
    return (c % sheet.grid) * px, math.floor(c / sheet.grid) * px, px
end
-- Applies the cell to an ImageLabel (no-op for built-in sprites). Returns true when a real sheet cell was set.
function Assets.setCell(image: any, key: string, cell: number): boolean
    local x, y, size = Assets.cellRect(key, cell)
    if not x then return false end
    image.ImageRectOffset, image.ImageRectSize = Vector2.new(x, y), Vector2.new(size, size)
    return true
end

-- True when the key currently shows the real Blender art (used by docs and the QA overlay).
function Assets.isReal(key: string): boolean
    local req = Assets.Requested[key]
    return (req ~= nil and valid(req.id)) or valid(Assets.Uploaded[key])
end

return Assets
