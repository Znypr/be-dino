--!strict
-- BD-1218 + BD-1219 (docs/242 benchmark gaps 3 and 4): calm music beds per place and the sounds for the silent cues, plus soft dino
-- footsteps by surface. Used ONLY while Config.AudioPolishEnabled is on (playtest profile); src/client/AudioPolish.client.luau applies it.
-- Flag off: nothing here is read, Sfx.Sounds keeps its empty owner slots and the game sounds exactly as before.
-- Every id is Roblox-licensed Creator Store audio (APMOfficial music, ProSoundEffects sound effects), checked with
-- MarketplaceService:GetProductInfo on 2026-11-16 and listed in docs/77. NOBODY HAS LISTENED: the owner judges by ear before it ships
-- (docs/87). Volumes follow docs/87: beds 0.15-0.3, cues 0.15-0.5 before Sfx.Master and the sliders.
local A = {}

-- Fills for the empty Sfx.Sounds slots (same fields as Sfx.Sounds). apply() copies id/volume/rate/len into Sfx.Sounds.
A.Fills = {
    hatch_rattle = {id = "rbxassetid://9112752910", volume = .3, rate = 1, gap = .12, len = .6}, -- Bubble Wobble Comic Bloops 4
    hatch_burst = {id = "rbxassetid://9119378289", volume = .45, rate = 1.1, gap = .3, len = .9}, -- Soft Suck Explosion Med Whoosh 8
    rare_hatch_fanfare = {id = "rbxassetid://9116395085", volume = .5, rate = 1, gap = .3, len = 2.5}, -- Magic Glows Soft Chiming Hits 5
    mutation_dewdrop_reveal = {id = "rbxassetid://9126190364", volume = .5, rate = 1, gap = .3, len = 1.5}, -- Water Drips Into Bowl
    mutation_charged_reveal = {id = "rbxassetid://9126072453", volume = .35, rate = 1, gap = .3, len = 1}, -- Synth Sparkle Bell Tone Burst
    mutation_frost_reveal = {id = "rbxassetid://9125644905", volume = .4, rate = 1, gap = .3, len = 2}, -- Magic Twirling Spinning Chime
    mutation_seismic_reveal = {id = "rbxassetid://9114166629", volume = .45, rate = .8, gap = .3, len = 1}, -- Dragon Footsteps 27, lower
    mutation_ember_reveal = {id = "rbxassetid://9114446852", volume = .35, rate = 1, gap = .3, len = 1}, -- Fire Whoosh 15
    mutation_aurora_reveal = {id = "rbxassetid://9125635650", volume = .45, rate = 1, gap = .3, len = 2.5}, -- Magical Exit Sparkling Chime
    mutation_bloodmoon_reveal = {id = "rbxassetid://9116394756", volume = .5, rate = .8, gap = .3, len = 2.5}, -- Magic Glows Chiming 3, lower
    defeat_soft = {id = "rbxassetid://9112752818", volume = .35, rate = .8, gap = .3, len = 1}, -- Bubble Wobble Comic Bloops 3, slower
    cracked_fail = {id = "rbxassetid://9113959343", volume = .35, rate = 1, gap = .3, len = .8}, -- Crack Egg Crunchy 11
    crystal_cue = {id = "rbxassetid://9114619221", volume = .3, rate = 1.1, gap = .3, len = .8}, -- Glass Tinks 3
    nest_open_cue = {id = "rbxassetid://9120873624", volume = .4, rate = 1, gap = .3, len = 1.2}, -- Wooden Chest Open Cedar Box 5
    -- not benchmark slots: a soft pop when a menu window opens or closes
    ui_open = {id = "rbxassetid://9113537815", volume = .2, rate = 1, gap = .25, len = .4}, -- Boink Wet Suction Pop Blip Hollow 3
    ui_close = {id = "rbxassetid://9113537815", volume = .15, rate = .85, gap = .25, len = .4},
}
-- Music beds: one per place, crossfaded. hatch plays softer UNDER the hatch cues (docs/242: "softer under the hatch").
A.Music = {
    island = {id = "rbxassetid://9046598930", volume = .22}, -- APM "Watching the Garden Grow (a)" (Johnny Wishbone), 163 s
    home = {id = "rbxassetid://9046598509", volume = .2}, -- APM "Tiny Twinkle Toes (a)" (Johnny Wishbone), 141 s
    hatch = {id = "rbxassetid://1842071889", volume = .14}, -- APM "Whimsical Carousel (a)" (Guy Edward Fletcher), 135 s
}
A.MusicOrder = {"island", "home", "hatch"}
A.FadeSeconds = 2.5 -- full crossfade time (0 -> bed volume)

