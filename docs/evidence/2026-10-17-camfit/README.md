# BD-500 / BD-471: default camera framing and size audit for the BD-232 species sizes (2026-10-17)

Build: `python tools/build.py --profile playtest` of branch `claude/bd500-camfit` (own file `dtmp/camfit.rbxlx`, own Studio window), Play (client + server), a real run on the island (`RunLifecycle.requestStart`), weather cleared, `LowPolyDinos` on (22 loaded). Viewport 1140 x 785, FOV 70, pitch about -15 (the stock Custom camera). Species and growth scale set on the server (`Dinosaur.render` with `HubScaleRules.islandScale`); the camera was pulled to its minimum zoom (`CameraMaxZoomDistance = CameraMinZoomDistance`, then restored to 110), which is the default gameplay camera. Images are Studio `screen_capture` only.

## 1. Does the camera read the species size? (before)

No. `Bootstrap.client.luau` set `CameraMinZoomDistance = 12 x VisualScale` and the aim lift `2 x (VisualScale - 1)`: the growth step only. docs/139 s3.2 expected every dino to fill the same share of the screen at every size; that was true only for one body shape. Measured before (share of the screen height, the dino's real box projected; HUD = a HUD box over the dino):

| Species | Scale 1 | Scale 2 | Scale 4 | Problem |
| --- | ---: | ---: | ---: | --- |
| Compy | 40% | 41% | 43% | none (the reference) |
| Triceratops | 58% | 58% | 58% | fills a bit more, ok |
| T-Rex | 72% | 72% | 71% | head behind the HUD title at scale 2 (top 53 px) and 4 (top 18 px) |
| Ankylosaurus (14.4 long) | 79% | 89% | 95% | bottom edge off screen at spawn (-16 px), HUD over the dino, off the top at scale 4 (-85 px) |
| Spinosaurus (12.1 long, tall sail) | 108% | 121% | 128% | out of the frame at every size |
| Stegosaurus, Elasmosaurus, Therizinosaurus | 61% to 71% | same | same | heads at the HUD (top 70 to 178 px at scale 4) |
| Raptor, Gallimimus, fliers, swimmers | 26% to 46% | same | same | fine (small) |

Images (before): `before-compy-s1/s2/s4.jpg`, `before-triceratops-s1/s2/s4.jpg`, `before-trex-s1/s2/s4.jpg`, `before-ankylosaurus-s1/s2/s4.jpg`, `before-spinosaurus-s1.jpg`.

## 2. Fix

`src/shared/CameraFraming.luau` (pure numbers) and `src/client/CameraFit.luau` (measures the local dino once per model, at its first sighting, in the root's frame: no per-frame measuring, no walk-animation jitter):

- size = sqrt(height^2 + (0.65 x length)^2) of the real model box at the drawn size; the minimum zoom is `12 x max(scale, size / Compy size)`, never closer than the old `12 x scale`, capped at 75 studs (the CameraOcclusion range is 80);
- aim lift = `2 / 6.6` stud per stud of height above the Compy, so a Compy keeps exactly `2 x (scale - 1)`.

Calibration: a Studio fit of the distance at which each species fills 45% to 50% of the screen with the dino top clear of the HUD (needed 1.0 to 1.6 x the old distance); the 0.65 length weight is the least-squares value over the 22 boxes (under-framing penalised 3x). `tools/verify_camera_framing.py` (in CI) keeps the module and the sweep below in step.

## 3. After (all 22 species, scale 1, 2, 4, default camera)

Measured minimum zoom, share of the screen height and the dino top (px from the top of a 785 px screen), from the sweep; every row in frame, the ground ahead of the dino visible (the bottom margin of 71 px or more is the dino's feet, the ground in front of it is above the horizon line at y = 242), no HUD box over the dino.

| Species | Scale 1 zoom / fill / top | Scale 2 | Scale 4 |
| --- | --- | --- | --- |
| compy | 12.0 / 40% / 278 | 24.1 / 41% / 224 | 48.2 / 43% / 184 |
| triceratops | 14.4 / 47% / 259 | 28.8 / 47% / 211 | 57.7 / 46% / 190 |
| tyrannosaurus | 17.3 / 46% / 242 | 34.6 / 45% / 204 | 69.1 / 45% / 184 |
| ankylosaurus | 18.8 / 44% / 266 | 37.7 / 42% / 241 | 75.0 / 41% / 222 |
| spinosaurus | 18.0 / 53% / 255 | 36.1 / 54% / 199 | 72.1 / 56% / 165 |
| stegosaurus | 15.3 / 46% / 285 | 30.6 / 44% / 247 | 61.1 / 45% / 211 |
| elasmosaurus | 16.5 / 47% / 260 | 33.0 / 46% / 219 | 66.1 / 46% / 196 |
| therizinosaurus | 16.1 / 42% / 258 | 32.1 / 42% / 209 | 64.3 / 44% / 178 |
| raptor, gallimimus, archaeopteryx, dimorphodon, microraptor, pteranodon, quetzalcoatlus, ichthyosaurus, mosasaurus | 12.0 to 12.1 (unchanged) | 24.0 to 24.3 | 48.0 to 48.5 |
| the other 5 (baryonyx, brachiosaurus, pachycephalosaurus, parasaurolophus, plesiosaurus) | 13.4 to 14.7 | 26.8 to 29.5 | 53.6 to 58.9 |

All 66 rows are in `tools/verify_camera_framing.py` (`STUDIO`). Range of the fill: 26% to 56%.

Images (after): `after-compy-s1/s2/s4.jpg`, `after-triceratops-s1/s2/s4.jpg`, `after-trex-s1/s2/s4.jpg`, `after-ankylosaurus-s1/s2/s4.jpg`, `after-spinosaurus-s1.jpg`.

Not fixed (rare, new row BD-513): BIG at growth scale 4.8 hits the 75 stud cap. `after-spinosaurus-big-4.8-capped.jpg` (72% of the screen height, the sail behind the HUD banner) and `after-trex-big-4.8-capped.jpg` (51%, head at the hint line).

## 4. Hitbox, reach and clearance audit (code plus Studio)

| Thing | Uses species size? | Finding |
| --- | --- | --- |
| Torso collider (`MovementEnvelope.collider`, `Dinosaur.placeCollider`) | No: 2.6 x 3.2 x growth scale for every species | Nothing can wedge on the species size; the visual overlaps walls by a few studs (BD-516, design question) |
| Cave gate 30 x 20, tunnel 22 wide x 30 high, path 8 wide, nest and station pads | Not by species (the hub dino is always 1x, BD-480) | Largest hub bodies: 8.1 wide (Ankylosaurus), 9.7 tall, 14.7 long: clear by 3.7x (gate), 2.7x (tunnel) |
| Walk test in the hub (Studio) | n/a | Spinosaurus, Ankylosaurus, Stegosaurus, Gallimimus each walked from the Heart room to the cave gate, 117 studs in 5.25 s (walk speed 22), no stop; images `hub-ankylosaurus-tunnel.jpg`, `hub-ankylosaurus-at-cave-gate.jpg` |
| Stepping stones (6 x 6, in the lava basin) | n/a | They sit inside the lava fence (6 rim colliders, gaps 3.1 studs wide), not on a walking route |
| Food pickup `FoodPickupRadius 2.25 + 0.75 (s - 1)` | No (root distance) | Design question BD-515 |
| Predation `5.5 + 1.25 (s - 1)` | No (root distance) | BD-515 |
| Combat bite range and body radius (`CombatService.radiusOf`, server `GetExtentsSize`) | Partly: reads the server model, which is the LEGACY shell, not the low-poly | Compy 4.2 x 5.6 x 6.1, 15 species the same 4.2 x 5.6 x 9.8 fallback box (radius 4.9); BD-514; CombatEnabled is off |
| NPC predators (raptor, baryonyx, tyrannosaurus, spinosaurus; combat flag off, none spawn in the playtest build) | Yes: low-poly clone x 1.0 to 1.3, radius = max(X, Z) / 2 (clamp 1 to 14) | Raptor -21%, Baryonyx +28%, T-Rex -5%, Spinosaurus +15% as drawn; wild Spinosaurus up to 15.7 long (radius 7.8) |

## 5. Fliers (BD-232 template pose vs in game)

Template pose (wings spread) is the BD-232 measuring box; in game `LowPolyPose` folds the wings (`FoldAngle`) at rest and in a walk, and opens them in a leap. Rest box measured in game: Quetzalcoatlus 6.2 x 6.0 x 8.2 (template 8.2 wide), Pteranodon 4.9 x 5.1 x 7.0 (7.1), Dimorphodon 4.0 (5.8), Microraptor 5.7 (7.1), Archaeopteryx 5.5 (7.2): 24% to 31% narrower, so the bulk at rest is 8% to 9% below the rule (still rising with the unlock tier; BD-517). Images: `flier-quetzalcoatlus-rest-behind-s1.jpg`, `flier-quetzalcoatlus-leap-behind-s1.jpg`, `flier-quetzalcoatlus-rest-side-s1.jpg`, `flier-quetzalcoatlus-jump-side-s1.jpg`, `flier-pteranodon-rest-side-s1.jpg`, `flier-pteranodon-leap-side-s1.jpg`. The folded wings read as shoulder wings, nothing pokes through the body, the leap pose spreads them wider.

Limits: Studio on one PC; phone and the published server not tested; hit feel not tested (combat is off in the playtest profile); the sweep sets the camera by pulling it to the minimum zoom, a player can zoom out to 110.
