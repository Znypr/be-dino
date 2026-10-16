--!strict
-- BD-393 (docs/72 words, docs/46): the Aura and Trail shops style ONE dino, the equipped one. This is the pure copy and layout
-- for the "For: <dino>" header drawn by ShopCards.forHeader. Short, kid-readable lines; no jargon.
local Copy = {}
Copy.HeaderHeight = 40 -- studs of body height the header strip takes (cards move down by this much)
Copy.CardsHeightDesktop = 250 -- card height on desktop with the header (was 270)
Copy.Note = "Switch dinos in Dinos to style another one"
Copy.MaxTitleLength = 22
-- "For: Compy". name = the species display name; falls back to "your dino" when nothing is known.
function Copy.title(name: any): string
    local text = if type(name) == "string" and name ~= "" then name else "your dino"
    if #text > Copy.MaxTitleLength then text = string.sub(text, 1, Copy.MaxTitleLength - 1) .. "." end
    return "For: " .. text
end
return Copy
