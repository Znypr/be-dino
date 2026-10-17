--!strict
-- Water dash delivery (docs/101 s2: the jump button is a forward dash). PURE: numbers in, numbers out, so it runs in the offline
-- Luau runner. The server answers a ClassDash request with a planar velocity (ClassMovement.launchVelocity, 48 studs/s) and a
-- duration (ClassMovement.duration, 0.35 s, about 17 studs). A single write is damped by the Humanoid ground controller within a
-- few frames, so the local client re-applies the velocity every frame for the whole duration, exactly like the E leap does.
-- The server stays authoritative on whether a dash is allowed; this only decides what the local character is told each frame.
--  step(...) returns action, vx, vy, vz, reason:
--    "hold"  write (vx, vy, vz) now and keep going;
--    "stop"  write (0, vy, 0) once and finish (wall ahead);
--    "end"   write nothing and finish (time up, or the dash can no longer run: dead, left the run, changed dino).
-- vy is never above 0: a dash does not lift the dino (a falling dino keeps falling).
local DashHold = {}

DashHold.MaxSpeed = 120 -- studs/s: a velocity the server never sends; anything faster is junk and refused
DashHold.MaxSeconds = 1  -- hard ceiling on the hold, whatever the caller passes

local function finite(v: any): boolean
    return typeof(v) == "number" and v == v and v ~= math.huge and v ~= -math.huge
end

-- New hold for a server answer, or nil for junk (non-numbers, NaN, zero or absurd speed, non-positive duration).
function DashHold.begin(vx: any, vz: any, now: any, seconds: any): { [string]: number }?
    if not (finite(vx) and finite(vz) and finite(now) and finite(seconds)) then return nil end
    local speed = math.sqrt(vx * vx + vz * vz)
    if speed < 1e-3 or speed > DashHold.MaxSpeed or seconds <= 0 then return nil end
    return { vx = vx, vz = vz, startedAt = now, untilAt = now + math.min(seconds, DashHold.MaxSeconds) }
end

-- Decision for one frame. vy = the root's current vertical speed; blocked = a wall is directly ahead (same Blockcast the server
-- uses at the start); alive = still the same character, Active run, health above 0, still a Water dino.
function DashHold.step(hold: any, now: number, vy: number, blocked: boolean, alive: boolean): (string, number, number, number, string)
    if typeof(hold) ~= "table" or not alive then return "end", 0, 0, 0, "gone" end
    if not finite(now) or now >= hold.untilAt then return "end", 0, 0, 0, "time" end
    local y = if finite(vy) then math.min(vy, 0) else 0
    if blocked then return "stop", 0, y, 0, "wall" end
    return "hold", hold.vx, y, hold.vz, "hold"
end

return DashHold
