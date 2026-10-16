--!nocheck
-- BD-411 PALETTE probe (docs/114 s5). Run with execute_luau (Server, Play mode) in YOUR OWN temp Studio copy (CaveHub = true for the cave).
-- For every distinct generated prop (cave props + island world kit) read the colour texture with EditableImage (a 1/16 sample of the
-- pixels) and print dominant hue bucket data. A prop with no texture (flat Color) reports that colour. The rules live in
-- src/shared/AssetPalette.luau; tools/qa/palette_report.py applies them to the saved output.
-- Row: COL <place> <key> <source> <samples> <meanS> <meanV> <neutralShare> <hist of 12 hue buckets of 30 degrees among S>0.2,V>0.15>
local AssetService = game:GetService("AssetService")
local function hsv(r, g, b)
    local mx, mn = math.max(r, g, b), math.min(r, g, b)
    local d = mx - mn
    local h = 0
    if d > 0 then
        if mx == r then h = ((g - b) / d) % 6 elseif mx == g then h = (b - r) / d + 2 else h = (r - g) / d + 4 end
        h = h * 60
    end
    return h, (mx == 0 and 0 or d / mx), mx
end
local function stats(meshOrId)
    local id = meshOrId
    local ok, img = pcall(function() return AssetService:CreateEditableImageAsync(Content.fromUri(id)) end)
    if not ok then return nil, "load failed" end
    local size = img.Size
    local buf = img:ReadPixelsBuffer(Vector2.zero, size)
    local hist, n, sS, sV, neutral = table.create(12, 0), 0, 0, 0, 0
    local step = 16
    for y = 0, size.Y - 1, step do
        for x = 0, size.X - 1, step do
            local o = (y * size.X + x) * 4
            if buffer.readu8(buf, o + 3) > 128 then
                local h, s, v = hsv(buffer.readu8(buf, o) / 255, buffer.readu8(buf, o + 1) / 255, buffer.readu8(buf, o + 2) / 255)
                n += 1 sS += s sV += v
                if s > 0.2 and v > 0.15 then hist[math.min(12, math.floor(h / 30) + 1)] += 1 else neutral += 1 end
            end
        end
    end
    img:Destroy()
    if n == 0 then return nil, "empty" end
    return {n = n, s = sS / n, v = sV / n, neutral = neutral / n, hist = hist}
end
local seen, lines = {}, {}
local function row(place, key, mesh)
    local tag = place .. key
    if seen[tag] then return end
    seen[tag] = true
    local sa = mesh:FindFirstChildWhichIsA("SurfaceAppearance")
    local id = if sa and sa.ColorMap ~= "" then sa.ColorMap elseif mesh.TextureID ~= "" then mesh.TextureID else nil
    if id then
        local st, err = stats(id)
        if st then
            table.insert(lines, string.format("COL\t%s\t%s\ttexture\t%d\t%.3f\t%.3f\t%.3f\t%s", place, key, st.n, st.s, st.v, st.neutral, table.concat(st.hist, ",")))
        else
            table.insert(lines, string.format("ERR\t%s\t%s\t%s", place, key, err))
        end
    else
        local h, s, v = hsv(mesh.Color.R, mesh.Color.G, mesh.Color.B)
        local hist = table.create(12, 0)
        if s > 0.2 and v > 0.15 then hist[math.min(12, math.floor(h / 30) + 1)] = 1000 end
        table.insert(lines, string.format("COL\t%s\t%s\tflat\t1000\t%.3f\t%.3f\t%.3f\t%s", place, key, s, v, (s > 0.2 and v > 0.15) and 0 or 1, table.concat(hist, ",")))
    end
end
local arena = workspace:FindFirstChild("BeDinoArena")
local caveProps = arena and arena:FindFirstChild("Sanctuary") and arena.Sanctuary:FindFirstChild("CaveProps")
if caveProps then
    for _, m in caveProps:GetChildren() do if m:IsA("MeshPart") then row("cave", m.Name, m) end end
end
local kit = arena and arena:FindFirstChild("WorldKit")
if kit then
    for _, m in kit:GetChildren() do
        if m:IsA("Model") and m:GetAttribute("GeneratedMesh") then
            local mesh = m:FindFirstChildWhichIsA("MeshPart")
            if mesh then row("island", m:GetAttribute("GeneratedMesh"), mesh) end
        end
    end
end
return table.concat(lines, "\n")
