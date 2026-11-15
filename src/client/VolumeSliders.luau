--!strict
-- Settings volume rows (Everything / Sounds / Weather). One draggable bar per AudioMixer channel; drag or tap to set,
-- the level applies live through the SoundGroups. Lives in its own module because Bootstrap.client is at the 200-local limit.
local UserInputService = game:GetService("UserInputService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Theme = require(Shared:WaitForChild("UITheme"))
local Mixer = require(Shared:WaitForChild("AudioMixer"))
local C = Theme.Colors

local Sliders = {}

local function text(parent: Instance, value: string, x: number, w: number, h: number, size: number, align: Enum.TextXAlignment, z: number): TextLabel
    local t = Instance.new("TextLabel")
    t.BackgroundTransparency, t.Position, t.Size, t.Text = 1, UDim2.fromOffset(x, 0), UDim2.fromOffset(w, h), value
    t.Font, t.TextSize, t.TextColor3, t.TextXAlignment, t.ZIndex = Enum.Font.FredokaOne, size, C.text, align, z
    t.TextStrokeTransparency, t.TextStrokeColor3, t.Parent = 0, C.outline, parent
    return t
end

-- One row at (x, y), width w, height 40. `onChange` fires after every level change (for a preview tick).
-- BD-1205: `look` (the Toybox Settings panel, cream): {labelW, valueW, textSize} = label left, slider, value right on ONE row, dark ink with no outline,
-- a cream track with a dark outline; nil = the row exactly as before.
function Sliders.row(parent: Instance, key: string, x: number, y: number, w: number, z: number, onChange: (() -> ())?, look: {labelW: number, valueW: number, textSize: number}?): Frame
    local row = Instance.new("Frame")
    row.Name, row.BackgroundTransparency, row.Position, row.Size, row.ZIndex = "Volume_" .. key, 1, UDim2.fromOffset(x, y), UDim2.fromOffset(w, 40), z
    row.Parent = parent
    local name = text(row, Mixer.Labels[key] or key, 0, if look then look.labelW else 190, 40, if look then look.textSize else 26, Enum.TextXAlignment.Left, z + 1)
    local percent = text(row, Mixer.percent(Mixer.get(key)), w - (if look then look.valueW else 90), if look then look.valueW else 90, 40, if look then look.textSize else 24, Enum.TextXAlignment.Right, z + 1)
    local trackX, trackW = 200, w - 200 - 100
    if look then trackX, trackW = look.labelW + 12, w - look.labelW - look.valueW - 24 end
    if look then
        local Layout = require(Shared:WaitForChild("ToyboxLayout"))
        Layout.ink(name)
        Layout.ink(percent)
    end
    local track = Instance.new("Frame")
    track.BackgroundColor3, track.Position, track.Size, track.Active, track.ZIndex = C.card, UDim2.fromOffset(trackX, 14), UDim2.fromOffset(trackW, 14), true, z + 1
    track.Parent = row
    if look then
        local Layout = require(Shared:WaitForChild("ToyboxLayout"))
        track.BackgroundColor3 = Layout.tone("slot")
        local round = Instance.new("UICorner") round.CornerRadius = UDim.new(0, 7) round.Parent = track
        local line = Instance.new("UIStroke") line.Color, line.Thickness, line.Parent = Color3.fromRGB(13, 15, 20), 2, track
    else
        Theme.decorate(track, 7)
    end
    local fill = Instance.new("Frame")
    fill.BackgroundColor3, fill.BorderSizePixel, fill.ZIndex, fill.Parent = C.accent, 0, z + 2, track
    local fillCorner = Instance.new("UICorner") fillCorner.CornerRadius = UDim.new(0, 7) fillCorner.Parent = fill
    local knob = Instance.new("Frame")
    knob.AnchorPoint, knob.Size, knob.BackgroundColor3, knob.ZIndex = Vector2.new(.5, .5), UDim2.fromOffset(30, 30), C.gold, z + 3
    knob.Parent = track
    if look then
        local round = Instance.new("UICorner") round.CornerRadius = UDim.new(0, 15) round.Parent = knob
        local line = Instance.new("UIStroke") line.Color, line.Thickness, line.Parent = Color3.fromRGB(13, 15, 20), 2, knob
    else
        Theme.decorate(knob, 15)
    end
    local function show()
        local v = Mixer.get(key)
        fill.Size, knob.Position = UDim2.fromScale(v, 1), UDim2.fromScale(v, .5)
        percent.Text = Mixer.percent(v)
    end
    show()
    -- 44+ px touch target around the thin track.
    local hit = Instance.new("TextButton")
    hit.Text, hit.BackgroundTransparency, hit.AutoButtonColor, hit.ZIndex = "", 1, false, z + 4
    hit.Position, hit.Size, hit.Parent = UDim2.fromOffset(-12, -14), UDim2.new(1, 24, 0, 44), track
    local dragging = false
    local function apply(px: number)
        Mixer.set(key, (px - track.AbsolutePosition.X) / math.max(1, track.AbsoluteSize.X))
        show()
        if onChange then onChange() end
    end
    hit.InputBegan:Connect(function(input)
        if input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch then
            dragging = true
            apply(input.Position.X)
        end
    end)
    local moved = UserInputService.InputChanged:Connect(function(input)
        if dragging and (input.UserInputType == Enum.UserInputType.MouseMovement or input.UserInputType == Enum.UserInputType.Touch) then
            apply(input.Position.X)
        end
    end)
    local ended = UserInputService.InputEnded:Connect(function(input)
        if dragging and (input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch) then
            dragging = false
        end
    end)
    row.Destroying:Connect(function() moved:Disconnect() ended:Disconnect() end)
    return row
end

return Sliders
