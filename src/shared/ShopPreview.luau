--!strict
-- BD-142 / BD-143 / BD-083: pure rules for the Aura and Trail shop cards (docs/72 copy, docs/103 card states).
-- No Instances here: src/client/ShopCards.luau draws what this returns. Tested by tools/verify_shop_preview.py.
local State = require(script.Parent.ShopCardState)
local P = {}
P.MinText = 14   -- docs/72: no text under 14 px
P.Touch = 44     -- smallest tap target in px
-- BD-1120: no rarity palette here any more. The chip colour is Theme.RarityColors (docs/114 s5.2), read through Shared/RarityWord by src/client/ShopCards.
P.AuraTiers = {Common = 1, Rare = 2, Legendary = 3}

-- Speed in words, never "1.04x": the number only picks the word.
function P.speedWords(speed: number): string
    if speed <= 1.001 then return "Normal speed" end
    if speed <= 1.05 then return "A little faster" end
    if speed <= 1.11 then return "Faster" end
    if speed <= 1.15 then return "Much faster" end
    return "Super fast"
end

function P.rarityChip(rarity: string?): {text: string}
    return {text = rarity or "Common"}
end

-- The owner's icon id for a trail, or nil (the card then shows the live preview). ids: Config.TrailIconAssetIds.
function P.trailIconId(ids: {[string]: string}?, trailId: string): string?
    local id = if ids then ids[trailId] else nil
    if type(id) == "string" and string.match(id, "^rbxassetid://%d+$") then return id end
    return nil
end

function P.auraTier(rarity: string?): number return P.AuraTiers[rarity or "Common"] or 1 end
function P.tierBadge(rarity: string?): string return "T" .. P.auraTier(rarity) end

-- info: {owned, equipped, level}. Returns what the card prints, in short words.
function P.trailCard(item, info)
    local look = State.look({owned = info.owned, levelNeeded = item.level, level = info.level,
        ownedButton = if info.equipped then "UNEQUIP" else "EQUIP", ownedActive = true}, item.price .. " Crystals")
    return {
        kind = look.kind, look = look, equipped = info.equipped == true, dim = look.dim,
        name = item.name, chip = P.rarityChip(item.rarity),
        levelText = if item.level > 1 then "Level " .. item.level else "Starter",
        speedText = P.speedWords(item.speed),
        caption = if info.equipped then "Equipped" elseif look.kind == State.Locked then item.price .. " Crystals" else look.caption,
        buttonText = look.buttonText, tone = if info.equipped then "equipped" else look.tone,
    }
end

function P.auraCard(item, growthText: string?, info)
    local look = State.look({owned = info.owned, ownedButton = if info.equipped then "UNEQUIP" else "EQUIP", ownedActive = true},
        item.price .. " Crystals")
    return {
        kind = look.kind, look = look, equipped = info.equipped == true, dim = look.dim,
        name = item.name, chip = P.rarityChip(item.rarity), tier = P.tierBadge(item.rarity),
        growthText = growthText or "Growth", caption = if info.equipped then "Equipped" else look.caption,
        buttonText = look.buttonText, tone = if info.equipped then "equipped" else look.tone,
    }
end
return P
