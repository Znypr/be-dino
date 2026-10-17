--!strict
-- BD-495 .. BD-497 (docs/146 s10, risks 2, 3 and 5 of the 2026-10-17 phone forecast): the cheap PHONE-ONLY guards as pure rules.
-- Pure numbers and tables, no Instances and no services, so tools/verify_phone_guards.py checks them offline. The clients ask these functions:
--   * client/CavePhoneGuard   -> which cave lights and shaft beams may be on (nearest 12 lights, 4 beams)
--   * client/FxRig            -> may a cosmetic aura glow light shine (not inside the hub on a phone)
--   * client/CosmeticVisuals  -> cosmetic beam ceiling inside the hub on a phone (24 minus the 4 shaft beams = 20, BD-502)
--   * client/WeatherVisuals   -> weather particle density (phone 0.25)
--   * client/WorldCulling     -> are the invisible prop colliders culled with the props (phone only)
-- `device` is "phone" | "tablet" | "desktop" in any letter case (FxRecipes.deviceClass says "phone", WorldCulling says "Phone"). Anything else counts as
-- desktop, and the desktop answers are exactly today's behaviour: no cap, density 1, colliders never culled, cosmetic lights always allowed.
-- Numbers also live in tools/qa/phone_budgets.json under "guards" (tools/verify_phone_guards.py checks both agree). All PROVISIONAL until BD-085.
local Guards = {}

Guards.Phone = table.freeze({
    caveLights = 12, -- cave point lights enabled at once (the layout has 30; the budget is 16 for everything, docs/146 risk 3)
    caveBeams = 4, -- cave shaft beams enabled at once (8 on desktop: a haze and a core beam per hole)
    hubCosmeticLights = 0, -- aura / mutation glow lights inside the hub (EffectsLod.Live.phone.lights is 16 elsewhere)
    weatherDensity = 0.25, -- multiplier of every weather emitter rate (was 0.5 for every touch-only device)
    evalSeconds = 0.5, -- the cave light choice is re-evaluated on this calm interval, never per frame
    lightMargin = 1.25, -- a light that is off only replaces an on light that is at least this much farther away (no flicker)
    cullColliders = true,
})
-- A touch-only tablet keeps today's 0.5; desktop is untouched.
Guards.TabletWeatherDensity = 0.5

local function kind(device: string?): string
    local d = string.lower(device or "")
    if d == "phone" or d == "tablet" then return d end
    return "desktop"
end

function Guards.isPhone(device: string?): boolean
    return kind(device) == "phone"
end

-- Weather emitter density: phone 0.25, tablet 0.5 (as before), desktop 1. Reduce Motion is a separate, stricter rule (WeatherTextures.emitRate
-- returns 0 when motion is off, whatever the density), so it never reads this.
function Guards.weatherDensity(device: string?): number
    local k = kind(device)
    if k == "phone" then return Guards.Phone.weatherDensity end
    if k == "tablet" then return Guards.TabletWeatherDensity end
    return 1
end

-- Cave point lights allowed on at once: nil = no cap (tablet, desktop).
function Guards.caveLightCap(device: string?): number?
    if kind(device) == "phone" then return Guards.Phone.caveLights end
    return nil
end

-- Cave shaft beams allowed on at once: nil = no cap.
function Guards.caveBeamCap(device: string?): number?
    if kind(device) == "phone" then return Guards.Phone.caveBeams end
    return nil
end

-- How many beams of each shaft stay on: the cap shared evenly over the shafts, at most `perShaft` (the order is haze first, then core).
-- Phone: 4 beams over 4 shafts = 1 each (the wide soft haze, every hole keeps its shaft). Desktop: all of them.
function Guards.beamsPerShaft(device: string?, shafts: number, perShaft: number): number
    local cap = Guards.caveBeamCap(device)
    if cap == nil or shafts <= 0 then return perShaft end
    return math.clamp(math.floor(cap / shafts), 0, perShaft)
end

-- BD-502: the cosmetic beam ceiling (aura rings, spirals) of the scene-wide live-FX budget (EffectsLod.Live[device].beams = `liveCap`). Inside the
-- hub on a phone the cave's own shaft beams (4 after caveBeams) count against the same phone budget (24), so the cosmetic beams get the rest:
-- 24 - 4 = 20 and the hub total is <= 24. Outside the hub, and on tablet and desktop, the cap is `liveCap` unchanged.
function Guards.cosmeticBeamCap(device: string?, insideHub: boolean, liveCap: number): number
    if kind(device) ~= "phone" or not insideHub then return liveCap end
    return math.max(liveCap - Guards.Phone.caveBeams, 0)
end

-- May an aura / mutation glow light shine? Not on a phone while its player is inside the cave hub, except the OWN dino under Reduce Motion
-- (there the single soft light IS the whole look, docs/93: one light is 13 of 16, still under the budget). Everything else: yes.
function Guards.cosmeticLightWanted(device: string?, insideHub: boolean, reduced: boolean, own: boolean): boolean
    if kind(device) ~= "phone" or not insideHub then return true end
    if Guards.Phone.hubCosmeticLights > 0 then return true end
    return reduced and own
end

-- Which lights are on. `dists[i]` = distance from the camera to light i; `wasOn[i]` = last answer. Returns {[i] = true} for at most `cap` lights:
-- the nearest ones, but an incumbent only gives its place to a light that is at least `margin` times nearer, so lights at nearly the same distance
-- never trade places while the camera moves (no flicker). cap == nil -> every light is on. Deterministic: ties go to the lower index.
function Guards.selectLights(cap: number?, dists: {number}, wasOn: {[number]: boolean}?, margin: number?): {[number]: boolean}
    local n = #dists
    local on: {[number]: boolean} = {}
    if cap == nil or cap >= n then
        for i = 1, n do on[i] = true end
        return on
    end
    local m = math.max(margin or Guards.Phone.lightMargin, 1)
    local order = {}
    for i = 1, n do order[i] = i end
    table.sort(order, function(a, b)
        if dists[a] ~= dists[b] then return dists[a] < dists[b] end
        return a < b
    end)
    local count = 0
    if wasOn then
        for _, i in order do -- nearest first, so a shrunken cap keeps the nearest incumbents
            if wasOn[i] and count < cap then on[i] = true count += 1 end
        end
    end
    for _, i in order do -- free places go to the nearest lights that are off
        if count >= cap then break end
        if not on[i] then on[i] = true count += 1 end
    end
    for _ = 1, n do -- swap the farthest on-light for the nearest off-light only while the gain is clear
        local far, near = 0, 0
        for k = n, 1, -1 do if on[order[k]] then far = order[k] break end end
        for k = 1, n do if not on[order[k]] then near = order[k] break end end
        if far == 0 or near == 0 or dists[near] * m >= dists[far] then break end
        on[far] = nil
        on[near] = true
    end
    return on
end

-- Is the invisible collider of a prop kept? Phone: kept inside the cull radius (outer edge radius * hysteresis while it is already kept), culled
-- beyond. Anything that is not a phone keeps every collider, as today. `shown` = it is kept now, `d` = distance from the local dino in studs.
function Guards.cullColliders(device: string?): boolean
    return kind(device) == "phone" and Guards.Phone.cullColliders
end
function Guards.colliderWanted(device: string?, shown: boolean, d: number, radius: number, hysteresis: number): boolean
    if not Guards.cullColliders(device) then return true end
    return d < (if shown then radius * hysteresis else radius)
end

return Guards
