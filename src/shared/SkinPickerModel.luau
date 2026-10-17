--!strict
-- BD-456 (docs/137 s5, s6): the PURE state model of the skin picker. No Roblox services, no Instances, no art, no clock: it only turns what
-- the server answered (SkinAction "get") into cards and builds the exact requests the server accepts. The picker UI itself, its viewport
-- carousel and its art are BD-457; nothing here draws anything. tools/verify_skins.py runs this exact file offline against the real
-- SkinService, so a request built here is proven to pass the server's strict shapes.
--
-- Copy follows docs/72: short plain words for children, no jargon, no prices, no "limited time". A style the dino cannot wear yet says
-- "Coming soon" (docs/137 s6, Q8); the picker never shows a broken or Base-looking preview for it.
local SkinCatalog = require(script.Parent.SkinCatalog)

local Model = {}

Model.RemoteName = "SkinAction"

Model.Copy = table.freeze({
    wear = "Wear",
    wearing = "Wearing",
    locked = "Locked",
    soon = "Coming soon",
    defaultTitle = "For all my dinos",
})

-- Short next-step lines for the server's reason codes (docs/72: errors say what to do next). Unknown codes read "Try again."
Model.Messages = table.freeze({
    not_owned = "You don't have this look yet.",
    no_model = "This dino can't wear it yet.",
    unknown_skin = "Pick a look from the list.",
    rate_limited = "Slow down a little.",
    disabled = "Looks are not ready yet.",
    profile_not_loaded = "Try again in a moment.",
    instance_missing = "Pick a dino first.",
    identity_unavailable = "Try again in a moment.",
})
Model.FallbackMessage = "Try again."

function Model.message(reason: any): string
    local text = if type(reason) == "string" then (Model.Messages :: any)[reason] else nil
    return if type(text) == "string" then text else Model.FallbackMessage
end

-- ------------------------------------------------------------------ requests (exactly the shapes SkinService accepts)
function Model.getRequest(instanceId: string?): {[string]: any}
    return if instanceId ~= nil then {action = "get", instanceId = instanceId} else {action = "get"}
end
function Model.equipRequest(instanceId: string, skinId: string): {[string]: any}
    return {action = "equip", instanceId = instanceId, skin = skinId}
end
function Model.unequipRequest(instanceId: string): {[string]: any}
    return {action = "unequip", instanceId = instanceId}
end
function Model.defaultRequest(skinId: string): {[string]: any}
    return {action = "setDefault", skin = skinId}
end

-- ------------------------------------------------------------------ view
-- The server's "get" answer for one dino: {ok, owned = {ids}, defaultSkin, skin?, speciesId, wearing}. Anything unreadable reads as a
-- profile that owns nothing and wears Base (never an error in the UI).
export type View = {owned: {[string]: boolean}, defaultSkin: string, skin: string?, speciesId: string?, wearing: string}

function Model.view(answer: any): View
    local owned: {[string]: boolean} = {}
    local list = if type(answer) == "table" and type(answer.owned) == "table" then answer.owned else {}
    for _, id in list do
        if type(id) == "string" and SkinCatalog.isKnown(id) then owned[id] = true end
    end
    local speciesId = if type(answer) == "table" and type(answer.speciesId) == "string" then answer.speciesId else nil
    local skin = if type(answer) == "table" and SkinCatalog.isKnown(answer.skin) then answer.skin :: string else nil
    local default = SkinCatalog.normalize(if type(answer) == "table" then answer.defaultSkin else nil)
    return {owned = owned, defaultSkin = default, skin = skin, speciesId = speciesId,
        wearing = SkinCatalog.effective(owned, default, skin, speciesId)}
end

-- ------------------------------------------------------------------ cards
-- state: "worn" (on this dino now), "wear" (owned and this species has the model: tap to wear), "locked" (not owned, the model exists),
-- "soon" (this species has no model for the style yet; owned or not).
export type Card = {id: string, label: string, state: string, text: string, isDefault: boolean, request: {[string]: any}?}

function Model.cards(view: View, instanceId: string?): {Card}
    local cards: {Card} = {}
    for _, skin in SkinCatalog.List do
        local state: string
        if not (SkinCatalog.isFree(skin.id) or SkinCatalog.hasModel(skin.id, view.speciesId)) then -- Base fits every dino
            state = "soon"
        elseif not SkinCatalog.owns(view.owned, skin.id) then
            state = "locked"
        elseif view.wearing == skin.id then
            state = "worn"
        else
            state = "wear"
        end
        local text = if state == "worn" then Model.Copy.wearing elseif state == "wear" then Model.Copy.wear
            elseif state == "locked" then Model.Copy.locked else Model.Copy.soon
        table.insert(cards, {id = skin.id, label = skin.label, state = state, text = text, isDefault = view.defaultSkin == skin.id,
            request = if state == "wear" and instanceId ~= nil then Model.equipRequest(instanceId, skin.id) else nil})
    end
    return cards
end

-- After a successful reply, the view the picker shows next (no second round trip). A failed reply changes nothing.
function Model.applyResult(view: View, request: any, reply: any): View
    if type(reply) ~= "table" or reply.ok ~= true or type(request) ~= "table" then return view end
    local owned = table.clone(view.owned)
    local skin: string? = view.skin
    local default = view.defaultSkin
    if request.action == "equip" and SkinCatalog.isKnown(request.skin) then
        skin = request.skin
    elseif request.action == "unequip" then
        skin = nil
    elseif request.action == "setDefault" and SkinCatalog.isKnown(request.skin) then
        default = request.skin
    else
        return view
    end
    return {owned = owned, defaultSkin = default, skin = skin, speciesId = view.speciesId,
        wearing = SkinCatalog.effective(owned, default, skin, view.speciesId)}
end

return Model
