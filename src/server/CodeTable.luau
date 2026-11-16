--!strict
-- BD-1233 (docs/242 gap 18): the server-only code table for the code box (ServerScriptService: clients never see it).
-- Key = the code in upper case, letters and digits only (Shared/CodeRules.normalize). crystals = free crystals, once per player (PROVISIONAL).
-- endsAt = unix time when the code stops working (nil = no end). To add a code: add a line here and ship a build; to end one, set endsAt.
-- Crystals only: no Robux, no paid item, nothing random (docs/43).
return table.freeze({
    BEDINO = {crystals = 50}, -- LEAD decision 2026-11-16: the launch code (PROVISIONAL amount)
    HATCH = {crystals = 25}, -- LEAD decision 2026-11-16: a second small starter code (PROVISIONAL amount)
})
