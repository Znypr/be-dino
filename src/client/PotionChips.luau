--!strict
-- BD-101: small potion icons next to the active-potion timer lines of the bottom-right HUD (one chip per active effect).
-- Lives in its own module because Bootstrap.client is at the 200-local limit. attach(label) once, update(buffs, now) each HUD tick.
-- The chips are children of the timer text label (they follow its layout and visibility) and reserve a strip at the right of
-- the text with a UIPadding, so the lines never run under an icon. With no valid image id (AssetSlots empty or a failed
-- slot) no chip is made and the text lines stay exactly as before.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local PotionArt = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("PotionArt"))

local Chips = {}
local CHIP, GAP = 26, 2
local KINDS = {"speed", "growth", "loot"} -- fixed left-to-right order
local host: TextLabel? = nil
local padding: UIPadding? = nil
local strip: Frame? = nil
local shown = "" -- potion ids currently drawn, so nothing is rebuilt while the set is unchanged

function Chips.attach(label: TextLabel)
    host = label
    local pad = Instance.new("UIPadding")
    pad.Name = "PotionChipPadding"
    pad.Parent = label
    padding = pad
    local frame = Instance.new("Frame")
    frame.Name = "PotionChips"
    frame.BackgroundTransparency = 1
    frame.AnchorPoint = Vector2.new(1, 0)
    frame.ZIndex = label.ZIndex + 1
    frame.Visible = false
    frame.Parent = label
    strip = frame
end

-- buffs: the profile's active buffs, {[kind]: {id: string, expiresAt: number}}; now: server time.
function Chips.update(buffs: {[string]: {id: string, expiresAt: number}}, now: number)
    local frame, pad = strip, padding
    if not frame or not pad then return end
    local ids = {}
    for _, kind in KINDS do
        local buff = buffs[kind]
        if buff and buff.expiresAt > now and PotionArt.imageFor(buff.id) then table.insert(ids, buff.id) end
    end
    local key = table.concat(ids, ",")
    if key == shown then return end
    shown = key
    frame:ClearAllChildren()
    local width = #ids * (CHIP + GAP)
    pad.PaddingRight = UDim.new(0, width)
    frame.Visible = #ids > 0
    -- UIPadding also offsets children, so the strip sits in the reserved band: right edge = label right edge.
    frame.Position = UDim2.new(1, width, 0, 0)
    frame.Size = UDim2.fromOffset(width, CHIP)
    for i, id in ids do
        PotionArt.icon(frame, id, UDim2.fromOffset(CHIP, CHIP), UDim2.fromOffset((i - 1) * (CHIP + GAP), CHIP / 2), frame.ZIndex)
    end
end

return Chips
