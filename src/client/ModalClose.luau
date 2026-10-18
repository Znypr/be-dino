--!strict
-- Close paths (BD-1019, docs/181). Owner bug 2026-10-18: "when hatching the egg, pressing X doesnt work", and a tap outside did nothing.
-- Root cause: HatchSequence put a full-screen tap catcher (ZIndex 46) on the BeDinoUI ScreenGui, above the whole menu (ModalScrim 20), so
-- every tap on X, on the dark backdrop and on the end buttons (DONE / TRY AGAIN) landed on the catcher instead.
-- This module (a) builds the hatch tap catcher so it covers only the card body, never X, the end buttons or the backdrop, (b) lets the
-- hatch screen decide what a tap on the backdrop does, and (c) offers a hit test (topAt / coverOf) that tests and Studio scripts use to
-- prove that a control can really be reached. Pure numbers and decisions live in Shared/ModalCloseRules.
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Rules = require(Shared:WaitForChild("ModalCloseRules"))

local M = {}

-- ---------------------------------------------------------------- the backdrop tap
-- The open hatch screen registers one function: it returns true when a tap on the dark backdrop should close the menu (same as X).
-- Anything else it handles itself (a tap that speeds the egg up) and returns false. No hatch screen open = a backdrop tap closes.
local outside: (() -> boolean)? = nil
function M.setOutside(fn: () -> boolean) outside = fn end
function M.clearOutside(fn: () -> boolean) if outside == fn then outside = nil end end
function M.outsideTap(): boolean
    local fn = outside
    return fn == nil or fn()
end

-- ---------------------------------------------------------------- the hatch tap catcher
export type Zone = {overlay: TextButton, layer: Frame, step: () -> (), destroy: () -> ()}

local function rectOf(o: GuiObject): Rules.Rect
    local p, s = o.AbsolutePosition, o.AbsoluteSize
    return {x = p.X, y = p.Y, w = s.X, h = s.Y}
end

-- overlay = the tap catcher (Active, named HatchTapCatcher like before). It is placed over the card minus its header strip and minus the
--   end-button row, so X, DONE / TRY AGAIN and the dark backdrop receive their own taps. The backdrop tap then reaches ModalScrim
--   (Bootstrap), which asks M.outsideTap().
-- layer = a full-screen Frame that is NOT Active: the home of "Skip the rest" and the dino-turning hint, exactly where they were.
-- step() follows the card (it slides in, and the phone layout scrolls); call it once a frame.
function M.hatchZone(gui: ScreenGui, panel: GuiObject, header: GuiObject?, body: GuiObject): Zone
    local overlay = Instance.new("TextButton")
    overlay.Name, overlay.Text, overlay.BackgroundTransparency, overlay.AutoButtonColor = "HatchTapCatcher", "", 1, false
    overlay.Size, overlay.ZIndex, overlay.Visible, overlay.Parent = UDim2.fromOffset(Rules.MinTarget, Rules.MinTarget), 46, false, gui -- hidden until step() sizes it
    local layer = Instance.new("Frame")
    layer.Name, layer.BackgroundTransparency, layer.BorderSizePixel, layer.Active = "HatchUiLayer", 1, 0, false
    layer.Size, layer.ZIndex, layer.Parent = UDim2.fromScale(1, 1), 46, gui
    local lx, ly, lw, lh = nil :: number?, nil :: number?, 0, 0
    local function step()
        if not overlay.Parent then return end
        local card = rectOf(panel)
        local headerBottom = if header then header.AbsolutePosition.Y + header.AbsoluteSize.Y else card.y
        local row = body:FindFirstChild("EndButtons")
        local endTop: number? = nil
        if row and row:IsA("GuiObject") and row.Visible then endTop = row.AbsolutePosition.Y end
        local zone = Rules.tapZone(card, headerBottom, endTop)
        if zone == nil then
            if overlay.Visible then overlay.Visible = false end
            return
        end
        local origin = layer.AbsolutePosition -- the full-screen layer sits at the gui's (0, 0): this is where overlay offsets start, whatever gui.AbsolutePosition says about insets
        local x, y = zone.x - origin.X, zone.y - origin.Y
        if x ~= lx or y ~= ly or zone.w ~= lw or zone.h ~= lh then
            lx, ly, lw, lh = x, y, zone.w, zone.h
            overlay.Position, overlay.Size = UDim2.fromOffset(x, y), UDim2.fromOffset(zone.w, zone.h)
        end
        if not overlay.Visible then overlay.Visible = true end
    end
    step()
    return {overlay = overlay, layer = layer, step = step, destroy = function()
        if overlay.Parent then overlay:Destroy() end
        if layer.Parent then layer:Destroy() end
    end}
end

-- ---------------------------------------------------------------- hit test (tests and Studio scripts)
-- Which control gets a tap at (x, y)? Mirrors Roblox with ZIndexBehavior.Sibling: inside one parent the higher ZIndex wins (a later child
-- wins a tie) and a child always draws above its parent; a whole subtree stays above or below its siblings. A visible button, or a
-- GuiObject with Active = true, takes the tap; other objects let it fall through to what is under them. Higher DisplayOrder wins between
-- ScreenGuis. Does not model ClipsDescendants. x / y are in the same space as AbsolutePosition.
local function sinks(o: GuiObject): boolean
    return o:IsA("GuiButton") or o.Active
end

local function better(a: {number}, b: {number}): boolean -- is key a above key b?
    for i = 1, math.min(#a, #b) do
        if a[i] ~= b[i] then return a[i] > b[i] end
    end
    return #a > #b
end

function M.topAt(root: Instance, x: number, y: number): GuiObject?
    local best: GuiObject? = nil
    local bestKey: {number} = {}
    local function visit(node: Instance, key: {number})
        local children = node:GetChildren()
        for index, child in children do
            if child:IsA("GuiObject") then
                if not child.Visible then continue end
                local k = table.clone(key)
                table.insert(k, child.ZIndex)
                table.insert(k, index)
                local r = rectOf(child)
                if sinks(child) and Rules.contains(r, x, y) and (best == nil or better(k, bestKey)) then best, bestKey = child, k end
                visit(child, k)
            elseif child:IsA("ScreenGui") then
                if not child.Enabled then continue end
                local k = table.clone(key)
                table.insert(k, child.DisplayOrder)
                table.insert(k, index)
                visit(child, k)
            end
        end
    end
    visit(root, {})
    return best
end

-- BD-1083: is the topmost thing that takes a tap at (x, y) the dark backdrop of a menu (Bootstrap's ModalScrim or the Fusion menu's FusionScrim)
-- and nothing of the menu itself (a tab, X, a card, a button)? HubTravelClient asks this before it turns a raw tap into "close the menu and travel":
-- the raw input event does not know that the Index tab sits on top of the rail button underneath it (owner QA 2026-10-18, picture 350).
M.BackdropNames = {ModalScrim = true, FusionScrim = true}
function M.onBackdrop(root: Instance, x: number, y: number): boolean
    local top = M.topAt(root, x, y)
    return top ~= nil and M.BackdropNames[top.Name] == true
end

-- Who covers the centre of `target`? nil = the target itself (or something inside it) gets the tap, i.e. it is reachable.
function M.coverOf(root: Instance, target: GuiObject): GuiObject?
    local r = rectOf(target)
    local top = M.topAt(root, r.x + r.w / 2, r.y + r.h / 2)
    if top == nil or top == target or top:IsDescendantOf(target) then return nil end
    return top
end

return M
