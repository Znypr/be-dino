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
    smokeSheet = {id = "rbxassetid://109810080362045", fallback = "smoke"}, -- fx3 smoke-anime: puff grows, then breaks into curls
    sparkSheet = {id = "rbxassetid://71657118485647", fallback = "spark"},  -- fx3 sparkle: star grows, then shrinks
    flameSheet = {id = "rbxassetid://105817278245256", fallback = "fire"},   -- fx3 flame: 16 flame shapes (random frame)
    swirl = {id = "rbxassetid://84584423423015", fallback = "spark"},       -- fx3 swirl: rotating energy swirl (loop)
    rays = {id = "rbxassetid://99778248779183", fallback = "spark"},        -- fx3 rays: single image, rising aura light rays
    ribbonSoft = {id = "", fallback = "spark"},    -- soft tapered ribbon strip for Trail/Beam, 512x64
    speedLine = {id = "", fallback = "spark"},     -- thin speed streak strip, 512x32
    starFour = {id = "rbxassetid://71657118485647", fallback = "spark"},    -- four-point twinkle: the fx3 sparkle sheet
    crystalSheet = {id = "", fallback = "spark"},  -- frost crystals, droplets, pebbles, embers 4x4
    -- Pending owner uploads (docs/120): bind with tools/bind_assets.py. A key nothing reads yet simply resolves to its built-in sprite.
    glowPlateDroplet = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); read by FxRecipes.MutationTex (docs/92); empty = today's look
    glowPlateCrescent = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); read by FxRecipes.MutationTex (docs/92); empty = today's look
    glowPlateRound = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); read by FxRecipes.MutationTex (docs/92); empty = today's look
    ringSeismic = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); read by FxRecipes.MutationTex (docs/92); empty = today's look
    smokeSoft = {id = "", fallback = "smoke"}, -- owner upload slot (docs/120): BD-187 layered soft smoke flipbook; empty = built-in sprite
    smokeDense = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); read by FxRecipes.MutationTex (docs/92); empty = today's look
    smokeWispy = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); read by FxRecipes.MutationTex (docs/92); empty = today's look
    motifDroplets = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); read by FxRecipes.MutationTex (docs/92); empty = today's look
    motifSoftSparks = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); read by FxRecipes.MutationTex (docs/92); empty = today's look
    motifSnowCrystals = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); read by FxRecipes.MutationTex (docs/92); empty = today's look
    motifPebbles = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); read by FxRecipes.MutationTex (docs/92); empty = today's look
    motifEmbers = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); read by FxRecipes.MutationTex (docs/92); empty = today's look
    motifAurora = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); read by FxRecipes.MutationTex (docs/92); empty = today's look
    motifCrimson = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); read by FxRecipes.MutationTex (docs/92); empty = today's look
    confetti = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); empty = built-in sprite
    lavaCrust = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); empty = built-in sprite
    flameTongue = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); empty = built-in sprite
    starPop = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); empty = built-in sprite
    domeGradient = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); empty = built-in sprite
    speedStreaks = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); empty = built-in sprite
    rainbowStrip = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); empty = built-in sprite
    rimRingUi = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); empty = built-in sprite
    paintCrown = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); empty = built-in sprite
    paintDrips = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); empty = built-in sprite
    paintDroplet = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); empty = built-in sprite
    weatherCloud = {id = "", fallback = "spark"}, -- owner upload slot (docs/120): soft sky cloud puff, single image 512 px, white on alpha (fog banks / storm cover)
    lightningBolt = {id = "", fallback = "spark"}, -- owner upload slot (docs/120): branching lightning strip, white on alpha, 512x128 (thunder bolts)
    rainStreak = {id = "", fallback = "spark"}, -- owner upload slot (docs/120): thin rain streak, white on alpha, 64x256
    snowFlakeSheet = {id = "", fallback = "spark"}, -- owner upload slot (docs/120): snow flakes and crystals 4x4, white on alpha
    ashFlake = {id = "", fallback = "spark"}, -- owner upload slot (docs/120): ash flakes and embers 4x4, white on alpha
    bloodMoonDisc = {id = "", fallback = "spark"}, -- owner upload slot (docs/120): blood moon disc with soft craters, 512 px, on alpha
    -- BD-131 weather textures (Blender renders in resources/effects/fx-v2, docs/120): white on alpha, tinted by the weather code; none is read by the weather rigs yet
    emberSpark = {id = "", fallback = "spark"}, -- owner upload slot (docs/120): ember and lava sparks 4x4 of 128 px, glowing beads and streaks (volcano embers, lava bombs)
    dustSand = {id = "", fallback = "spark"}, -- owner upload slot (docs/120): dust and sand grain sprays over a faint haze 4x4 (earthquake)
    auroraCurtain = {id = "", fallback = "spark"}, -- owner upload slot (docs/120): northern lights curtain, 16-frame loop 4x4, white on alpha (sky curtain particles)
    bloodMoonMotes = {id = "", fallback = "spark"}, -- owner upload slot (docs/120): soft crimson motes, bubble rings and wisps 4x4 (blood moon)
    paintGloss = {id = "", fallback = "spark"}, -- owner upload slot (docs/120); empty = built-in sprite
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
    starFour = {size = 1024, grid = 4}, swirl = {size = 1024, grid = 4}, crystalSheet = {size = 512, grid = 4},
    paintCrown = {size = 1024, grid = 4}, paintDrips = {size = 1024, grid = 4}, paintDroplet = {size = 1024, grid = 4}}
