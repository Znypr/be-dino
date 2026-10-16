--!strict
-- Polish pass: one table of named UI/gameplay sounds. The 17-sound pack was uploaded by the owner on 2026-10-15
-- (docs/77); hatch_rattle and hatch_burst still have no sound and stay empty (silent). Empty or malformed ids are a
-- silent no-op, so a missing sound never errors. Honors the SOUND ON/OFF setting
-- (Theme.HatchSoundEnabled). Sound instances are pooled per name; repeats are throttled.
local Sfx = {}
-- id = "" PROVISIONAL (do not invent ids). gap = minimum seconds between plays of the same name.
Sfx.Sounds = {
    hatch_crack = {id = "rbxassetid://135613869332284", volume = .6, rate = 1, gap = .12},
    hatch_common = {id = "rbxassetid://123602379376075", volume = .6, rate = 1, gap = .2},
    hatch_rare = {id = "rbxassetid://100769608611671", volume = .7, rate = 1, gap = .2},
    hatch_legendary = {id = "rbxassetid://109331854464968", volume = .85, rate = 1, gap = .2},
    -- Hatch sequence hooks (HatchTimeline cues): silent until ids are bound.
    hatch_rattle = {id = "", volume = .5, rate = 1, gap = .12},
    hatch_crack_stage = {id = "rbxassetid://135613869332284", volume = .6, rate = 1, gap = .2},
    hatch_burst = {id = "", volume = .8, rate = 1, gap = .3},
    hatch_reveal_common = {id = "rbxassetid://123602379376075", volume = .6, rate = 1, gap = .2},
    hatch_reveal_uncommon = {id = "rbxassetid://123602379376075", volume = .65, rate = 1, gap = .2},
    hatch_reveal_rare = {id = "rbxassetid://100769608611671", volume = .75, rate = 1, gap = .2},
    hatch_reveal_epic = {id = "rbxassetid://109331854464968", volume = .85, rate = 1, gap = .2},
    hatch_reveal_legendary = {id = "rbxassetid://109331854464968", volume = .95, rate = 1, gap = .2},
    shiny_bang = {id = "rbxassetid://124365194004947", volume = .8, rate = 1, gap = .3},
    big_thud = {id = "rbxassetid://88666885925372", volume = .8, rate = 1, gap = .3},
    pickup = {id = "rbxassetid://97315544055472", volume = .35, rate = 1, gap = .06},
    pickup_hi = {id = "rbxassetid://86225160041514", volume = .35, rate = 1, gap = .06},
    pickup_lo = {id = "rbxassetid://80767583749596", volume = .35, rate = 1, gap = .06},
    run_start = {id = "rbxassetid://87202810278231", volume = .25, rate = 1, gap = .5},
    -- BD-166: run end reuses the short soft run_start chime, lower and slightly slower; the sharp 1.1 s 3-note run_end sound is retired from play.
    run_end = {id = "rbxassetid://87202810278231", volume = .2, rate = .9, gap = .5, len = .6},
    shop_buy = {id = "rbxassetid://102585210519734", volume = .35, rate = 1, gap = .15},
    shop_refresh = {id = "rbxassetid://91960074825710", volume = .45, rate = 1, gap = .5},
    weather_start = {id = "rbxassetid://120619985059497", volume = .2, rate = 1, gap = 1},
    level_up = {id = "rbxassetid://135894580270926", volume = .4, rate = .95, gap = .5, len = 1.5},
    fusion_reveal = {id = "rbxassetid://90816090310479", volume = .75, rate = 1, gap = .3},
    ui_click = {id = "rbxassetid://77237659470894", volume = .4, rate = 1, gap = .04},
    rare_hatch_fanfare = {id = "", volume = .6, rate = 1, gap = .3}, -- owner upload slot (docs/120 section 6); silent while empty
    mutation_dewdrop_reveal = {id = "", volume = .6, rate = 1, gap = .3}, -- owner upload slot (docs/120 section 6); silent while empty
    mutation_charged_reveal = {id = "", volume = .6, rate = 1, gap = .3}, -- owner upload slot (docs/120 section 6); silent while empty
    mutation_frost_reveal = {id = "", volume = .6, rate = 1, gap = .3}, -- owner upload slot (docs/120 section 6); silent while empty
    mutation_seismic_reveal = {id = "", volume = .6, rate = 1, gap = .3}, -- owner upload slot (docs/120 section 6); silent while empty
    mutation_ember_reveal = {id = "", volume = .6, rate = 1, gap = .3}, -- owner upload slot (docs/120 section 6); silent while empty
    mutation_aurora_reveal = {id = "", volume = .6, rate = 1, gap = .3}, -- owner upload slot (docs/120 section 6); silent while empty
    mutation_bloodmoon_reveal = {id = "", volume = .6, rate = 1, gap = .3}, -- owner upload slot (docs/120 section 6); silent while empty
    defeat_soft = {id = "", volume = .6, rate = 1, gap = .3}, -- owner upload slot (docs/120 section 6); silent while empty
    cracked_fail = {id = "", volume = .6, rate = 1, gap = .3}, -- owner upload slot (docs/120 section 6); silent while empty
    crystal_cue = {id = "", volume = .6, rate = 1, gap = .3}, -- owner upload slot (docs/120 section 6); silent while empty
    nest_open_cue = {id = "", volume = .6, rate = 1, gap = .3}, -- owner upload slot (docs/120 section 6); silent while empty
}
Sfx.Master = .5 -- global gain; synthesized placeholder sounds were far too loud (owner, 2026-10-15)
Sfx.PoolSize = 3
-- BD-081 audit (docs/100): no cue may exceed MaxCueVolume before Master x group (clamped in Sfx.play, asset ids unchanged).
Sfx.MaxCueVolume = .9
-- Rapid cues (food/pickup ticks) share ONE throttle across variants and call sites (Bootstrap + DinoMotion + CombatHud
-- can all fire pickup in the same frame): at most one per RapidGap seconds, whichever variant.
Sfx.RapidNames = {pickup = true, pickup_hi = true, pickup_lo = true}
Sfx.RapidGap = .15
function Sfx.rapidThrottled(name: string, lastRapid: number?, now: number): boolean
    return Sfx.RapidNames[name] == true and lastRapid ~= nil and now - lastRapid < Sfx.RapidGap
