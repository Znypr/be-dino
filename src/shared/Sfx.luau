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
    run_end = {id = "rbxassetid://127962506254484", volume = .6, rate = 1, gap = .5},
    shop_buy = {id = "rbxassetid://102585210519734", volume = .6, rate = 1, gap = .15},
    shop_refresh = {id = "rbxassetid://91960074825710", volume = .45, rate = 1, gap = .5},
    weather_start = {id = "rbxassetid://120619985059497", volume = .6, rate = 1, gap = 1},
    level_up = {id = "rbxassetid://135894580270926", volume = .7, rate = 1, gap = .5},
    fusion_reveal = {id = "rbxassetid://90816090310479", volume = .75, rate = 1, gap = .3},
    ui_click = {id = "rbxassetid://77237659470894", volume = .4, rate = 1, gap = .04},
}
Sfx.Master = .5 -- global gain; synthesized placeholder sounds were far too loud (owner, 2026-10-15)
Sfx.PoolSize = 3
Sfx.Group = "BeDinoSfx"

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
local lastPlayed: {[string]: number} = {}
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
    if Sfx.throttled(entry, lastPlayed[name], now) then return false end
    local ok = pcall(function()
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
        sound.SoundId, sound.Volume, sound.PlaybackSpeed = assetId, entry.volume * Sfx.Master, entry.rate
        sound.TimePosition = 0
        sound:Play()
    end)
    if ok then lastPlayed[name] = now end
    return ok
end
return Sfx
