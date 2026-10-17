--!strict
-- BD-500 / BD-471 (docs/139 s7, docs/115 SZ1-SZ3): where the default gameplay camera sits for a dinosaur of a given REAL size.
-- Before: the minimum zoom was 12 x growth scale and the aim lift 2 x (growth scale - 1), so every species was framed like a Compy
-- of the same growth. After the BD-232 species sizes a Spinosaurus (12 long), Ankylosaurus (14.4 long) or T-Rex (9.7 tall) filled
-- 70% to 128% of the screen: head behind the HUD, tail club in the lens, off the screen at growth scale 4.
-- Now both numbers read the measured model box (height and length at the current drawn size, studs), calibrated so a Compy is
-- framed EXACTLY as before (minimum zoom 12 x scale, lift 2 x (scale - 1)) and a bigger body only ever pushes the camera back.
-- PURE numbers, no Roblox types, so tools/verify_camera_framing.py runs this same file. The client driver is Bootstrap.client.luau.
local CameraFraming = {}

CameraFraming.ReferenceHeight = 6.6 -- the Compy at spawn (ScaleLadder.Sizing: ground height of tier 1)
CameraFraming.ReferenceLength = 7.7 -- the Compy's measured length at spawn (BD-471: 7.69)
CameraFraming.LengthWeight = 0.65 -- how much of the body length counts as "size": a long body reaches toward the lens (fit to Studio shots, BD-500)
CameraFraming.LiftPerStud = 2 / 6.6 -- aim lift per stud of body height above the Compy: 2 studs per growth step of a Compy, as before
CameraFraming.MaxDistance = 90 -- never pull the minimum zoom past this; CameraOcclusion switches off beyond 100 (BD-513: was 75 / 80, which pinned a BIG dino at growth scale 4.8 to 72% of the screen; the widest body at 4.8 needs 89.2)

-- One number for "how big does this body look": the diagonal of its height and weighted length (width is ignored: fliers' wings are
-- spread in the template pose but folded in game, and the camera is rarely square-on to a flank).
function CameraFraming.size(height: number, length: number): number
    local l = CameraFraming.LengthWeight * length
    return math.sqrt(height * height + l * l)
end

CameraFraming.ReferenceSize = CameraFraming.size(CameraFraming.ReferenceHeight, CameraFraming.ReferenceLength)

local function ok(n: any): boolean return typeof(n) == "number" and n == n and n > 0 and n < math.huge end

-- Minimum camera distance. base = Config.CameraMinZoom (12), growthScale = VisualScale, height / length = the body box at the CURRENT
-- drawn size. Never below base x growthScale (a small or flat body is framed as before), capped at MaxDistance.
function CameraFraming.minZoom(base: number, growthScale: number, height: number?, length: number?): number
    local s = if ok(growthScale) then math.max(1, growthScale) else 1
    local ratio = s
    if ok(height) and ok(length) then
        ratio = math.max(s, CameraFraming.size(height :: number, length :: number) / CameraFraming.ReferenceSize)
    end
    return math.max(base * s, math.min(base * ratio, CameraFraming.MaxDistance))
end

-- Aim lift (studs above the humanoid's default camera focus). A Compy: 2 x (scale - 1), as before. A taller body lifts the aim
-- further so its head stays in the frame; a shorter one is not lowered (never below 0).
function CameraFraming.lift(height: number?): number
    if not ok(height) then return 0 end
    return math.max(0, CameraFraming.LiftPerStud * ((height :: number) - CameraFraming.ReferenceHeight))
end

return CameraFraming
