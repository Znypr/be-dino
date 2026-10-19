--!strict
-- BD-1124 (docs/202 R11, docs/220): the weather tile and the active-potion lines of the bottom-right HUD. Moved out of Bootstrap.client
-- (200-local and size limits) with the same behaviour; with Config.TimerChipsEnabled the words are the short ones of Shared/TimerWords
-- ("Next: 4 min", "Rain: 2 min", "Speed: 3 min") and PotionChips draws a drain bar under each potion chip. The weather toast and its sound are unchanged.
-- attach(ctx) once with Bootstrap's tile, labels and helpers; refresh(progression, now) every HUD tick.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Theme = require(Shared:WaitForChild("UITheme"))
local Sfx = require(Shared:WaitForChild("Sfx"))
local UIFormat = require(Shared:WaitForChild("UIFormat"))
local Words = require(Shared:WaitForChild("TimerWords"))
local ProgressionConfig = require(Shared:WaitForChild("ProgressionConfig"))
local ProgressionRules = require(Shared:WaitForChild("ProgressionRules"))
local PotionChips = require(script.Parent:WaitForChild("PotionChips"))
local C = Theme.Colors

local M = {}
local ctx: any = nil
local weatherArt: Frame? = nil
local lastWeather = ""

local function placeArt(art: Frame?)
    if art then art.Position, art.Size = UDim2.fromOffset(4, 7), UDim2.fromOffset(48, 48) end
end

function M.short(): boolean
    return Config.TimerChipsEnabled == true
end

-- d: {tile = the weather tile, text = its label, buffs = the potion lines label, notify, num}
function M.attach(d: any)
    ctx = d
    weatherArt = Theme.icon(d.tile, "weather")
    placeArt(weatherArt)
end

function M.refresh(p: any, now: number)
    local d = ctx
    if d == nil then return end
    local id = workspace:GetAttribute("WeatherId") or "clear"
    if id ~= lastWeather then
        lastWeather = id
        if weatherArt then weatherArt:Destroy() end
        local event = ProgressionRules.item(ProgressionConfig.Weather, id)
        weatherArt = Theme.icon(d.tile, if event then event.icon or id else "weather")
        placeArt(weatherArt)
        if id ~= "clear" then
            d.notify((workspace:GetAttribute("WeatherName") or id) .. " started!", C.blue, {key = "weather", icon = if event then event.icon or id else "weather", body = "Special eggs can drop!"})
            Sfx.play("weather_start")
        end
    end
    local short = M.short()
    local endsAt = if id == "clear" then workspace:GetAttribute("NextWeatherAt") else workspace:GetAttribute("WeatherEndsAt")
    d.text.Text = Words.weather(id, workspace:GetAttribute("WeatherName"), (endsAt or now) - now, short)
    local boosts = UIFormat.boostLines(d.num("GrowthMultiplier"), d.num("SpeedMultiplier"), d.num("LootMultiplier"))
    d.buffs.Text = table.concat(Words.potionLines(p.buffs, now, short, boosts), "\n")
    PotionChips.update(p.buffs, now)
end

return M
