--!strict
-- BD-1071: the hatch egg keeps ONE size and place from the first frame to the crack. Studio round 4 (docs/192, pictures 243 vs 246) measured the
-- flat egg picture at 188 px wide and the 3D egg that replaces it when the second colour arrives at 114 px, because the 3D egg only filled
-- 42.5% of its 268 px box. Now the size is decided here once: the flat picture is the reference, and the 3D egg's camera is zoomed (the viewport
-- attribute InspectZoom that PreviewCamera already reads) and moved so both draw the same egg. Pure numbers, no Roblox types
-- (offline-tested by tools/verify_hatch_polish.py).
local S = {}

S.Canvas = 460                       -- HatchPresentation: the flat egg layers are 460 px squares
S.ArtSize = 512                      -- premium-egg-normal.png canvas
S.ArtBox = {151, 107, 361, 383}      -- the egg's alpha bounding box inside that art: x0, y0, x1, y1 (measured from the PNG)
S.NativeBox = 268                    -- the 3D egg's viewport, px (a square box)
S.NativeFill = 114 / 268             -- MEASURED in Studio (docs/192, picture 246): the 3D egg's width over its box at zoom 1
S.NativeZoom = 1.65                  -- camera zoom that makes the 3D egg as wide as the flat one (188.7 / (268 * 0.4254) = 1.655)
S.Tolerance = 0.03                   -- the two eggs may differ by at most 3% of the width

-- The flat egg picture on screen (px, at zoom 1): width, height, and where its centre sits relative to the centre of the 460 box.
function S.flat()
    local k = S.Canvas / S.ArtSize
    local b = S.ArtBox
    local w, h = (b[3] - b[1]) * k, (b[4] - b[2]) * k
    local cx, cy = (b[1] + b[3]) / 2 * k - S.Canvas / 2, (b[2] + b[4]) / 2 * k - S.Canvas / 2
    return {w = w, h = h, dx = cx, dy = cy}
end
-- The 3D egg on screen at the same zoom: width and height (the egg is as tall as the flat one when the widths match).
function S.native()
    return {w = S.NativeBox * S.NativeFill * S.NativeZoom}
end
-- Where the 3D viewport sits inside the egg root so its egg lands on the flat egg's centre (whole pixels).
function S.nativeOffset(): (number, number)
    local f = S.flat()
    return math.floor(f.dx + 0.5), math.floor(f.dy + 0.5)
end
-- Every state the hatch egg is drawn in -> its width. The regression check wants them all equal (within Tolerance).
function S.states()
    return {flat = S.flat().w, native = S.native().w}
end
function S.sameSize(): (boolean, number)
    local s = S.states()
    local widest, narrowest = math.max(s.flat, s.native), math.min(s.flat, s.native)
    local spread = (widest - narrowest) / widest
    return spread <= S.Tolerance, spread
end
-- The zoomed egg must stay inside its viewport (the height at zoom must be under the box, else the crack would be cropped).
function S.fitsBox(): boolean
    local h = S.flat().h
    return h <= S.NativeBox
end

return S
