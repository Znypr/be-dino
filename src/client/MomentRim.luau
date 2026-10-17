--!nonstrict
-- BD-433 (docs/123 s2 T6): the 1.5 s rim light on the local player's OWN dino when a mutation is revealed (CosmeticVisuals: a new event
-- mutation shows on the world dino) or hatched (RareHatchClient: a mutation egg lands). All the rules are in Shared/MomentRimPlan (pure, verified
-- offline); this file only draws them.
--   * ONE Highlight (named MomentRim), in the mutation's rim colour, fading in and out. Only one moment is alive at a time: a new one replaces it.
--   * If the dino already wears the fused-tier rim (Highlight "LPTierRim"), no second Highlight is made: that rim is brightened for the same time
--     and put back exactly as it was.
--   * Budget: EffectsLod.rimFits(effects, Highlights alive in the world) (RimHighlights Full / Lite / Off, one below the engine cap of 31).
--   * Effects Off: nothing. Lite: outline only, fainter. Reduce Motion: a still rim for the same time, no fade, and a tier rim is left alone.
-- Client only; local instances, nothing replicates and nothing is saved or sent.
local RunService = game:GetService("RunService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Plan = require(Shared:WaitForChild("MomentRimPlan"))
local Lod = require(Shared:WaitForChild("EffectsLod"))
local Look = require(Shared:WaitForChild("MutationLook"))
local Tier = require(Shared:WaitForChild("LowPolyTier"))
local Settings = require(Shared:WaitForChild("SettingsModel"))

local M = {}
local WHITE = Color3.new(1, 1, 1)
local active = nil
local lastAt = -100

local function c3(c: {number}): Color3
    return Color3.fromRGB(math.clamp(math.floor(c[1] + 0.5), 0, 255), math.clamp(math.floor(c[2] + 0.5), 0, 255), math.clamp(math.floor(c[3] + 0.5), 0, 255))
end

-- Highlights alive in the world right now (tier rims, food glows, our own). One scan per moment, and moments are at least Plan.Gap apart.
local function liveHighlights(): number
    local n = 0
    for _, d in workspace:GetDescendants() do
        if d:IsA("Highlight") then n += 1 end
    end
    return n
end

local function finish()
    local a = active
    if not a then return end
    active = nil
    if a.conn then a.conn:Disconnect() end
    if a.mode == "new" then
        if a.rim then a.rim:Destroy() end
    elseif a.rim and a.rim:IsDescendantOf(workspace) then -- hand the tier rim back exactly as it was
        a.rim.FillTransparency, a.rim.OutlineColor = a.baseFill, a.baseOutline
    end
end

local function step(dt: number)
    local a = active
    if not a then return end
    a.age += dt
    if a.age >= Plan.Life or not a.rim or not a.rim:IsDescendantOf(workspace) then finish() return end
    local e = Plan.envelope(a.age, a.look.still)
    if a.mode == "new" then
        a.rim.OutlineTransparency, a.rim.FillTransparency = Plan.newTransparency(a.look, e)
    else
        a.rim.FillTransparency = Plan.brightenFill(a.baseFill, a.look, e)
        a.rim.OutlineColor = a.baseOutline:Lerp(WHITE, Plan.brightenWhite(a.look, e))
    end
end

-- The dino model that carries the rim: the local mesh visual when there is one, otherwise the character itself.
local function carrier(character: Instance): Instance
    return character:FindFirstChild("LocalMeshVisual") or character:FindFirstChild("DinoVisual") or character
end

-- character = the local player's character. info = {mutationId = string?, tierId = string?} (both optional: colour only).
-- Returns true when a rim moment started (a new Highlight or a brightened tier rim).
function M.play(character: Instance?, info: {mutationId: string?, tierId: string?}?): boolean
    if not character or not character.Parent then return false end
    local s = Settings.get()
    local effects, calm = s.effects or "full", s.calm == true
    local now = os.clock()
    if now - lastAt < Plan.Gap then return false end
    local target = carrier(character)
    local tierRim = character:FindFirstChild(Plan.TierRimName, true) -- anywhere on the dino: the tier rim may sit on the visual or its model
    if tierRim and not tierRim:IsA("Highlight") then tierRim = nil end
    local mode = Plan.mode(effects, calm, tierRim ~= nil)
    if mode == "none" then return false end
    local look = Plan.look(effects, calm)
    finish() -- a new moment replaces a running one: never two Highlights of ours
    local entry = Look.get(info and info.mutationId)
    local tierEntry = Tier.get((info and info.tierId) or target:GetAttribute("LPTier"))
    local col = c3(Plan.colour(if entry then entry.rim else nil, if tierEntry then tierEntry.tint else nil))
    local a = {mode = mode, look = look, age = 0}
    if mode == "new" then
        if not Lod.rimFits(effects, liveHighlights()) then return false end
        local h = Instance.new("Highlight")
        h.Name, h.Adornee = Plan.Name, target
        h.FillColor, h.OutlineColor = col, col:Lerp(WHITE, 0.25)
        h.DepthMode = Enum.HighlightDepthMode.Occluded
        h.OutlineTransparency, h.FillTransparency = Plan.newTransparency(look, Plan.envelope(0, look.still))
        h.Parent = target
        a.rim = h
    else
        a.rim, a.baseFill, a.baseOutline = tierRim, tierRim.FillTransparency, tierRim.OutlineColor
    end
    lastAt = now
    a.conn = RunService.Heartbeat:Connect(step)
    active = a
    return true
end

function M.isActive(): boolean return active ~= nil end
function M.stop() finish() end

return M
