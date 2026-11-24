--!strict
-- BD-1319 (owner 2026-11-23: "the horizon is perfectly visible between trees, which doesn't make sense"; docs/250 s9). Roblox classic fog colours
-- parts and terrain but never the sky, so a crisp sky line showed between fogged trees. This ring of soft bands stands at the fog distance around
-- the camera, painted in the live fog colour: below eye level it is solid (the far land and sea dissolve into it), above eye level it fades out
-- into the sky, so the horizon becomes haze and the island reads bigger. Client-only, no collisions, no shadows, built once; update() only moves
-- and recolours it. Used by WeatherVisuals while Config.BiomeRotationEnabled (the biome looks set the fog).
local HorizonSkirt = {}
HorizonSkirt.Segments = 24
HorizonSkirt.BelowDeg = 25 -- the solid part reaches this far below eye level
HorizonSkirt.AboveDeg = 12 -- the fade reaches this far above eye level
HorizonSkirt.MinRadius, HorizonSkirt.MaxRadius = 60, 1200
HorizonSkirt.RadiusShare = .9 -- of Lighting.FogEnd: inside the fully fogged distance, so the band and the nearly fogged land meet in one colour

export type Skirt = {update: (camera: Vector3, color: Color3, fogEnd: number, visible: boolean) -> ()}

function HorizonSkirt.new(parent: Instance): Skirt
    local folder = Instance.new("Folder")
    folder.Name = "HorizonSkirt"
    folder.Parent = parent
    local n = HorizonSkirt.Segments
    local items: {{part: BasePart, frame: Frame, gui: SurfaceGui, angle: number}} = {}
    for i = 1, n do
        local p = Instance.new("Part")
        p.Name = "Band" .. i
        p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.CastShadow = true, false, false, false, false
        p.Transparency = 1
        p.Size = Vector3.new(1, 1, .2)
        local gui = Instance.new("SurfaceGui")
        gui.Face = Enum.NormalId.Front
        gui.LightInfluence = 0
        gui.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
        gui.PixelsPerStud = .5
        gui.Parent = p
        local frame = Instance.new("Frame")
        frame.Size = UDim2.fromScale(1, 1)
        frame.BorderSizePixel = 0
        frame.Parent = gui
        local below, above = math.tan(math.rad(HorizonSkirt.BelowDeg)), math.tan(math.rad(HorizonSkirt.AboveDeg))
        local split = above / (below + above) -- the eye-level line, from the top
        local grad = Instance.new("UIGradient")
        grad.Rotation = 90 -- top (0) to bottom (1)
        grad.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(split * .45, .55), NumberSequenceKeypoint.new(split * .85, .05), NumberSequenceKeypoint.new(1, 0)})
        grad.Parent = frame
        p.Parent = folder
        items[i] = {part = p, frame = frame, gui = gui, angle = (i - 1) / n * math.pi * 2}
    end
    local lastR, lastColor, shown = -1, Color3.new(), true
    local function update(camera: Vector3, color: Color3, fogEnd: number, visible: boolean)
        if visible ~= shown then
            shown = visible
            for _, it in items do it.gui.Enabled = visible end
        end
        if not visible then return end
        local r = math.clamp(fogEnd * HorizonSkirt.RadiusShare, HorizonSkirt.MinRadius, HorizonSkirt.MaxRadius)
        local below, above = math.tan(math.rad(HorizonSkirt.BelowDeg)) * r, math.tan(math.rad(HorizonSkirt.AboveDeg)) * r
        if math.abs(r - lastR) > .5 then
            lastR = r
            local w = 2 * r * math.tan(math.pi / n) + 2
            for _, it in items do it.part.Size = Vector3.new(w, below + above, .2) end
        end
        if color ~= lastColor then
            lastColor = color
            for _, it in items do it.frame.BackgroundColor3 = color end
        end
        local mid = (above - below) / 2
        for _, it in items do
            local pos = camera + Vector3.new(math.cos(it.angle) * r, mid, math.sin(it.angle) * r)
            it.part.CFrame = CFrame.lookAt(pos, Vector3.new(camera.X, pos.Y, camera.Z))
        end
    end
    return {update = update}
end

return HorizonSkirt
