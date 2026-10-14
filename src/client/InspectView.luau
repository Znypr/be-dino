--!strict
-- BD-149 reusable "drag to turn" for ONE ViewportFrame dino preview. Pointer maths lives in Shared.InspectMath
-- (tools/verify_inspect.py). This module only wires input and writes the InspectYaw / InspectZoom attributes that
-- Shared.PreviewCamera reads: the camera orbits the dino, so the one viewport and one model are reused (no clones,
-- no per-frame Instance creation) and patient preview loading keeps working when the model reloads.
-- Reduced Motion (Theme.MotionEnabled false): no idle spin and no inertia; dragging still turns the dino.
local RunService = game:GetService("RunService")
local Input = game:GetService("UserInputService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Theme = require(Shared.UITheme)
local Math = require(Shared.InspectMath)

local InspectView = {}
InspectView.DragThreshold = Math.DragThreshold

export type Options = {
    surface: GuiObject?,   -- where drags are read (default: the viewport itself)
    uiParent: GuiObject?,  -- where the hint and reset button live (default: the viewport)
    zoom: boolean?,        -- wheel / pinch zoom (default true)
    hint: boolean?,        -- "Drag to turn" (default true)
    resetButton: boolean?, -- 44 px reset-view button (default true)
    resetPosition: UDim2?, -- default top-right of uiParent
    hintPosition: UDim2?,  -- default bottom-center of uiParent
    autoSpin: boolean?,    -- idle turntable until first touch (default true)
    zIndex: number?,
}
export type Handle = {
    destroy: () -> (), reset: () -> (), wasDrag: () -> boolean, setEnabled: (boolean) -> (), yaw: () -> number,
}

local function shown(view: GuiObject): boolean
    local item: Instance? = view
    while item do
        if item:IsA("GuiObject") and not item.Visible then return false end
        if item:IsA("ScreenGui") and not item.Enabled then return false end
        item = item.Parent
    end
    return view.AbsoluteSize.X > 0 and view.AbsoluteSize.Y > 0
end

function InspectView.attach(viewport: ViewportFrame, options: Options?): Handle
    local o: Options = options or {}
    local surface: GuiObject = o.surface or viewport
    local uiParent: GuiObject = o.uiParent or viewport
    if surface == viewport then viewport.Active = true end -- sink the press so it never reaches a scrim behind
    local z = o.zIndex or (uiParent.ZIndex + 3)
    local s = Math.new()
    if o.autoSpin == false then s.touched = true end
    local enabled = true
    local alive = true
    local connections: {RBXScriptConnection} = {}
    local pointer: InputObject? = nil -- the press that started the drag
    local pinchStart = 1

    local function motion(): boolean return Theme.MotionEnabled ~= false end
    local hintLabel: TextLabel? = nil
    local resetButton: TextButton? = nil

    local function apply()
        viewport:SetAttribute("InspectYaw", s.yaw)
        viewport:SetAttribute("InspectZoom", s.zoom)
        if resetButton then resetButton.Visible = enabled and Math.changed(s) end
    end

    if o.hint ~= false then
        local hint = Instance.new("TextLabel")
        hint.Name, hint.BackgroundColor3, hint.BackgroundTransparency = "DragHint", Color3.fromRGB(13, 15, 20), .45
        hint.AnchorPoint, hint.Position = Vector2.new(.5, 1), o.hintPosition or UDim2.new(.5, 0, 1, -6)
        hint.Size, hint.Text, hint.Font = UDim2.fromOffset(132, 26), "Drag to turn", Enum.Font.FredokaOne
        hint.TextColor3, hint.TextScaled, hint.ZIndex = Color3.new(1, 1, 1), true, z
        local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(0, 13) corner.Parent = hint
        local limit = Instance.new("UITextSizeConstraint") limit.MaxTextSize, limit.MinTextSize, limit.Parent = 18, 10, hint
        hint.Parent = uiParent
        hintLabel = hint
    end
    if o.resetButton ~= false then
        local b = Instance.new("TextButton")
        b.Name, b.Text, b.Font, b.TextColor3 = "ResetView", "RESET", Enum.Font.FredokaOne, Color3.new(1, 1, 1)
        b.AnchorPoint, b.Position = Vector2.new(1, 0), o.resetPosition or UDim2.new(1, -6, 0, 6)
        b.Size, b.BackgroundColor3, b.AutoButtonColor = UDim2.fromOffset(72, 44), Theme.Colors.blue:Lerp(Color3.new(0, 0, 0), .45), true
        b.TextSize, b.ZIndex, b.Visible = 18, z + 1, false
        local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(0, 10) corner.Parent = b
        local stroke = Instance.new("UIStroke") stroke.Color, stroke.Thickness, stroke.Parent = Color3.fromRGB(13, 15, 20), 2, b
        b.Activated:Connect(function()
            Math.reset(s)
            s.touched = true
            apply()
        end)
        b.Parent = uiParent
        resetButton = b
    end
    apply()

    local function dropHint()
        if hintLabel then hintLabel:Destroy() hintLabel = nil end
    end
    local function isPress(input: InputObject): boolean
        return input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch
    end
    local function follows(input: InputObject): boolean
        local p = pointer
        if not p then return false end
        if p.UserInputType == Enum.UserInputType.Touch then return input == p end
        return input.UserInputType == Enum.UserInputType.MouseMovement
    end

    table.insert(connections, surface.InputBegan:Connect(function(input)
        if not enabled or pointer or not isPress(input) then return end
        pointer = input
        Math.press(s, input.Position.X, input.Position.Y, os.clock())
    end))
    table.insert(connections, Input.InputChanged:Connect(function(input)
        if not follows(input) then return end
        if Math.move(s, input.Position.X, input.Position.Y, os.clock()) then
            dropHint()
            apply()
        end
    end))
    table.insert(connections, Input.InputEnded:Connect(function(input)
        local p = pointer
        if not p then return end
        local ends = if p.UserInputType == Enum.UserInputType.Touch then input == p else input.UserInputType == Enum.UserInputType.MouseButton1
        if not ends then return end
        pointer = nil
        Math.release(s, os.clock(), motion())
        if s.moved then dropHint() end
        apply()
    end))
    if o.zoom ~= false then
        table.insert(connections, surface.InputChanged:Connect(function(input)
            if enabled and input.UserInputType == Enum.UserInputType.MouseWheel then
                s.touched = true
                Math.wheel(s, input.Position.Z)
                apply()
            end
        end))
        table.insert(connections, Input.TouchPinch:Connect(function(positions, scale, _velocity, state)
            if not enabled then return end
            local p = positions[1]
            if not p then return end
            local low, high = surface.AbsolutePosition, surface.AbsolutePosition + surface.AbsoluteSize
            if p.X < low.X or p.Y < low.Y or p.X > high.X or p.Y > high.Y then return end
            if state == Enum.UserInputState.Begin then pinchStart = s.zoom end
            -- A pinch is never a tap or a one-finger drag.
            s.dragged, s.dragging, s.touched = true, false, true
            pointer = nil
            Math.pinch(s, pinchStart, scale)
            apply()
        end))
    end

    -- One Heartbeat: it only writes the attributes while something moves (idle spin, inertia).
    local sinceCheck, onScreen = 0, true
    table.insert(connections, RunService.Heartbeat:Connect(function(dt)
        if not alive then return end
        sinceCheck += dt
        if sinceCheck > .25 then sinceCheck = 0 onScreen = shown(viewport) end
        if not enabled or not onScreen then return end
        if Math.step(s, math.min(dt, .1), motion()) then apply() end
    end))

    local handle = {} :: Handle
    function handle.destroy()
        if not alive then return end
        alive = false
        for _, c in connections do c:Disconnect() end
        table.clear(connections)
        if hintLabel then hintLabel:Destroy() hintLabel = nil end
        if resetButton then resetButton:Destroy() resetButton = nil end
    end
    function handle.reset() Math.reset(s) s.touched = true apply() end
    function handle.wasDrag(): boolean return Math.consumedTap(s) end
    function handle.setEnabled(on: boolean)
        enabled = on
        if hintLabel then hintLabel.Visible = on end
        if not on then pointer = nil s.dragging = false end
        apply()
    end
    function handle.yaw(): number return s.yaw end
    viewport.Destroying:Once(handle.destroy)
    return handle
end

return InspectView
