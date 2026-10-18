--!strict
-- BD-292 (docs/104 s6, docs/72): the ONE table of station sign words for the Cave hub, plus the walk-there toast. One or two
-- plain words, at most 14 characters, no numbers, no jargon (children are the audience). CaveHubLayout.STATION_DEFS still
-- carries the same strings for the sign props; tools/verify_hub_walk_there.py fails if the two ever differ.
-- Pure data: no requires, no Instances.
local Copy = {}
Copy.MaxLength = 14
-- The Heart has no sign on purpose (it is the plaza, not a place to open).
Copy.Signs = table.freeze({
    heart = "",
    gate = "ISLAND",
    nests = "NESTS",
    potions = "POTIONS",
    fusion = "FUSE",
    style = "SHOP",
    index = "DINOS",
    settings = "QUIET SPOT",
    fame = "TOP DINOS",
})
-- BD-1017 (docs/180 option A, behind Config.ShopPromptBubbleEnabled): the message bubble above a stall (and the Heart "Show off" spot). A title (the name on the
-- sign, in small letters) and ONE warm line. The line is at most BubbleLineMax characters so it fits the smallest bubble (HubWalkUpRules.bubbleLayout) without
-- shrinking under 14 px. Same child-copy rules as the signs (docs/72): plain short words, no numbers, no jargon.
Copy.BubbleLineMax = 24
Copy.BubbleTitleMax = 10
Copy.BubbleTitles = table.freeze({
    nests = "Nests",
    potions = "Potions",
    fusion = "Fuse",
    style = "Shop",
    index = "Dinos",
    heart = "Show off",
})
Copy.BubbleLines = table.freeze({
    nests = "Come and see your eggs!",
    potions = "Fresh potions here!",
    fusion = "Make a stronger dino!",
    style = "Auras and trails!",
    index = "Meet all your dinos!",
    heart = "Let everyone see you!",
})
Copy.GuideToast = "Follow the glow" -- shown when "Teleport to shops" is off and a rail button starts the moss trail (15 chars: a toast, not a sign)
-- Words a sign or toast must never contain (jargon / system words).
Copy.Forbidden = table.freeze({"station", "teleport", "menu", "server", "tier", "xp", "dna", "ui", "hud", "gui", "ack", "error"})

function Copy.sign(station: any): string?
    return if typeof(station) == "string" then Copy.Signs[station] else nil
end

function Copy.bubbleTitle(station: any): string?
    return if typeof(station) == "string" then Copy.BubbleTitles[station] else nil
end
function Copy.bubbleLine(station: any): string?
    return if typeof(station) == "string" then Copy.BubbleLines[station] else nil
end

-- BD-292: the text a sign PROP row shows, or nil. `key` is the prop key (hub_sign_stone / hub_sign_arrow), `owner` the station id.
-- The Heart has no sign; an unknown station has none.
function Copy.forRow(key: any, owner: any): string?
    if key ~= "hub_sign_stone" and key ~= "hub_sign_arrow" then return nil end
    local text = Copy.sign(owner)
    if text == nil or text == "" then return nil end
    return text
end

-- true when `text` is acceptable child-facing copy: no digits and no forbidden whole word (any case). Length is checked
-- separately (signs: MaxLength).
function Copy.acceptable(text: any): boolean
    if typeof(text) ~= "string" or text:find("%d") then return false end
    local lower = " " .. (text:lower():gsub("[^%a]+", " ")) .. " "
    for _, word in Copy.Forbidden do
        if lower:find(" " .. word .. " ", 1, true) then return false end
    end
    return true
end

return Copy
