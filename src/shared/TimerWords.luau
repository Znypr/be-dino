--!strict
-- BD-1124 (docs/202 R11 and R12, docs/220): the short words of the HUD timers, the potion shop restock line and the Index count, behind
-- Config.TimerChipsEnabled (short = true). With short = false every function returns exactly the Build 020 sentence, so the flag-off build does not change.
-- Pure: no Instances. Tested by tools/verify_timer_words.py. Time words come from UIFormat.duration (docs/72: "5 min", "40 s", never "5m 0s").
local UIFormat = require(script.Parent.UIFormat)
local W = {}

-- The weather tile: the icon is the picture, the words say what and for how long. Clear sky: "Next: 4 min"; during an event: "Rain: 2 min".
function W.weather(id: string, name: any, secondsLeft: number, short: boolean): string
    local time = UIFormat.duration(secondsLeft)
    local what = if type(name) == "string" and name ~= "" then name else id
    if id == "clear" then return if short then "Next: " .. time else "Weather in " .. time end
    return if short then what .. ": " .. time else what .. " " .. time
end

-- One active potion line: "Speed: 3 min" (short; the chip beside it is the picture) or "Speed potion 3 min".
function W.potion(kind: string, secondsLeft: number, short: boolean): string
    local word = string.upper(string.sub(kind, 1, 1)) .. string.sub(kind, 2)
    return if short then word .. ": " .. UIFormat.duration(secondsLeft) else word .. " potion " .. UIFormat.duration(secondsLeft)
end

-- The lines under the weather tile: every running potion (sorted), then the boost line. buffs: {[kind]: {id, expiresAt}}.
function W.potionLines(buffs: {[string]: any}, now: number, short: boolean, boosts: {string}): {string}
    local lines = {}
    for kind, buff in buffs do
        if buff.expiresAt > now then table.insert(lines, W.potion(kind, buff.expiresAt - now, short)) end
    end
    table.sort(lines)
    if #boosts > 0 then table.insert(lines, table.concat(boosts, " • ")) end
    return lines
end

-- The potion shop restock line.
function W.restock(crystals: any, secondsLeft: number, short: boolean): string
    return string.format(if short then "Crystals: %s  •  New in %s" else "Crystals: %s  •  New offers in %s", tostring(crystals), UIFormat.duration(secondsLeft))
end

-- The Index count on the big bar: "Found 1/22".
function W.found(found: number, total: number): string
    return string.format("Found %d/%d", found, total)
end

-- How full a drain bar is: 1 just after the potion was drunk, 0 when it ends. Unknown duration: nil (no bar is drawn).
function W.drain(expiresAt: number, duration: number?, now: number): number?
    if duration == nil or duration <= 0 then return nil end
    return math.clamp((expiresAt - now) / duration, 0, 1)
end

return W
