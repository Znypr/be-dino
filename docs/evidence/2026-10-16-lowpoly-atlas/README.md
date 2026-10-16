# Low-poly bake budget (BD-306), pattern polish (BD-307), tier readability (BD-308), denied-API fallbacks (BD-309)

Own temp copy of the playtest build (`tools/build.py --profile playtest`, then `Config.LowPolyDinos = true` patched into the copy only, never committed), owner's Studio on the owner's PC, 2026-10-16. Edit mode for the contact sheets (flat Edit lighting), Play Solo client for every budget number. All judged by the agent's eye only; owner eye check pending (BD-305). Not verified: phone, published place, multiplayer.

## Measurements (Play Solo client)

| Probe | Result |
|---|---|
| `CreateEditableImage` until nil, fresh client | 320 x 256 px = **80 MiB**; 5,119 x 64 px = 80 MiB: a **byte** budget, not a count |
| Same probe in Edit mode | 800 x 256 px (200 MiB) succeeded: Edit mode enforces no limit (the earlier "273 images" was an Edit-mode artefact) |
| `CreateEditableMeshAsync` of the Compy body (2,988 faces) | free budget 42.00 -> 39.00 MiB (**3 MiB, ~1 KiB per face**); `CreateMeshPartAsync` from it: no change; destroying the part: no change; destroying the mesh: back to 42.00 |
| Raptor body (714 faces) | 0.75 MiB |
| 27 Compy bodies alive at once | the 28th returns nil (the same shared budget) |
| 22 species, 7 parts each (ichthyosaurus 6) | 154,660 faces total; per species 2,798 (baryonyx) .. 9,710 (quetzalcoatlus); biggest single part 5,524 (ankylosaurus) |
| Atlas prototype (one 512 px image + remapped species meshes), 5 species | free budget 80 -> 42 MiB (5.5 .. 10.25 MiB per species); with 12 species 4 of 12 mesh sets denied, rejected |
| **Final: 12 distinct dinos (12 species x 12 gene sets), sized per-part bakes** | all 12 fully textured: **84 images, 9.75 MiB, budget free 80.00 -> 70.00 MiB**, 0 denials, total client memory 3,223 -> 3,375 MB, **38.5 s** for the whole batch with source reads throttled to 2 at a time (about 3 s per new dino; the cheap tint shows meanwhile) |
| 10 distinct dinos in Edit mode (sheet) | 70 images, 8.13 MiB, 8.4 s |
| Deny hook `LowPolyDenyEditable = "all"` (elasmosaurus, fresh species) | `LPLod = tint`, no image created |
| `"mesh"` (ichthyosaurus) | `LPLod = texture`, `hasPositions = false`: baked with the UV-space (jigsaw) pattern |
| `nil` (mosasaurus) | `LPLod = texture`, `hasPositions = true`: 3D pattern |
| Tier row (raptor red/gold spots): base / gold / emerald / diamond / gold with Calm motion | Plastic 0 / Metal 0.14 / Glass 0.10 / Glass 0.22 / Metal 0.14; sparkle rate 3.3 / 4.4 / 6.6 at raptor size; **no `LPTierSparkle` under Calm motion** |

## Pictures

| File | Shows |
|---|---|
| 00-atlas-probe-one-image-seven-parts.jpg | The rejected atlas prototype working in Edit mode: one 512 px image (each cell a flat colour) driving all seven remapped Compy parts. Kept as the record of what was measured. |
| 01-before-scales-freckles-islands-patches-overview.jpg | BEFORE (PR #165 code): Compy (white/blue) and Triceratops (green/teal) rows, left to right scales, freckles, islands, patches, blend 65. |
| 02-before-scales-freckles-closeup.jpg | BEFORE close-up: `07_diamond_scales` as a square lattice (zigzag), freckles small. |
| 03-scales-v1-corner-blobs-rejected.jpg | First staggered-scale attempt: the rim mask peaked at the gaps between four scales, so the quantile painted corner blobs. Rejected; the final metric takes the nearest scale over three rows. |
| 04-tiers-gold-aura-emerald-diamond-closeup.jpg | Gold (sparkle + `tidal` aura rig stacked), Emerald, Diamond raptors, flat Edit light, with the baked facet sheen. |
| 05-tiers-row-base-gold-emerald-diamond-calm.jpg | The tier row: base (left, cut), gold with aura, emerald, diamond, gold under Calm motion (right, cut: no sparkle). |
| 06-play-12-distinct-dinos-all-textured.jpg | Play Solo, game lighting: 12 distinct species x gene sets, all on their bakes (the player's own plain dino in front). |
| 07-play-deny-row-tint-jigsaw-3d.jpg | Play Solo, behind the foreground dinos: elasmosaurus on the tint (deny all), ichthyosaurus jigsaw stripes (deny mesh), mosasaurus 3D stripes (allowed). |
| 08-play-deny-mesh-uv-jigsaw-closeup.jpg | The deny-mesh ichthyosaurus: UV-space stripes chopped per facet, the documented fallback look. |
| 09-after-scales-v2-staggered-rims-freckles-closeup.jpg | AFTER: Compy (blue/gold) scales as staggered plump scales with continuous gold rims; Triceratops scales on the frill; Compy freckles right. |
| 10-after-sheet-scales-freckles-islands-patches-overview.jpg | AFTER overview: Compy and Triceratops rows, scales, freckles, islands, patches, spots at blend 35. |
| 11-after-patches-and-spots-blend35-closeup.jpg | AFTER: Compy bold patches (left) and round spots at blend 35 (right): small spots under the coverage curve, not blobs; Triceratops islands/patches behind. |

Honest notes: in flat Edit light the Gold/Emerald/Diamond difference is mostly the trim colour and a brighter facet contrast; the material gloss stays subtle (no rim Highlight added). Scales are computed in the side plane, so the back and belly show bands rather than scales. Nothing here was seen on a phone.
