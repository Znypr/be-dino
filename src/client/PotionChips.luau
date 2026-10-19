--!strict
-- BD-101: small potion icons next to the active-potion timer lines of the bottom-right HUD (one chip per active effect).
-- Lives in its own module because Bootstrap.client is at the 200-local limit. attach(label) once, update(buffs, now) each HUD tick.
-- The chips are children of the timer text label (they follow its layout and visibility) and reserve a strip at the right of
-- the text with a UIPadding, so the lines never run under an icon. With no valid image id (AssetSlots empty or a failed
-- slot) no chip is made and the text lines stay exactly as before.
-- BD-1124 (docs/202 R11, docs/220): with Config.TimerChipsEnabled a thin drain bar sits under each chip (full when the potion was drunk,
-- empty when it ends: Shared/TimerWords.drain); the bar is refreshed every tick, the chips only when the set of potions changes.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local PotionArt = require(Shared:WaitForChild("PotionArt"))
local Config = require(Shared:WaitForChild("Config"))
local Words = require(Shared:WaitForChild("TimerWords"))
local ProgressionConfig = require(Shared:WaitForChild("ProgressionConfig"))
local ProgressionRules = require(Shared:WaitForChild("ProgressionRules"))

local Chips = {}
local CHIP, GAP, BAR_H = 26, 2, 4
local TRACK, FILL = Color3.fromRGB(13, 15, 20), Color3.fromRGB(255, 210, 43) -- docs/114 s5: outline and the crystal amber
local KINDS = {"speed", "growth", "loot"} -- fixed left-to-right order
local host: TextLabel? = nil
local padding: UIPadding? = nil
local strip: Frame? = nil
local shown = "" -- potion ids currently drawn, so nothing is rebuilt while the set is unchanged
local bars: {[string]: Frame} = {} -- kind -> the fill of its drain bar (flag on only)

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

function Chips.drainBars(): boolean
    return Config.TimerChipsEnabled == true
end

local function durationOf(potionId: string): number?
    local item = ProgressionRules.item(ProgressionConfig.Potions, potionId)
    return if item then item.duration else nil
end

-- buffs: the profile's active buffs, {[kind]: {id: string, expiresAt: number}}; now: server time.
function Chips.update(buffs: {[string]: {id: string, expiresAt: number}}, now: number)
    local frame, pad = strip, padding
    if not frame or not pad then return end
    local ids, kinds = {}, {}
    for _, kind in KINDS do
        local buff = buffs[kind]
        if buff and buff.expiresAt > now and PotionArt.imageFor(buff.id) then table.insert(ids, buff.id) table.insert(kinds, kind) end
    end
    local key = table.concat(ids, ",")
    local withBars = Chips.drainBars()
    if key ~= shown then
        shown = key
        frame:ClearAllChildren()
        bars = {}
        local width = #ids * (CHIP + GAP)
        pad.PaddingRight = UDim.new(0, width)
        frame.Visible = #ids > 0
        -- UIPadding also offsets children, so the strip sits in the reserved band: right edge = label right edge.
        frame.Position = UDim2.new(1, width, 0, 0)
        frame.Size = UDim2.fromOffset(width, if withBars then CHIP + GAP + BAR_H else CHIP)
        for i, id in ids do
            local x = (i - 1) * (CHIP + GAP)
            PotionArt.icon(frame, id, UDim2.fromOffset(CHIP, CHIP), UDim2.fromOffset(x, CHIP / 2), frame.ZIndex)
            if withBars and durationOf(id) then
                local track = Instance.new("Frame")
                track.Name, track.BorderSizePixel, track.BackgroundColor3 = "DrainTrack", 0, TRACK
                track.Size, track.Position, track.ZIndex, track.Parent = UDim2.fromOffset(CHIP, BAR_H), UDim2.fromOffset(x, CHIP + GAP), frame.ZIndex, frame
                local fill = Instance.new("Frame")
                fill.Name, fill.BorderSizePixel, fill.BackgroundColor3 = "DrainFill", 0, FILL
                fill.Size, fill.ZIndex, fill.Parent = UDim2.new(1, 0, 1, 0), track.ZIndex + 1, track
                bars[kinds[i]] = fill
            end
        end
    end
    for kind, fill in bars do -- every tick: the bar drains with the time left
        local buff = buffs[kind]
        local fraction = if buff then Words.drain(buff.expiresAt, durationOf(buff.id), now) else nil
        fill.Size = UDim2.new(fraction or 0, 0, 1, 0)
    end
end

return Chips
