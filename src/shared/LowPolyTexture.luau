--!strict
-- BD-225 / BD-061: bakes a gene-coloured, gene-patterned (and fused-tier tinted) copy of a generated low-poly part texture
-- as a 256x256 EditableImage. Pixel maths is pure (LowPolyRecolor, LowPolyPattern, LowPolyTier; tested offline); this module only
-- owns the Roblox side: reading the source texture once, yielding bakes, and the image budget.
-- Budget (BD-203): bakes live in a PatternAtlasCache (shared per key = texture + colours + pattern + blend + tier, reference counted,
-- warm LRU, hard cap LowPolyTexture.Cap). A dino costs one image per part (7); identical genes share every image. When the cache is
-- full, acquire returns nil and the caller uses the cheap fallback (original species texture tinted by MeshPart.Color).
-- Any failure (no permission, load error) also returns nil: eyes/belly are always on screen because the original texture stays.
-- Yields: call acquire from task.spawn, never inline.
local AssetService = game:GetService("AssetService")
local Recolor = require(script.Parent.LowPolyRecolor)
local Pattern = require(script.Parent.LowPolyPattern)
local Tier = require(script.Parent.LowPolyTier)
local Cache = require(script.Parent.PatternAtlasCache)
local Texture = {}
local SIZE = Pattern.Size
Texture.Cap = 24 -- low-poly bakes; PatternGenes keeps its own 30 for eggs/legacy (low-poly dinos replace legacy dinos on screen)
local atlas = Cache.new(Texture.Cap, function(image) pcall(function() image:Destroy() end) end)
local sources: {[string]: any} = {}   -- textureId -> {buf = buffer, weights = {number}, pos = buffer?} | "loading" | "failed"
local pending: {[string]: boolean} = {} -- bake keys in flight (a second part with the same key waits instead of baking twice)
-- Geometry of the TEMPLATE part (unscaled, unposed) so the 3D pattern reads its model-space position: meshId, cframe relative to the
-- model centre, scale = part.Size / part.MeshSize, norm = 1 / longest model side.
export type Geom = {meshId: string, cframe: CFrame, scale: Vector3, norm: number}
-- Rasterise the part's triangles into its UV space (EditableMesh, once per texture). nil on any failure: the UV-space pattern is used.
local function positionMap(geom: Geom?): buffer?
    if not geom or geom.meshId == "" then return nil end
    local ok, map = pcall(function()
        local mesh = AssetService:CreateEditableMeshAsync(Content.fromUri(geom.meshId))
        local tris = {}
        for _, face in mesh:GetFaces() do
            local verts, uvs = mesh:GetFaceVertices(face), mesh:GetFaceUVs(face)
            if #verts ~= 3 or #uvs ~= 3 then continue end
            local t = {}
            for i = 1, 3 do
                local uv = mesh:GetUV(uvs[i])
                local p = geom.cframe:PointToWorldSpace(mesh:GetPosition(verts[i]) * geom.scale) * geom.norm
                table.insert(t, uv.X) table.insert(t, uv.Y)
                table.insert(t, p.X) table.insert(t, p.Y) table.insert(t, p.Z)
            end
            table.insert(tris, t)
        end
        mesh:Destroy()
        return Pattern.rasterize(tris)
    end)
    return if ok then map else nil
end
local partEntry = setmetatable({} :: {[Instance]: any}, {__mode = "k"})
export type Spec = {primary: Color3, secondary: Color3, same: boolean, primaryShare: number, patternId: string, tier: string?, seedName: string}
local function publish()
    pcall(function()
        local s = atlas:stats()
        workspace:SetAttribute("LowPolyImagesLive", s.live) workspace:SetAttribute("LowPolyImagesPinned", s.pinned)
        workspace:SetAttribute("LowPolyCacheHits", s.hits) workspace:SetAttribute("LowPolyCacheMisses", s.misses)
        workspace:SetAttribute("LowPolyCacheDenied", s.denied)
    end)
end
function Texture.stats() return atlas:stats() end
local function source(textureId: string, geom: Geom?): any?
    local state = sources[textureId]
    while state == "loading" do task.wait(0.05) state = sources[textureId] end
    if state == "failed" then return nil end
    if state then return state end
    sources[textureId] = "loading"
    local ok, result = pcall(function()
        local img = AssetService:CreateEditableImageAsync(Content.fromUri(textureId))
        local full = img.Size
        local raw = img:ReadPixelsBuffer(Vector2.zero, full)
        local small = buffer.create(SIZE * SIZE * 4)
        local weights = table.create(SIZE * SIZE, 0)
        for y = 0, SIZE - 1 do
            local sy = math.min(full.Y - 1, math.floor((y + 0.5) * full.Y / SIZE))
            for x = 0, SIZE - 1 do
                local sx = math.min(full.X - 1, math.floor((x + 0.5) * full.X / SIZE))
                local o = (y * SIZE + x) * 4
                buffer.writeu32(small, o, buffer.readu32(raw, (sy * full.X + sx) * 4))
                weights[y * SIZE + x + 1] = Recolor.bodyWeight(buffer.readu8(small, o) / 255, buffer.readu8(small, o + 1) / 255, buffer.readu8(small, o + 2) / 255)
            end
            if y % 32 == 31 then task.wait() end
        end
        img:Destroy()
        -- the species' own body colour, measured from this texture (replaces a hand table: every generated species recolours)
        local sr, sg, sb, sw = 0, 0, 0, 0
        for i = 1, SIZE * SIZE do
            local w = weights[i]
            if w > 0.5 then
                local o = (i - 1) * 4
                sr += buffer.readu8(small, o) / 255 * w sg += buffer.readu8(small, o + 1) / 255 * w sb += buffer.readu8(small, o + 2) / 255 * w sw += w
            end
        end
        local base = if sw > 50 then {sr / sw, sg / sw, sb / sw} else nil
        return {buf = small, weights = weights, pos = positionMap(geom), base = base}
    end)
    sources[textureId] = if ok then result else "failed"
    return if ok then result else nil
