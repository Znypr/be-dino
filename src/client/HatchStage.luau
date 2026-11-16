--!strict
-- BD-1211 (BD-1206 cohesion order step 1, docs/240 R1/R2/R3/R7, style tile v2 boards 2-4): with Config.HatchStageEnabled the hatch is a full
-- STAGE over the world, not a window: the shared modal's stud body, frame and header strip are hidden while the hatch is open, the dark scrim
-- becomes a light veil with soft rays (the uploaded fx3 rays picture) behind the egg, "Egg 2 of 5" sits in a cream chip at the top, and every
-- dark plate or chip the hatch builds (colour and pattern buckets, labels, "Skip the rest") is turned into the one style: cream plate with an ink
-- outline and ink text, buttons grey (the green NEXT EGG stays green). The X stays (red, top right of the stage).
-- Bootstrap calls apply() when the hatch opens and restore() whenever any screen opens or the modal closes, so every other screen keeps its
-- window exactly as before. Flag off = this file is never required.
local TweenService = game:GetService("TweenService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Effects = require(Shared:WaitForChild("EffectAssets"))

local Stage = {}
Stage.Cream = Color3.fromRGB(255, 247, 227)
Stage.Ink = Color3.fromRGB(46, 38, 30)
Stage.Grey = Color3.fromRGB(196, 200, 208)
Stage.Veil = .78 -- scrim transparency on the stage (the window used .42): the world stays visible under the rays

local function luminance(c: Color3): number return .299 * c.R + .587 * c.G + .114 * c.B end
-- true for the dark navy / slate plates the old window style used (R1)
function Stage.isDark(c: Color3): boolean return luminance(c) < .42 end
-- true for a green "main" button (kept: one green button per screen, R3)
function Stage.isGreen(c: Color3): boolean return c.G > .5 and c.G > c.R * 1.25 and c.G > c.B * 1.25 end

local state: {restore: {() -> ()}, conns: {RBXScriptConnection}}? = nil

local function painted(o: Instance, stop: Instance): GuiObject?
    local node: Instance? = o
    while node and node ~= stop do
        if node:IsA("GuiObject") and node.BackgroundTransparency < .9 then return node end
        node = node.Parent
    end
    return nil
end
-- One object to the style: dark plates -> cream + ink outline, dark buttons -> grey, light text on cream -> ink.
local function style(o: Instance, stop: Instance)
    if not o:IsA("GuiObject") then return end
    if o.BackgroundTransparency < .9 and Stage.isDark(o.BackgroundColor3) and o.AbsoluteSize.X < 700 then
        local isButton = o:IsA("TextButton") or o:IsA("ImageButton")
        o.BackgroundColor3 = if isButton then Stage.Grey else Stage.Cream
        local stroke = o:FindFirstChildOfClass("UIStroke") or Instance.new("UIStroke")
        stroke.Color, stroke.Thickness, stroke.ApplyStrokeMode, stroke.Transparency = Stage.Ink, 2, Enum.ApplyStrokeMode.Border, 0
        stroke.Parent = o
        if not o:FindFirstChildOfClass("UICorner") then
            local corner = Instance.new("UICorner")
            corner.CornerRadius = UDim.new(0, 10)
            corner.Parent = o
        end
    end
    if (o:IsA("TextLabel") or o:IsA("TextButton")) and luminance(o.TextColor3) > .7 then
        local plate = painted(o, stop)
        if plate and (plate.BackgroundColor3 == Stage.Cream or plate.BackgroundColor3 == Stage.Grey) then
            o.TextColor3 = Stage.Ink
            o.TextStrokeTransparency = 1
            for _, child in o:GetChildren() do if child:IsA("UIStroke") and child.ApplyStrokeMode == Enum.ApplyStrokeMode.Contextual then child.Enabled = false end end
        end
    end
end
function Stage.styleTree(root: Instance)
    style(root, root)
    for _, o in root:GetDescendants() do style(o, root) end
end

export type Parts = {gui: ScreenGui, shade: GuiObject, panel: GuiObject, header: GuiObject, heading: GuiObject, body: GuiObject, reduceMotion: boolean}
function Stage.apply(p: Parts)
    Stage.restore()
    local restore: {() -> ()} = {}
    local conns: {RBXScriptConnection} = {}
    local function keep(object: Instance, property: string, value: any)
        local ok, before = pcall(function() return (object :: any)[property] end)
        if not ok then return end -- the object has no such property (a stroke has no Visible)
        table.insert(restore, function() pcall(function() (object :: any)[property] = before end) end)
        pcall(function() (object :: any)[property] = value end)
    end
    -- chrome off: panel plate + its Toybox pictures (stud body, frame), header strip and its title (the X keeps its own picture)
    keep(p.panel, "BackgroundTransparency", 1)
    keep(p.header, "BackgroundTransparency", 1)
    keep(p.heading, "Visible", false)
    for _, child in p.panel:GetChildren() do
        if child:IsA("ImageLabel") or child:IsA("UIStroke") then keep(child, "Visible", false) keep(child, "Enabled", false) end
    end
    for _, child in p.header:GetChildren() do
        if child:IsA("ImageLabel") or child:IsA("UIStroke") then keep(child, "Visible", false) keep(child, "Enabled", false) end
    end
    -- the scrim: a light veil instead of the dark window backdrop (Bootstrap animates it to .42 on open; set it after that tween)
    task.delay(.2, function()
        if state and state.restore == restore then keep(p.shade, "BackgroundTransparency", Stage.Veil) end
    end)
    -- a soft warm glow behind the egg (real art: the uploaded neutral radial glow plate); it breathes gently, still with Reduce Motion
    local rays = Instance.new("ImageLabel")
    rays.Name, rays.BackgroundTransparency, rays.Image = "HatchStageRays", 1, Effects.Requested.glowPlate.id
    rays.AnchorPoint, rays.Position, rays.Size = Vector2.new(.5, .5), UDim2.fromScale(.5, .46), UDim2.fromOffset(760, 760)
    rays.ImageColor3, rays.ImageTransparency, rays.ZIndex = Color3.fromRGB(255, 244, 200), .35, p.body.ZIndex
    rays.Parent = p.panel
    table.insert(restore, function() rays:Destroy() end)
    if not p.reduceMotion then
        local spin = TweenService:Create(rays, TweenInfo.new(2.4, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true), {ImageTransparency = .55})
        spin:Play()
        table.insert(restore, function() spin:Cancel() end)
    end
    -- "Egg N of M": the counter HatchSequence puts in the header becomes a cream chip at the top centre of the stage
    local function chipCounter(o: Instance)
        if o.Name ~= "EggCounter" or not o:IsA("TextLabel") then return end
        o.AnchorPoint, o.Position, o.Size = Vector2.new(.5, 0), UDim2.new(.5, 0, 0, 8), UDim2.fromOffset(170, 36)
        o.TextXAlignment, o.TextSize = Enum.TextXAlignment.Center, 22
        o.BackgroundColor3, o.BackgroundTransparency = Stage.Cream, 0
        style(o, p.panel)
    end
    -- everything the hatch builds now and later (buckets, labels, the end buttons, the Skip layer) follows the style
    local layer = p.gui:FindFirstChild("HatchUiLayer")
    for _, root in {p.body, p.header, layer} do
        if root then
            Stage.styleTree(root)
            for _, o in root:GetDescendants() do chipCounter(o) end
            table.insert(conns, root.DescendantAdded:Connect(function(o)
                task.defer(function()
                    if not o.Parent then return end
                    style(o, root)
                    for _, d in o:GetDescendants() do style(d, root) end
                    chipCounter(o)
                end)
            end))
        end
    end
    if not layer then
        table.insert(conns, p.gui.ChildAdded:Connect(function(o)
            if o.Name == "HatchUiLayer" then
                task.defer(function() Stage.styleTree(o) end)
                table.insert(conns, o.DescendantAdded:Connect(function(d) task.defer(function() if d.Parent then style(d, o) end end) end))
            end
        end))
    end
    state = {restore = restore, conns = conns}
end

-- Back to the window look (any screen opens, or the modal closes). Safe to call when nothing was applied.
function Stage.restore()
    local s = state
    state = nil
    if not s then return end
    for _, c in s.conns do c:Disconnect() end
    for i = #s.restore, 1, -1 do s.restore[i]() end
end
return Stage
