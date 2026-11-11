--!strict
-- BD-225 / BD-061 / BD-306: bakes a gene-coloured, gene-patterned (and fused-tier tinted) copy of each generated low-poly part
-- texture as an EditableImage. Pixel maths is pure (LowPolyRecolor, LowPolyPattern, LowPolyTier; tested offline); this module only
-- owns the Roblox side: reading the source textures once, yielding bakes, and the image budget.
-- Budget (BD-306, measured in a Play client of the owner's Studio, docs/105 s3): EditableImage AND EditableMesh share ONE budget of
-- 80 MiB per client. The image count never mattered (5,119 x 64 px and 320 x 256 px both stop at 80 MiB); an EditableMesh costs
-- about 1 KiB per face (a Compy body = 3 MiB), which is why a per-species mesh atlas was measured and rejected. So a dino bakes
-- its body and head at 256 px (256 KiB each) and every other part at 128 px (64 KiB): about 0.8 MiB per distinct dino, no mesh
-- kept alive. Bakes live in two PatternAtlasCaches (reference counted, warm LRU): Texture.BigCap x 256 KiB + Texture.SmallCap x
-- 64 KiB, plus at most Texture.MaxReads source reads in flight (a 1024 px source image 4 MiB + its transient position-map mesh up
-- to 5.5 MiB each): worst case stays under half the budget (tools/verify_lowpoly_budget.py), leaving room for PatternGenes' egg
-- textures and anything else. When a cache is full acquire returns nil and the caller uses the cheap fallback (original species
-- texture tinted by MeshPart.Color). Any failure (no permission, nil image = budget, load error) also returns nil: eyes/belly are
-- always on screen because the original texture stays. Failed reads are retried after Texture.RetryAfter seconds.
-- Yields: call acquire from task.spawn, never inline.
local AssetService = game:GetService("AssetService")
local Recolor = require(script.Parent.LowPolyRecolor)
local Pattern = require(script.Parent.LowPolyPattern)
local Tier = require(script.Parent.LowPolyTier)
local Look = require(script.Parent.MutationLook)
local Cache = require(script.Parent.PatternAtlasCache)
local Texture = {}
Texture.BigSize = Pattern.Size -- body and head: 256 px (eyes, facets)
Texture.SmallSize = 128        -- tail, legs, arms, wings, flippers, neck
Texture.BigCap = 48            -- 24 dinos' bodies + heads = 12 MiB
Texture.SmallCap = 120         -- 24 dinos' five small parts = 7.5 MiB
Texture.BudgetMiB = 80         -- measured engine budget per client, shared by every EditableImage and EditableMesh in the game
Texture.MaxReads = 2           -- source reads (image + mesh) in flight at once; 12 parallel reads starved the budget in testing
Texture.RetryAfter = 20        -- s before a failed source read (budget, transient load error, permission) is tried again
local function destroyImage(image) pcall(function() image:Destroy() end) end
local big = Cache.new(Texture.BigCap, destroyImage)
local small = Cache.new(Texture.SmallCap, destroyImage)
local sources: {[string]: any} = {}   -- textureId@size -> {buf, weights, pos, base, size} | "loading" | {failedAt = t}
local pending: {[string]: boolean} = {} -- bake keys in flight (a second part with the same key waits instead of baking twice)
local reading = 0
-- Geometry of the TEMPLATE part (unscaled, unposed) so the 3D pattern reads its model-space position: meshId, cframe relative to the
-- model centre, scale = part.Size / part.MeshSize, norm = 1 / longest model side.
export type Geom = {meshId: string, cframe: CFrame, scale: Vector3, norm: number}
export type Spec = {primary: Color3, secondary: Color3, same: boolean, primaryShare: number, patternId: string, tier: string?, seedName: string, own: boolean?, mutation: string?}
-- Test hook (Studio only, BD-309): workspace attribute LowPolyDenyEditable = "mesh" | "image" | "all" simulates a server that may
-- not open the owner's assets (CreateEditableMeshAsync / CreateEditableImageAsync return nil), so the fallbacks can be exercised
-- without a second account: "mesh" -> UV-space (jigsaw) patterns, "image" / "all" -> plain tint.
local function denied(what: string): boolean
    local ok, v = pcall(function() return workspace:GetAttribute("LowPolyDenyEditable") end)
    return ok and (v == what or v == "all")
end
-- Bake size per part role: body and head keep the full 256 px (eyes, most facets), everything else 128 px.
function Texture.sizeFor(role: string): number
    return if role == "body" or role == "head" then Texture.BigSize else Texture.SmallSize
end
local function cacheFor(size: number) return if size >= Texture.BigSize then big else small end
local function publish()
    pcall(function()
        local b, s = big:stats(), small:stats()
        workspace:SetAttribute("LowPolyImagesLive", b.live + s.live) workspace:SetAttribute("LowPolyImagesPinned", b.pinned + s.pinned)
        workspace:SetAttribute("LowPolyImagesMiB", math.floor(Texture.stats().mib * 100 + 0.5) / 100)
        workspace:SetAttribute("LowPolyCacheHits", b.hits + s.hits) workspace:SetAttribute("LowPolyCacheMisses", b.misses + s.misses)
        workspace:SetAttribute("LowPolyCacheDenied", b.denied + s.denied)
    end)
end
function Texture.stats()
    local b, s = big:stats(), small:stats()
    return {big = b, small = s, live = b.live + s.live, pinned = b.pinned + s.pinned, denied = b.denied + s.denied,
        mib = (b.live * Texture.BigSize ^ 2 + s.live * Texture.SmallSize ^ 2) * 4 / 1048576}
end
-- Triangles {u1,v1,x1,y1,z1, ...} of one part in its own UV space with normalised model positions. The EditableMesh is transient
-- (destroyed right after: nothing references it, so the PR #117 cube bug cannot apply). nil on any failure: UV-space pattern.
local function triangles(geom: Geom?): {{number}}?
    if not geom or geom.meshId == "" or denied("mesh") then return nil end
    local ok, tris = pcall(function()
        local mesh = AssetService:CreateEditableMeshAsync(Content.fromUri(geom.meshId))
        if not mesh then error("no mesh (budget or permission)") end
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
        return tris
    end)
    if not ok then warn("[Be Dino] low-poly mesh " .. geom.meshId .. " unreadable (UV-space pattern): " .. tostring(tris)) end
    return if ok then tris else nil
end
-- Source texture at `size` px (downsampled once from the 1024 px asset), body weights, measured species body colour and the
-- position map. The read (image + mesh) is throttled to MaxReads at once. nil when the texture cannot be read (retried later).
local function source(textureId: string, size: number, geom: Geom?): any?
    local key = textureId .. "@" .. size
    local state = sources[key]
    while state == "loading" do task.wait(0.05) state = sources[key] end
    if type(state) == "table" and state.failedAt then
        if os.clock() - state.failedAt < Texture.RetryAfter then return nil end
        state = nil
    end
    if state then return state end
    if denied("image") then sources[key] = {failedAt = os.clock()} return nil end
    sources[key] = "loading"
    while reading >= Texture.MaxReads do task.wait(0.05) end
    reading += 1
    local okRead, read = pcall(function()
        local img = AssetService:CreateEditableImageAsync(Content.fromUri(textureId))
        if not img then error("no image (budget or permission)") end
        local full = img.Size
        local raw = img:ReadPixelsBuffer(Vector2.zero, full)
        img:Destroy()
        return {full = full, raw = raw, tris = triangles(geom)}
    end)
    reading -= 1
    if not okRead then
        sources[key] = {failedAt = os.clock()}
        warn("[Be Dino] low-poly texture " .. textureId .. " unreadable (tint fallback, retry in " .. Texture.RetryAfter .. " s): " .. tostring(read))
        return nil
    end
    local ok, result = pcall(function()
        local full, raw = read.full, read.raw
        local buf = buffer.create(size * size * 4)
        local weights = table.create(size * size, 0)
        for y = 0, size - 1 do
            local sy = math.min(full.Y - 1, math.floor((y + 0.5) * full.Y / size))
            for x = 0, size - 1 do
                local sx = math.min(full.X - 1, math.floor((x + 0.5) * full.X / size))
                local o = (y * size + x) * 4
                buffer.writeu32(buf, o, buffer.readu32(raw, (sy * full.X + sx) * 4))
                weights[y * size + x + 1] = Recolor.bodyWeight(buffer.readu8(buf, o) / 255, buffer.readu8(buf, o + 1) / 255, buffer.readu8(buf, o + 2) / 255)
            end
            if y % 32 == 31 then task.wait() end
        end
        -- the species' own body colour, measured from this texture (replaces a hand table: every generated species recolours)
        local sr, sg, sb, sw = 0, 0, 0, 0
        for i = 1, size * size do
            local w = weights[i]
            if w > 0.5 then
                local o = (i - 1) * 4
                sr += buffer.readu8(buf, o) / 255 * w sg += buffer.readu8(buf, o + 1) / 255 * w sb += buffer.readu8(buf, o + 2) / 255 * w sw += w
            end
        end
        local base = if sw > 50 * (size / Pattern.Size) ^ 2 then {sr / sw, sg / sw, sb / sw} else nil
        local pos = if read.tris and #read.tris > 0 then Pattern.rasterize(read.tris, size) else nil
        return {buf = buf, weights = weights, pos = pos, base = base, size = size}
    end)
    if not ok then
        sources[key] = {failedAt = os.clock()}
        warn("[Be Dino] low-poly texture " .. textureId .. " bake prep failed (tint fallback): " .. tostring(result))
        return nil
    end
    sources[key] = result
    return result
end
local function q(c: Color3): string
    return string.format("%d,%d,%d", math.floor(c.R * 31 + 0.5), math.floor(c.G * 31 + 0.5), math.floor(c.B * 31 + 0.5))
end
-- Stable cache key: everything that changes the pixels. Pure (tested): same spec -> same key, any change -> a different key.
function Texture.key(textureId: string, spec: Spec): string
    return string.format("%s|%s|%s|%s|%s|%d|%s", textureId, spec.patternId, q(spec.primary), q(spec.secondary), if spec.same then "s" else "d",
        math.floor(math.clamp(spec.primaryShare, 0, 1) * 20 + 0.5), (spec.tier or "base") .. (if spec.own then "|own" else "") .. (if spec.mutation then "|m:" .. spec.mutation else ""))
end
-- Pure pixel pass (shared with the verifier through LowPolyRecolor/LowPolyPattern/LowPolyTier): writes the baked RGBA into out.
-- size defaults to Pattern.Size.
function Texture.paint(src: buffer, weights: {number}, mask: {number}, spec: Spec, base: {number}, out: buffer, onRow: ((number) -> ())?, size: number?, pos: buffer?, species: string?)
    local size = size or Pattern.Size
    local a, b = spec.primary, spec.secondary
    local ar, ag, ab, br, bg, bb = a.R, a.G, a.B, b.R, b.G, b.B
    if spec.same then -- same-family genes: pattern regions read as a lighter / darker version of the one colour (PatternGenes rule)
        ar, ag, ab = ar * 0.86, ag * 0.86, ab * 0.86
        br, bg, bb = math.min(1, br * 1.08 + 0.05), math.min(1, bg * 1.08 + 0.05), math.min(1, bb * 1.08 + 0.05)
    end
    if spec.own then ar, ag, ab, br, bg, bb = base[1], base[2], base[3], base[1], base[2], base[3] end -- no genes: the tier tints the species' own colour
    local tier = Tier.get(spec.tier)
    local mutationId = if tier then nil else spec.mutation -- fused tiers never get a mutation tint (docs/46, MutationLook)
    for y = 0, size - 1 do
        if onRow then onRow(y) end
        for x = 0, size - 1 do
            local i = y * size + x
            local o = i * 4
            local r, g, bl = buffer.readu8(src, o) / 255, buffer.readu8(src, o + 1) / 255, buffer.readu8(src, o + 2) / 255
            local accent = false
            if tier and pos and species and buffer.readu8(pos, o + 3) == 255 and (r + r + r + g + g + g + bl) / 7 > 0.15 then -- dark texels = eyes: never
                local px, py, pz = buffer.readu8(pos, o) / 127.5 - 1, buffer.readu8(pos, o + 1) / 127.5 - 1, buffer.readu8(pos, o + 2) / 127.5 - 1
                if Tier.inAccentRegion(species, px, py, pz) then
                    accent = true
                    r, g, bl = Tier.regionColor(r, g, bl, tier, Recolor.shade(r, g, bl, base), (x + y) / (2 * size), py, px, pz)
                end
            end
            -- 2026-10-16 FINAL owner rule: body and pattern texels are the dino's own colours at EVERY tier (identical to base);
            -- the tier is the translucent glossy shell (LowPolyDinos) plus these solid horn / claw texels.
            if accent then -- horns / claws painted in the tier metal or gem (base tier never gets here)
            elseif weights[i + 1] > 0 then
                local m = mask[i + 1]
                local tr, tg, tb = ar + (br - ar) * m, ag + (bg - ag) * m, ab + (bb - ab) * m
                if mutationId then tr, tg, tb = Look.pull(tr, tg, tb, mutationId) end -- BD-518: Part.Color cannot tint a baked texture, so the event mutation is baked in
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
local partEntry = setmetatable({} :: {[Instance]: any}, {__mode = "k"})
local cacheOf = setmetatable({} :: {[any]: any}, {__mode = "k"}) -- entry -> the cache it lives in
local hooked = setmetatable({} :: {[Instance]: boolean}, {__mode = "k"})
function Texture.release(part: Instance)
    local entry = partEntry[part]
    if not entry then return end
    partEntry[part] = nil
    local cache = cacheOf[entry] or big
    cache:release(entry)
    publish()
end
local function pin(part: Instance, entry): Content
    Texture.release(part)
    partEntry[part] = entry
    if not hooked[part] then hooked[part] = true part.Destroying:Once(function() Texture.release(part) end) end
    publish()
    return Content.fromObject(entry.image)
end
-- Content for `part` (pinned to it until release/Destroying) or nil (cache full / failed / no permission): caller keeps a fallback.
-- size: Texture.sizeFor(role) (default 256).
-- wanted (BD-1066): asked again just before the result is pinned to the part. A bake that finished LATE (the genes or the mutation changed
-- meanwhile) must not pin: pinning releases the part's CURRENT entry, which then looks unused (warm), gets evicted under cache pressure and
-- its destroyed image leaves the part showing black. When not wanted the entry is handed back and nil is returned.
function Texture.acquire(part: Instance, textureId: string, speciesId: string, spec: Spec, geom: Geom?, size: number?, wanted: (() -> boolean)?): Content?
    local size = size or Texture.BigSize
    local cache = cacheFor(size)
    local key = Texture.key(textureId, spec) .. "@" .. size
    local current = partEntry[part]
    if current and current.key == key then return Content.fromObject(current.image) end
    while pending[key] do task.wait(0.1) end
    local entry = cache:acquire(key)
    if entry then
        if wanted and not wanted() then cache:release(entry) return nil end
        return pin(part, entry)
    end
    if cache:free() <= 0 then cache.denied += 1 publish() return nil end
    pending[key] = true
    local ok, image = pcall(function()
        local src = source(textureId, size, geom)
        if not src then return nil end
        local okMask, mask = pcall(Pattern.compute, spec.patternId, Pattern.seed(spec.seedName), src.weights, spec.primaryShare, spec.same, yielder(), src.pos, size)
        if not okMask then mask = table.create(size * size, 0) end -- pattern failure: plain colours, never nothing
        local out = buffer.create(size * size * 4)
        Texture.paint(src.buf, src.weights, mask, spec, src.base or Recolor.baseOf(speciesId), out, yielder(), size, src.pos, speciesId)
        if not cache:reserve() then return nil end
        local img = AssetService:CreateEditableImage({Size = Vector2.new(size, size)})
        if not img then return nil end -- budget (shared with every EditableImage/EditableMesh in the game): tint fallback
        img:WritePixelsBuffer(Vector2.zero, Vector2.new(size, size), out)
        return img
    end)
    pending[key] = nil
    if not ok then warn("[Be Dino] low-poly bake failed for " .. speciesId .. " (tint fallback): " .. tostring(image)) end
    if not ok or not image then publish() return nil end
    entry = cache:insert(key, image)
    cacheOf[entry] = cache
    if wanted and not wanted() then cache:release(entry) publish() return nil end
    return pin(part, entry)
end
-- Measured body colour of a loaded texture (nil until loaded): the cheap tint fallback divides by it.
function Texture.baseOf(textureId: string): {number}?
    for _, size in {Texture.BigSize, Texture.SmallSize} do
        local s = sources[textureId .. "@" .. size]
        if type(s) == "table" and s.buf then return s.base end
    end
    return nil
end
function Texture.hasPositions(textureId: string): boolean?
    for _, size in {Texture.BigSize, Texture.SmallSize} do
        local s = sources[textureId .. "@" .. size]
        if type(s) == "table" and s.buf then return s.pos ~= nil end
    end
    return nil
end
return Texture
