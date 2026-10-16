--!strict
-- BD-081 / BD-343: data for the Sound Lab page (docs/121). Lists EVERY registered sound (Sfx.Sounds, WeatherSounds.Sounds,
-- the two raw HatchPresentation ids) with a category, so the owner can audition by ear. Pure data, no gameplay change;
-- checked offline by tools/verify_sound_lab.py (every registered name must have a category).
local Sfx = require(script.Parent:WaitForChild("Sfx"))
local WeatherSounds = require(script.Parent:WaitForChild("WeatherSounds"))
local Lab = {}

Lab.Categories = table.freeze({"ui", "pickup", "hatch", "rare", "reward", "mutation", "peaceful", "cave", "weather"})
Lab.Labels = table.freeze({
    ui = "UI TAPS", pickup = "PICKUPS", hatch = "EGG HATCH", rare = "RARE MOMENTS", reward = "RUN AND SHOP",
    mutation = "MUTATIONS", peaceful = "SOFT / PEACEFUL", cave = "CAVE HOME", weather = "WEATHER",
})

-- name -> category. Anything new in Sfx.Sounds or WeatherSounds.Sounds MUST be added here (verify_sound_lab.py fails otherwise).
Lab.CategoryOf = table.freeze({
    ui_click = "ui",
    pickup = "pickup", pickup_hi = "pickup", pickup_lo = "pickup",
    hatch_crack = "hatch", hatch_common = "hatch", hatch_rare = "hatch", hatch_legendary = "hatch",
    hatch_rattle = "hatch", hatch_crack_stage = "hatch", hatch_burst = "hatch",
    hatch_reveal_common = "hatch", hatch_reveal_uncommon = "hatch", hatch_reveal_rare = "hatch",
    hatch_reveal_epic = "hatch", hatch_reveal_legendary = "hatch",
    hatch_crunch_raw = "hatch", hatch_chime_raw = "hatch",
    shiny_bang = "rare", big_thud = "rare", fusion_reveal = "rare",
    run_start = "reward", run_end = "reward", level_up = "reward", shop_buy = "reward", shop_refresh = "reward",
    weather_start = "weather",
    rain_bed = "weather", thunder_bed = "weather", thunder_roll = "weather", thunder_strike = "weather",
    blizzard_bed = "weather", volcano_bed = "weather", volcano_boom = "weather", quake_bed = "weather",
    quake_burst = "weather", bloodmoon_bed = "weather", aurora_bed = "weather",
})

-- Raw ids used by HatchPresentation outside the Sfx pool (docs/77: Creator Store, ProSoundEffects).
Lab.Raw = table.freeze({
    {name = "hatch_crunch_raw", id = "rbxassetid://9120490790", volume = .38},
    {name = "hatch_chime_raw", id = "rbxassetid://9116394545", volume = .24},
})

export type Row = {name: string, category: string, id: string, volume: number, source: string, silent: boolean}

-- Every registered sound, sorted by category order then name. silent = no asset id yet (shows "no sound yet").
function Lab.rows(): {Row}
    local out: {Row} = {}
    local function add(name: string, id: string, volume: number, source: string)
        table.insert(out, {name = name, category = Lab.CategoryOf[name] or "other", id = id, volume = volume, source = source, silent = Sfx.normalizeId(id) == nil})
    end
    for name, e in Sfx.Sounds do add(name, e.id, e.volume, "sfx") end
    for name, e in WeatherSounds.Sounds do add(name, e.id, e.volume, "weather") end
    for _, r in Lab.Raw do add(r.name, r.id, r.volume, "raw") end
    local order: {[string]: number} = {}
    for i, c in Lab.Categories do order[c] = i end
    table.sort(out, function(a, b)
        local oa, ob = order[a.category] or 99, order[b.category] or 99
        if oa ~= ob then return oa < ob end
        return a.name < b.name
    end)
    return out
end

-- Categories with no playable sound at all yet (TODO for the owner): shown as gap lines in the lab.
function Lab.gaps(): {string}
    local have: {[string]: boolean} = {}
    for _, r in Lab.rows() do if not r.silent then have[r.category] = true end end
    local gaps = {}
    for _, c in Lab.Categories do if not have[c] then table.insert(gaps, c) end end
    return gaps
end

return Lab