-- Footsteps: one or two variants per surface; the walker alternates variants and jitters pitch a little.
A.Steps = {
    soft = {ids = {"rbxassetid://9114165461", "rbxassetid://9114165789"}, volume = .16, rate = 1.05}, -- Dragon Footsteps 5 / 11
    sand = {ids = {"rbxassetid://9118685591"}, volume = .14, rate = 1.1}, -- Rocks Dirt Impacts In Ground 12
    rock = {ids = {"rbxassetid://9118609285"}, volume = .1, rate = 1.15}, -- Rock Hits Rock 10
    wood = {ids = {"rbxassetid://9114166137"}, volume = .14, rate = 1.2}, -- Dragon Footsteps 18, higher
    snow = {ids = {"rbxassetid://9126274134"}, volume = .14, rate = 1.1}, -- Canoe Paddle Into Icy Snow
    water = {ids = {"rbxassetid://9120609652"}, volume = .14, rate = 1}, -- Water Wading Shallow Pool 2
}
local surfaceOf: {[string]: string} = {
    Sand = "sand", Sandstone = "sand", Mud = "sand", Salt = "sand",
    Rock = "rock", Slate = "rock", Basalt = "rock", Granite = "rock", Concrete = "rock", Cobblestone = "rock", Pavement = "rock",
    Brick = "rock", Limestone = "rock", Marble = "rock", CrackedLava = "rock", Asphalt = "rock", Pebble = "rock",
    Wood = "wood", WoodPlanks = "wood",
    Snow = "snow", Ice = "snow", Glacier = "snow",
    Water = "water",
}
-- Pure: material NAME (Enum.Material.X.Name) -> step set; anything else (Grass, LeafyGrass, Ground, Plastic ...) is "soft".
function A.surface(materialName: string?, swimming: boolean?): string?
    if swimming then return "water" end
    if materialName == nil or materialName == "Air" then return nil end
    return surfaceOf[materialName] or "soft"
end
A.StepStride = 6.5 -- studs per step at scale 1
A.StepMin, A.StepMax = .26, .6
A.StepMinSpeed = 3 -- slower than this = standing, no steps
-- Pure: seconds between steps at a ground speed (studs/s) and dino size scale (nil = 1). nil = no steps.
function A.stepInterval(speed: number, scale: number?): number?
    if speed ~= speed or speed < A.StepMinSpeed then return nil end
    local s = math.clamp(scale or 1, .5, 3)
    return math.clamp(A.StepStride * s / speed, A.StepMin, A.StepMax * s)
end

-- Pure: which bed plays. screen = BeDinoUI "Screen" attribute ("" = no window), location = player "Location" attribute.
function A.musicTarget(location: any, screen: any): string
    if screen == "hatch" then return "hatch" end
    if location == "Island" then return "island" end
    return "home"
end
-- Pure: move a bed level toward its target at full-bed-per-FadeSeconds.
function A.step(level: number, target: number, dt: number, full: number): number
    local delta = math.max(full, .01) * dt / A.FadeSeconds
    if level < target then return math.min(target, level + delta) end
    return math.max(target, level - delta)
end
-- Pure: target level per bed (sound off = every bed fades to 0).
function A.bedTargets(active: string, soundOn: boolean): {[string]: number}
    local out = {}
    for _, name in A.MusicOrder do out[name] = if soundOn and name == active then A.Music[name].volume else 0 end
    return out
end

-- Pure: the sound for the hatcher's own rare celebration (RareHatchClient). A known mutation gets its own reveal; any other
-- non-secret celebration gets the soft fanfare instead of the harsh shiny_bang (docs/161). planSound "" (secret) stays silent.
function A.rareSound(planSound: string, data: any): string
    if planSound == "" then return "" end
    if type(data) == "table" and (data.kind == "mutation" or data.mutation == true) and type(data.mutationId) == "string" then
        local name = "mutation_" .. string.lower(data.mutationId) .. "_reveal"
        if A.Fills[name] then return name end
    end
    return "rare_hatch_fanfare"
end
-- Hatch code (owned by the hatch PR) may call Sfx.play(AudioPolish.HatchCueNames.cracked) for a failed Cracked egg.
A.HatchCueNames = {cracked = "cracked_fail", fanfare = "rare_hatch_fanfare", burst = "hatch_burst", rattle = "hatch_rattle"}
-- Run end reasons that count as a gentle defeat (server RunLifecycle.tryEnd reasons).
A.DefeatReasons = {Defeated = true, Eaten = true, Death = true}

-- Copies the fills into the empty Sfx.Sounds slots, points the crystal alias at crystal_cue and lets SfxRules keep (spaced)
-- rattles. Only the client script calls this, and only with the flag on. Returns the number of slots filled.
function A.apply(Sfx: any, Rules: any?): number
    local n = 0
    for name, fill in A.Fills do
        local entry = Sfx.Sounds[name]
        if entry and (entry.id == nil or entry.id == "") then
            entry.id, entry.volume, entry.rate, entry.gap, entry.len = fill.id, fill.volume, fill.rate, fill.gap, fill.len
            n += 1
        end
    end
    if Rules then
        Rules.KeepRattle = true
        local alias = Rules.Aliases.crystal_reward
        if alias then alias.cue, alias.volume = "crystal_cue", 1 end
    end
    return n
end
return A