end
function Sfx.clampVolume(v: number): number
    return math.clamp(v, 0, Sfx.MaxCueVolume)
end
Sfx.Group = "BeDinoSfx"

-- BD-258: reward cues (run_end, level_up, nest opened ...) play ONE AT A TIME. Pure: given the time the last cue
-- finishes (+ a pause) and `now`, returns when this cue may start and the new free time. A cue never starts less than
-- CueGap after the previous one started, and a cue that would wait longer than CueMaxWait is dropped (start = nil).
Sfx.CueGap = .6
Sfx.CueMaxWait = 3
function Sfx.cueSlot(freeAt: number, now: number, len: number?): (number?, number)
    local start = math.max(now, freeAt)
    if start - now > Sfx.CueMaxWait then return nil, freeAt end
    return start, start + math.max(Sfx.CueGap, (len or 0) + .15)
end
-- Pure: returns a "rbxassetid://N" string, or nil for empty/invalid ids.
function Sfx.normalizeId(id: any): string?
    if type(id) == "number" and id > 0 and id % 1 == 0 then return "rbxassetid://" .. string.format("%d", id) end
    if type(id) ~= "string" then return nil end
    local digits = string.match(id, "^rbxassetid://(%d+)$") or string.match(id, "^(%d+)$")
    if not digits or tonumber(digits) == 0 then return nil end
    return "rbxassetid://" .. digits
end
-- Pure: should a play at `now` be allowed given the previous accepted play time (nil = never)?
function Sfx.throttled(entry: any, last: number?, now: number): boolean
    if type(entry) ~= "table" then return true end
    return last ~= nil and now - last < (entry.gap or 0)
end
-- Pure: next round-robin slot (1..size).
function Sfx.nextSlot(current: number, size: number): number
    return current % size + 1
end
-- Pure: sound name for a hatched egg. rarity 1..5 (Config.SpeciesRarityNames): Common/Uncommon share
-- the common sting, Rare has its own, Epic/Legendary share the big one.
function Sfx.hatchName(rarity: number?): string
    local r = rarity or 1
    return if r >= 4 then "hatch_legendary" elseif r == 3 then "hatch_rare" else "hatch_common"
end

