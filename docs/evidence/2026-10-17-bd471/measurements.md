# BD-471: species heights at scale 1, measured in Studio (2026-10-17)

Build: `python tools/build.py --profile playtest` (branch `claude/bd471-measure-heights`, from `claude/bd407-scale-ladder` plus origin/main), own file `dtmp/bd471.rbxlx`, Play (Server), after `LowPolyDinosLoaded = 22`, `LowPolyDinosFailed = 0`.

Method: for each species in `Config.SpeciesOrder`, `LowPolyDinos.clone(id)` (the model `ResourceModels.clone` hands to `DinosaurVisual.render`), `ScaleTo(1)`, then the `Model:GetBoundingBox()` size (pivot aligned, so width = X, height = Y, length = Z in the template pose; no animation, no accessories). Studs, 2 decimals.

Low-poly (LowPolyDinos on, the ladder rows) against the old ESTIMATE (`scale x 2.84`). The last column is the legacy model with the flag off (reference only).

| Species | Width | Height | Length | Estimate | Error | Legacy W x H x L |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| compy | 3.49 | 6.60 | 7.69 | 6.6 | +0% | 4.60 x 5.56 x 7.79 |
| triceratops | 6.07 | 8.39 | 9.00 | 8.5 | -1% | 6.21 x 4.50 x 7.43 |
| tyrannosaurus | 5.60 | 10.20 | 10.98 | 10.3 | -1% | 4.68 x 5.56 x 7.80 |
| raptor | 4.44 | 8.40 | 9.85 | 6.0 | +40% | 3.94 x 5.00 x 8.68 |
| stegosaurus | 3.56 | 4.91 | 7.92 | 7.5 | -35% | 5.57 x 4.95 x 7.46 |
| ankylosaurus | 5.75 | 6.49 | 10.64 | 7.6 | -15% | 5.42 x 5.37 x 8.09 |
| archaeopteryx | 7.12 | 5.28 | 5.89 | 5.0 | +6% | 4.14 x 3.00 x 5.04 |
| baryonyx | 3.10 | 6.22 | 7.26 | 6.9 | -10% | 2.08 x 3.00 x 6.83 |
| brachiosaurus | 4.97 | 10.63 | 11.61 | 11.0 | -3% | 1.39 x 4.00 x 5.10 |
| dimorphodon | 6.40 | 5.70 | 6.36 | 5.4 | +6% | 4.33 x 3.00 x 5.35 |
| elasmosaurus | 2.94 | 6.52 | 7.98 | 7.6 | -14% | 5.83 x 3.00 x 12.73 |
| gallimimus | 1.80 | 4.92 | 5.80 | 4.9 | +0% | 1.79 x 3.00 x 5.61 |
| ichthyosaurus | 3.03 | 3.45 | 6.90 | 6.5 | -47% | 4.97 x 3.00 x 9.46 |
| microraptor | 7.95 | 5.10 | 5.92 | 4.8 | +6% | none |
| mosasaurus | 3.13 | 3.29 | 9.66 | 9.1 | -64% | none |
| pachycephalosaurus | 3.18 | 5.11 | 5.94 | 5.6 | -9% | none |
| parasaurolophus | 4.04 | 5.54 | 6.93 | 6.6 | -16% | none |
| plesiosaurus | 4.05 | 6.73 | 7.26 | 6.9 | -2% | none |
| pteranodon | 10.60 | 6.93 | 10.34 | 6.6 | +5% | none |
| quetzalcoatlus | 11.26 | 8.40 | 11.03 | 8.0 | +5% | none |
| spinosaurus | 4.83 | 8.43 | 10.53 | 10.0 | -16% | none |
| therizinosaurus | 6.11 | 10.93 | 12.76 | 9.1 | +20% | none |

Legacy column: the model a client draws with the flag off (`AuthoredCreatures.clone` where present, else the `Resources` model; raw bounding box before any `ScaleTo`). Nine species have no legacy model at all (microraptor, mosasaurus, pachycephalosaurus, parasaurolophus, plesiosaurus, pteranodon, quetzalcoatlus, spinosaurus, therizinosaurus). Reference only; the ladder is the low-poly table.

Notes:
- Heights include whatever the template pose raises: quetzalcoatlus, pteranodon, microraptor, archaeopteryx and dimorphodon have wings up or out (their width is a wingspan, 7 to 11 studs).
- Compy 6.60, Gallimimus 4.92 and Tyrannosaurus 10.20 match the earlier BD-329/BD-337/docs/108 boxes within 0.1.
- Lineup images: `lineup-22-species-scale1.jpg` (long lens, equal size) and `lineup-22-species-scale1-perspective.jpg`. Sorted by height in three rows, a Compy (6.6) at the start of each row, a 10 stud ruler (2 stud bands) beside each Compy, label = species and height.
