--!strict
-- BD-411: the handbook palette rules (docs/114 s5.3, s5.10, s5.12) as DATA + one pure check, no Instances. tools/qa/colour_probe.server.luau
-- reads the dominant hues of every placed generated prop's texture in Studio; tools/qa/palette_report.py runs `AssetPalette.check` over
-- that output (offline, via the Luau runner). Change a zone rule here and in docs/114 together.
-- Hue buckets are 12 slices of 30 degrees counted over pixels with saturation > 0.2 and value > 0.15 ("coloured pixels"):
-- 1 = 0-30 red-orange, 2 = 30-60 amber/yellow, 3 = 60-90, 4 = 90-120 yellow-green, 5 = 120-150 green, 6 = 150-180 teal,
-- 7 = 180-210 cyan, 8 = 210-240 blue, 9 = 240-270 blue-violet, 10 = 270-300 purple, 11 = 300-330 magenta, 12 = 330-360 pink.
local AssetPalette = {}

AssetPalette.AmberBucket = 2
AssetPalette.CoolBuckets = {7, 8, 9, 10, 11} -- cyan .. magenta: the cold band that must not dominate the warm cave
AssetPalette.PurpleBuckets = {9, 10, 11}

-- Zone rules. currency: crystals the player buys or earns with (shop crystals, amber food): amber/yellow only (handbook 5.3, OWNER 2026-10-16).
-- cave: warm grey-stone + warm lamp light (5.10): cool hues may not dominate. island: daylight meadow: no purple/magenta cast.
AssetPalette.Zones = {
    currency = {minAmber = 0.6, note = "currency/shop crystals are amber/yellow (docs/114 s5.3)"},
    cave = {maxCool = 0.35, note = "cave props are warm grey-stone, cool hues under 35% of the coloured pixels (docs/114 s5.10)"},
    island = {maxPurple = 0.2, note = "island props carry no purple/magenta cast (docs/114 s5.8, s5.12)"},
}
-- Layout keys that are currency/shop crystals. A flat-coloured override (CaveHubProps.Warm) counts as its Color.
AssetPalette.Currency = {hub_crystal_s = true, hub_crystal_l = true, food_amber_a = true, food_amber_b = true}
-- Decoration crystals the handbook allows in blue-purple INSIDE the cave only (never next to a shop): exempt from the cool rule.
AssetPalette.DecorCrystal = {rock_crystal = true}

function AssetPalette.zoneOf(place: string, key: string): string
    if AssetPalette.Currency[key] then return "currency" end
    return if place == "cave" then "cave" else "island"
end

local function share(hist: {number}, buckets: {number}, total: number): number
    if total <= 0 then return 0 end
    local n = 0
    for _, b in buckets do n += hist[b] or 0 end
    return n / total
end

-- hist: 12 counts of coloured pixels. Returns ok, reason.
function AssetPalette.check(place: string, key: string, hist: {number}): (boolean, string)
    local zone = AssetPalette.zoneOf(place, key)
    local total = 0
    for _, c in hist do total += c end
    if zone == "currency" then
        local a = if total > 0 then (hist[AssetPalette.AmberBucket] or 0) / total else 0
        if total > 0 and a < AssetPalette.Zones.currency.minAmber then
            return false, string.format("currency prop only %d%% amber (needs %d%%)", a * 100 + .5, AssetPalette.Zones.currency.minAmber * 100)
        end
        return true, "amber"
    end
    if zone == "cave" then
        if AssetPalette.DecorCrystal[key] then return true, "decoration crystal (allowed inside the cave)" end
        local c = share(hist, AssetPalette.CoolBuckets, total)
        if c > AssetPalette.Zones.cave.maxCool then
            return false, string.format("%d%% cool hues (cave allows %d%%)", c * 100 + .5, AssetPalette.Zones.cave.maxCool * 100)
        end
        return true, "warm"
    end
    local p = share(hist, AssetPalette.PurpleBuckets, total)
    if p > AssetPalette.Zones.island.maxPurple and not AssetPalette.DecorCrystal[key] then
        return false, string.format("%d%% purple/magenta (island allows %d%%)", p * 100 + .5, AssetPalette.Zones.island.maxPurple * 100)
    end
    return true, "ok"
end

return AssetPalette
