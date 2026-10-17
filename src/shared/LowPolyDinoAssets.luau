--!strict
-- BD-225 / BD-232: species -> published low-poly generated Model (Roblox mesh generator, 2026-10-16), all 22 shipped species.
-- Each asset is a Model with one MeshPart per body part (body, head/neck, tail, arms or wings or flippers, legs).
-- Pure data (no Roblox APIs) so tools/verify_lowpoly_dinos.py runs it. Gated by Config.LowPolyDinos (false by default).
-- Never invent ids: a species not listed keeps its current visual.
-- class = Ground/Fly/Water/Armored (docs/101 section 2 and 16; a Fly dino walks with wings folded, a Water dino stays low).
-- scale = studs multiplier applied once at clone time, THE ONE PLACE a species' in-game size is set (BD-232 owner rule "sizes follow about
-- 10% growth per unlock tier; fly and water species are scaled by bulk up to the T-Rex", LEAD decision 2026-10-17 in docs/115). The generated
-- models are all normalised to about 3 studs, so scale restores the intended size: scale = target size / the model's size at scale 1, where
-- the target comes from src/shared/ScaleLadder.luau Sizing (tier = Config.SpeciesRarities, the unlock tier):
--   Ground and Armored (and Elasmosaurus, a normal Ground dino): HEIGHT 6.6 x 1.1^(tier - 1), Compy tier 1 = 6.6.
--   Fly and Water: BULK = cube root of the bounding-box volume, the T-Rex's bulk at tier 5 and 10% less per tier below (C-39, docs/116: Water was
--   sized by length until the owner's wording "fly/water scaled by bulk" was applied; a long low swimmer is now chunkier and much longer).
-- tools/verify_scale_ladder.py checks every species against that rule (tolerance 2%) and that this table equals ScaleLadder.
-- Compy 2.2 is the original spike value and the anchor. tier is stored per entry and tools/verify_lowpoly_dinos.py checks it against
-- Config.SpeciesRarities. History: BD-225 first used scale = 2.0 * 1.1^(tier - 1) * shape; the Studio boxes (BD-471) showed that shape
-- guess broke the owner rule (Stegosaurus 4.9, Mosasaurus 3.3 and Ichthyosaurus 3.5 below the 6.6 Compy, Raptor above Triceratops,
-- Therizinosaurus above the T-Rex).
return {
    compy = {assetId = 94548957808227, version = "v1", scale = 2.2, tier = 1, class = "Ground"},
    triceratops = {assetId = 107596736973492, version = "v3", scale = 2.86, tier = 3, class = "Ground"},
    tyrannosaurus = {assetId = 70893952304488, version = "v1", scale = 3.47, tier = 5, class = "Ground"},
    raptor = {assetId = 83260397513385, version = "v1", scale = 1.65, tier = 1, class = "Ground"},
    stegosaurus = {assetId = 92335618053209, version = "v1", scale = 3.9, tier = 2, class = "Ground"},
    ankylosaurus = {assetId = 125812700099310, version = "v1", scale = 3.6, tier = 4, class = "Armored"},
    archaeopteryx = {assetId = 108659121473793, version = "v1", scale = 1.77, tier = 2, class = "Fly"},
    baryonyx = {assetId = 131708938808155, version = "v1", scale = 3.11, tier = 3, class = "Ground"},
    brachiosaurus = {assetId = 104593280278631, version = "v1", scale = 2.91, tier = 3, class = "Ground"},
    dimorphodon = {assetId = 117242533934118, version = "v1", scale = 1.71, tier = 1, class = "Fly"},
    elasmosaurus = {assetId = 76344726254379, version = "v1", scale = 3.58, tier = 4, class = "Ground"},
    gallimimus = {assetId = 99873366835296, version = "v1", scale = 3.89, tier = 1, class = "Ground"},
    ichthyosaurus = {assetId = 133825037148251, version = "v1", scale = 3.71, tier = 3, class = "Water"},
    microraptor = {assetId = 137027841072493, version = "v1", scale = 1.52, tier = 1, class = "Fly"},
    mosasaurus = {assetId = 116180724806366, version = "v1", scale = 5.64, tier = 5, class = "Water"},
    pachycephalosaurus = {assetId = 75417530223759, version = "v1", scale = 2.81, tier = 2, class = "Ground"},
    parasaurolophus = {assetId = 125203763120290, version = "v1", scale = 3.03, tier = 2, class = "Ground"},
    plesiosaurus = {assetId = 107885207120586, version = "v1", scale = 2.78, tier = 3, class = "Water"},
    pteranodon = {assetId = 101283644467729, version = "v1", scale = 1.54, tier = 2, class = "Fly"},
    quetzalcoatlus = {assetId = 126028097030256, version = "v1", scale = 2.04, tier = 4, class = "Fly"},
    spinosaurus = {assetId = 94005222354362, version = "v1", scale = 4.02, tier = 5, class = "Ground"},
    therizinosaurus = {assetId = 94894343028103, version = "v1", scale = 2.56, tier = 4, class = "Ground"},
}
