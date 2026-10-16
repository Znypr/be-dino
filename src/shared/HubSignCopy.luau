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
Copy.GuideToast = "Follow the glow" -- shown when "Teleport to shops" is off and a rail button starts the moss trail (15 chars: a toast, not a sign)
-- Words a sign or toast must never contain (jargon / system words).
Copy.Forbidden = table.freeze({"station", "teleport", "menu", "server", "tier", "xp", "dna", "ui", "hud", "gui", "ack", "error"})

function Copy.sign(station: any): string?
    return if typeof(station) == "string" then Copy.Signs[station] else nil
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
