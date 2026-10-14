--!strict
-- BD-086/110/111/112 Mythic Glow v2 (owner pick 2026-10-14, docs/70 + docs/81). Pure and
-- dependency-free: turns an equipped aura/trail plus a quality level into a list of effect
-- layers, which CosmeticEffects builds. Textures come from EffectAssets (owner uploads); until
-- every texture has an ID, `ready` is false and the game keeps the v1 strip effects.
local Style = {}

-- Ten trails in six classes (docs/70 section d). Speed/price/level never depend on the class.
Style.TrailClass = {white = 1, fern = 1, tidal = 2, ember = 2, violet = 3, electric = 3, frost = 4, solar = 4, nova = 5, astra = 6}
Style.ClassNames = {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"}
Style.TextureKeys = {"sigil-outer", "sigil-inner", "runes", "glow-dot", "ribbon-plain", "ribbon-plasma",
    "ribbon-lightning", "light-pillar", "halo-ring", "twinkle"}

-- Per-player budget at full quality (docs/70 section c, adjusted for the navy under-layer trail).
Style.Budget = {
    full = {emitters = 4, beams = 5, trails = 4, discs = 2, billboards = 1},
    lite = {emitters = 0, beams = 0, trails = 1, discs = 1, billboards = 0},
}

function Style.trailClass(trail: any): number
    if typeof(trail) ~= "table" then return 0 end
    return Style.TrailClass[trail.id] or 1
end

-- Aura tier from the existing growth multiplier: below 1.3 -> 1, below 1.6 -> 2, else 3.
function Style.auraTier(aura: any): number
    if typeof(aura) ~= "table" then return 0 end
    local growth = if typeof(aura.growth) == "number" then aura.growth else 1
    return if growth >= 1.6 then 3 elseif growth >= 1.3 then 2 else 1
end

function Style.ready(assets: any): boolean
    if typeof(assets) ~= "table" then return false end
    for _, key in Style.TextureKeys do
        local id = assets[key]
        if typeof(id) ~= "string" or not string.match(id, "^rbxassetid://%d+$") then return false end
    end
    return true
end

-- Quality for one player: own dino and the 2 nearest within 25 studs get "full", others within
-- 80 studs "lite", beyond that "off". Motion off caps at "lite" (no orbit/spin).
function Style.quality(isLocal: boolean, distance: number, nearRank: number, motion: boolean): string
    local q = if isLocal or (distance <= 25 and nearRank <= 2) then "full" elseif distance <= 80 then "lite" else "off"
    if q == "full" and not motion then q = "lite" end
    return q
end

-- Returns a list of layers. Every layer has `kind` and, where it draws an image, `texture`
-- (a TextureKeys entry). The builder maps kinds to Roblox instances.
function Style.plan(aura: any, trail: any, quality: string)
    local layers = {}
    if quality == "off" then return layers end
    local full = quality == "full"
    local tier = Style.auraTier(aura)
    if tier > 0 then
        table.insert(layers, {kind = "disc", texture = "sigil-outer", spin = 0.35, radius = 2.4, height = -1.75, under = true})
        if full then
            if tier >= 2 then table.insert(layers, {kind = "disc", texture = "sigil-inner", spin = -0.55, radius = 1.6, height = -1.72}) end
            table.insert(layers, {kind = "emitter", role = "runes", texture = "runes", flipbook = "Random", rate = 3 + tier, size = 0.45, rise = 1.2})
            table.insert(layers, {kind = "emitter", role = "motes", texture = "glow-dot", rate = 6 + 2 * tier, size = 0.22, rise = 1.6})
            table.insert(layers, {kind = "comets", texture = "ribbon-plasma", count = 1 + tier})
            if tier >= 2 then table.insert(layers, {kind = "pillar", texture = "light-pillar", width = 2.2}) end
            if tier >= 3 then table.insert(layers, {kind = "halo", texture = "halo-ring", size = 2.6}) end
        end
    end
    local class = Style.trailClass(trail)
    if class > 0 then
        local strand = if trail.id == "electric" then "ribbon-lightning" else "ribbon-plasma"
        if full then table.insert(layers, {kind = "trail", role = "under", texture = "ribbon-plain", widthScale = 1.5}) end
        table.insert(layers, {kind = "trail", role = "main", texture = "ribbon-plain", widthScale = 1, rainbow = class >= 6})
        if full then
            if class >= 3 then table.insert(layers, {kind = "trail", role = "strand", texture = strand, widthScale = 0.8, offset = 0.35}) end
            if class >= 5 then table.insert(layers, {kind = "trail", role = "braid", texture = "ribbon-plasma", widthScale = 0.6, offset = -0.35}) end
            if class >= 2 and tier == 0 then
                table.insert(layers, {kind = "emitter", role = "trailMotes", texture = "glow-dot", rate = 3 + 2 * class, size = 0.18, walking = true})
            end
            if class >= 4 then table.insert(layers, {kind = "emitter", role = "twinkle", texture = "twinkle", flipbook = "OneShot", rate = class, size = 0.6, walking = true}) end
        end
    end
    return layers
end

-- Counts per budget bucket, for tests and the debug overlay.
function Style.cost(layers: {any})
    local c = {emitters = 0, beams = 0, trails = 0, discs = 0, billboards = 0}
    for _, layer in layers do
        if layer.kind == "emitter" then c.emitters += 1
        elseif layer.kind == "comets" then c.beams += layer.count
        elseif layer.kind == "pillar" then c.beams += 1
        elseif layer.kind == "trail" then c.trails += 1
        elseif layer.kind == "disc" then c.discs += 1
        elseif layer.kind == "halo" then c.billboards += 1 end
    end
    return c
end

function Style.withinBudget(layers: {any}, quality: string): boolean
    local budget = Style.Budget[quality]
    if budget == nil then return #layers == 0 end
    for key, used in Style.cost(layers) do
        if used > budget[key] then return false end
    end
    return true
end

return Style
