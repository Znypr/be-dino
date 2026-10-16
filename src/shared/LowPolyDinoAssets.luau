--!strict
-- BD-225 spike: species -> published low-poly generated Model (Roblox mesh generator, 2026-10-16). Each asset is a Model with
-- one MeshPart per body part (body, head, tail, arms, legs). Pure data (no Roblox APIs) so tools/verify_lowpoly_dinos.py runs it.
-- Gated by Config.LowPolyDinos (false by default). Never invent ids: a species not listed keeps its current visual.
-- scale = studs multiplier applied once at clone time (generated models are about 3 studs long; the old shells are 8 to 10).
return {
    compy = {assetId = 94548957808227, version = "v1", scale = 2.2},
    raptor = {assetId = 83260397513385, version = "v1", scale = 2.1},
    triceratops = {assetId = 107596736973492, version = "v3", scale = 3.0},
}
