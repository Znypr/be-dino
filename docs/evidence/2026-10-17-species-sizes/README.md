# BD-500 / BD-232: species sizes follow about 10% growth per unlock tier (2026-10-17)

OWNER rule (BD-232): "Sizes follow about 10% growth per unlock tier; fly and water species are scaled by bulk up to the T-Rex". LEAD decision (owner delegated 2026-10-16) in docs/115, SZ1 to SZ3.

**What size the game uses.** A species' size at spawn = the `scale` in `src/shared/LowPolyDinoAssets.luau` (baked into the parts by `LowPolyDinos.clone`) times the growth scale (`DinosaurVisual.render` / `ResourceVisuals` call `ScaleTo(VisualScale)`; 1 at spawn and always 1 in the cave hub, BD-480). The BD-471 "height at scale 1" is therefore the real spawn height. Checked in Play: the local player's Compy `LocalMeshVisual` (the low-poly model the client draws) is 3.49 x 6.60 x 7.78 with `VisualScale` 1.

**Rule.** Tier = `Config.SpeciesRarities`. Ground and Armored (and Elasmosaurus): height 6.6 x 1.1^(tier - 1). Fly: bulk (cube root of W x H x L), T-Rex bulk 8.12 at tier 5, 10% less per tier below. Water: length, T-Rex length 10.41 at tier 5, 10% less per tier below. Tolerance 2%. Data: `ScaleLadder.Sizing` and `ScaleLadder.Dino.species[..].{tier, basis, target}`; enforced by `tools/verify_scale_ladder.py`.

**Method.** Playtest build of this branch (`python tools/build.py --profile playtest`, own file `dtmp/sizes.rbxlx`), Play (Server), `LowPolyDinosLoaded = 22`, `LowPolyDinosFailed = 0`; `LowPolyDinos.clone(id)`, `ScaleTo(1)`, `Model:GetBoundingBox()` (template pose, wings as authored; the BD-471 method). Images from Studio `screen_capture`, play GUI hidden, lighting overridden for the lineup only (flat light, no cave grade).

Before = BD-471 (BD-225 scales), after = this change. Metric = the species' own basis (height for ground, bulk for fly, length for water). Sorted by unlock tier, then `Config.SpeciesOrder`.

| Tier | Species | Basis | Target | Scale before | Scale after | Height before | Height after | Metric before | Metric after | W x H x L after |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | compy | height | 6.60 | 2.2 | 2.2 | 6.60 | 6.60 | 6.60 | 6.60 | 3.49 x 6.60 x 7.69 |
| 1 | raptor | height | 6.60 | 2.1 | 1.65 | 8.40 | 6.60 | 8.40 | 6.60 | 3.49 x 6.60 x 7.74 |
| 1 | dimorphodon | bulk | 5.55 | 1.9 | 1.71 | 5.70 | 5.13 | 6.14 | 5.53 | 5.76 x 5.13 x 5.73 |
| 1 | gallimimus | height | 6.60 | 2.9 | 3.89 | 4.92 | 6.61 | 4.92 | 6.61 | 2.42 x 6.61 x 7.78 |
| 1 | microraptor | bulk | 5.55 | 1.7 | 1.52 | 5.10 | 4.56 | 6.21 | 5.56 | 7.11 x 4.56 x 5.29 |
| 2 | stegosaurus | height | 7.26 | 2.64 | 3.9 | 4.91 | 7.25 | 4.91 | 7.25 | 5.25 x 7.25 x 11.70 |
| 2 | archaeopteryx | bulk | 6.10 | 1.76 | 1.77 | 5.28 | 5.31 | 6.05 | 6.09 | 7.17 x 5.31 x 5.92 |
| 2 | pachycephalosaurus | height | 7.26 | 1.98 | 2.81 | 5.11 | 7.25 | 5.11 | 7.25 | 4.51 x 7.25 x 8.43 |
| 2 | parasaurolophus | height | 7.26 | 2.31 | 3.03 | 5.54 | 7.27 | 5.54 | 7.27 | 5.30 x 7.27 x 9.09 |
| 2 | pteranodon | bulk | 6.10 | 2.31 | 1.54 | 6.93 | 4.62 | 9.12 | 6.08 | 7.07 x 4.62 x 6.89 |
| 3 | triceratops | height | 7.99 | 3.0 | 2.86 | 8.39 | 8.00 | 8.39 | 8.00 | 5.79 x 8.00 x 8.58 |
| 3 | baryonyx | height | 7.99 | 2.42 | 3.11 | 6.22 | 7.99 | 6.22 | 7.99 | 3.99 x 7.99 x 9.33 |
| 3 | brachiosaurus | height | 7.99 | 3.87 | 2.91 | 10.63 | 8.00 | 10.63 | 8.00 | 3.73 x 8.00 x 8.73 |
| 3 | ichthyosaurus | length | 8.60 | 2.3 | 2.87 | 3.45 | 4.31 | 6.90 | 8.61 | 3.78 x 4.31 x 8.61 |
| 3 | plesiosaurus | length | 8.60 | 2.42 | 2.87 | 6.73 | 7.99 | 7.26 | 8.61 | 4.81 x 7.99 x 8.61 |
| 4 | ankylosaurus | height | 8.78 | 2.66 | 3.6 | 6.49 | 8.78 | 6.49 | 8.78 | 7.78 x 8.78 x 14.40 |
| 4 | elasmosaurus | height | 8.78 | 2.66 | 3.58 | 6.52 | 8.78 | 6.52 | 8.78 | 3.95 x 8.78 x 10.74 |
| 4 | quetzalcoatlus | bulk | 7.38 | 2.8 | 2.04 | 8.40 | 6.12 | 10.14 | 7.39 | 8.20 x 6.12 x 8.04 |
| 4 | therizinosaurus | height | 8.78 | 3.19 | 2.56 | 10.93 | 8.78 | 10.93 | 8.78 | 4.91 x 8.78 x 10.24 |
| 5 | T-Rex | height | 9.66 | 3.66 | 3.47 | 10.20 | 9.67 | 10.20 | 9.67 | 5.31 x 9.67 x 10.41 |
| 5 | mosasaurus | length | 10.41 | 3.22 | 3.47 | 3.29 | 3.55 | 9.66 | 10.41 | 3.37 x 3.55 x 10.41 |
| 5 | spinosaurus | height | 9.66 | 3.51 | 4.02 | 8.43 | 9.66 | 8.43 | 9.66 | 5.53 x 9.66 x 12.06 |

Images:
- `lineup-22-species-spawn-size-by-tier.jpg`: all 22 species at spawn size, three shelves in unlock order (tier colour bar, label = tier, name, height), a Compy reference with a 10 stud ruler (2 stud bands) at the start of each shelf. Same equal-size long lens style as BD-471 (`../2026-10-17-bd471/lineup-22-species-scale1.jpg`, which stays as the before image).
- `gate-compy-triceratops-trex.jpg`: Compy (tier 1), Triceratops (tier 3) and T-Rex (tier 5) in front of the cave gate glow, from the hub side, real hub lighting, each dino at the hub scale 1.

Limits: the box is the template pose; fliers fold their wings in game (`LowPolyPose.FoldAngle`), so their real silhouette is narrower than the width here, the bulk rule uses the same template box on purpose so it is measurable offline. Not verified: phone, published server, camera framing, hitbox feel.
