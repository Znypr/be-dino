--!strict
-- BD-423 (docs/101 s2, docs/72): kid-copy class label + one-line feel hint for the species picker. Text only, no art.
local ClassMovement = require(script.Parent.ClassMovement)
local ClassInfo = {}
-- Owner 2026-10-18 words: Ground / Fly / Water / Armored (was Runner / Flyer / Swimmer). The same word sits next to the class icon.
ClassInfo.Labels = table.freeze({ Ground = "Ground", Fly = "Fly", Water = "Water", Armored = "Armored" })
ClassInfo.Hints = table.freeze({
    Ground = "Fast runner",
    Fly = "Flies and glides",
    Water = "Swims and dashes",
    Armored = "Tough armor",
})
-- Class colours (owner 2026-10-16 'Nature set', docs/114 s5.11): Ground green, Fly sky blue, Water teal, Armored amber-brown.
ClassInfo.Colors = table.freeze({
    Ground = Color3.fromRGB(47, 158, 68),
    Fly = Color3.fromRGB(30, 136, 229),
    Water = Color3.fromRGB(15, 143, 128),
    Armored = Color3.fromRGB(168, 100, 58),
})
-- Class badge: the 4 owner-made icons are asset slots (AssetSlots.Images, bound 2026-10-18, docs/77). With no id ClassBadge draws the class word on a
-- colour pill. There is NO one-letter label any more (owner 2026-10-18).
ClassInfo.IconSlots = table.freeze({ Ground = "class_ground", Fly = "class_flyer", Water = "class_water", Armored = "class_armored" })
-- {class, label, hint} for any species id (unknown = Ground, like ClassMovement).
function ClassInfo.forSpecies(speciesId: any): { class: string, label: string, hint: string }
    local class = ClassMovement.classForSpecies(speciesId)
    return { class = class, label = ClassInfo.Labels[class], hint = ClassInfo.Hints[class] }
end
-- Card line, e.g. "Fly: Flies and glides".
function ClassInfo.line(speciesId: any): string
    local i = ClassInfo.forSpecies(speciesId)
    return i.label .. ": " .. i.hint
end
return ClassInfo
