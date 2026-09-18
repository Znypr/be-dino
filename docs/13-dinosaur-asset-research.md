# Dinosaur asset sourcing
Researched 2026-09-18. Budget €0. Source-page research only; archives, models, rigs and Studio imports have not been inspected or tested.

## Recommended sources
| Source | Advertised contents | License | Proposed use |
|---|---|---|---|
| [Quaternius Animated Dinosaur Pack](https://quaternius.com/packs/animateddinosaurs.html) | 6 animated models; FBX, OBJ, Blend | CC0 | First import candidate; cohesive starting collection |
| [Gobkit Dinosaur Pack](https://gobkit.itch.io/gobkit-free-dinosaur-pack) | 10 rigged GLB models; idle, attack, death, walk | CC0 | Extra species after a style/import check |

Quaternius's [creator download page](https://quaternius.itch.io/animated-lowpoly-dinosaurs) lists idle, death, walk, run, attack and jump animations and a name-your-price download.
Its [bundle listing](https://poly.pizza/bundle/Animated-Dinosaur-Bundle-SmoLdBLO2K) identifies T-Rex, Triceratops, Stegosaurus, Velociraptor, Apatosaurus and Parasaurolophus. This is the same pack, not six additional models.

Gobkit adds Ankylosaurus, Spinosaurus, Carnotaurus, Pachycephalosaurus and Oviraptor beyond the overlapping T-Rex, Triceratops and Stegosaurus. Pterodactylus and Plesiosaurus are also included, but fall outside the ground-only first release. They are prehistoric reptiles rather than dinosaurs.
The creator's [free collection page](https://gobkit.com/freebies) provides a public download manifest. It contains conflicting descriptions of named clips versus one combined timeline, so inspect the actual files before assuming animation structure. Do not adopt its web-engine integration instructions for Roblox.

Deduplicated candidate inventory: 11 ground species, plus 2 out-of-scope creatures. Not a promise of 16 distinct species or 11 successful imports.

## Licensing
Both creator pages explicitly label these packs CC0. [Creative Commons explains](https://creativecommons.org/publicdomain/zero/1.0/) that CC0 permits copying, modification and commercial distribution without asking permission.
Record source URLs, downloaded LICENSE files and file hashes in the asset manifest. No paid assets, subscriptions or paid generation are proposed.
This recommendation extends the original procedural-only asset plan with licensed third-party source art; it does not copy Be Fish assets.

## Integration proposal
1. Download the Quaternius pack, preserve its license, and pick one biped (T-Rex or Velociraptor).
2. Import the FBX into a separate Studio test place under Znypr's account. Verify scale, orientation, texture/material appearance, bones and one walk animation.
3. Attach the imported visual to the tested controller; keep movement and cosmetic rig responsibilities separate.
4. Verify at small and large sizes, in two clients, and on phone. Record mesh/animation IDs and permissions.
5. Only then prepare the other five models in a batch.
6. Trial one Gobkit model beside the first pack before combining visual styles. If GLB is not accepted directly, export from Blender to FBX or supported glTF, preserving animation and textures.

[Roblox's Importer](https://create.roblox.com/docs/studio/importer) documents FBX/OBJ/glTF mesh import and rigging/animation support for FBX and glTF. OBJ is not our animated-character route. Import support does not establish that these particular rigs work without changes.

## Getting a larger collection
Start with 6 species, then target 11 after integration. Proposed later variants: base, Gold and a second owner-approved mutation would give 33 collectible forms, not 33 species. Only Gold is currently in first-test scope.
For genuinely new species, use original Blender modeling/scripts around a few compatible body families. Share rigs only where anatomy supports them; long-neck quadrupeds and bipeds should not be forced onto one skeleton.
Generate inventory portraits from imported models so icons match gameplay. Recolors/material changes should be tracked as mutations rather than counted as new species.

## Alternatives and tradeoffs
[BlendSwap dinosaur category](https://blendswap.com/3d/dinosaurs/3) contains additional candidates, but licenses and art styles vary per entry. Not bulk-approved for this project.
Prefer a coherent rigged pack to dozens of unrelated free models: adapting rigs, textures and proportions can cost more time than the download saves.
AI model generation is an optional future experiment, not a verified free production pipeline here. No paid generator or untested free-trial quota is on the launch path.

## Next actionable task
ART/DEV: one Quaternius biped import spike; QA: idle/walk, scale, multiplayer appearance and asset access; Znypr: Studio import/account actions unavailable in this environment.
Accept only after a real in-game demonstration. Keep existing procedural prototype as fallback.
