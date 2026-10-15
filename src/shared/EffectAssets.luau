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
    -- FX v3 (owner uploads 2026-10-16, docs/77 fx3_*): anime cel sheets, white on transparent, 4x4 cells of 256 px.
    smokeSheet = {id = "rbxassetid://140058716506789", fallback = "smoke"}, -- fx3 smoke-anime: puff grows, then breaks into curls
    sparkSheet = {id = "rbxassetid://97747398683135", fallback = "spark"},  -- fx3 sparkle: star grows, then shrinks
    flameSheet = {id = "rbxassetid://81481519628921", fallback = "fire"},   -- fx3 flame: 16 flame shapes (random frame)
    swirl = {id = "rbxassetid://99422347356351", fallback = "spark"},       -- fx3 swirl: rotating energy swirl (loop)
    rays = {id = "rbxassetid://89127115370689", fallback = "spark"},        -- fx3 rays: single image, rising aura light rays
    ribbonSoft = {id = "", fallback = "spark"},    -- soft tapered ribbon strip for Trail/Beam, 512x64
    speedLine = {id = "", fallback = "spark"},     -- thin speed streak strip, 512x32
    starFour = {id = "rbxassetid://97747398683135", fallback = "spark"},    -- four-point twinkle: the fx3 sparkle sheet
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

-- Flipbook sheets (docs/93 section 8): square, 4 x 4 cells (fx3 sheets are 1024 px, 256 px cells; Roblox stores at most 1024). A sprite showing a sheet MUST select one cell, otherwise the
-- whole sheet is drawn. cellRect is pure: it returns nil while the key still uses a built-in sprite (single image, no cell).
Assets.Sheets = {smokeSheet = {size = 1024, grid = 4}, sparkSheet = {size = 1024, grid = 4}, flameSheet = {size = 1024, grid = 4},
    starFour = {size = 1024, grid = 4}, swirl = {size = 1024, grid = 4}, crystalSheet = {size = 512, grid = 4}}
-- How the 16 cells play (ParticleEmitter.FlipbookMode name): OneShot = in order over the particle life, Random = one random shape,
-- Loop = cycles at LoopFps. Keys not listed play Random.
Assets.FlipbookMode = {smokeSheet = "OneShot", sparkSheet = "OneShot", starFour = "OneShot", flameSheet = "Random", swirl = "Loop", crystalSheet = "Random"}
Assets.LoopFps = 10
-- Sheets whose upload may carry a black background: draw them additively (LightEmission 1) so black never shows.
Assets.Additive = {swirl = true, rays = true}
function Assets.mode(key: string): string return Assets.FlipbookMode[key] or "Random" end
function Assets.isSheet(key: string): boolean return Assets.Sheets[key] ~= nil and Assets.isReal(key) end
-- Pure: which cell (1..16) a 2D sprite shows. t = 0..1 of its life, age = seconds alive, seed = the sprite's random pick.
function Assets.frameAt(key: string, t: number, age: number, seed: number): number
    local mode = Assets.mode(key)
    if mode == "OneShot" then return math.clamp(math.floor(math.clamp(t, 0, 1) * 16) + 1, 1, 16) end
    if mode == "Loop" then return math.floor(age * Assets.LoopFps + seed) % 16 + 1 end
    return (math.floor(seed) - 1) % 16 + 1
end
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
