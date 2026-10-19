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

-- BD-1118 / BD-1144 (docs/202 R3, docs/213): the card with the PRICE ON THE BUTTON. data = what P.trailCard / P.auraCard returned for the same item.
-- The one button says the price ("35 Crystals") while the item can be bought, EQUIP / UNEQUIP when owned, LEVEL n when locked, SOLD OUT when sold out.
-- tone: buy | equip | unequip | locked | soldOut (the client picks the colour: green for buy and equip, the card colour for unequip, grey for the rest).
-- Details (rarity, level, odds) are NOT on the card: they sit behind the Info word (P.InfoWord) on the read-only page of P.infoLines.
P.InfoWord = "Info"
function P.priceCard(data, item, isTrail: boolean)
    local button
    if data.equipped then button = {text = "UNEQUIP", tone = "unequip", active = true}
    elseif data.kind == State.Owned then button = {text = "EQUIP", tone = "equip", active = true}
    elseif data.kind == State.Locked then button = {text = data.buttonText, tone = "locked", active = true} -- a tap says why (the level note), like the old card
    elseif data.kind == State.SoldOut then button = {text = "SOLD OUT", tone = "soldOut", active = false}
    else button = {text = item.price .. " Crystals", tone = "buy", active = true} end
    return {
        name = item.name, rarity = item.rarity or "Common", benefit = if isTrail then data.speedText else data.growthText,
        button = button, equipped = data.equipped == true, dim = data.dim == true, look = data.look, info = P.InfoWord,
    }
end

-- The lines of the read-only details page behind Info: benefit, rarity (the tier word, coloured by the client), the level a trail needs, then
-- what the player has: on the dino, owned, or the price. Short words for a child (docs/72); no odds (auras and trails have none).
function P.infoLines(item, isTrail: boolean, info, growthText: string?): {string}
    local lines = {if isTrail then P.speedWords(item.speed) else (growthText or "Growth")}
    table.insert(lines, (item.rarity or "Common") .. (if isTrail then " trail" else " aura"))
    if isTrail then table.insert(lines, if item.level > 1 then "Needs level " .. item.level else "Starter trail") end
    if info.equipped then table.insert(lines, "On your dino now")
    elseif info.owned then table.insert(lines, "You own this")
    else table.insert(lines, item.price .. " Crystals") end
    return lines
end
return P
