--!strict
-- Authored broad ramps and mountain masses; the center remains a readable chase meadow.
local IslandLayout = {}
IslandLayout.Peaks = {
    {x = -145, z = -140, height = 65, radius = 90},
    {x = 145, z = -130, height = 80, radius = 105},
    {x = -165, z = 125, height = 46, radius = 82},
    {x = 160, z = 140, height = 58, radius = 95},
}
function IslandLayout.height(x: number, z: number): number
    local h = 0
    for _, peak in IslandLayout.Peaks do
        local r2 = ((x-peak.x)^2 + (z-peak.z)^2) / peak.radius^2
        h += peak.height * math.exp(-r2 * 1.6)
    end
    local meadow = math.exp(-(x*x + (z-30)^2) / 5000)
    h *= 1 - meadow * .95
    local edge = math.max(math.abs(x), math.abs(z))
    h += math.max(0, edge - 190) * .55
    return h + math.noise(x / 65, z / 65, 14) * 2 * (1-meadow)
end
return IslandLayout
