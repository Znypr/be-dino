--!strict
-- BD-456 (docs/137 s2, s3, s7, s15): the ONE dino-skin catalogue. PURE: no Roblox services, no clock, no store. GiftRules builds its four skin
-- gift items from Skins below (so a skin id exists in exactly one place), SkinService/ProfileRepository validate against it and
-- SkinPickerModel shows it. tools/verify_skins.py runs this exact file offline.
--
-- Three layers (docs/137 s2), kept apart on purpose:
--   Entitlement   "I may use style X"            the ACCOUNT, profile.ownedSkins[id] = true (shared with gifting, docs/134)
--   Model         "species S has a style-X model" the GAME, Models below (NOT the player)
--   Equipped      "this dino copy wears X"        the dino INSTANCE (instance.skin) plus an account default (profile.defaultSkin)
-- A skin is a LOOK only (docs/137 s1): it never changes stats, growth, size, odds, genes, Shiny/BIG, mutations or fusion inputs. Nothing in
-- this file or in the equip path reads or writes those.
local SkinCatalog = {}

SkinCatalog.Base = "Base" -- the always-owned, always-available fallback look

export type Skin = {id: string, label: string, kind: string, defeat: string}

-- Order is the picker order and the gift catalogue order. kind: "free" = everybody has it; "robux" = bought (BD-459) or gifted (docs/134).
-- Anime and Movie (crystals, later, docs/137 Q3) are NOT here yet: they join when they are built.
local skins: {Skin} = {
    {id = "Base", label = "Classic", kind = "free", defeat = "stars"},
    {id = "Plush", label = "Plushy", kind = "robux", defeat = "deflate"},
    {id = "Clay", label = "Clay", kind = "robux", defeat = "squish"},
    {id = "Bricks", label = "Bricks", kind = "robux", defeat = "bricks"},
    {id = "Balloon", label = "Balloon", kind = "robux", defeat = "pop"},
}
SkinCatalog.List = table.freeze(skins)

local byId: {[string]: Skin} = {}
for _, skin in skins do byId[skin.id] = skin end
SkinCatalog.ById = table.freeze(byId)

-- Skins that are not free: the ones a player must own (and the ones gifting can send).
local owned: {Skin} = {}
for _, skin in skins do
    if skin.kind ~= "free" then table.insert(owned, skin) end
end
SkinCatalog.Ownable = table.freeze(owned)

-- Which species have a model for which style (docs/137 s2 "Model availability", s8). EVERY set is EMPTY at first: no art exists yet
-- (BD-455 is the Compy pilot, BD-458 the rollout), so no non-Base skin can be worn by any species. A later task adds a species id here
-- together with its verified model and its docs/77 line, nothing else. Base is not listed: it fits every species.
local models: {[string]: {[string]: boolean}} = {
    Plush = {},
    Clay = {},
    Bricks = {},
    Balloon = {},
}
SkinCatalog.Models = table.freeze(models)

function SkinCatalog.isKnown(id: any): boolean
    return type(id) == "string" and byId[id] ~= nil
end

function SkinCatalog.get(id: any): Skin?
    return if type(id) == "string" then byId[id] else nil
end

function SkinCatalog.label(id: any): string
    local skin = SkinCatalog.get(id)
    return if skin then skin.label else byId.Base.label
end

-- A free skin (Base) needs no entitlement and no model.
function SkinCatalog.isFree(id: any): boolean
    local skin = SkinCatalog.get(id)
    return skin ~= nil and skin.kind == "free"
end

-- Unknown, missing or wrong-typed ids read as Base (fail safe, docs/137 s7).
function SkinCatalog.normalize(id: any): string
    return if SkinCatalog.isKnown(id) then id :: string else SkinCatalog.Base
end

-- Does this species have a model for the style? Base fits every species; any other style only where Models lists it.
function SkinCatalog.hasModel(skinId: any, speciesId: any): boolean
    if type(speciesId) ~= "string" or speciesId == "" then return false end
    if SkinCatalog.isFree(skinId) then return true end
    local set = if type(skinId) == "string" then models[skinId] else nil
    return set ~= nil and set[speciesId] == true
end

-- The species that can wear a style, sorted (the picker lists them on the style card, docs/137 Q8).
function SkinCatalog.supportedSpecies(skinId: any): {string}
    local list: {string} = {}
    local set = if type(skinId) == "string" then models[skinId] else nil
    if set then
        for speciesId, yes in set do
            if yes then table.insert(list, speciesId) end
        end
        table.sort(list)
    end
    return list
end

-- The model set for a style (frozen, shared) or nil for Base/unknown. The profile transaction receives this set instead of the catalogue.
function SkinCatalog.modelSet(skinId: any): {[string]: boolean}?
    return if type(skinId) == "string" then models[skinId] else nil
end

-- Does this account own the style? Base always; the others only with an explicit `true` (a junk value is "not owned"). `ownedSkins` is the
-- profile record; it may be nil (a profile that never touched skins) or junk.
function SkinCatalog.owns(ownedSkins: any, skinId: any): boolean
    if not SkinCatalog.isKnown(skinId) then return false end
    if SkinCatalog.isFree(skinId) then return true end
    return type(ownedSkins) == "table" and (ownedSkins :: any)[skinId] == true
end

-- May this account put this style on a dino of this species? Returns ok, code.
function SkinCatalog.canEquip(ownedSkins: any, skinId: any, speciesId: any): (boolean, string)
    if not SkinCatalog.isKnown(skinId) then return false, "unknown_skin" end
    if not SkinCatalog.owns(ownedSkins, skinId) then return false, "not_owned" end
    if not SkinCatalog.hasModel(skinId, speciesId) then return false, "no_model" end
    return true, "ok"
end

-- The look a dino renders (the single input to LPSkin, docs/137 s7). Never errors, never writes:
--   an instance with its own choice wears it if it is still ownable and has a model, else Base (an unowned or unknown choice is Base,
--     NOT the account default);
--   an instance with no choice wears the account default under the same test, else Base.
-- So a revoked skin, a newer build's unknown id, or a species without a model all fall back to Base without touching the profile.
function SkinCatalog.effective(ownedSkins: any, defaultSkin: any, instanceSkin: any, speciesId: any): string
    local chosen = if instanceSkin ~= nil then instanceSkin else defaultSkin
    if chosen ~= nil and SkinCatalog.canEquip(ownedSkins, chosen, speciesId) then return chosen :: string end
    return SkinCatalog.Base
end

return SkinCatalog
