--!strict
-- BD-285 (docs/104 s5, docs/87 calm and bubbly): the Cave lava falls as pure numbers and math: the scrolling flame layers drawn on the
-- sheet, the emitter rates (desktop and phone) kept under the FX budget, and the Reduce Motion rule. No Instances, no requires:
-- src/server/CaveLavaFx.luau builds the sheet, layers and emitters from this, src/client/CaveLavaClient.luau scrolls the layers and scales
-- the emitters, tools/verify_cave_lava.py runs the same functions offline. All numbers are PROVISIONAL (the owner judges by eye).
-- Textures: only the existing alpha sheets (EffectAssets flameSheet, swirl, smokeSheet, sparkSheet); nothing here is new art.
local Rules = {}
Rules.Version = 1

Rules.CanvasPxPerStud = 10 -- the sheet SurfaceGui canvas is (width * 10) x (height * 10) pixels
Rules.FxBudget = {desktop = 25, phone = 10} -- particles per second for the whole lava (docs/104 s5)

-- Scrolling layers on the sheet, back to front. tileStuds = one tile of the 4 x 4 sheet in studs (a cell is a quarter of it),
-- speed = studs per second falling (down), offsetU = sideways shift in studs so the layers do not line up, alpha = ImageTransparency.
Rules.Layers = {
    {name = "FlamesBack", key = "flameSheet", tileStuds = 38, speed = 4.5, offsetU = 0, alpha = 0.45, color = {255, 120, 40}},
    {name = "SwirlMid", key = "swirl", tileStuds = 22, speed = 2.5, offsetU = 5, alpha = 0.6, color = {255, 190, 100}},
    {name = "FlamesFront", key = "flameSheet", tileStuds = 26, speed = 7.5, offsetU = 9, alpha = 0.4, color = {255, 176, 70}},
}

-- Particles per second, desktop. Their sum stays under Rules.FxBudget.desktop; phones scale every rate by phoneScale().
Rules.Rates = {
    lipFlames = 4, -- small flames dropping off the top lip
    baseMist = 3, -- warm mist where the falls meet the basin
    steam = 5, -- steam over the basin
    embers = 8, -- sparks popping up from the basin
    bubbles = 4, -- slow bubbles rising and popping
}

function Rules.totalRate(rates: {[string]: number}?): number
    local sum = 0
    for _, r in (rates or Rules.Rates) :: any do sum += r end
    return sum
end

-- Factor applied to every rate on phones so the total is <= the phone budget (never above 1).
function Rules.phoneScale(): number
    return math.min(1, Rules.FxBudget.phone / Rules.totalRate())
end

-- Emitter rate for one emitter given the viewer: Reduce Motion (calm) = 0 (the first frame stays, nothing moves), phone = scaled.
function Rules.rate(name: string, phone: boolean, calm: boolean): number
    local base = (Rules.Rates :: any)[name]
    if base == nil or calm then return 0 end
    return if phone then base * Rules.phoneScale() else base
end

-- Pixels one tile spans on the canvas.
function Rules.tilePx(layer: any): number
    return layer.tileStuds * Rules.CanvasPxPerStud
end

-- Scroll position in pixels (0 <= v < tile) of a layer after `seconds`. Reduce Motion (calm) returns the static first frame
-- (the same value as seconds = 0). Bounded, so a long session never drifts or loses float precision.
function Rules.scroll(layer: any, seconds: number, calm: boolean): number
    local tile = Rules.tilePx(layer)
    if calm or seconds ~= seconds or seconds <= 0 then return 0 end
    return (layer.speed * Rules.CanvasPxPerStud * seconds) % tile
end

-- Y position (pixels) of a layer's image strip: the strip is one tile taller than the canvas and starts one tile above it, so
-- moving it down by scroll() (0..tile) never shows an edge.
function Rules.stripY(layer: any, seconds: number, calm: boolean): number
    return -Rules.tilePx(layer) + Rules.scroll(layer, seconds, calm)
end

return Rules
