--!strict
-- BD-225: builds a gene-coloured copy of a generated low-poly part texture (EditableImage, 256x256, cached per texture + colour).
-- Eyes (black) and belly (cream) pass through LowPolyRecolor untouched. Any failure (no permission, load error) returns nil and the
-- caller keeps the model's original texture, which still has its eyes and belly. Yields: call from task.spawn, never inline.
local AssetService = game:GetService("AssetService")
local Recolor = require(script.Parent.LowPolyRecolor)
local Texture = {}
local SIZE = 256
local MAX_BAKED = 160
local sources: {[string]: any} = {}   -- textureId -> {buf = buffer} | "loading" | "failed"
local baked: {[string]: any} = {}
local bakedCount = 0
local function source(textureId: string): any?
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
        for y = 0, SIZE - 1 do
            local sy = math.min(full.Y - 1, math.floor((y + 0.5) * full.Y / SIZE))
            for x = 0, SIZE - 1 do
                local sx = math.min(full.X - 1, math.floor((x + 0.5) * full.X / SIZE))
                buffer.writeu32(small, (y * SIZE + x) * 4, buffer.readu32(raw, (sy * full.X + sx) * 4))
            end
        end
        img:Destroy()
        return {buf = small}
    end)
    sources[textureId] = if ok then result else "failed"
    return if ok then result else nil
end
function Texture.key(textureId: string, c: Color3): string
    return string.format("%s|%d,%d,%d", textureId, math.floor(c.R * 15 + 0.5), math.floor(c.G * 15 + 0.5), math.floor(c.B * 15 + 0.5))
end
function Texture.bake(textureId: string, speciesId: string, color: Color3): Content?
    local key = Texture.key(textureId, color)
    local hit = baked[key]
    if hit then return Content.fromObject(hit) end
    if bakedCount >= MAX_BAKED then return nil end
    local src = source(textureId)
    if not src then return nil end
    hit = baked[key]
    if hit then return Content.fromObject(hit) end
    local ok, image = pcall(function()
        local out = buffer.create(SIZE * SIZE * 4)
        local base = Recolor.baseOf(speciesId)
        local tr, tg, tb = color.R, color.G, color.B
        for i = 0, SIZE * SIZE - 1 do
            local o = i * 4
            local r, g, b = buffer.readu8(src.buf, o) / 255, buffer.readu8(src.buf, o + 1) / 255, buffer.readu8(src.buf, o + 2) / 255
            r, g, b = Recolor.pixel(r, g, b, tr, tg, tb, base)
            buffer.writeu8(out, o, math.floor(r * 255 + 0.5))
            buffer.writeu8(out, o + 1, math.floor(g * 255 + 0.5))
            buffer.writeu8(out, o + 2, math.floor(b * 255 + 0.5))
            buffer.writeu8(out, o + 3, 255)
        end
        local img = AssetService:CreateEditableImage({Size = Vector2.new(SIZE, SIZE)})
        img:WritePixelsBuffer(Vector2.zero, Vector2.new(SIZE, SIZE), out)
        return img
    end)
    if not ok then return nil end
    baked[key] = image
    bakedCount += 1
    return Content.fromObject(image)
end
return Texture
