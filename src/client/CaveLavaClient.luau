--!strict
-- BD-285 (docs/104 s5): the client half of the Cave lava falls. The server (CaveLavaFx) builds the sheet, its scrolling layers and
-- the emitters at their static first frame; this module, called from CaveAtmosphere.step while the player is inside the hall:
--   * preloads the lava textures with ContentProvider:PreloadAsync before use and swaps a texture that fails to load for the
--     built-in sprite (Studio showed the flame / swirl uploads as "still being generated" for a while),
--   * scrolls the flame layers down the sheet and turns the pool disc (CaveLavaRules.scroll / stripY),
--   * sets every emitter Rate from CaveLavaRules.rate: phones get the 10 per second budget, Reduce Motion (Calm motion) stops
--     the scrolling, the turning and the particles, leaving the static first frame.
-- Local property writes only (nothing replicates). With Config.CaveHub false CaveAtmosphere never calls step.
local ContentProvider = game:GetService("ContentProvider")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Rules = require(Shared:WaitForChild("CaveLavaRules"))
local Assets = require(Shared:WaitForChild("EffectAssets"))

local Lava = {}
local folder: Instance? = nil
local strips: {ImageLabel} = {}
local emitters: {ParticleEmitter} = {}
local disc: BasePart? = nil
local seconds = 0 -- animation clock; stops while Calm motion is on
local nextFind = 0
local preloadStarted = false
local lastCalm: boolean? = nil

local function isPhone(): boolean
    return UserInputService.TouchEnabled and not UserInputService.KeyboardEnabled
end

local function find()
    local found = workspace:FindFirstChild("LavaFalls", true)
    if not found then return end
    folder = found
    table.clear(strips)
    table.clear(emitters)
    for _, d in found:GetDescendants() do
        if d:IsA("ImageLabel") and d.Name == "Strip" then table.insert(strips, d)
        elseif d:IsA("ParticleEmitter") and d:GetAttribute("LavaRule") then table.insert(emitters, d) end
    end
    local pool = found:FindFirstChild("FX_LavaPool")
    disc = if pool and pool:IsA("BasePart") then pool else nil
end

-- Preload the lava textures once; a texture that does not come back Success is replaced by the built-in sprite (white, tinted).
local function preload()
    if preloadStarted then return end
    preloadStarted = true
    local items: {Instance} = {}
    for _, s in strips do table.insert(items, s) end
    for _, e in emitters do table.insert(items, e) end
    if disc then
        for _, c in (disc :: BasePart):GetChildren() do
            if c:IsA("Decal") then table.insert(items, c) end
        end
    end
    task.spawn(function()
        local ok, err = pcall(function()
            ContentProvider:PreloadAsync(items, function(contentId: string, status: Enum.AssetFetchStatus)
                if status == Enum.AssetFetchStatus.Success then return end
                warn("[Be Dino] lava texture " .. contentId .. " not loaded (" .. tostring(status) .. "); using the built-in sprite")
                for _, s in strips do
                    if s.Image == contentId then s.Image = Assets.Builtin.fire end
                end
                for _, e in emitters do
                    if e.Texture == contentId then e.Texture = Assets.Builtin.spark e.FlipbookLayout = Enum.ParticleFlipbookLayout.None end
                end
            end)
        end)
        if not ok then warn("[Be Dino] lava preload failed: " .. tostring(err)) end
        if folder then (folder :: Instance):SetAttribute("Preloaded", true) end
    end)
end

function Lava.step(dt: number, calm: boolean)
    local now = os.clock()
    if folder == nil or (folder :: Instance).Parent == nil then
        if now < nextFind then return end
        nextFind = now + 1
        find()
        if folder == nil then return end
    end
    preload()
    if not calm then seconds += dt end
    for _, s in strips do
        local layer = Rules.Layers[s:GetAttribute("LayerIndex") :: number]
        if layer then s.Position = UDim2.fromOffset(s:GetAttribute("OffsetX") :: number, Rules.stripY(layer, seconds, calm)) end
    end
    local pool = disc
    if pool and pool.Parent then
        local spin = (pool:GetAttribute("SpinSeconds") :: number?) or 60
        local base = pool:GetAttribute("SpinBase")
        if typeof(base) == "CFrame" then
            local a = if calm then 0 else (seconds / spin % 1) * 2 * math.pi
            pool.CFrame = (base :: CFrame) * CFrame.Angles(0, a, 0) * CFrame.Angles(0, 0, math.pi / 2)
        end
    end
    if lastCalm ~= calm then
        lastCalm = calm
        local phone = isPhone()
        for _, e in emitters do
            local rule = e:GetAttribute("LavaRule") :: string
            local rate = Rules.rate(rule, phone, calm)
            e.Rate = rate
            e.Enabled = rate > 0
        end
    end
end

return Lava
