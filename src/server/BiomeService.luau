--!strict
-- BD-1314 (docs/250 S1): the biome clock on the server. Publishes CurrentBiome / NextBiome / BiomeChangeAt / BiomePhase on workspace (the
-- contract other systems read, docs/250 s4) and blends the island's terrain colours into the next biome inside the storm (Shared/BiomeRotation).
-- Light, fog, grade and the storm are client-side (WeatherVisuals). No-op unless Config.WorldV3Enabled and Config.BiomeRotationEnabled.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local Biome = require(ReplicatedStorage.Shared.BiomeRotation)
local Toon = require(ReplicatedStorage.Shared.WorldToon)

local BiomeService = {}

function BiomeService.start()
    if not Biome.enabled(Config) then return end
    task.spawn(function()
        local t0 = os.clock()
        while not workspace:GetAttribute("IslandTerrainReady") and os.clock() - t0 < 120 do task.wait(.5) end
        local terrain = workspace.Terrain
        -- the base (meadow) colour of each toon material, as the terrain painter left it
        local base: {[string]: {number}} = {}
        for _, name in Toon.materials() do
            local ok, c = pcall(function() return terrain:GetMaterialColor((Enum.Material :: any)[name]) end)
            if ok and typeof(c) == "Color3" then base[name] = {c.R * 255, c.G * 255, c.B * 255} end
        end
        local lastKey = ""
        while true do
            local now = Biome.clock(workspace:GetServerTimeNow(), workspace:GetAttribute("BiomeTestOffset"), game:GetService("RunService"):IsStudio())
            local s = Biome.state(now)
            workspace:SetAttribute("CurrentBiome", s.id)
            workspace:SetAttribute("NextBiome", s.next)
            workspace:SetAttribute("BiomeChangeAt", s.changeAt)
            workspace:SetAttribute("BiomePhase", s.phase)
            -- terrain colours: written only when the blend moved (inside the storm, 4 times a second) or on the first pass
            local from, to, mix = Biome.mix(now)
            local key = from .. ">" .. to .. ":" .. math.floor(mix * 40)
            if key ~= lastKey then
                lastKey = key
                for name, c in base do
                    local rgb = Biome.terrainColor(name, c, now)
                    terrain:SetMaterialColor((Enum.Material :: any)[name], Color3.fromRGB(rgb[1], rgb[2], rgb[3]))
                end
            end
            task.wait(if from ~= to then .25 else 1)
        end
    end)
end

return BiomeService
