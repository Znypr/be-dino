--!strict
-- BD-081 / BD-343 Sound Lab page (docs/121): a scrolling list of every registered sound with its category and a PLAY
-- button, so the owner can audition by ear. Opened from the Settings Sound tab. Plays raw (no throttle/limiter) at the
-- cue's own volume x Sfx.Master through the "sfx" mixer group (weather rows use "ambience"). No gameplay effect.
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Theme = require(Shared:WaitForChild("UITheme"))
local Lab = require(Shared:WaitForChild("SoundLabData"))
local Sfx = require(Shared:WaitForChild("Sfx"))
local Mixer = require(Shared:WaitForChild("AudioMixer"))
local C = Theme.Colors
local SoundLab = {}

local current: Sound? = nil
local function playRow(row: any)
    local id = Sfx.normalizeId(row.id)
    if not id then return end
    if current then current:Stop() current:Destroy() current = nil end
    local s = Instance.new("Sound")
    s.Name = "SoundLab_" .. row.name
    s.SoundId, s.Volume = id, math.clamp(row.volume, 0, Sfx.MaxCueVolume) * Sfx.Master
    s.Parent = game:GetService("SoundService")
    pcall(function() Mixer.attach(s, if row.source == "weather" then "ambience" else "sfx") end)
    s.Ended:Once(function() if s.Parent then s:Destroy() end end)
    current = s
    s:Play()
end

function SoundLab.draw(body: Instance, ctx: any, back: () -> ())
    ctx.button(body, "BACK", 0, 0, 160, 48, C.card, back)
    ctx.label(body, "Sound lab: tap PLAY and listen", 180, 0, 640, 48, 24, C.gold)
    local list = Instance.new("ScrollingFrame")
    list.Name = "SoundLabList"
    list.Position, list.Size = UDim2.fromOffset(0, 56), UDim2.fromOffset(824, 346)
    list.BackgroundTransparency, list.BorderSizePixel = 1, 0
    list.ScrollBarThickness = 8
    list.Parent = body
    local y, last = 0, ""
    for _, row in Lab.rows() do
        if row.category ~= last then
            last = row.category
            ctx.label(list, Lab.Labels[row.category] or "OTHER", 0, y, 800, 36, 22, C.gold).TextXAlignment = Enum.TextXAlignment.Left
            y += 38
        end
        ctx.label(list, row.name, 0, y, 520, 48, 20).TextXAlignment = Enum.TextXAlignment.Left
        if row.silent then
            ctx.label(list, "no sound yet", 540, y, 250, 48, 18, C.red)
        else
            local b = ctx.button(list, "PLAY", 540, y, 250, 48, C.accent, function() playRow(row) end)
            b.Name = "Play_" .. row.name
        end
        y += 52
    end
    for _, cat in Lab.gaps() do
        ctx.label(list, (Lab.Labels[cat] or cat) .. ": no sounds yet (TODO owner)", 0, y, 800, 40, 18, C.red).TextXAlignment = Enum.TextXAlignment.Left
        y += 42
    end
    list.CanvasSize = UDim2.fromOffset(0, y + 8)
end

return SoundLab