-- BD-186..189 mutation textures (Blender renders, docs/92): smoke and motif sheets are 512 px, 4 x 4 cells of 128 px, 16 frames in order.
-- Glow plates and ringSeismic are single 256 px images (no sheet). Which mutation reads which key: FxRecipes.MutationTex.
for _, key in {"smokeSoft", "smokeDense", "smokeWispy", "motifDroplets", "motifSoftSparks", "motifSnowCrystals", "motifPebbles", "motifEmbers", "motifAurora", "motifCrimson"} do
    Assets.Sheets[key] = {size = 512, grid = 4}
end
-- How the 16 cells play (ParticleEmitter.FlipbookMode name): OneShot = in order over the particle life, Random = one random shape,
-- Loop = cycles at LoopFps. Keys not listed play Random.
Assets.FlipbookMode = {smokeSheet = "OneShot", sparkSheet = "OneShot", starFour = "OneShot", flameSheet = "Random", swirl = "Loop", crystalSheet = "Random",
    paintCrown = "OneShot", paintDrips = "OneShot", paintDroplet = "Random"}
-- The smoke puffs and motif sheets grow, rest and shrink over one particle life (OneShot). The Aurora ribbons are a seamless loop (Loop).
for _, key in {"smokeSoft", "smokeDense", "smokeWispy", "motifDroplets", "motifSoftSparks", "motifSnowCrystals", "motifPebbles", "motifEmbers", "motifCrimson"} do
    Assets.FlipbookMode[key] = "OneShot"
end
Assets.FlipbookMode.motifAurora = "Loop"
Assets.LoopFps = 10
-- BD-131 weather flipbooks: 512 px sheets of 16 cells of 128 px (not 1024 / 256), shapes picked at random per particle, the aurora curtain loops.
-- Inert until an id is bound: cellRect / isSheet return nil / false while the key resolves to a built-in sprite.
for _, key in {"snowFlakeSheet", "ashFlake", "emberSpark", "dustSand", "bloodMoonMotes"} do
    Assets.Sheets[key], Assets.FlipbookMode[key] = {size = 512, grid = 4}, "Random"
end
Assets.Sheets.auroraCurtain, Assets.FlipbookMode.auroraCurtain = {size = 512, grid = 4}, "Loop"
-- Studio check 2026-10-16 (AssetService EditableImage): the five fx3 uploads are OPAQUE on black (no alpha), unlike the
-- white-on-alpha PNGs in resources/effects/fx-v3. Until they are re-uploaded with alpha:
--   * world ParticleEmitters draw them additively (LightEmission 1), so black adds nothing and only the white shape shows;
--   * 2D UI (FxUi, HatchFx) cannot blend additively, so it keeps the built-in sprites (resolveUi / isRealUi / setCell).
-- 2026-10-16: all five re-uploaded WITH alpha (Studio: corner alpha 0, 1024 px), so HasAlpha is true for every fx3 key.
-- Clearing a key falls back to additive world / built-in UI sprites.
Assets.HasAlpha = {smokeSheet = true, sparkSheet = true, flameSheet = true, starFour = true, swirl = true, rays = true, paintCrown = true, paintDrips = true, paintDroplet = true} -- paint sheets are white on alpha (docs/118 s4 C)
Assets.Additive = {}
for _, key in {"smokeSheet", "sparkSheet", "flameSheet", "starFour", "swirl", "rays"} do Assets.Additive[key] = true end
function Assets.isAdditive(key: string): boolean return Assets.Additive[key] == true and not Assets.HasAlpha[key] end
function Assets.isRealUi(key: string): boolean return Assets.isReal(key) and not Assets.isAdditive(key) end
function Assets.resolveUi(key: string): string
    if Assets.isRealUi(key) then return Assets.resolve(key) end
    local req = Assets.Requested[key]
    return Assets.Builtin[if req then req.fallback else key] or Assets.Builtin.spark
end
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
    if not Assets.isRealUi(key) then return false end
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
