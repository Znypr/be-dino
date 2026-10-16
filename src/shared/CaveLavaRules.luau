--!strict
-- BD-285 / BD-385 (docs/104 s5, docs/87 calm and bubbly): the Cave lava falls as pure numbers: the soft particle strands that make the
-- falling lava, the emitter rates (desktop and phone) kept under the FX budget, and the Reduce Motion rule. No Instances, no requires:
-- src/server/CaveLavaFx.luau builds the emitters from this, src/client/CaveLavaClient.luau scales them, tools/verify_cave_lava.py
-- runs the same functions offline. All numbers are PROVISIONAL (the owner judges by eye).
-- Textures: only the existing alpha sheets (EffectAssets flameSheet, smokeSheet, sparkSheet); nothing here is new art. A real
-- hand-made lava texture is a TODO in docs/120.
local Rules = {}
Rules.Version = 2

Rules.FxBudget = {desktop = 25, phone = 10} -- particles per second for the whole lava (docs/104 s5)

-- BD-385 (owner QA 2026-10-16): the falls used to be scrolling tiled sheets in a SurfaceGui, which read as a flat rectangular billboard
-- with a visible tile grid. They are now soft particle STRANDS: each strand is one ParticleEmitter at an irregular spot along the top
-- lip (dx = studs from the falls centre, dy = studs below the lip, so the silhouette is ragged), dropping big soft flameSheet
-- flipbook puffs that overlap their neighbours. No Texture, no SurfaceGui, no ImageLabel, no tiling, no hard rectangle edge.
-- size = puff size (studs), life = seconds, fall = downward acceleration (studs/s^2), rate = particles per second (desktop).
Rules.Strands = {
    {dx = -17.5, dy = 0.5, size = 7.5, life = 4.2, fall = 3.6, rate = 2.0},
    {dx = -11.5, dy = 2.5, size = 6.0, life = 3.6, fall = 4.4, rate = 1.5},
    {dx = -5.0, dy = 0.0, size = 8.5, life = 4.6, fall = 3.2, rate = 2.0},
    {dx = 0.5, dy = 1.5, size = 6.5, life = 4.0, fall = 3.8, rate = 1.5},
    {dx = 6.0, dy = 3.5, size = 7.0, life = 3.4, fall = 4.6, rate = 2.0},
    {dx = 12.0, dy = 0.5, size = 8.0, life = 4.4, fall = 3.4, rate = 1.5},
    {dx = 17.0, dy = 2.0, size = 6.0, life = 3.8, fall = 4.0, rate = 1.5},
}
Rules.StillBurst = 20 -- Reduce Motion: one burst of frozen soft glow puffs across the wall (no loop, no scrolling)

-- Glowing base pool in front of the falls: stacked flat discs, brighter in the middle (stepped soft edge), no lights added (16-light cap).
Rules.Glow = {
    {diameter = 22, transparency = 0.82, color = {255, 120, 40}},
    {diameter = 15, transparency = 0.7, color = {255, 150, 60}},
    {diameter = 8, transparency = 0.55, color = {255, 190, 100}},
}
Rules.GlowFront = 2.5 -- studs in front of the back sheet

-- Particles per second, desktop. Their sum stays under Rules.FxBudget.desktop; phones scale every rate by phoneScale().
Rules.Rates = {
    wallGlow = 3, -- big faint warm puffs across the wall so the recess glows (soft, irregular, no rectangle)
    baseMist = 3, -- warm mist where the falls meet the basin
    steam = 3, -- steam over the basin
    embers = 3, -- sparks popping up from the basin
    bubbles = 1, -- slow bubbles rising and popping
}
for i, strand in Rules.Strands do Rules.Rates["strand" .. i] = strand.rate end

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

return Rules
