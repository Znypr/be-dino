--!strict
-- BD-1178 (docs/228 board 3, docs/231): the Crystal Shop in the "Toybox" look, as plain rules. No engine call, no clock, no RNG:
-- tools/verify_toybox_shop.py runs this file with the pinned Luau runtime. src/client/ShopToyboxCard.luau draws what this returns.
-- Words are for children (docs/72): short, obvious, no numbers like "1.25x". Nothing here touches prices, saves or the server.
local S = {}

S.Rarities = {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"}

-- The card picture (one of the six toybox_card_* slots) of a rarity word. An unknown or missing rarity is Common, like RarityWord.get.
function S.cardSlot(rarity: any): string
    if type(rarity) == "string" then
        local lower = string.lower(rarity)
        for _, name in S.Rarities do
            if string.lower(name) == lower then return "toybox_card_" .. lower end
        end
    end
    return "toybox_card_common"
end

-- A locked Legendary (or Mythic) card keeps its secret: a "?" instead of the picture and one short hint. Only a LOCKED card does this.
function S.mystery(rarity: any, tone: any): boolean
    return tone == "locked" and (rarity == "Legendary" or rarity == "Mythic")
end
S.MysteryMark = "?"

-- The hint under the "?": what the item asks for, in words the game already knows (a trail needs an account level).
function S.hint(item: {level: number?}): string
    local level = item.level or 1
    if level > 1 then return "Reach level " .. level end
    return "Keep playing to find it"
end

-- The one wide button: which colour it wears. Green for buy and equip, the card grey for unequip, flat grey for locked and sold out
-- (the skin turns each of them into the nearest gloss button).
function S.buttonColour(tone: string): string
    if tone == "buy" or tone == "equip" then return "accent" end
    if tone == "unequip" then return "card" end
    return "soldOut"
end

-- The slow rays behind the art: the existing shaftGradient texture (EffectAssets, owner upload), three copies fanned out and turned very
-- slowly. No texture bound = no rays (the cream box stays plain); nothing is drawn in code. Reduce Motion keeps them still.
S.RaysKey = "shaftGradient"
S.RayAngles = {-35, 0, 35}
S.RaySeconds = 40 -- one full turn
S.RayTransparency = 0.55
function S.raySeconds(reduceMotion: boolean): number
    return if reduceMotion then 0 else S.RaySeconds
end

-- The soft gold glow of the equipped card: the existing glowPlate texture behind the card, plus the gold ring the old card already has.
S.GlowKey = "glowPlate"

-- The "Buy X?" popup: the name in the title and "Not now" instead of Cancel. The page keeps its price and balance lines.
function S.confirm(name: string, isTrail: boolean): {title: string, buy: string, cancel: string}
    return {
        title = "Buy " .. name .. "?",
        buy = if isTrail then "BUY TRAIL" else "BUY AURA",
        cancel = "NOT NOW",
    }
end

-- Where the card parts go, in design px. `rowH` is the height of the name row (also the Info button, a 44 px tap target on screen),
-- `pillH` the rarity word row, `bandH` the benefit band, `buyY` the top of the action button.
function S.layout(buyY: number, rowH: number, pillH: number, bandH: number): {pillY: number, artY: number, artH: number, bandY: number}
    local pillY = rowH + 2
    local artY = pillY + pillH + 4
    local artH = math.max(buyY - 6 - artY, 0)
    return {pillY = pillY, artY = artY, artH = artH, bandY = math.max(artH - bandH, 0)}
end

return S
