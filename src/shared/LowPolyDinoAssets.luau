--!strict
-- BD-225 / BD-232: species -> published low-poly generated Model (Roblox mesh generator, 2026-10-16), all 22 shipped species.
-- Each asset is a Model with one MeshPart per body part (body, head/neck, tail, arms or wings or flippers, legs).
-- Pure data (no Roblox APIs) so tools/verify_lowpoly_dinos.py runs it. Gated by Config.LowPolyDinos (false by default).
-- Never invent ids: a species not listed keeps its current visual.
-- class = Ground/Fly/Water/Armored (docs/101 section 2 and 16; a Fly dino walks with wings folded, a Water dino stays low).
-- scale = studs multiplier applied once at clone time. The generated models are all normalised to the same bulk (about 3 studs long),
-- so scale restores the intended relative size: scale = 2.0 * 1.1^(tier - 1) * shape, rounded to 2 decimals, where tier is the species
-- rarity/unlock tier (Config.SpeciesRarities, about 10% growth per tier) and shape is a per-species bulk factor (Compy, Archaeopteryx,
-- Microraptor small; Brachiosaurus 1.6, T-Rex 1.25, Spinosaurus/Therizinosaurus/Stegosaurus 1.2 large; fly and water near 1).
-- tier is stored per entry and tools/verify_lowpoly_dinos.py checks scale against it. Compy 2.2, Raptor 2.1, Triceratops 3.0 are the
-- original spike values (shape 1.10, 1.05, 1.24). BD-329: Gallimimus is a very thin generated body (about 1.2 x 3.4 x 4.0 studs at 2.0),
-- so its shape factor is 1.45 (scale 2.9) to give it visual mass comparable to Compy and Raptor.
return {
    compy = {assetId = 94548957808227, version = "v1", scale = 2.2, tier = 1, class = "Ground"},
    triceratops = {assetId = 107596736973492, version = "v3", scale = 3.0, tier = 3, class = "Ground"},
    tyrannosaurus = {assetId = 70893952304488, version = "v1", scale = 3.66, tier = 5, class = "Ground"},
    raptor = {assetId = 83260397513385, version = "v1", scale = 2.1, tier = 1, class = "Ground"},
    stegosaurus = {assetId = 92335618053209, version = "v1", scale = 2.64, tier = 2, class = "Ground"},
    ankylosaurus = {assetId = 125812700099310, version = "v1", scale = 2.66, tier = 4, class = "Armored"},
    archaeopteryx = {assetId = 108659121473793, version = "v1", scale = 1.76, tier = 2, class = "Fly"},
    baryonyx = {assetId = 131708938808155, version = "v1", scale = 2.42, tier = 3, class = "Ground"},
    brachiosaurus = {assetId = 104593280278631, version = "v1", scale = 3.87, tier = 3, class = "Ground"},
    dimorphodon = {assetId = 117242533934118, version = "v1", scale = 1.9, tier = 1, class = "Fly"},
    elasmosaurus = {assetId = 76344726254379, version = "v1", scale = 2.66, tier = 4, class = "Water"},
    gallimimus = {assetId = 99873366835296, version = "v1", scale = 2.9, tier = 1, class = "Ground"},
    ichthyosaurus = {assetId = 133825037148251, version = "v1", scale = 2.3, tier = 3, class = "Water"},
    microraptor = {assetId = 137027841072493, version = "v1", scale = 1.7, tier = 1, class = "Fly"},
    mosasaurus = {assetId = 116180724806366, version = "v1", scale = 3.22, tier = 5, class = "Water"},
    pachycephalosaurus = {assetId = 75417530223759, version = "v1", scale = 1.98, tier = 2, class = "Ground"},
    parasaurolophus = {assetId = 125203763120290, version = "v1", scale = 2.31, tier = 2, class = "Ground"},
    plesiosaurus = {assetId = 107885207120586, version = "v1", scale = 2.42, tier = 3, class = "Water"},
    pteranodon = {assetId = 101283644467729, version = "v1", scale = 2.31, tier = 2, class = "Fly"},
    quetzalcoatlus = {assetId = 126028097030256, version = "v1", scale = 2.8, tier = 4, class = "Fly"},
    spinosaurus = {assetId = 94005222354362, version = "v1", scale = 3.51, tier = 5, class = "Ground"},
    therizinosaurus = {assetId = 94894343028103, version = "v1", scale = 3.19, tier = 4, class = "Ground"},
}