-- Pure: reveal sting for a hatched dinosaur, one hook per rarity 1..5.
Sfx.RevealNames = {"hatch_reveal_common", "hatch_reveal_uncommon", "hatch_reveal_rare", "hatch_reveal_epic", "hatch_reveal_legendary"}
function Sfx.revealName(rarity: number?): string
    return Sfx.RevealNames[math.clamp(math.floor(rarity or 1), 1, #Sfx.RevealNames)]
end

local pools: {[string]: {sounds: {Sound}, slot: number}} = {}
-- BD-339/341/342: voice limiter, ducking, dedupe and jitter (pure rules in SfxRules; loaded lazily so a missing module is a no-op).
local active: {any} = {}
local playCount: {[string]: number} = {}
local function rules(): any?
    local ok, mod = pcall(function() return require((script :: any).Parent.SfxRules) end)
    return if ok then mod else nil
end
local lastPlayed: {[string]: number} = {}
local lastRapid: number? = nil
local folder: Instance? = nil

local function enabled(): boolean
    local ok, value = pcall(function()
        return (require((script :: any).Parent.UITheme) :: any).HatchSoundEnabled ~= false
    end)
    return not ok or value
end

-- Returns true when a sound was actually started. Never throws.
function Sfx.play(name: string): boolean
    local entry = Sfx.Sounds[name]
    if not entry then return false end
    local assetId = Sfx.normalizeId(entry.id)
    if not assetId or not enabled() then return false end
    local now = os.clock()
    if Sfx.throttled(entry, lastPlayed[name], now) or Sfx.rapidThrottled(name, lastRapid, now) then return false end
    local R = rules()
    local replaceSound: Sound? = nil
    if R then
        if R.deduped(name, lastPlayed[name], now) then return false end
        local action, index = R.limit(active, name, now)
        if action == "drop" then return false end
        if action == "replace" and index then replaceSound = active[index].sound table.remove(active, index) end
    end
    local ok = pcall(function()
        if replaceSound then replaceSound:Stop() end
        if not folder or not folder.Parent then
            local created = Instance.new("Folder")
            created.Name = Sfx.Group
            created.Parent = game:GetService("SoundService")
            folder = created
            pools = {}
        end
        local pool = pools[name]
        if not pool then pool = {sounds = {}, slot = 0} pools[name] = pool end
        pool.slot = Sfx.nextSlot(pool.slot, Sfx.PoolSize)
        local sound = pool.sounds[pool.slot]
        if not sound or not sound.Parent then
            sound = Instance.new("Sound")
            sound.Name = name
            sound.Parent = folder
            pool.sounds[pool.slot] = sound
        end
        local count = (playCount[name] or 0) + 1
        playCount[name] = count
        local volume = Sfx.clampVolume(entry.volume) * Sfx.Master
        sound.SoundId, sound.Volume, sound.PlaybackSpeed = assetId, volume, entry.rate * (if R then R.jitter(name, count) else 1)
        if R then
            local len = (entry :: any).len or R.DefaultLen
            for i = #active, 1, -1 do
                local other = active[i]
                if other.endsAt <= now or not other.sound.Parent then table.remove(active, i)
                else
                    local mult = R.duck(name, other.name)
                    if mult < 1 then
                        other.sound.Volume = other.volume * mult
                        task.delay(len, function() if other.sound.Parent then other.sound.Volume = other.volume end end)
                    end
                end
            end
            table.insert(active, {name = name, sound = sound, volume = volume, startedAt = now, endsAt = now + len})
        end
        -- Mixer: master x Sounds sliders (AudioMixer.luau). Outside Roblox/tests the require fails and the sound plays ungrouped.
        local okMixer, mixer = pcall(function() return require((script :: any).Parent.AudioMixer) :: any end)
        if okMixer then mixer.attach(sound, "sfx") end
        sound.TimePosition = 0
        sound:Play()
    end)
    if ok then
        lastPlayed[name] = now
        if Sfx.RapidNames[name] then lastRapid = now end
    end
    return ok
end

-- BD-342: soft reward cue that REUSES a registered cue (see SfxRules.Aliases), behind a cooldown.
local aliasLast: {[string]: number} = {}
function Sfx.playAlias(alias: string): boolean
    local R = rules()
    local def = if R then R.Aliases[alias] else nil
    if not def then return false end
    local now = os.clock()
    if aliasLast[alias] and now - aliasLast[alias] < def.cooldown then return false end
    local base = Sfx.Sounds[def.cue]
    if not base then return false end
    local saved = base.volume
    base.volume = saved * def.volume
    local ok = Sfx.play(def.cue)
    base.volume = saved
    if ok then aliasLast[alias] = now end
    return ok
end

local cueFreeAt = 0
local cueRequested: {[string]: number} = {}
-- Plays a reward cue in turn (see Sfx.cueSlot). Returns false when it was dropped. Never throws.
function Sfx.playCue(name: string): boolean
    local entry = Sfx.Sounds[name]
    local now = os.clock()
    -- BD-342: the same reward cue requested twice within its window (level up + nest open) is one cue.
    local R = rules()
    if R and R.deduped(name, cueRequested[name], now) then return false end
    cueRequested[name] = now
    local start, freeAt = Sfx.cueSlot(cueFreeAt, now, if entry then (entry :: any).len else nil)
    if start == nil then return false end
    cueFreeAt = freeAt
    if start - now < .01 then return Sfx.play(name) end
    task.delay(start - now, Sfx.play, name)
    return true
end
return Sfx