end
local function q(c: Color3): string
    return string.format("%d,%d,%d", math.floor(c.R * 31 + 0.5), math.floor(c.G * 31 + 0.5), math.floor(c.B * 31 + 0.5))
end
-- Stable cache key: everything that changes the pixels. Pure (tested): same spec -> same key, any change -> a different key.
function Texture.key(textureId: string, spec: Spec): string
    return string.format("%s|%s|%s|%s|%s|%d|%s", textureId, spec.patternId, q(spec.primary), q(spec.secondary), if spec.same then "s" else "d",
        math.floor(math.clamp(spec.primaryShare, 0, 1) * 20 + 0.5), spec.tier or "base")
end
-- Pure pixel pass (shared with the verifier through LowPolyRecolor/LowPolyPattern/LowPolyTier): writes the baked RGBA into out.
function Texture.paint(src: buffer, weights: {number}, mask: {number}, spec: Spec, base: {number}, out: buffer, onRow: ((number) -> ())?)
    local a, b = spec.primary, spec.secondary
    local ar, ag, ab, br, bg, bb = a.R, a.G, a.B, b.R, b.G, b.B
    if spec.same then -- same-family genes: pattern regions read as a lighter / darker version of the one colour (PatternGenes rule)
        ar, ag, ab = ar * 0.86, ag * 0.86, ab * 0.86
        br, bg, bb = math.min(1, br * 1.08 + 0.05), math.min(1, bg * 1.08 + 0.05), math.min(1, bb * 1.08 + 0.05)
    end
    local tier = Tier.get(spec.tier)
    for y = 0, SIZE - 1 do
        if onRow then onRow(y) end
        for x = 0, SIZE - 1 do
            local i = y * SIZE + x
            local o = i * 4
            local r, g, bl = buffer.readu8(src, o) / 255, buffer.readu8(src, o + 1) / 255, buffer.readu8(src, o + 2) / 255
            if weights[i + 1] > 0 then
                local m = mask[i + 1]
                local tr, tg, tb = ar + (br - ar) * m, ag + (bg - ag) * m, ab + (bb - ab) * m
                if tier then tr, tg, tb = Tier.blend(tr, tg, tb, tier, m >= 0.5) end
                r, g, bl = Recolor.pixel(r, g, bl, tr, tg, tb, base)
            end
            buffer.writeu8(out, o, math.floor(r * 255 + 0.5))
            buffer.writeu8(out, o + 1, math.floor(g * 255 + 0.5))
            buffer.writeu8(out, o + 2, math.floor(bl * 255 + 0.5))
            buffer.writeu8(out, o + 3, 255)
        end
    end
end
local function yielder(): (number) -> ()
    return function(y) if y % 24 == 23 then task.wait() end end
end
function Texture.release(part: Instance)
    local entry = partEntry[part]
    if not entry then return end
    partEntry[part] = nil
    atlas:release(entry)
    publish()
end
local hooked = setmetatable({} :: {[Instance]: boolean}, {__mode = "k"})
local function pin(part: Instance, entry): Content
    Texture.release(part)
    partEntry[part] = entry
    if not hooked[part] then hooked[part] = true part.Destroying:Once(function() Texture.release(part) end) end
    publish()
    return Content.fromObject(entry.image)
end
-- Content for `part` (pinned to it until release/Destroying) or nil (cache full / failed / no permission): caller keeps a fallback.
function Texture.acquire(part: Instance, textureId: string, speciesId: string, spec: Spec, geom: Geom?): Content?
    local key = Texture.key(textureId, spec)
    local current = partEntry[part]
    if current and current.key == key then return Content.fromObject(current.image) end
    while pending[key] do task.wait(0.1) end
    local entry = atlas:acquire(key)
    if entry then return pin(part, entry) end
    if atlas:free() <= 0 then atlas.denied += 1 publish() return nil end
    pending[key] = true
    local src = source(textureId, geom)
    if not src then pending[key] = nil return nil end
    local okMask, mask = pcall(Pattern.compute, spec.patternId, Pattern.seed(spec.seedName), src.weights, spec.primaryShare, spec.same, yielder(), src.pos)
    if not okMask then mask = table.create(SIZE * SIZE, 0) end -- pattern failure: plain colours, never nothing
    local ok, image = pcall(function()
        local out = buffer.create(SIZE * SIZE * 4)
        Texture.paint(src.buf, src.weights, mask, spec, src.base or Recolor.baseOf(speciesId), out, yielder())
        if not atlas:reserve() then return nil end
        local img = AssetService:CreateEditableImage({Size = Vector2.new(SIZE, SIZE)})
        img:WritePixelsBuffer(Vector2.zero, Vector2.new(SIZE, SIZE), out)
        return img
    end)
    pending[key] = nil
    if not ok or not image then publish() return nil end
    entry = atlas:insert(key, image)
    return pin(part, entry)
end
-- Measured body colour of a loaded texture (nil until loaded): the cheap tint fallback divides by it.
function Texture.baseOf(textureId: string): {number}?
    local s = sources[textureId]
    return if type(s) == "table" then s.base else nil
end
function Texture.hasPositions(textureId: string): boolean?
    local s = sources[textureId]
    return if type(s) == "table" then s.pos ~= nil else nil
end
return Texture
