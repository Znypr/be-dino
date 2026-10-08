--!strict
local Config = require(script.Parent.Config)
local Traits = {}
function Traits.roll(eventId: string, shinyRoll: number, bigRoll: number)
    return {
        shiny = Config.IrregularWeather[eventId] == true and shinyRoll < Config.ShinyChance,
        big = bigRoll < Config.BigChance,
    }
end
function Traits.key(mutationId: string, shiny: boolean, big: boolean): string
    return mutationId .. ":" .. (if shiny then "shiny" else "plain") .. ":" .. (if big then "big" else "normal")
end
function Traits.selected(entry)
    local selected = nil
    local best = -1
    for key, variant in (if entry then entry.variants or {} else {}) do
        local rank = (if variant.big then 2 else 0) + (if variant.shiny then 1 else 0)
        if variant.count > 0 and (rank > best or (rank == best and selected and key < selected.key)) then
            best = rank
            selected = {key = key, big = variant.big, shiny = variant.shiny, mutationId = variant.mutationId}
        end
    end
    return selected
end
function Traits.valid(variants): boolean
    if typeof(variants) ~= "table" then return false end
    for key, variant in variants do
        if typeof(variant) ~= "table" or typeof(variant.big) ~= "boolean" or typeof(variant.shiny) ~= "boolean"
            or typeof(variant.mutationId) ~= "string" or typeof(variant.count) ~= "number"
            or variant.count ~= variant.count or variant.count < 0 or variant.count % 1 ~= 0 or variant.count > 2000000000
            or key ~= Traits.key(variant.mutationId, variant.shiny, variant.big)
            or not (variant.shiny or variant.big) then return false end
    end
    return true
end
return Traits
