--!strict
-- Close paths (BD-1019, docs/181): the pure rules behind "every screen has a way out that works".
-- Owner bug 2026-10-18: while an egg was hatching, X and a tap outside the card did nothing, because a full-screen tap catcher sat
-- above the whole menu. These are the numbers and decisions; src/client/ModalClose.luau draws them. Nothing here touches Instances.
local Rules = {}

Rules.MinTarget = 44 -- docs/72 and docs/114 s4.4: a tap target is at least 44 px on screen
Rules.ReadyGrace = 0.6 -- hatch: for this many seconds after the dino is shown, a tap outside the card cannot close it

export type Rect = {x: number, y: number, w: number, h: number}

-- Left/top inclusive, right/bottom exclusive (the same edge rule as HubTravelClientRules.routeScrimTap).
function Rules.contains(r: Rect, x: number, y: number): boolean
    return x >= r.x and x < r.x + r.w and y >= r.y and y < r.y + r.h
end

function Rules.bigEnough(w: number, h: number): boolean
    return w >= Rules.MinTarget and h >= Rules.MinTarget
end

-- The hatch tap zone, in screen pixels: the card (panel) minus its header strip (that is where X lives) and minus the row of end buttons
-- (DONE / TRY AGAIN) once it is shown. Taps inside the zone move the egg along; everything outside it (X, the end buttons, the dark
-- backdrop) is NOT covered, so those controls receive their own taps. nil = nothing to cover yet (the card is not laid out).
function Rules.tapZone(panel: Rect, headerBottom: number, endRowTop: number?): Rect?
    local top = math.max(panel.y, headerBottom)
    local bottom = panel.y + panel.h
    if endRowTop ~= nil then bottom = math.min(bottom, math.max(top, endRowTop)) end
    if panel.w < 1 or bottom - top < 1 then return nil end
    return {x = panel.x, y = top, w = panel.w, h = bottom - top}
end

-- What a tap on the dark backdrop does while the hatch screen is open:
--   "tap"    it counts like a tap on the egg (fast-forward the build-up, as before this change)
--   "ignore" nothing happens (the answer is still on its way, or the egg is cracking, or the dino was only just shown)
--   "close"  same as X
-- readySince = seconds since the "tap for next egg" hint appeared, nil while it has not appeared.
function Rules.outsideAction(pending: boolean, phase: string, readySince: number?): string
    if pending then return "ignore" end
    if readySince ~= nil then
        return if readySince >= Rules.ReadyGrace then "close" else "ignore"
    end
    return if phase == "build" then "tap" else "ignore"
end

-- Fusion menu: a tap on the dark backdrop closes the menu only on screens where nothing is being saved or revealed.
-- fusing = the server is committing the fusion; reveal = the wheel ceremony; details = a sub-page that has its own Back.
Rules.FusionOutsideCloses = {browse = true, confirm = true, resume = true, unavailable = true}
function Rules.fusionOutsideCloses(mode: string): boolean
    return Rules.FusionOutsideCloses[mode] == true
end

return Rules
