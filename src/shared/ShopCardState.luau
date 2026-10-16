--!strict
-- BD-267: one pure rule for how a shop card looks and reads: Normal / Owned / Sold out (+ Locked).
-- Sold out and Owned are calm: grey or soft, no red, no countdown pressure (docs/72, docs/103).
-- The client component (src/client/ShopCard.luau) only applies what this returns. Tested by tools/verify_odds_copy.py.
local State = {}
State.Normal, State.Owned, State.SoldOut, State.Locked = "normal", "owned", "soldOut", "locked"

-- info: {owned: boolean?, left: number? (stock; nil = unlimited), levelNeeded: number?, level: number?}
function State.kind(info): string
    if info.owned == true then return State.Owned end
    if info.left ~= nil and info.left <= 0 then return State.SoldOut end
    if info.levelNeeded ~= nil and (info.level or 0) < info.levelNeeded then return State.Locked end
    return State.Normal
end

-- priceText: e.g. "30 Crystals". Returns look = {kind, dim, caption, buttonText, active, tone}
-- tone: "price" (gold) | "calm" (soft grey)
function State.look(info, priceText: string)
    local kind = State.kind(info)
    if kind == State.Owned then
        return {kind = kind, dim = false, caption = "Owned", buttonText = info.ownedButton or "OWNED", active = info.ownedActive == true, tone = "calm"}
    elseif kind == State.SoldOut then
        return {kind = kind, dim = true, caption = "Sold out. Back later!", buttonText = "SOLD OUT", active = false, tone = "calm"}
    elseif kind == State.Locked then
        return {kind = kind, dim = true, caption = "Level " .. tostring(info.levelNeeded), buttonText = "LEVEL " .. tostring(info.levelNeeded), active = true, tone = "calm"}
    end
    local caption = priceText
    if info.left ~= nil then caption = priceText .. "  " .. tostring(info.left) .. " left" end
    return {kind = kind, dim = false, caption = caption, buttonText = info.buyButton or "BUY", active = true, tone = "price"}
end

return State
