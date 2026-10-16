--!strict
-- BD-423 (docs/101 s2, docs/72): kid-copy class label + one-line feel hint for the species picker. Text only, no art.
local ClassMovement = require(script.Parent.ClassMovement)
local ClassInfo = {}
ClassInfo.Labels = table.freeze({ Ground = "Runner", Fly = "Flyer", Water = "Swimmer", Armored = "Armored" })
ClassInfo.Hints = table.freeze({
    Ground = "Fast runner",
    Fly = "Flies and glides",
    Water = "Swims and dashes",
    Armored = "Tough armor",
})
-- {class, label, hint} for any species id (unknown = Ground, like ClassMovement).
function ClassInfo.forSpecies(speciesId: any): { class: string, label: string, hint: string }
    local class = ClassMovement.classForSpecies(speciesId)
    return { class = class, label = ClassInfo.Labels[class], hint = ClassInfo.Hints[class] }
end
-- Card line, e.g. "Flyer: Flies and glides".
function ClassInfo.line(speciesId: any): string
    local i = ClassInfo.forSpecies(speciesId)
    return i.label .. ": " .. i.hint
end
return ClassInfo
