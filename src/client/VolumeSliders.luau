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
function Sliders.row(parent: Instance, key: string, x: number, y: number, w: number, z: number, onChange: (() -> ())?): Frame
    local row = Instance.new("Frame")
    row.Name, row.BackgroundTransparency, row.Position, row.Size, row.ZIndex = "Volume_" .. key, 1, UDim2.fromOffset(x, y), UDim2.fromOffset(w, 40), z
    row.Parent = parent
    text(row, Mixer.Labels[key] or key, 0, 190, 40, 26, Enum.TextXAlignment.Left, z + 1)
    local percent = text(row, Mixer.percent(Mixer.get(key)), w - 90, 90, 40, 24, Enum.TextXAlignment.Right, z + 1)
    local trackX, trackW = 200, w - 200 - 100
    local track = Instance.new("Frame")
    track.BackgroundColor3, track.Position, track.Size, track.Active, track.ZIndex = C.card, UDim2.fromOffset(trackX, 14), UDim2.fromOffset(trackW, 14), true, z + 1
    track.Parent = row
    Theme.decorate(track, 7)
    local fill = Instance.new("Frame")
    fill.BackgroundColor3, fill.BorderSizePixel, fill.ZIndex, fill.Parent = C.accent, 0, z + 2, track
    local fillCorner = Instance.new("UICorner") fillCorner.CornerRadius = UDim.new(0, 7) fillCorner.Parent = fill
    local knob = Instance.new("Frame")
    knob.AnchorPoint, knob.Size, knob.BackgroundColor3, knob.ZIndex = Vector2.new(.5, .5), UDim2.fromOffset(30, 30), C.gold, z + 3
    knob.Parent = track
    Theme.decorate(knob, 15)
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
