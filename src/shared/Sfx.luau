--!strict
-- Polish pass: one table of named UI/gameplay sounds. Every id is an EMPTY PROVISIONAL placeholder
-- until the owner uploads the audio pack (docs/62). Empty or malformed ids are a silent no-op, so the
-- game stays silent (never errors) until ids are filled. Honors the SOUND ON/OFF setting
-- (Theme.HatchSoundEnabled). Sound instances are pooled per name; repeats are throttled.
local Sfx = {}
-- id = "" PROVISIONAL (do not invent ids). gap = minimum seconds between plays of the same name.
Sfx.Sounds = {
    hatch_crack = {id = "", volume = .6, rate = 1, gap = .12},
    hatch_common = {id = "", volume = .6, rate = 1, gap = .2},
    hatch_rare = {id = "", volume = .7, rate = 1, gap = .2},
    hatch_legendary = {id = "", volume = .85, rate = 1, gap = .2},
    shiny_bang = {id = "", volume = .8, rate = 1, gap = .3},
    big_thud = {id = "", volume = .8, rate = 1, gap = .3},
    pickup = {id = "", volume = .35, rate = 1, gap = .06},
    run_start = {id = "", volume = .6, rate = 1, gap = .5},
    run_end = {id = "", volume = .6, rate = 1, gap = .5},
    shop_buy = {id = "", volume = .6, rate = 1, gap = .15},
    shop_refresh = {id = "", volume = .45, rate = 1, gap = .5},
    weather_start = {id = "", volume = .6, rate = 1, gap = 1},
    level_up = {id = "", volume = .7, rate = 1, gap = .5},
    fusion_reveal = {id = "", volume = .75, rate = 1, gap = .3},
    ui_click = {id = "", volume = .4, rate = 1, gap = .04},
}
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
-- Pure: sound name for a hatched egg. rarity 1..3 (Common/Rare/Legendary).
function Sfx.hatchName(rarity: number?): string
    return if rarity == 3 then "hatch_legendary" elseif rarity == 2 then "hatch_rare" else "hatch_common"
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
        sound.SoundId, sound.Volume, sound.PlaybackSpeed = assetId, entry.volume, entry.rate
        sound.TimePosition = 0
        sound:Play()
    end)
    if ok then lastPlayed[name] = now end
    return ok
end
return Sfx
