# BD-515: eating happens at the mouth (2026-10-17)

Build: `python tools/build.py --profile playtest` of branch `claude/bd515-mouth-pickup` (own file `dtmp/mouth.rbxlx`, own Studio window), Play (client + server), a real run on the island (`RemoteEvent RequestStartRun`), `LowPolyDinos` on (22 loaded), weather cleared (`ProgressionService.adminStopWeather`). Images are Studio `screen_capture` only (default HUD, side camera set with the capture's `camera_position` / `look_at_position`; the game camera stands behind the dino and the body hides the berry, so a side view shows the mouth). Species and growth scale are set on the server (`Dinosaur.render` after setting `GrowthScore`, so the growth rule does not undo the scale when the berry is eaten).

How each "before / eaten" pair was made (a real server pickup, not an edit of the berry): the dino is posed head-first with the root at the exact distance that puts the HEAD POINT `radius + 0.6` studs from a berry (the berry is about 2 studs ahead of the nose), the root is held, then moved forward 0.25 stud at a time until `FoodService` hides the berry (about 3 steps, under 1 stud). The server tick (`Config.FoodTickSeconds` 0.08) decides, with the rate limits, the movement plausibility check and the pickup grid untouched. `MovementGuard` rolls back a teleport, so the pose is set while the run state is `Sanctuary` and then back to `Active`.

## Images

| Pair | Before (berry ahead of the nose) | Eaten (the moment it is gone) | Numbers at the eat |
| --- | --- | --- | --- |
| Compy, scale 1 | `compy-s1-before.jpg` | `compy-s1-eaten.jpg` | berry 2.06 from the head point (radius 2.26), 1.23 ahead of the nose, 5.11 from the root |
| Ankylosaurus, scale 1 (14.4 long) | `ankylosaurus-s1-before.jpg` | `ankylosaurus-s1-eaten.jpg` | 3.00 from the head point (radius 3.25), 1.17 ahead of the nose, 8.48 from the root |
| Ankylosaurus, scale 2 (28.8 long) | `ankylosaurus-s2-before.jpg` | `ankylosaurus-s2-eaten.jpg` | 4.87 (radius 5.03), 1.27 ahead of the nose, 15.68 from the root |
| Spinosaurus, scale 1 (12.1 long) | `spinosaurus-s1-before.jpg` | `spinosaurus-s1-eaten.jpg` | 2.78 (radius 2.93), 1.27 ahead of the nose, 7.31 from the root |
| Control: Ankylosaurus, berry under the chest | `ankylosaurus-s1-berry-under-chest-not-eaten.jpg` | the berry stays (1.5 s on top of it, root 0.00 from the berry) | the old rule ate this berry, the new one does not |

The old rule needed the berry within 2.25 studs of the ROOT: for the Ankylosaurus that is a berry 4.95 studs BEHIND its nose (under the front legs), the head passed over everything ahead of it.

## Real walk (Humanoid, WalkSpeed 12, not stepped)

Each species placed 14 studs behind a berry and told to walk straight through it (`Humanoid:MoveTo`); the server picked the berry up when:

| Species | Berry to head point | Radius | Berry to the nose | Berry to the root |
| --- | ---: | ---: | ---: | ---: |
| Compy | 1.36 | 2.25 | 0.53 | 4.37 |
| Ankylosaurus | 1.84 | 3.23 | 0.04 | 7.24 |
| Spinosaurus | 2.74 | 2.93 | 1.23 | 7.26 |

## Measured head data (Studio, the 22 low-poly templates at scale 1, template pose)

The `head` MeshPart of every template sits at the front of the body (its front edge is the model's front edge, `snout = length / 2`, for 21 of 22 species; Microraptor's template wings reach 0.33 stud further forward than its head). Raw head-part length along the body (it includes neck, crest or frill, so `Shared/MouthReach` clamps it to 20% to 25% of the body length): compy 1.65, triceratops 4.76, tyrannosaurus 5.13, raptor 2.80, stegosaurus 2.55, ankylosaurus 5.17, archaeopteryx 1.34, baryonyx 3.82, brachiosaurus 3.52, dimorphodon 3.06, elasmosaurus 4.38, gallimimus 2.52, ichthyosaurus 3.95, microraptor 0.32, mosasaurus 2.69, pachycephalosaurus 3.54, parasaurolophus 3.94, plesiosaurus 4.04, pteranodon 2.29, quetzalcoatlus 3.41, spinosaurus 4.54, therizinosaurus 2.75. They are stored in `ScaleLadder.Dino.species[id].snout` and `.headLength`.

Not verified: a phone, a published server, a second player, flying and swimming species in a real run (offline only), the food-per-minute change (new row BD-521).
