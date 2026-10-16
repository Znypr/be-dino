--!strict
-- BD-225: pure pixel maths for gene-colouring the generated low-poly dino textures WITHOUT wiping detail. No Roblox APIs (tested offline
-- by tools/verify_lowpoly_dinos.py). The generated textures hold a species body colour, a cream belly and glossy black eyes/claws.
-- A pixel is recoloured only when it is both colourful (not cream/white belly or highlight) and bright enough (not black eyes/claws);
-- its shade relative to the species base colour is kept, so the baked facet shading and darker stripes survive.
local Recolor = {}
-- Average body-texture colour per species (0..1), measured from the generated body textures of the published models.
Recolor.Base = {
    compy = {0.37, 0.58, 0.32},
    raptor = {0.80, 0.49, 0.36},
    triceratops = {0.59, 0.30, 0.13},
}
local DEFAULT_BASE = {0.5, 0.5, 0.5}
local function smooth(x: number, a: number, b: number): number
    local t = math.clamp((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)
end
local function luma(r: number, g: number, b: number): number
    return 0.299 * r + 0.587 * g + 0.114 * b
end
-- Share (0..1) of a pixel that counts as body colour: 0 for black eyes/claws and cream belly/white highlight, 1 for body colour.
function Recolor.bodyWeight(r: number, g: number, b: number): number
    local mx, mn = math.max(r, g, b), math.min(r, g, b)
    if mx <= 0 then return 0 end
    return smooth(mx, 0.2, 0.3) * smooth((mx - mn) / mx, 0.34, 0.44)
end
function Recolor.pixel(r: number, g: number, b: number, tr: number, tg: number, tb: number, base: {number}?): (number, number, number)
    local w = Recolor.bodyWeight(r, g, b)
    if w <= 0 then return r, g, b end
    local bs = base or DEFAULT_BASE
    local k = math.clamp(luma(r, g, b) / math.max(luma(bs[1], bs[2], bs[3]), 0.05), 0.3, 1.6)
    return r + (math.clamp(tr * k, 0, 1) - r) * w, g + (math.clamp(tg * k, 0, 1) - g) * w, b + (math.clamp(tb * k, 0, 1) - b) * w
end
function Recolor.baseOf(speciesId: string): {number}
    return (Recolor.Base :: any)[speciesId] or DEFAULT_BASE
end
-- Cheap fallback (no EditableImage): a MeshPart.Color that multiplies the ORIGINAL species texture so its body reads as the
-- gene colour. Eyes/claws (black) stay black; the cream belly takes a light tint. Used when the bake cache is full or far away.
function Recolor.flatTint(base: {number}, tr: number, tg: number, tb: number): (number, number, number)
    local function ch(t: number, b: number): number return math.clamp(t / math.max(b, 0.15), 0, 1) end
    return ch(tr, base[1]), ch(tg, base[2]), ch(tb, base[3])
end
return Recolor
