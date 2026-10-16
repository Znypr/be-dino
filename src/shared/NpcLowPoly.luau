--!strict
-- BD-324 (docs/108): pure rules for the low-poly look of the wild NPC predators. No Roblox APIs (tested offline by
-- tools/verify_lowpoly_dinos.py). The server (NpcPredatorService) clones the species' low-poly model with LowPolyDinos.clone and
-- tints it dark with a translucent shell only: NO EditableImage bake for NPCs, so wild dinos never spend the image budget (docs/107).
-- The client animates them with LowPolyAnimator (same LowPolyPose functions as the players' rigs).
local NpcLowPoly = {}
-- Studio 2026-10-16: a plain MeshPart.Color is IGNORED on a textured MeshPart, and SurfaceAppearance.ColorMap cannot be written from
-- a game script (capability Plugin). So the wild look is a thin dark translucent SHELL: a copy of each textured part with no texture,
-- slightly larger, Color = the muted dark "wild gene" colour below, Transparency = ShellTransparency. The model's own texture shows
-- through (eyes stay darker than the body, the belly stays lighter), and no EditableImage / image memory is used (docs/107).
NpcLowPoly.ShellTransparency = 0.38
NpcLowPoly.ShellGrow = 1.02
NpcLowPoly.Wild = {
    raptor = {0.20, 0.12, 0.30},
    baryonyx = {0.17, 0.14, 0.26},
    tyrannosaurus = {0.22, 0.12, 0.22},
    spinosaurus = {0.16, 0.14, 0.28},
}
NpcLowPoly.Default = {0.19, 0.13, 0.27}
-- Which visual an NPC gets: "lowpoly" only when the flag is on AND the species has a registered asset AND its model loaded; otherwise
-- "legacy" (DinosaurVisual.render), exactly as before.
function NpcLowPoly.pick(flagOn: boolean, hasAsset: boolean, loaded: boolean): string
    if flagOn and hasAsset and loaded then return "lowpoly" end
    return "legacy"
end
function NpcLowPoly.wild(speciesId: string): {number}
    return (NpcLowPoly.Wild :: any)[speciesId] or NpcLowPoly.Default
end
function NpcLowPoly.shellColor(speciesId: string): (number, number, number)
    local w = NpcLowPoly.wild(speciesId)
    return w[1], w[2], w[3]
end
-- NPC action cues -> pose phase: a new bite (BiteSeq changed) wins, then the windup cue; nil = plain idle/walk.
function NpcLowPoly.phase(cue: string, biteChanged: boolean, current: string?): string?
    if biteChanged then return "bite" end
    if current == "bite" then return current end -- a started bite plays out
    if cue == "windup" then return "windup" end
    return nil
end
return NpcLowPoly
