--!strict
-- BD-285 / BD-385 (docs/104 s5): the client half of the Cave lava falls. The server (CaveLavaFx) builds the particle strands and the
-- emitters; this module, called from CaveAtmosphere.step while the player is inside the hall:
--   * preloads the lava textures with ContentProvider:PreloadAsync before use and swaps a texture that fails to load for the
--     built-in sprite (Studio showed the flame / swirl uploads as "still being generated" for a while),
--   * turns the pool disc slowly,
--   * sets every emitter Rate from CaveLavaRules.rate: phones get the 10 per second budget; Reduce Motion (Calm motion) stops the
--     turning and the particles and instead emits one burst of soft glow puffs (StillGlow) frozen with TimeScale 0 (static variant).
-- Local property writes only (nothing replicates). With Config.CaveHub false CaveAtmosphere never calls step.
local ContentProvider = game:GetService("ContentProvider")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Rules = require(Shared:WaitForChild("CaveLavaRules"))
local Assets = require(Shared:WaitForChild("EffectAssets"))

local Lava = {}
local folder: Instance? = nil
local still: ParticleEmitter? = nil
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
    table.clear(emitters)
    for _, d in found:GetDescendants() do
        if d:IsA("ParticleEmitter") and d:GetAttribute("LavaRule") then table.insert(emitters, d)
        elseif d:IsA("ParticleEmitter") and d.Name == "StillGlow" then still = d end
    end
    local pool = found:FindFirstChild("FX_LavaPool")
    disc = if pool and pool:IsA("BasePart") then pool else nil
end

-- Preload the lava textures once; a texture that does not come back Success is replaced by the built-in sprite (white, tinted).
local function preload()
    if preloadStarted then return end
    preloadStarted = true
    local items: {Instance} = {}
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
            if not calm then e.TimeScale = 1 end
        end
        local glow = still
        if glow and glow.Parent then
            if calm then
                -- static variant: one burst of constant-alpha soft puffs across the wall, then frozen
                glow.TimeScale = 1
                glow:Clear()
                glow:Emit((glow:GetAttribute("StillBurst") :: number?) or Rules.StillBurst)
                task.defer(function() glow.TimeScale = 0 end)
            else
                glow.TimeScale = 1
                glow:Clear()
            end
        end
    end
end

return Lava
